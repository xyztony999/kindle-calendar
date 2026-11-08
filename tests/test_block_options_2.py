"""积木自定义二期·轮 1：显示单位、中国 AQI、页眉日期格式、文本选项、今日标记、字段分组。"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

try:
    from test_web_admin import PASSWORD, _offline_network
except ImportError:  # 以 tests.xxx 模块名直接运行时
    from tests.test_web_admin import PASSWORD, _offline_network

from PIL import Image, ImageDraw

from server import aqi as aqi_mod
from server.aqi import AirQuality, cn_aqi_from, cn_level, cn_level_en, iaqi, _BP
from server.app import create_app
from server.data import build_payload
from server.datefmt import header_date_text, render_template, template_error
from server.fields import field_text
from server.layout import FIELD_DEFS, _validate_block, block_options, field_group, field_groups_catalog, system_options_catalog
from server.locale import page_label
from server.render import style
from server.render.pages import common, detail, month, today
from server.render.regions import Rect
from server.settings import defaults_from_config, normalize, validate
from server.units import aqi_band, aqi_view, beaufort, fmt_temp, fmt_temp_delta, fmt_wind
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData

DEPLOY = {"location_name": "北京", "latitude": 39.9, "longitude": 116.4, "timezone": "Asia/Shanghai"}
F = {"units": {"temp": "f"}}


def _payload(day: int = 3, temperature: float = 20, apparent: float | None = None, aqi: AirQuality | None = None, settings: dict | None = None) -> dict:
    tz = ZoneInfo("Asia/Shanghai")
    now = datetime(2026, 11, day, 16, 0, tzinfo=tz)
    weather = WeatherData(
        CurrentWeather(temperature, 50, 5, 0, "晴", apparent),
        [DailyForecast(f"2026-11-{day:02d}", 24, 14, 0, "晴")],
        [HourlyPoint(f"2026-11-{day:02d}T16:00", 20, 0, 0)],
    )
    with patch("server.quotes.get_quote", return_value={"text": "测试一言", "from": "单测"}):
        return build_payload({"latitude": 39.9, "longitude": 116.4, "location_name": "北京"}, weather, now, aqi=aqi, settings=settings)


def _ink(img, box=None) -> int:
    px = img.load()
    x0, y0, x1, y1 = box or (0, 0, img.width, img.height)
    return sum(1 for y in range(y0, y1) for x in range(x0, x1) if px[x, y] < 128)


class UnitsFormatTest(unittest.TestCase):
    def test_negative_zero_never_shown(self):
        for value in (-0.4, -0.49, -0.5, -0.0):
            self.assertEqual(fmt_temp(value, None), "0°", value)
        self.assertEqual(fmt_temp(-0.51, None), "-1°")

    def test_half_up_rounding(self):
        self.assertEqual(fmt_temp(22.5, None), "23°")
        self.assertEqual(fmt_temp(22.49, None), "22°")

    def test_fahrenheit(self):
        self.assertEqual(fmt_temp(0, F), "32°")
        self.assertEqual(fmt_temp(100, F), "212°")
        self.assertEqual(fmt_temp(-40, F), "-40°")
        self.assertEqual(fmt_temp(-17.78, F), "0°")
        # 温差只乘 9/5：6℃ 降温 = 10.8℉ → 11°
        self.assertEqual(fmt_temp_delta(6, F), "11°")
        self.assertEqual(fmt_temp_delta(6, None), "6°")

    def test_missing_values_blank(self):
        self.assertEqual(fmt_temp(None, None), "")
        self.assertEqual(fmt_temp(True, None), "")
        self.assertEqual(fmt_wind(None, None), "")

    def test_wind_units(self):
        self.assertEqual(fmt_wind(12.5, None), "13 km/h")
        self.assertEqual(fmt_wind(20, {"units": {"wind": "ms"}}), "5.6 m/s")
        self.assertEqual(fmt_wind(20, {"units": {"wind": "bft"}}), "4级")
        self.assertEqual(fmt_wind(20, {"units": {"wind": "bft"}, "ui_lang": "en"}), "Force 4")

    def test_beaufort_boundaries(self):
        self.assertEqual(beaufort(0.0), 0)
        self.assertEqual(beaufort(0.29 * 3.6), 0)
        self.assertEqual(beaufort(0.3 * 3.6), 1)
        self.assertEqual(beaufort(10.8 * 3.6), 6)
        self.assertEqual(beaufort(32.7 * 3.6), 12)
        self.assertEqual(beaufort(200), 12)

    def test_unknown_units_fall_back(self):
        self.assertEqual(fmt_temp(10, {"units": {"temp": "k"}}), "10°")
        self.assertEqual(fmt_wind(10, {"units": "bogus"}), "10 km/h")


class ChinaAqiTest(unittest.TestCase):
    def test_iaqi_breakpoints(self):
        self.assertEqual(iaqi(0, _BP["pm25_24h"]), 0)
        self.assertEqual(iaqi(35, _BP["pm25_24h"]), 50)
        self.assertEqual(iaqi(75, _BP["pm25_24h"]), 100)
        self.assertEqual(iaqi(80, _BP["pm25_24h"]), 107)
        self.assertEqual(iaqi(600, _BP["pm25_24h"]), 500)
        self.assertEqual(iaqi(100, _BP["pm10_24h"]), 75)
        self.assertEqual(iaqi(180, _BP["o3_1h"]), 75)
        self.assertEqual(iaqi(4, _BP["co_1h"]), 40)

    def test_exact_breakpoints_never_round_up(self):
        for key, bps in _BP.items():
            for index, bp in enumerate(bps[1:], start=1):
                self.assertEqual(iaqi(bp, bps), (0, 50, 100, 150, 200, 300, 400, 500)[index], (key, bp))

    def test_aqi_is_max_of_parts(self):
        self.assertEqual(cn_aqi_from(pm2_5=80, pm10=100, o3=180, no2=40, so2=10, co=4000), 107)
        self.assertEqual(cn_aqi_from(pm2_5=10, pm10=20, o3=250), 125)
        self.assertIsNone(cn_aqi_from(pm2_5=10))
        # SO2 1 小时浓度 >800 改用 24 小时限值表
        self.assertEqual(cn_aqi_from(pm2_5=0, pm10=0, so2=1600), 300)

    def test_levels(self):
        self.assertEqual([cn_level(v) for v in (0, 50, 51, 100, 101, 150, 151, 200, 201, 300, 301, 500)],
                         ["优", "优", "良", "良", "轻度污染", "轻度污染", "中度污染", "中度污染", "重度污染", "重度污染", "严重污染", "严重污染"])
        self.assertEqual(cn_level_en("轻度污染"), "Light")

    def test_indices_long_value_stays_inside_card(self):
        # 英文美标「Very Unhealthy」与国标等级都不得向左冲出指数卡（既有溢出一并修复）
        quality = AirQuality(us_aqi=250, level="重度")
        payload = dict(_payload(aqi=quality), ui_lang="en")
        img = detail.render_indices(payload, Rect(0, 0, 646, 350), "")
        card_w = (646 - 16 - 2) // 2
        aqi_card_left = card_w + 16  # 第 6 张卡在右列
        row_top = 2 * ((350 - 32 - 2) // 3 + 16)
        self.assertEqual(_ink(img, (aqi_card_left - 14, row_top + 8, aqi_card_left - 2, 350)), 0)

    def test_fetch_failure_returns_none_without_name_error(self):
        # 回归：b0ba151 起 except 分支引用未定义的 log，失败时抛 NameError 打断整条天气刷新
        with patch("server.aqi.requests.get", side_effect=TimeoutError("timed out")):
            self.assertIsNone(aqi_mod.fetch_aqi(39.9, 116.4))
        self.assertFalse(aqi_mod.health()["ok"])
        self.assertIn("timed out", aqi_mod.health()["error"])

    def test_fetch_parses_pollutants(self):
        resp = MagicMock()
        resp.json.return_value = {"current": {"us_aqi": 160, "pm2_5": 80, "pm10": 100, "ozone": 180,
                                              "nitrogen_dioxide": 40, "sulphur_dioxide": 10, "carbon_monoxide": 4000}}
        with patch("server.aqi.requests.get", return_value=resp) as get:
            result = aqi_mod.fetch_aqi(39.9, 116.4)
        self.assertIn("pm2_5", get.call_args.kwargs["params"]["current"])
        self.assertEqual((result.us_aqi, result.level, result.cn_aqi, result.cn_level), (160, "中度", 107, "轻度污染"))

    def test_view_follows_standard(self):
        quality = AirQuality(us_aqi=160, level="中度", pm2_5=80, pm10=100, cn_aqi=107, cn_level="轻度污染")
        self.assertEqual(aqi_view(_payload(aqi=quality)), (160, "中度"))
        cn = _payload(aqi=quality, settings=_settings(units={"aqi": "cn"}))
        self.assertEqual(aqi_view(cn), (107, "轻度污染"))
        self.assertEqual(field_text(cn, "aqi.value"), "107")
        self.assertEqual(field_text(cn, "aqi.level"), "轻度污染")
        # 国标数据缺失时回退美标
        no_cn = _payload(aqi=AirQuality(us_aqi=42, level="优"), settings=_settings(units={"aqi": "cn"}))
        self.assertEqual(aqi_view(no_cn), (42, "优"))

    def test_band(self):
        self.assertEqual([aqi_band(v) for v in (0, 50, 51, 100, 101, 200, 201, 300, 301)], [0, 0, 1, 1, 2, 3, 4, 4, 5])

    def test_sun_card_renders_cn_levels(self):
        # 旧实现按美标中文等级名查表定位刻度段，国标等级名会抛 ValueError
        quality = AirQuality(us_aqi=160, level="中度", pm2_5=80, pm10=100, cn_aqi=107, cn_level="轻度污染")
        payload = _payload(aqi=quality, settings=_settings(units={"aqi": "cn"}))
        img = today.render_sun(payload, Rect(0, 0, 646, 132), "")
        self.assertGreater(_ink(img, (430, 0, 646, 132)), 0)


def _settings(**overrides) -> dict:
    base = defaults_from_config(DEPLOY)
    base.update(overrides)
    return normalize(base)


class SettingsUnitsTest(unittest.TestCase):
    def test_defaults_and_legacy_config(self):
        legacy = defaults_from_config(DEPLOY)
        legacy.pop("units")
        self.assertEqual(validate(legacy), [])
        self.assertEqual(normalize(legacy)["units"], {"temp": "c", "wind": "kmh", "aqi": "us"})

    def test_invalid_units_rejected(self):
        body = defaults_from_config(DEPLOY)
        body["units"] = {"temp": "k", "wind": "kmh"}
        codes = {(item["field"], item["code"]) for item in validate(body)}
        self.assertIn(("units.temp", "UNITS_INVALID"), codes)
        body["units"] = "f"
        self.assertIn(("units", "UNITS_INVALID"), {(item["field"], item["code"]) for item in validate(body)})

    def test_payload_carries_units(self):
        payload = _payload(settings=_settings(units={"temp": "f", "wind": "bft"}))
        self.assertEqual(payload["units"], {"temp": "f", "wind": "bft", "aqi": "us"})
        self.assertEqual(_payload()["units"], {"temp": "c", "wind": "kmh", "aqi": "us"})


class RenderUnitsTest(unittest.TestCase):
    RECT = Rect(0, 0, 646, 244)

    def test_feels_minus_zero_renders_as_zero(self):
        # 体感 -0.3 与 0.2 都应显示「0°」：整块像素完全一致
        a = today.render_weather(_payload(temperature=-0.3, apparent=-0.3), self.RECT, "", options={"show_feels": True})
        b = today.render_weather(_payload(temperature=0.2, apparent=0.2), self.RECT, "", options={"show_feels": True})
        self.assertEqual(a.tobytes(), b.tobytes())
        self.assertEqual(field_text(_payload(apparent=-0.3), "weather.apparent"), "0°")

    def test_fahrenheit_changes_render(self):
        c = today.render_weather(_payload(), self.RECT, "")
        f = today.render_weather(_payload(settings=_settings(units={"temp": "f"})), self.RECT, "")
        self.assertNotEqual(c.tobytes(), f.tobytes())
        self.assertEqual(field_text(_payload(settings=_settings(units={"temp": "f"})), "weather.temperature"), "68°")


class HeaderDateTest(unittest.TestCase):
    DAY = date(2026, 11, 8)

    def test_presets(self):
        expect = {
            "cn": ("十一月八", "8 Nov"),
            "md": ("11月8日", "Nov 8"),
            "ymd": ("2026年11月8日", "8 November 2026"),
            "dot": ("11.08", "11.08"),
        }
        for fmt, (zh, en) in expect.items():
            self.assertEqual(header_date_text(fmt, self.DAY, False), zh)
            self.assertEqual(header_date_text(fmt, self.DAY, True), en)

    def test_template(self):
        self.assertEqual(render_template("{M}月{D}日 周{W}", self.DAY, False), "11月8日 周日")
        self.assertEqual(render_template("{Y}.{MM}.{DD}", date(2026, 3, 5), False), "2026.03.05")
        self.assertEqual(render_template("{CM}月{CD}日", date(2026, 12, 31), False), "十二月三十一日")
        self.assertEqual(render_template("{CM}/{CD} {W}", self.DAY, True), "11/8 Sun")
        self.assertEqual(template_error("{M}月{X}"), "{X}")
        self.assertEqual(template_error("{M}月{D}日 {"), "{")
        # 输入框截断留下的残缺占位（如「周{W」）也要报错，不能当普通文字放过
        self.assertEqual(template_error("{M}月{D}日 周{W"), "{W")
        self.assertIsNone(template_error("{Y}年{M}月{D}日 周{W}"))
        # 自定义但模板为空或非法 → 按默认 cn
        self.assertEqual(header_date_text("custom", self.DAY, False, ""), "十一月八")
        self.assertEqual(header_date_text("custom", self.DAY, False, "{X}"), "十一月八")

    def test_template_validation(self):
        def errors(options):
            details: list = []
            block = {"widget": "header", "id": "header", "x": 0, "y": 122, "w": 646, "h": 78, "z": 0, "options": options}
            _validate_block(block, 0, 0, details, set(), set(), set(), {})
            return [d["message"] for d in details]

        self.assertEqual(errors({"date_format": "custom", "date_template": "{M}月{D}日 周{W}"}), [])
        self.assertEqual(errors({"date_template": "{Y}年{M}月{D}日 周{W}"}), [])
        self.assertTrue(any("{X}" in m for m in errors({"date_template": "{X}"})))
        self.assertTrue(any("24" in m for m in errors({"date_template": "1" * 25})))
        self.assertTrue(errors({"date_template": 5}))
        self.assertTrue(errors({"date_format": "weird"}))
        self.assertEqual(block_options("header", {"date_template": "{X}"})["date_template"], "")

    def test_header_render_uses_format(self):
        payload = _payload(day=8)
        rect = Rect(0, 0, 646, 78)
        cn = common.render_header(payload, rect, "", page="today")
        md = common.render_header(payload, rect, "", page="today", options={"date_format": "md"})
        self.assertNotEqual(_ink(cn, (0, 0, 280, 40)), _ink(md, (0, 0, 280, 40)))
        # 默认（未配置）与显式 cn 像素一致
        explicit = common.render_header(payload, rect, "", page="today", options={"date_format": "cn"})
        self.assertEqual(cn.tobytes(), explicit.tobytes())

    def test_long_template_shrinks_beside_tabs(self):
        payload = _payload(day=8)
        rect = Rect(0, 0, 646, 78)
        long = {"date_format": "custom", "date_template": "{Y}年{M}月{D}日 星期{W}"}

        def first_glyph_height(img):
            px = img.load()
            rows = [y for y in range(0, 40) for x in range(0, 16) if px[x, y] < 128]
            return max(rows) - min(rows)

        roomy = common.render_header(payload, rect, "", page="today", options={**long, "show_tabs": False})
        tight = common.render_header(payload, rect, "", page="today", options=long)
        self.assertLess(first_glyph_height(tight), first_glyph_height(roomy))

    def test_extreme_template_never_reaches_tabs(self):
        payload = _payload(day=8)
        rect = Rect(0, 0, 646, 78)
        extreme = {"date_format": "custom", "date_template": "{Y}" * 8, "show_lunar": False, "show_notes": False}
        img = common.render_header(payload, rect, "", page="today", options=extreme)
        draw = ImageDraw.Draw(Image.new("L", (rect.w, rect.h)))
        f_page = style.get_font(20, "")
        tabs_x = rect.w - sum(style.tracked_width(draw, page_label(p, payload), f_page, 2) + 46 for p in payload["pages"])
        # 页签圆点紧左侧的留白带不得出现日期墨迹（缩字到下限后截断加省略号）
        self.assertEqual(_ink(img, (tabs_x - 6, 4, tabs_x, 40)), 0)


class TodayMarkTest(unittest.TestCase):
    RECT = Rect(0, 0, 646, 730)
    CELL = (94, 166, 182, 240)  # 11 月 3 日格（周二）

    def _digit_box(self):
        # 今日=5 时 3 号格只有数字，取其墨水包围盒推算标记几何
        px = month.render_grid(_payload(day=5), self.RECT, "").load()
        pts = [(x, y) for y in range(self.CELL[1], self.CELL[3]) for x in range(self.CELL[0], self.CELL[2]) if px[x, y] < 128]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1

    def test_marks(self):
        payload = _payload(day=3)
        circle = month.render_grid(payload, self.RECT, "")
        explicit = month.render_grid(payload, self.RECT, "", options={"today_mark": "circle"})
        box = month.render_grid(payload, self.RECT, "", options={"today_mark": "box"})
        fill = month.render_grid(payload, self.RECT, "", options={"today_mark": "fill"})
        self.assertEqual(circle.tobytes(), explicit.tobytes())
        x0, y0, x1, y1 = self._digit_box()
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        r = max(x1 - x0, y1 - y0) // 2 + 9
        corner = (cx - r - 1, cy - r - 1, cx - r + 6, cy - r + 6)
        self.assertGreater(_ink(box, corner), 0, "box mark must have ink at its corner")
        self.assertEqual(_ink(circle, corner), 0, "circle mark must leave the corner blank")
        self.assertGreater(_ink(fill, self.CELL), 2 * _ink(circle, self.CELL), "filled mark must be solid")


class FieldGroupTest(unittest.TestCase):
    def test_groups_contiguous_in_catalog_order(self):
        groups = [field_group(item[0]) for item in FIELD_DEFS]
        runs = [g for i, g in enumerate(groups) if i == 0 or groups[i - 1] != g]
        self.assertEqual(len(runs), len(set(runs)), runs)
        self.assertEqual(runs, [item["key"] for item in field_groups_catalog("zh") if item["key"] in runs])

    def test_every_group_has_label(self):
        keys = {item["key"] for item in field_groups_catalog("en")}
        self.assertTrue({field_group(item[0]) for item in FIELD_DEFS} <= keys)


class AdminApiUnitsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SETTINGS_PATH"] = str(Path(self.tmp.name) / "settings.json")
        os.environ["ADMIN_PASSWORD"] = PASSWORD
        self.patches = _offline_network()
        for item in self.patches:
            item.start()
        self.client = create_app().test_client()
        self.headers = {"X-Requested-With": "kindle-admin", "Content-Type": "application/json"}
        self.client.post("/admin/api/login", json={"password": PASSWORD}, headers=self.headers)

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.tmp.cleanup()

    def test_units_roundtrip_and_validation(self):
        current = self.client.get("/admin/api/settings").get_json()["data"]["settings"]
        self.assertEqual(current["units"], {"temp": "c", "wind": "kmh", "aqi": "us"})
        current["units"] = {"temp": "f", "wind": "bft", "aqi": "cn"}
        saved = self.client.post("/admin/api/settings/save", json=current, headers=self.headers)
        self.assertEqual(saved.status_code, 200)
        reloaded = self.client.get("/admin/api/settings").get_json()["data"]["settings"]
        self.assertEqual(reloaded["units"], {"temp": "f", "wind": "bft", "aqi": "cn"})
        reloaded["units"]["wind"] = "knots"
        bad = self.client.post("/admin/api/settings/save", json=reloaded, headers=self.headers)
        self.assertEqual(bad.status_code, 400)

    def test_catalog_groups_and_labels(self):
        data = self.client.get("/admin/api/widget-catalog", headers=self.headers).get_json()["data"]
        self.assertTrue(all("group" in field for field in data["fields"]))
        self.assertEqual([g["key"] for g in data["field_groups"]][0], "weather")
        header = next(item for item in data["system"] if item["id"] == "header")
        fmt = next(opt for opt in header["options"] if opt["key"] == "date_format")
        self.assertEqual(set(fmt["choice_labels"]), {"cn", "md", "ymd", "dot", "custom"})
        template = next(opt for opt in header["options"] if opt["key"] == "date_template")
        self.assertEqual(template["visible_when"], {"date_format": "custom"})

    def test_header_template_survives_save_and_preview(self):
        # 新 options 值必须走通 validate → normalize（_normalize_block）链路，不被静默剥离
        current = self.client.get("/admin/api/settings").get_json()["data"]["settings"]
        page = next(p for p in current["pages"] if p["page_id"] == "today")
        header = next(b for b in page["layout"] if b["widget"] == "header")
        header["options"] = {"date_format": "custom", "date_template": "{M}月{D}日 周{W}"}
        saved = self.client.post("/admin/api/settings/save", json=current, headers=self.headers)
        self.assertEqual(saved.status_code, 200)
        reloaded = self.client.get("/admin/api/settings").get_json()["data"]["settings"]
        page = next(p for p in reloaded["pages"] if p["page_id"] == "today")
        header = next(b for b in page["layout"] if b["widget"] == "header")
        self.assertEqual(header["options"]["date_template"], "{M}月{D}日 周{W}")
        preview = self.client.post("/admin/api/layout-preview", json={"page_id": "today", "layout": page["layout"]}, headers=self.headers)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.mimetype, "image/png")


if __name__ == "__main__":
    unittest.main()

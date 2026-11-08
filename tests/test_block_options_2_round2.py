"""积木自定义二期·轮 2：天气数据扩展、生活建议、数据积木新字段、指数卡自选、逐时图表、一周积木。"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

try:
    from test_web_admin import PASSWORD, _offline_network
except ImportError:  # 以 tests.xxx 模块名直接运行时
    from tests.test_web_admin import PASSWORD, _offline_network

from PIL import Image, ImageDraw

from server.advice import advice_text, uv_level
from server.app import create_app
from server.data import build_payload
from server.fields import field_text
from server.layout import _validate_block, block_options, field_group, list_option_error, system_options_catalog
from server.render import style
from server.render.pages import detail, week
from server.render.regions import Rect
from server.units import fmt_pressure, fmt_visibility, fmt_wind_dir
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData, fetch_weather

TZ = ZoneInfo("Asia/Shanghai")


def _payload(hours: list[HourlyPoint] | None = None, days: list[DailyForecast] | None = None, current: CurrentWeather | None = None) -> dict:
    now = datetime(2026, 11, 8, 22, 0, tzinfo=TZ)
    hours = hours or [
        HourlyPoint(f"2026-11-{8 + (22 + i) // 24:02d}T{(22 + i) % 24:02d}:00", -1 + (i % 12) * 0.7, [0, 10, 35, 60][i % 4], 0) for i in range(24)
    ]
    days = days or [DailyForecast(f"2026-11-{8 + i:02d}", 6 + i, -3 + i, 0, "晴", [0, 10, 70, 20, 0, 90, 5][i], 3.2) for i in range(7)]
    current = current or CurrentWeather(3, 61, 20, 0, "晴", 1, 0.0, 1013.4, 16560.0, 334)
    with patch("server.quotes.get_quote", return_value={"text": "测试", "from": "单测"}):
        return build_payload({"latitude": 39.9, "longitude": 116.4, "location_name": "北京"}, WeatherData(current, days, hours), now)


def _ink(img, box=None) -> int:
    px = img.load()
    x0, y0, x1, y1 = box or (0, 0, img.width, img.height)
    return sum(1 for y in range(y0, y1) for x in range(x0, x1) if px[x, y] < 128)


def _marked(img, box) -> int:
    """非纸色像素数（含浅灰填充与发丝线）。"""
    px = img.load()
    x0, y0, x1, y1 = box
    return sum(1 for y in range(y0, y1) for x in range(x0, x1) if px[x, y] != style.PAPER)


def _count(img, box, value: int) -> int:
    px = img.load()
    x0, y0, x1, y1 = box
    return sum(1 for y in range(y0, y1) for x in range(x0, x1) if px[x, y] == value)


class WeatherParseTest(unittest.TestCase):
    def _response(self, with_new: bool) -> MagicMock:
        today = datetime.now(TZ).date()
        dates = [(today + timedelta(days=offset)).isoformat() for offset in (-1, 0, 1)]
        current = {"temperature_2m": 3.2, "relative_humidity_2m": 61, "weather_code": 0, "wind_speed_10m": 20.0, "apparent_temperature": 1.0}
        daily = {"time": dates, "weather_code": [0, 2, 61], "temperature_2m_max": [8, 6, 7], "temperature_2m_min": [-1, -3, 0]}
        if with_new:
            current.update(uv_index=0.0, pressure_msl=1043.2, visibility=16560.0, wind_direction_10m=334)
            daily.update(precipitation_probability_max=[5, 10, 70], uv_index_max=[3.0, 3.25, None])
        resp = MagicMock()
        resp.json.return_value = {"current": current, "daily": daily, "hourly": {"time": [], "temperature_2m": []}}
        return resp

    def test_new_fields_parsed_after_yesterday_split(self):
        with patch("server.weather.requests.get", return_value=self._response(True)) as get:
            data = fetch_weather(39.9, 116.4, "Asia/Shanghai")
        params = get.call_args.kwargs["params"]
        self.assertIn("uv_index", params["current"])
        self.assertIn("precipitation_probability_max", params["daily"])
        self.assertEqual((data.current.uv, data.current.pressure, data.current.visibility, data.current.wind_dir), (0.0, 1043.2, 16560.0, 334.0))
        # 昨天切出后 daily[0] 是今天：降水概率/UV 跟着今天走，不能错位
        self.assertEqual((data.daily[0].precip_prob, data.daily[0].uv_max), (10, 3.25))
        self.assertEqual((data.daily[1].precip_prob, data.daily[1].uv_max), (70, None))
        self.assertEqual(data.yesterday.precip_prob, 5)

    def test_missing_new_fields_fall_back_to_none(self):
        with patch("server.weather.requests.get", return_value=self._response(False)):
            data = fetch_weather(39.9, 116.4, "Asia/Shanghai")
        self.assertIsNone(data.current.uv)
        self.assertIsNone(data.daily[0].precip_prob)
        payload = _payload(days=data.daily, current=data.current)
        self.assertIsNone(payload["weather"]["current"]["visibility_km"])

    def test_payload_carries_new_values(self):
        payload = _payload()
        current = payload["weather"]["current"]
        self.assertEqual((current["uv"], current["pressure"], current["visibility_km"], current["wind_dir"]), (0.0, 1013.4, 16.56, 334))
        self.assertEqual(payload["weather"]["daily"][2]["precip_prob"], 70)


def _advice(T=20.0, P=0, H=50, U=5.0, W=5, S=6.0, P1=0, aqi=None, code=0, cool=False, en=False, cn=False) -> dict:
    payload = {
        "weather": {
            "current": {"temperature": T, "apparent": T, "humidity": H, "wind_speed": W, "code": code, "uv": None},
            "daily": [{"precip_prob": P, "uv_max": U, "temp_max": 10 + S if S is not None else None, "temp_min": 10}, {"precip_prob": P1}],
            "precip_prob": P,
        },
        "aqi": None if aqi is None else {"us_aqi": aqi, "level_zh": "良", "cn_aqi": aqi - 50 if cn else None, "cn_level": "良" if cn else None},
        "weather_alerts": [{"kind": "cool", "drop": 6}] if cool else [],
        "units": {"aqi": "cn"} if cn else {},
    }
    if en:
        payload["ui_lang"] = "en"
    return payload


class AdviceRulesTest(unittest.TestCase):
    def assertAdvice(self, key, payload, expected):
        self.assertEqual(advice_text(payload, key), expected, (key, expected))

    def test_dress_bands(self):
        for temp, expected in ((28, "短袖"), (27.9, "薄长袖"), (23, "薄长袖"), (18, "长袖衬衫"), (12, "薄外套"),
                               (5, "厚外套"), (-5, "棉衣"), (-5.1, "羽绒服")):
            self.assertAdvice("dress", _advice(T=temp), expected)
        self.assertAdvice("dress", _advice(T=None), "")
        self.assertAdvice("dress", _advice(T=12, en=True), "Light jacket")

    def test_laundry(self):
        self.assertAdvice("laundry", _advice(P=50), "不宜")
        self.assertAdvice("laundry", _advice(P=0, code=61), "不宜")
        self.assertAdvice("laundry", _advice(P=30), "较不宜")
        self.assertAdvice("laundry", _advice(H=85), "较不宜")
        self.assertAdvice("laundry", _advice(U=3, H=69, P=19), "适宜")
        self.assertAdvice("laundry", _advice(U=2.9, H=69, P=19), "较适宜")
        self.assertAdvice("laundry", _advice(U=None, H=60, P=10), "较适宜")
        self.assertAdvice("laundry", _advice(P=None), "")

    def test_exercise(self):
        for kwargs in ({"aqi": 151}, {"P": 60}, {"T": 35}, {"T": -10}):
            self.assertAdvice("exercise", _advice(**kwargs), "不宜")
        for kwargs in ({"aqi": 101}, {"P": 30}, {"T": 30}, {"T": 0}, {"W": 39}):
            self.assertAdvice("exercise", _advice(**kwargs), "较不宜")
        self.assertAdvice("exercise", _advice(T=20, aqi=50, P=19), "适宜")
        # AQI 缺失时「适宜」条件不成立（偏保守）
        self.assertAdvice("exercise", _advice(T=20, aqi=None, P=0), "较适宜")
        # 跟随当前 AQI 标准：美标 160 不宜，国标 110 较不宜
        self.assertAdvice("exercise", _advice(aqi=160), "不宜")
        self.assertAdvice("exercise", _advice(aqi=160, cn=True), "较不宜")

    def test_carwash(self):
        self.assertAdvice("carwash", _advice(P=30), "不宜")
        self.assertAdvice("carwash", _advice(P1=50), "不宜")
        self.assertAdvice("carwash", _advice(W=39), "较不宜")
        self.assertAdvice("carwash", _advice(aqi=151), "较不宜")
        self.assertAdvice("carwash", _advice(), "适宜")

    def test_cold(self):
        self.assertAdvice("cold", _advice(S=10), "易发")
        self.assertAdvice("cold", _advice(T=5), "易发")
        self.assertAdvice("cold", _advice(cool=True), "易发")
        self.assertAdvice("cold", _advice(S=7), "较易发")
        self.assertAdvice("cold", _advice(T=10, S=5), "较易发")
        self.assertAdvice("cold", _advice(H=30, S=5, T=15), "较易发")
        self.assertAdvice("cold", _advice(T=15, S=5, H=50), "少发")

    def test_sunscreen(self):
        for uv, expected in ((11, "极强"), (8, "很强"), (6, "强"), (3, "中等"), (2.9, "弱"), (0, "弱")):
            self.assertAdvice("sunscreen", _advice(U=uv), expected)
        self.assertAdvice("sunscreen", _advice(U=None), "")
        self.assertEqual(uv_level(6, english=True), "High")


class FormatAndFieldTest(unittest.TestCase):
    def test_wind_direction(self):
        cases = {0: "北风", 22.4: "北风", 22.5: "东北风", 90: "东风", 180: "南风", 270: "西风", 337.5: "北风", 334: "西北风", 360: "北风"}
        for degrees, expected in cases.items():
            self.assertEqual(fmt_wind_dir(degrees, None), expected, degrees)
        self.assertEqual(fmt_wind_dir(45, {"ui_lang": "en"}), "NE")
        self.assertEqual(fmt_wind_dir(None, None), "")

    def test_visibility_and_pressure(self):
        self.assertEqual(fmt_visibility(24.4), "24 km")
        self.assertEqual(fmt_visibility(8.53), "8.5 km")
        self.assertEqual(fmt_pressure(1013.4), "1013 hPa")

    def test_new_fields(self):
        payload = _payload()
        self.assertEqual(field_text(payload, "weather.uv"), "3")  # 取当日最大值 3.2，而非夜间实况 0
        self.assertEqual(field_text(payload, "weather.pressure"), "1013 hPa")
        self.assertEqual(field_text(payload, "weather.visibility"), "17 km")
        self.assertEqual(field_text(payload, "weather.wind_dir"), "西北风")
        self.assertEqual(field_text(payload, "air.pm25"), "—")  # 无 AQI 数据 → 占位
        self.assertEqual(field_text(payload, "life.sunscreen"), "中等")
        self.assertEqual(field_text(payload, "life.dress"), "棉衣")  # 体感 1℃：低于 5℃ 档、不低于 −5℃
        for field in ("life.dress", "air.pm25", "weather.uv"):
            self.assertIn(field_group(field), ("life", "air", "weather"))


class ListOptionTest(unittest.TestCase):
    def test_validation(self):
        self.assertIsNone(list_option_error("indices", "items", ["uv", "dress"]))
        self.assertIn("1–6", list_option_error("indices", "items", []))
        self.assertIn("1–6", list_option_error("indices", "items", ["humidity", "wind", "precip", "sunrise", "sunset", "aqi", "uv"]))
        self.assertEqual(list_option_error("indices", "items", ["uv", "uv"]), "项目不能重复")
        self.assertEqual(list_option_error("indices", "items", ["bogus"]), "含未知项目")
        self.assertTrue(list_option_error("indices", "items", "uv"))

    def test_block_options_fallback(self):
        self.assertEqual(block_options("indices", {"items": ["uv", "dress"]})["items"], ["uv", "dress"])
        self.assertEqual(block_options("indices", {"items": ["bogus"]})["items"], ["humidity", "wind", "precip", "sunrise", "sunset", "aqi"])
        self.assertEqual(block_options("hourly", {"chart": "line"}), {"chart": "line", "span": "24", "precip": "dots", "labels": "ends", "ticks": "6", "border": False})

    def test_validate_block(self):
        def errors(options):
            details: list = []
            block = {"widget": "indices", "id": "indices", "x": 56, "y": 580, "w": 646, "h": 350, "z": 0, "options": options}
            _validate_block(block, 0, 0, details, set(), set(), set(), {})
            return details

        self.assertEqual(errors({"items": ["uv", "pm25", "dress"]}), [])
        self.assertTrue(errors({"items": ["uv"] * 2}))
        self.assertTrue(errors({"items": []}))

    def test_catalog(self):
        items = next(opt for opt in system_options_catalog("indices", "zh") if opt["key"] == "items")
        self.assertEqual((items["kind"], items["min_items"], items["max_items"]), ("list", 1, 6))
        self.assertEqual(len(items["choices"]), 21)
        self.assertEqual(items["default"], ["humidity", "wind", "precip", "sunrise", "sunset", "aqi"])
        self.assertEqual(items["choice_labels"]["dress"], "穿衣")


class IndicesRenderTest(unittest.TestCase):
    RECT = Rect(0, 0, 646, 350)

    def test_items_and_order_drive_output(self):
        payload = _payload()
        default = detail.render_indices(payload, self.RECT, "")
        explicit = detail.render_indices(payload, self.RECT, "", options={"items": ["humidity", "wind", "precip", "sunrise", "sunset", "aqi"]})
        self.assertEqual(default.tobytes(), explicit.tobytes())
        a = detail.render_indices(payload, self.RECT, "", options={"items": ["uv", "dress"]})
        b = detail.render_indices(payload, self.RECT, "", options={"items": ["dress", "uv"]})
        self.assertNotEqual(a.tobytes(), b.tobytes())

    def test_grid_adapts_to_count(self):
        payload = _payload()
        one = detail.render_indices(payload, self.RECT, "", options={"items": ["dress"]})
        # 单张卡独占整行：右边框在接近分区右缘处
        self.assertGreater(_marked(one, (640, 100, 646, 250)), 0)
        two = detail.render_indices(payload, self.RECT, "", options={"items": ["dress", "uv"]})
        # 两张卡一行占满高度：分区下部仍是卡片边框（六卡时第三排位置不同）
        self.assertGreater(_marked(two, (0, 340, 646, 350)), 0)

    def test_missing_values_show_dash(self):
        payload = _payload()
        with_pm = detail.render_indices(payload, self.RECT, "", options={"items": ["pm25"]})
        self.assertGreater(_ink(with_pm), 0)
        self.assertEqual(field_text(payload, "air.pm25"), "—")


class HourlyRenderTest(unittest.TestCase):
    RECT = Rect(0, 0, 646, 430)

    def render(self, **options):
        return detail.render_hourly(_payload(), self.RECT, "", options=options or None)

    def test_chart_styles_differ(self):
        bar, line, area = self.render(), self.render(chart="line"), self.render(chart="area")
        self.assertNotEqual(bar.tobytes(), line.tobytes())
        self.assertGreater(_marked(area, (0, 40, 646, 378)), _marked(line, (0, 40, 646, 378)))

    def test_span_ticks_labels_precip(self):
        base = self.render()
        self.assertNotEqual(base.tobytes(), self.render(span="12").tobytes())
        tick_row = (0, 390, 646, 420)
        self.assertGreater(_ink(self.render(ticks="3"), tick_row), _ink(base, tick_row))
        self.assertNotEqual(base.tobytes(), self.render(labels="extremes").tobytes())
        self.assertGreater(_ink(self.render(labels="every3")), _ink(base))
        off = self.render(precip="off")
        self.assertLess(_ink(off), _ink(base))
        bars = self.render(precip="bars")
        # 底部细条：基线上方单独一条带，只有中灰降水条；温度柱（浅灰填充）整体上移、不再伸进这条带
        strip = (0, 352, 646, 378)
        self.assertEqual(_count(bars, strip, style.LIGHT), 0)
        self.assertGreater(_count(base, strip, style.LIGHT), 0)
        self.assertGreater(_count(bars, strip, style.MID), 0)

    def test_edge_labels_not_clipped(self):
        # 首个刻度「22时」以柱心居中时左半会越界被裁成「2时」；现钳制在分区内
        img = self.render()
        self.assertEqual(_ink(img, (0, 385, 2, 425)), 0)
        self.assertEqual(_ink(img, (644, 0, 646, 430)), 0)


class WeekRenderTest(unittest.TestCase):
    def test_days_icon_precip(self):
        payload = _payload()
        rect = Rect(0, 0, 646, 490)
        seven = week.render_list(payload, rect, "")
        five = week.render_list(payload, rect, "", options={"days": "5"})
        self.assertNotEqual(seven.tobytes(), five.tobytes())
        no_icon = week.render_list(payload, rect, "", options={"show_icon": False})
        self.assertLess(_ink(no_icon, (120, 0, 200, 490)), _ink(seven, (120, 0, 200, 490)))
        precip = week.render_list(payload, rect, "", options={"show_precip": True})
        self.assertGreater(_ink(precip, (300, 0, 520, 490)), _ink(seven, (300, 0, 520, 490)))
        chart = Rect(0, 0, 646, 290)
        self.assertNotEqual(week.render_chart(payload, chart, "").tobytes(), week.render_chart(payload, chart, "", options={"days": "5"}).tobytes())


def _diff_bbox(a, b, box):
    pa, pb = a.load(), b.load()
    x0, y0, x1, y1 = box
    pts = [(x, y) for y in range(y0, y1) for x in range(x0, x1) if pa[x, y] != pb[x, y]]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


class LabelCollisionTest(unittest.TestCase):
    """切 ℃/℉ 只改标注文字、不动任何几何，两次渲染的像素差恰好就是温度标注的占位。"""

    def test_hourly_precip_marks_stack_above_temperature_label(self):
        temps = [2.0 + 0.3 * i for i in range(24)]

        def render(prob0, units=None):
            hours = [HourlyPoint(f"2026-11-{8 + (22 + i) // 24:02d}T{(22 + i) % 24:02d}:00", temps[i], prob0 if i == 0 else 0, 0) for i in range(24)]
            payload = _payload(hours=hours)
            if units:
                payload = dict(payload, units=units)
            return detail.render_hourly(payload, Rect(0, 0, 646, 430), "")

        region = (0, 0, 80, 380)
        marks = _diff_bbox(render(60), render(0), region)  # 首小时的降水圆点 + 「60%」
        label = _diff_bbox(render(0), render(0, {"temp": "f"}), region)  # 首小时温度标注
        self.assertIsNotNone(marks)
        self.assertIsNotNone(label)
        self.assertLess(marks[3], label[1], "precip dot and percentage must sit above the temperature label")

    def test_week_low_label_never_hits_date_row(self):
        # 首日低温恰是一周最低：旧版把「-3°」画在日期「8」上
        days = [DailyForecast(f"2026-11-{8 + i:02d}", 6 + i, -3 + i, 0, "晴") for i in range(7)]
        rect = Rect(0, 0, 646, 290)
        c = week.render_chart(_payload(days=days), rect, "")
        f = week.render_chart(dict(_payload(days=days), units={"temp": "f"}), rect, "")
        low = _diff_bbox(c, f, (0, 150, 80, 290))
        self.assertIsNotNone(low)
        date_top = ImageDraw.Draw(Image.new("L", (8, 8))).textbbox((0, 290 - 36 + 10), "0", font=style.get_font(20, ""))[1]
        self.assertLess(low[3], date_top - 1)


class AdminApiRound2Test(unittest.TestCase):
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

    def _detail_blocks(self, settings):
        page = next(p for p in settings["pages"] if p["page_id"] == "detail")
        return page, {b["widget"]: b for b in page["layout"]}

    def test_indices_and_hourly_options_roundtrip(self):
        settings = self.client.get("/admin/api/settings").get_json()["data"]["settings"]
        page, blocks = self._detail_blocks(settings)
        blocks["indices"]["options"] = {"items": ["uv", "dress", "pm25"]}
        blocks["hourly"]["options"] = {"chart": "area", "span": "12", "precip": "bars", "labels": "extremes", "ticks": "3"}
        saved = self.client.post("/admin/api/settings/save", json=settings, headers=self.headers)
        self.assertEqual(saved.status_code, 200)
        reloaded = self.client.get("/admin/api/settings").get_json()["data"]["settings"]
        page, blocks = self._detail_blocks(reloaded)
        self.assertEqual(blocks["indices"]["options"]["items"], ["uv", "dress", "pm25"])
        self.assertEqual(blocks["hourly"]["options"]["chart"], "area")
        preview = self.client.post("/admin/api/layout-preview", json={"page_id": "detail", "layout": page["layout"]}, headers=self.headers)
        self.assertEqual((preview.status_code, preview.mimetype), (200, "image/png"))
        blocks["indices"]["options"] = {"items": ["uv"] * 7}
        bad = self.client.post("/admin/api/settings/save", json=reloaded, headers=self.headers)
        self.assertEqual(bad.status_code, 400)


if __name__ == "__main__":
    unittest.main()

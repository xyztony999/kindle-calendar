"""系统积木外观选项（v2-system-options）测试。"""

from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from server.data import build_payload
from server.layout import SYSTEM_OPTIONS, _validate_block, block_options, clock_rect_for_options, system_options_catalog
from server.render.pages import almanac, common, month, today
from server.render.regions import Rect
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData


def _payload() -> dict:
    tz = ZoneInfo("Asia/Shanghai")
    now = datetime(2026, 10, 20, 16, 0, tzinfo=tz)
    weather = WeatherData(
        CurrentWeather(20, 50, 5, 0, "晴"),
        [DailyForecast("2026-10-20", 24, 14, 0, "晴")],
        [HourlyPoint("2026-10-20T16:00", 20, 0, 0)],
    )
    return build_payload({"latitude": 39.9, "longitude": 116.4, "location_name": "北京"}, weather, now)


def _payload_holiday() -> dict:
    tz = ZoneInfo("Asia/Shanghai")
    now = datetime(2026, 10, 1, 16, 0, tzinfo=tz)
    weather = WeatherData(
        CurrentWeather(20, 50, 5, 0, "晴"),
        [DailyForecast("2026-10-01", 24, 14, 0, "晴")],
        [HourlyPoint("2026-10-01T16:00", 20, 0, 0)],
    )
    return build_payload({"latitude": 39.9, "longitude": 116.4, "location_name": "北京"}, weather, now)


def _ink(img, box) -> int:
    px = img.load()
    x0, y0, x1, y1 = box
    return sum(1 for y in range(y0, min(y1, img.height)) for x in range(x0, min(x1, img.width)) if px[x, y] < 128)


def _block(widget: str, options=None) -> dict:
    block = {"widget": widget, "id": widget, "x": 0, "y": 122, "w": 646, "h": 78, "z": 0}
    if options is not None:
        block["options"] = options
    return block


class OptionsSchemaTest(unittest.TestCase):
    def test_every_system_widget_schema_labels(self):
        for widget, schema in SYSTEM_OPTIONS.items():
            for key, (zh, en, kind, default, choices) in schema.items():
                self.assertTrue(zh and en, (widget, key))
                if kind == "bool":
                    self.assertIsInstance(default, bool)
                    self.assertIsNone(choices)
                else:
                    self.assertEqual(kind, "choice")
                    self.assertIn(default, choices or ())

    def test_catalog_shape(self):
        items = system_options_catalog("clock", "zh")
        self.assertEqual(items[0]["key"], "size")
        self.assertEqual(items[0]["choices"], ["lg", "md", "sm"])
        quote = system_options_catalog("quote", "zh")
        self.assertEqual([item["key"] for item in quote], ["size", "border"])
        grid = {item["key"]: item for item in system_options_catalog("grid", "zh")}
        self.assertEqual(grid["week_start"]["choices"], ["mon", "sun"])

    def test_block_options_normalization(self):
        self.assertEqual(
            block_options("header", {"show_tabs": False}),
            {"show_tabs": False, "show_lunar": True, "show_notes": True, "border": False},
        )
        self.assertEqual(
            block_options("header", {"bogus": 1}),
            {"show_tabs": True, "show_lunar": True, "show_notes": True, "border": False},
        )
        self.assertEqual(block_options("clock", {"size": "xx"}), {"size": "lg", "hour12": False})
        self.assertEqual(block_options("clock", {"hour12": True}), {"size": "lg", "hour12": True})
        self.assertEqual(block_options("schedule", {}), {"show_tomorrow": False, "border": False})
        self.assertEqual(block_options("quote", {"size": "lg"}), {"size": "lg", "border": False})
        self.assertEqual(block_options("grid", {"week_start": "sun"}), {
            "show_badges": True, "show_lunar": True, "week_start": "sun", "show_event_dots": False, "border": False,
        })

    def test_border_schema_excludes_clock(self):
        self.assertNotIn("border", SYSTEM_OPTIONS["clock"])
        for widget in ("header", "weather", "sun", "scene", "quote", "list", "chart", "title", "grid", "hourly", "indices", "main", "schedule", "countdown"):
            self.assertIn("border", SYSTEM_OPTIONS[widget])

    def test_clock_glyphs_hour12(self):
        from server.render.pages.today import render_glyphs
        from server.render.regions import Rect, metrics_in

        rect = Rect(0, 0, 600, 200)
        base = render_glyphs(metrics_in(rect), "")
        self.assertEqual(sorted(base), sorted([str(i) for i in range(10)] + [":"]))
        metrics = metrics_in(rect, True)
        h12 = render_glyphs(metrics, "", True)
        self.assertIn("am", h12)
        self.assertIn("pm", h12)
        self.assertEqual(h12["am"].size, (metrics.suf_w, metrics.suf_h))
        self.assertGreater(metrics.total_w(), metrics_in(rect).total_w())

    def test_validate_text_size_field(self):
        details: list = []
        good = {"widget": "text", "id": "b00000001", "x": 0, "y": 200, "w": 280, "h": 80, "z": 0, "text": "你好", "align": "left", "size": "lg"}
        _validate_block(good, 0, 0, details, set(), set(), set(), {})
        self.assertFalse(any(".size" in str(d) for d in details))
        details = []
        bad = dict(good, size="huge")
        _validate_block(bad, 0, 0, details, set(), set(), set(), {})
        self.assertTrue(any(".size" in str(d) for d in details))

    def test_validate_rejects_bad_options(self):
        details: list = []
        _validate_block(_block("header", {"show_tabs": "yes"}), 0, 0, details, set(), set(), set(), {})
        self.assertTrue(any("options.show_tabs" in str(d) for d in details))

    def test_header_weather_alerts(self):
        rect = Rect(0, 0, 646, 78)
        payload = dict(_payload(), weather_alerts=[{"kind": "cool", "drop": 6}, {"kind": "rain", "prob": 70}])
        full = common.render_header(payload, rect, "", page="today")
        off = common.render_header(payload, rect, "", page="today", options={"show_notes": False})
        self.assertLess(_ink(off, (0, 30, 646, 78)), _ink(full, (0, 30, 646, 78)))

    def test_weather_feels_toggle(self):
        rect = Rect(0, 0, 646, 244)
        payload = _payload()
        payload["weather"]["current"]["apparent"] = 18
        on = today.render_weather(payload, rect, "", options={"show_feels": True})
        off = today.render_weather(payload, rect, "", options={"show_feels": False})
        self.assertGreater(_ink(on, (430, 100, 620, 230)), _ink(off, (430, 100, 620, 230)))

    def test_validate_rejects_options_on_custom(self):
        details: list = []
        _validate_block(
            {"widget": "custom", "id": "b00000001", "x": 0, "y": 200, "w": 280, "h": 160, "z": 0, "def": "w00000001", "options": {"a": 1}},
            0, 0, details, {"w00000001"}, set(), set(), {},
        )
        self.assertTrue(any("options" in str(d) for d in details))

    def test_clock_rect_shrinks_centered(self):
        self.assertEqual(clock_rect_for_options(0, 0, 100, 200, {"size": "md"}), (0, 25, 100, 150))
        self.assertEqual(clock_rect_for_options(0, 0, 100, 200, {}), (0, 0, 100, 200))


class OptionsRenderTest(unittest.TestCase):
    def setUp(self):
        self.payload = _payload()

    def test_header_tabs_lunar_hide(self):
        rect = Rect(0, 0, 646, 78)
        full = common.render_header(self.payload, rect, "", page="today")
        off = common.render_header(self.payload, rect, "", page="today", options={"show_tabs": False, "show_lunar": False})
        self.assertLess(_ink(off, (400, 0, 646, 78)), _ink(full, (400, 0, 646, 78)))

    def test_weather_stats_hide(self):
        rect = Rect(0, 0, 646, 244)
        full = today.render_weather(self.payload, rect, "")
        off = today.render_weather(self.payload, rect, "", options={"show_humidity": False, "show_wind": False, "show_precip": False})
        self.assertLess(_ink(off, (430, 30, 620, 160)), _ink(full, (430, 30, 620, 160)))

    def test_sun_arc_aqi_hide(self):
        rect = Rect(0, 0, 646, 132)
        off = today.render_sun(self.payload, rect, "", options={"show_arc": False, "show_aqi": False})
        self.assertEqual(_ink(off, (0, 40, 400, 132)), 0)
        self.assertEqual(_ink(off, (420, 0, 646, 132)), 0)

    def test_almanac_sections_hide(self):
        rect = Rect(0, 0, 646, 800)
        full = almanac.render_main(self.payload, rect, "")
        off = almanac.render_main(self.payload, rect, "", options={"show_yiji": False, "show_wuhou": False})
        self.assertLess(_ink(off, (180, 60, 646, 620)), _ink(full, (180, 60, 646, 620)))

    def test_grid_captions_hide(self):
        rect = Rect(0, 0, 646, 730)
        full = month.render_grid(self.payload, rect, "")
        off = month.render_grid(self.payload, rect, "", options={"show_badges": False, "show_lunar": False})
        self.assertLess(_ink(off, (0, 50, 646, 730)), _ink(full, (0, 50, 646, 730)))
        only_captions = month.render_grid(self.payload, rect, "", options={"show_lunar": False})
        self.assertLess(_ink(only_captions, (0, 50, 646, 730)), _ink(full, (0, 50, 646, 730)))

    def test_header_notes_hide(self):
        rect = Rect(0, 0, 646, 78)
        payload = _payload_holiday()
        full = common.render_header(payload, rect, "", page="today")
        off = common.render_header(payload, rect, "", page="today", options={"show_notes": False})
        self.assertLess(_ink(off, (0, 30, 646, 78)), _ink(full, (0, 30, 646, 78)))

    def test_weather_range_icon_hide(self):
        rect = Rect(0, 0, 646, 244)
        full = today.render_weather(self.payload, rect, "")
        off_range = today.render_weather(self.payload, rect, "", options={"show_range": False})
        self.assertLess(_ink(off_range, (0, 190, 400, 244)), _ink(full, (0, 190, 400, 244)))
        off_icon = today.render_weather(self.payload, rect, "", options={"show_icon": False})
        self.assertLess(_ink(off_icon, (460, 0, 646, 200)), _ink(full, (460, 0, 646, 200)))

    def test_quote_size_tiers(self):
        rect = Rect(0, 0, 646, 52)
        # 固定短句：在线一言可能超长，长句会触发自适应缩字号，lg/sm 收敛到同一字号
        payload = dict(self.payload, quote={"text": "此心安处是吾乡。", "from": "苏轼"})
        lg = common.render_quote(payload, rect, "", options={"size": "lg"})
        sm = common.render_quote(payload, rect, "", options={"size": "sm"})
        self.assertGreater(_ink(lg, (0, 0, 646, 52)), _ink(sm, (0, 0, 646, 52)))

    def test_grid_week_start_sunday(self):
        rect = Rect(0, 0, 646, 730)
        mon = month.render_grid(self.payload, rect, "")
        sun = month.render_grid(self.payload, rect, "", options={"week_start": "sun"})
        self.assertNotEqual(_ink(mon, (0, 0, 92, 44)), _ink(sun, (0, 0, 92, 44)))

    def test_month_grid_firstweekday(self):
        from server import almanac as al

        mon = al.month_grid_info(2026, 10)
        sun = al.month_grid_info(2026, 10, firstweekday=6)
        self.assertEqual(mon["weeks"][0].index(1), 3)  # 2026-10-01 周四
        self.assertEqual(sun["weeks"][0].index(1), 4)
        self.assertNotEqual(mon, sun)

    def test_paint_system_border(self):
        from server.render.placed import paint_system

        rect = Rect(0, 0, 646, 78)
        full = paint_system("header", self.payload, rect, "", "today")
        bordered = paint_system("header", self.payload, rect, "", "today", options={"border": True})
        self.assertGreater(_ink(bordered, (0, 0, 646, 78)), _ink(full, (0, 0, 646, 78)))

    def test_paint_text_size_tiers(self):
        from server.render.placed import paint_text

        rect = Rect(0, 0, 280, 80)
        lg = paint_text("字号测试", "center", rect, "", "lg")
        sm = paint_text("字号测试", "center", rect, "", "sm")
        self.assertGreater(_ink(lg, (0, 0, 280, 80)), _ink(sm, (0, 0, 280, 80)))


if __name__ == "__main__":
    unittest.main()

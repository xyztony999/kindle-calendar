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
        self.assertEqual(system_options_catalog("quote", "zh"), [])

    def test_block_options_normalization(self):
        self.assertEqual(block_options("header", {"show_tabs": False}), {"show_tabs": False, "show_lunar": True})
        self.assertEqual(block_options("header", {"bogus": 1}), {"show_tabs": True, "show_lunar": True})
        self.assertEqual(block_options("clock", {"size": "xx"}), {"size": "lg"})

    def test_validate_rejects_bad_options(self):
        details: list = []
        _validate_block(_block("header", {"show_tabs": "yes"}), 0, 0, details, set(), set(), set(), {})
        self.assertTrue(any("options.show_tabs" in str(d) for d in details))

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


if __name__ == "__main__":
    unittest.main()

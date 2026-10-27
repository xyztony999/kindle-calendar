"""自由画布：布局校验、目录过滤、env 与预览。"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from server.layout import FIELD_IDS, accept_center_item, applicable_data_styles, default_layout, field_kind
from server.settings import defaults_from_config, normalize, settings_version, validate
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData

PASSWORD = "test-only-not-a-secret"
DEPLOY = {
    "location_name": "北京",
    "latitude": 39.9042,
    "longitude": 116.4074,
    "timezone": "Asia/Shanghai",
}
FAKE_WEATHER = WeatherData(
    current=CurrentWeather(temperature=20.0, humidity=50, wind_speed=3.0, code=0, description="晴"),
    daily=[DailyForecast(date="2026-10-10", temp_max=22.0, temp_min=15.0, code=0, description="晴")],
    hourly=[HourlyPoint(time="2026-10-10T15:00", temperature=20.0, precipitation_probability=0, code=0)],
)


def _quote_stub(now, mode="online", custom=None, types=None):
    return {"text": "测试一言", "from": "单测"}


class LayoutUnitTests(unittest.TestCase):
    def test_schema1_keeps_city_and_gains_layout(self):
        raw = {
            "schema_version": 1,
            "pages": [
                {"page_id": "today", "enabled": True, "dwell_s": 120},
                {"page_id": "week", "enabled": False, "dwell_s": 30},
                {"page_id": "month", "enabled": True, "dwell_s": 30},
                {"page_id": "detail", "enabled": True, "dwell_s": 30},
                {"page_id": "almanac", "enabled": True, "dwell_s": 30},
            ],
            "rotation": {"enabled": True, "suppress_s": 120},
            "quote": {"mode": "online", "custom": []},
            "location": {"name": "杭州", "latitude": 30.27, "longitude": 120.15, "timezone": "Asia/Shanghai"},
        }
        self.assertEqual(validate(raw), [])
        from server.settings import normalize

        out = normalize(raw)
        self.assertEqual(out["schema_version"], 3)
        self.assertEqual(out["location"]["name"], "杭州")
        self.assertEqual(out["pages"][1]["enabled"], False)
        self.assertEqual(out["pages"][0]["layout"], default_layout("today"))

    def test_clock_overlap_and_custom_page(self):
        raw = defaults_from_config(DEPLOY)
        raw["pages"][0]["layout"] = [
            {"widget": "clock", "id": "clock", "x": 56, "y": 160, "w": 646, "h": 242, "z": 1},
            {"widget": "weather", "id": "weather", "x": 56, "y": 200, "w": 646, "h": 244, "z": 2},
        ]
        codes = {item["message"] for item in validate(raw)}
        self.assertIn("时钟不能与其他积木重叠", codes)

        raw = defaults_from_config(DEPLOY)
        raw["pages"].append(
            {"page_id": "c1234abcd", "name": "海报", "enabled": True, "dwell_s": 30, "layout": []}
        )
        self.assertEqual(validate(raw), [])

    def test_weather_alerts_rules(self):
        from server.data import _weather_alerts

        yesterday = DailyForecast("2026-10-25", 28.0, 18.0, 0, "晴")
        today = DailyForecast("2026-10-26", 20.0, 12.0, 61, "小雨")
        with_drop = WeatherData(current=FAKE_WEATHER.current, daily=[today], hourly=[], yesterday=yesterday)
        self.assertEqual(_weather_alerts(with_drop, 70), [{"kind": "cool", "drop": 8}, {"kind": "rain", "prob": 70}])
        no_yesterday = WeatherData(current=FAKE_WEATHER.current, daily=[today], hourly=[])
        self.assertEqual(_weather_alerts(no_yesterday, 10), [])
        mild = WeatherData(current=FAKE_WEATHER.current, daily=[DailyForecast("2026-10-26", 27.0, 18.0, 0, "晴")], hourly=[], yesterday=yesterday)
        self.assertEqual(_weather_alerts(mild, 30), [])

    def test_center_item_rejects_code(self):
        self.assertIsNone(accept_center_item({"id": "center.bad", "kind": "data", "review": "approved", "name": "坏", "style": "rows", "fields": ["weather.temperature"], "script": "print(1)"}))
        self.assertIsNone(accept_center_item({"id": "center.ok", "kind": "data", "review": "pending", "name": "等", "style": "rows", "fields": ["weather.temperature"]}))
        item = accept_center_item({"id": "center.ok", "kind": "data", "review": "approved", "name": "温度", "style": "hero", "fields": ["weather.temperature"]})
        self.assertEqual(item["placeable"], True)

    def test_text_size_field_roundtrip(self):
        raw = defaults_from_config(DEPLOY)
        raw["pages"][0]["layout"] = [
            {"widget": "text", "id": "b1234abcd", "x": 56, "y": 820, "w": 400, "h": 80, "z": 9, "text": "测试", "align": "center", "size": "lg"}
        ]
        self.assertEqual(validate(raw), [])
        out = normalize(raw)
        self.assertEqual(out["pages"][0]["layout"][0]["size"], "lg")
        self.assertEqual(out["pages"][0]["layout"][0]["align"], "center")
        raw["pages"][0]["layout"][0]["size"] = "huge"
        self.assertTrue(any(error["field"].endswith(".size") for error in validate(raw)))
        migrated = normalize(raw)
        self.assertEqual(migrated["pages"][0]["layout"][0]["size"], "md")

    def test_field_capabilities_and_style_boundaries(self):
        self.assertEqual(len(FIELD_IDS), 29)
        self.assertEqual({field_kind(field) for field in FIELD_IDS}, {"number", "time", "date", "short_text", "text"})
        self.assertEqual(field_kind("unknown"), "text")
        compact = ["weather.temperature", "sun.sunrise", "date.month_day", "weather.humidity", "aqi.value", "sun.sunset"]
        for count, recommended in ((1, "hero"), (2, "horizontal"), (3, "horizontal"), (4, "grid"), (6, "grid")):
            self.assertEqual(applicable_data_styles(compact[:count])["recommended"], recommended)
        for style_id, allowed_counts in (("hero", {1, 2, 3}), ("rows", {1, 2, 3, 4, 5, 6}), ("horizontal", {2, 3}), ("grid", {2, 3, 4, 5, 6})):
            for count in range(7):
                with self.subTest(style=style_id, count=count):
                    self.assertEqual(style_id in applicable_data_styles(compact[:count])["styles"], count in allowed_counts)
        self.assertEqual(applicable_data_styles(["quote.text", "weather.temperature"]), {"styles": ["rows"], "recommended": "rows"})
        self.assertNotIn("hero", applicable_data_styles(["weather.description"])["styles"])
        self.assertEqual(applicable_data_styles([])["styles"], [])
        self.assertEqual(applicable_data_styles(compact + ["weather.wind_speed"])["styles"], [])

    def test_instance_override_validation_and_legacy_inheritance(self):
        raw = defaults_from_config(DEPLOY)
        raw["schema_version"] = 2
        raw["widget_defs"] = [{"id": "w1234abcd", "name": "语录", "style": "hero", "fields": ["quote.text"]}]
        block = {"widget": "custom", "id": "b1234abcd", "def": "w1234abcd", "x": 56, "y": 160, "w": 300, "h": 200, "z": 1}
        raw["pages"][0]["layout"] = [block]
        self.assertEqual(validate(raw), [])
        migrated = normalize(raw)
        self.assertEqual(migrated["schema_version"], 3)
        self.assertNotIn("style", migrated["pages"][0]["layout"][0])
        block["style"] = "hero"
        errors = validate(raw)
        self.assertTrue(any(error["field"] == "pages[0].layout[0].style" and error["code"] == "LAYOUT_INVALID" for error in errors))
        block["style"] = "rows"
        self.assertEqual(validate(raw), [])
        self.assertEqual(normalize(raw)["pages"][0]["layout"][0]["style"], "rows")
        for invalid in ("unknown", None, ["rows"]):
            block["style"] = invalid
            self.assertTrue(any(error["field"].endswith(".style") for error in validate(raw)))
        block.pop("style")
        block["def"] = "center.pending"
        with patch("server.catalog.approved_data_items", return_value=[{"id": "center.pending", "kind": "data", "review": "pending", "name": "未审核", "style": "rows", "fields": ["weather.temperature"], "placeable": True}]):
            self.assertTrue(any(error["code"] == "WIDGET_DEF_INVALID" for error in validate(raw)))
        raw["pages"][0]["layout"] = [dict(default_layout("today")[0], style="rows")]
        self.assertTrue(any(error["field"].endswith(".style") for error in validate(raw)))

    def test_approved_center_instance_style_and_content_version(self):
        raw = defaults_from_config(DEPLOY)
        raw["pages"][0]["layout"] = [{"widget": "custom", "id": "b1234abcd", "def": "center.temps", "style": "horizontal", "x": 56, "y": 160, "w": 300, "h": 200, "z": 1}]
        center = {"id": "center.temps", "kind": "data", "review": "approved", "name": "温度湿度", "style": "rows", "fields": ["weather.temperature", "weather.humidity"]}
        with patch("server.catalog.approved_data_items", return_value=[center]):
            self.assertEqual(validate(raw), [])
            before = settings_version(normalize(raw))
            raw["pages"][0]["layout"][0]["style"] = "grid"
            self.assertEqual(validate(raw), [])
            self.assertNotEqual(before, settings_version(normalize(raw)))


class LayoutApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SETTINGS_PATH"] = str(Path(self.tmp.name) / "settings.json")
        os.environ["ADMIN_PASSWORD"] = PASSWORD
        os.environ["SECRET_KEY"] = "unit-test-secret"
        os.environ.pop("WIDGET_CENTER_URL", None)
        self.patches = (
            patch("server.service.fetch_weather", return_value=FAKE_WEATHER),
            patch("server.service.fetch_aqi", return_value=None),
            patch("server.quotes.get_quote", side_effect=_quote_stub),
        )
        for item in self.patches:
            item.start()
        from server.app import create_app

        self.app = create_app()
        self.client = self.app.test_client()
        self.client.post(
            "/admin/api/login",
            json={"password": PASSWORD},
            headers={"X-Requested-With": "kindle-admin"},
        )

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.tmp.cleanup()

    def _headers(self):
        return {"X-Requested-With": "kindle-admin"}

    def test_env_catalog_and_preview(self):
        env = self.client.get("/api/v1/dashboard.env").get_data(as_text=True)
        self.assertIn('PAGES="today week month detail almanac"', env)
        self.assertIn("CLOCK_TODAY_ENABLED=1", env)
        self.assertIn("CLOCK_TODAY_HOUR12=0", env)
        self.assertIn('DASH_MD5="', env)
        self.assertIn("DASH_SCRIPT_URL=", env)
        self.assertIn("R_TODAY_HEADER_X=", env)

        script = self.client.get("/api/v1/script")
        self.assertEqual(script.status_code, 200)
        body = script.get_data()
        self.assertIn(b"dash.sh", body)
        self.assertEqual(script.headers["X-Script-Md5"], __import__("hashlib").md5(body).hexdigest())

        sources = self.client.get("/admin/api/sources", headers=self._headers())
        self.assertEqual(sources.status_code, 200)
        ids = {item["id"] for item in sources.get_json()["data"]["sources"]}
        self.assertEqual(ids, {"weather", "aqi", "quote", "ics"})
        self.assertIn("R_MONTH_TITLE_TMPL=", env)

        catalog = self.client.get("/admin/api/widget-catalog", headers=self._headers())
        self.assertEqual(catalog.status_code, 200)
        body = catalog.get_json()["data"]
        self.assertTrue(any(item["id"] == "weather" for item in body["system"]))
        self.assertEqual(body["center"], [])
        self.assertTrue(body["fields"])
        self.assertEqual({item["id"] for item in body["data_styles"]}, {"hero", "rows", "horizontal", "grid"})
        self.assertTrue(all(item["kind"] == field_kind(item["id"]) for item in body["fields"]))

        settings = self.client.get("/admin/api/settings", headers=self._headers()).get_json()["data"]["settings"]
        page = settings["pages"][0]
        page["layout"] = [block for block in page["layout"] if block["widget"] != "scene"]
        page["layout"].append(
            {"widget": "text", "id": "b1234abcd", "x": 80, "y": 820, "w": 400, "h": 80, "z": 9, "text": "自定义一句", "align": "left"}
        )
        settings["widget_defs"] = [
            {"id": "w1234abcd", "name": "温度", "style": "hero", "fields": ["weather.temperature"]}
        ]
        saved = self.client.post("/admin/api/settings/save", json=settings, headers=self._headers())
        self.assertEqual(saved.status_code, 200, saved.get_data(as_text=True))

        preview = self.client.post(
            "/admin/api/layout-preview",
            json={"page_id": "today", "layout": page["layout"], "widget_defs": settings["widget_defs"]},
            headers=self._headers(),
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.mimetype, "image/png")
        Image.open(io.BytesIO(preview.get_data())).verify()

        missing = self.client.post(
            "/admin/api/assets",
            data={"file": (io.BytesIO(b"not-an-image"), "a.png")},
            headers=self._headers(),
            content_type="multipart/form-data",
        )
        self.assertIn(missing.status_code, (400, 502))
        self.assertIn(missing.get_json()["error"]["code"], {"OSS_NOT_CONFIGURED", "ASSET_TYPE_INVALID"})

    def test_asset_guards_and_catalog_storage_flag(self):
        catalog = self.client.get("/admin/api/widget-catalog", headers=self._headers()).get_json()["data"]
        self.assertEqual(catalog["storage"]["type"], "oss")
        self.assertFalse(catalog["storage"]["configured"])

        empty = self.client.post(
            "/admin/api/assets",
            data={},
            headers=self._headers(),
            content_type="multipart/form-data",
        )
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.get_json()["error"]["code"], "ASSET_EMPTY")

        from server.storage import AssetError, inspect_image

        with self.assertRaises(AssetError) as ctx:
            inspect_image(b"")
        self.assertEqual(ctx.exception.code, "ASSET_EMPTY")

        from server.render.placed import paint_image
        from server.render.regions import Rect

        transparent = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        flattened = paint_image(transparent, Rect(0, 0, 20, 20))
        self.assertEqual(flattened.getpixel((5, 5)), 255)

        placeholder = paint_image(None, Rect(0, 0, 20, 20))
        self.assertEqual(placeholder.getpixel((10, 5)), 255)
        self.assertNotEqual(placeholder.getpixel((7, 7)), 255)

    def test_import_schema1(self):
        raw = {
            "schema_version": 1,
            "pages": [
                {"page_id": "today", "enabled": True, "dwell_s": 90},
                {"page_id": "week", "enabled": True, "dwell_s": 30},
                {"page_id": "month", "enabled": True, "dwell_s": 30},
                {"page_id": "detail", "enabled": True, "dwell_s": 30},
                {"page_id": "almanac", "enabled": True, "dwell_s": 30},
            ],
            "rotation": {"enabled": False, "suppress_s": 10},
            "quote": {"mode": "offline", "custom": []},
            "location": {"name": "南京", "latitude": 32.06, "longitude": 118.79, "timezone": "Asia/Shanghai"},
        }
        resp = self.client.post(
            "/admin/api/settings/import",
            data=json.dumps(raw),
            headers={**self._headers(), "Content-Type": "application/json"},
        )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        saved = self.client.get("/admin/api/settings", headers=self._headers()).get_json()["data"]["settings"]
        self.assertEqual(saved["schema_version"], 3)
        self.assertEqual(saved["location"]["name"], "南京")
        self.assertTrue(saved["pages"][0]["layout"])

    def test_schema3_instance_style_save_preview_export_import(self):
        settings = self.client.get("/admin/api/settings", headers=self._headers()).get_json()["data"]["settings"]
        settings["widget_defs"] = [{"id": "w1234abcd", "name": "天气数据", "style": "rows", "fields": ["weather.temperature", "weather.humidity"]}]
        settings["pages"][0]["layout"] = [{"widget": "custom", "id": "b1234abcd", "def": "w1234abcd", "style": "horizontal", "x": 56, "y": 160, "w": 300, "h": 200, "z": 1}]
        response = self.client.post("/admin/api/settings/save", json=settings, headers=self._headers())
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        preview = self.client.post("/admin/api/layout-preview", json={"page_id": "today", "layout": settings["pages"][0]["layout"], "widget_defs": settings["widget_defs"]}, headers=self._headers())
        self.assertEqual(preview.status_code, 200, preview.get_data(as_text=True) if preview.mimetype != "image/png" else "")
        Image.open(io.BytesIO(preview.data)).verify()
        exported = self.client.get("/admin/api/settings/export", headers=self._headers()).get_json()
        self.assertEqual(exported["schema_version"], 3)
        self.assertEqual(exported["pages"][0]["layout"][0]["style"], "horizontal")
        response = self.client.post("/admin/api/settings/import", json=exported, headers=self._headers())
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        after = self.client.get("/admin/api/settings", headers=self._headers()).get_json()["data"]["settings"]
        self.assertEqual(after["pages"], exported["pages"])
        self.assertEqual(after["widget_defs"][0]["style"], "rows")
        exported["schema_version"] = 2
        exported["pages"][0]["layout"][0].pop("style")
        response = self.client.post("/admin/api/settings/import", json=exported, headers=self._headers())
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        migrated = self.client.get("/admin/api/settings", headers=self._headers()).get_json()["data"]["settings"]
        self.assertEqual(migrated["schema_version"], 3)
        self.assertNotIn("style", migrated["pages"][0]["layout"][0])


if __name__ == "__main__":
    unittest.main()

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

from server.layout import accept_center_item, default_layout
from server.settings import defaults_from_config, validate
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


def _quote_stub(now, mode="online", custom=None):
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
        self.assertEqual(out["schema_version"], 2)
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

    def test_center_item_rejects_code(self):
        self.assertIsNone(accept_center_item({"id": "center.bad", "kind": "data", "review": "approved", "name": "坏", "style": "rows", "fields": ["weather.temperature"], "script": "print(1)"}))
        self.assertIsNone(accept_center_item({"id": "center.ok", "kind": "data", "review": "pending", "name": "等", "style": "rows", "fields": ["weather.temperature"]}))
        item = accept_center_item({"id": "center.ok", "kind": "data", "review": "approved", "name": "温度", "style": "hero", "fields": ["weather.temperature"]})
        self.assertEqual(item["placeable"], True)


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
        self.assertIn("R_TODAY_HEADER_X=", env)
        self.assertIn("R_MONTH_TITLE_TMPL=", env)

        catalog = self.client.get("/admin/api/widget-catalog", headers=self._headers())
        self.assertEqual(catalog.status_code, 200)
        body = catalog.get_json()["data"]
        self.assertTrue(any(item["id"] == "weather" for item in body["system"]))
        self.assertEqual(body["center"], [])
        self.assertTrue(body["fields"])

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
        self.assertEqual(saved["schema_version"], 2)
        self.assertEqual(saved["location"]["name"], "南京")
        self.assertTrue(saved["pages"][0]["layout"])


if __name__ == "__main__":
    unittest.main()

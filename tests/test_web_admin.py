"""web-admin 契约测试。天气与一言外网调用均被替换，不依赖真机。"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from server.quotes import get_quote
from server.settings import defaults_from_config, settings_version, validate
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData

PASSWORD = "test-only-not-a-secret"
ROOT = Path(tempfile.mkdtemp(prefix="kc-admin-"))
os.environ["SETTINGS_PATH"] = str(ROOT / "boot.json")
os.environ["ADMIN_PASSWORD"] = PASSWORD
os.environ["SECRET_KEY"] = "unit-test-secret"
os.environ["ADMIN_LOCK_THRESHOLD"] = "5"
os.environ["ADMIN_LOCK_SECONDS"] = "900"

from server.app import create_app  # noqa: E402

FAKE_WEATHER = WeatherData(
    current=CurrentWeather(temperature=20.0, humidity=50, wind_speed=3.0, code=0, description="晴"),
    daily=[DailyForecast(date="2026-10-10", temp_max=22.0, temp_min=15.0, code=0, description="晴")],
    hourly=[HourlyPoint(time="2026-10-10T15:00", temperature=20.0, precipitation_probability=0, code=0)],
)
DEPLOY = {
    "location_name": "北京",
    "latitude": 39.9042,
    "longitude": 116.4074,
    "timezone": "Asia/Shanghai",
}


def _quote_stub(now, mode="online", custom=None):
    if mode in ("offline", "custom"):
        return get_quote(now, mode, custom)
    return {"text": "测试一言", "from": "单测"}


def _offline_network():
    return (
        patch("server.service.fetch_weather", return_value=FAKE_WEATHER),
        patch("server.service.fetch_aqi", return_value=None),
        patch("server.quotes.get_quote", side_effect=_quote_stub),
    )


class SettingsUnitTests(unittest.TestCase):
    def test_version_ignores_updated_at(self):
        base = defaults_from_config(DEPLOY)
        stamped = json.loads(json.dumps(base))
        stamped["updated_at"] = "2026-10-10T15:30:00+08:00"
        self.assertEqual(settings_version(base), settings_version(stamped))
        self.assertEqual(len(settings_version(base)), 12)

    def test_validate_collects_errors(self):
        raw = defaults_from_config(DEPLOY)
        raw["pages"][0]["enabled"] = False
        raw["pages"][0]["dwell_s"] = 1
        raw["quote"]["mode"] = "nope"
        codes = {item["code"] for item in validate(raw)}
        self.assertIn("TODAY_MUST_BE_FIRST_ENABLED", codes)
        self.assertIn("DWELL_OUT_OF_RANGE", codes)
        self.assertIn("QUOTE_MODE_INVALID", codes)

    def test_quote_rotation_without_network(self):
        now = datetime(2026, 10, 10, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        offline = get_quote(now, "offline")
        self.assertIn("text", offline)
        custom = [{"text": "甲", "from": "一"}, {"text": "乙", "from": "二"}]
        picked = get_quote(now, "custom", custom)
        again = get_quote(now, "custom", custom)
        self.assertEqual(picked, again)
        self.assertIn(picked["text"], {"甲", "乙"})
        self.assertEqual(get_quote(now, "custom", []), offline)


class AdminApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SETTINGS_PATH"] = str(Path(self.tmp.name) / "settings.json")
        os.environ["ADMIN_PASSWORD"] = PASSWORD
        self.patches = _offline_network()
        for item in self.patches:
            item.start()
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.tmp.cleanup()

    def _headers(self):
        return {"X-Requested-With": "kindle-admin", "Content-Type": "application/json"}

    def _login(self, password=PASSWORD):
        return self.client.post("/admin/api/login", json={"password": password}, headers=self._headers())

    def test_disabled_without_password(self):
        os.environ["ADMIN_PASSWORD"] = ""
        try:
            client = create_app().test_client()
            page = client.get("/admin")
            self.assertEqual(page.status_code, 503)
            self.assertIn("管理端未启用", page.get_data(as_text=True))
            api = client.get("/admin/api/settings")
            self.assertEqual(api.status_code, 503)
            self.assertEqual(api.get_json()["error"]["code"], "ADMIN_DISABLED")
            health = client.get("/health")
            self.assertEqual(health.status_code, 200)
        finally:
            os.environ["ADMIN_PASSWORD"] = PASSWORD

    def test_login_csrf_and_lock(self):
        missing = self.client.post("/admin/api/login", json={"password": PASSWORD})
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(missing.get_json()["error"]["code"], "ADMIN_CSRF_REJECTED")
        for _ in range(4):
            bad = self._login("wrong-password")
            self.assertEqual(bad.status_code, 401)
            self.assertEqual(bad.get_json()["error"]["code"], "ADMIN_AUTH_INVALID")
        locked = self._login("wrong-password")
        self.assertEqual(locked.status_code, 429)
        self.assertEqual(locked.get_json()["error"]["code"], "ADMIN_AUTH_LOCKED")
        self.assertGreater(locked.get_json()["error"]["details"][0]["retry_after_s"], 0)
        still = self._login(PASSWORD)
        self.assertEqual(still.status_code, 429)

    def test_save_env_preview_and_device(self):
        self.assertEqual(self._login().status_code, 200)
        current = self.client.get("/admin/api/settings").get_json()["data"]
        self.assertTrue(current["degraded"])
        body = current["settings"]
        body["pages"] = [
            {"page_id": "today", "enabled": True, "dwell_s": 300},
            {"page_id": "month", "enabled": True, "dwell_s": 20},
            {"page_id": "week", "enabled": True, "dwell_s": 20},
            {"page_id": "detail", "enabled": True, "dwell_s": 20},
            {"page_id": "almanac", "enabled": False, "dwell_s": 30},
        ]
        body["rotation"] = {"enabled": True, "suppress_s": 90}
        body["quote"] = {"mode": "custom", "custom": [{"text": "早睡早起", "from": "家里"}]}
        saved = self.client.post("/admin/api/settings/save", json=body, headers=self._headers())
        self.assertEqual(saved.status_code, 200, saved.get_data(as_text=True))
        payload = saved.get_json()["data"]
        self.assertFalse(payload["location_changed"])
        version = payload["settings_version"]

        env = self.client.get("/api/v1/dashboard.env", headers={"User-Agent": "Kindle/2.1"})
        text = env.get_data(as_text=True)
        pages_line = next(line for line in text.splitlines() if line.startswith("PAGES="))
        self.assertEqual(pages_line, 'PAGES="today month week detail"')
        self.assertIn("ROTATE_ENABLED=1", text)
        self.assertIn("ROTATE_TODAY_S=300", text)
        self.assertIn("ROTATE_MONTH_S=20", text)
        self.assertNotIn("ROTATE_ALMANAC_S=", text)
        self.assertIn("ROTATE_OTHER_S=20", text)
        self.assertIn("ROTATE_SUPPRESS_S=90", text)
        self.assertIn(f"SETTINGS_VERSION={version}", text)
        self.assertIn("ROTATE_OTHER_S=20", text)

        dash = self.client.get("/api/v1/dashboard.json")
        data = dash.get_json()
        self.assertEqual(data["pages"], ["today", "month", "week", "detail"])
        self.assertEqual(data["settings_version"], version)
        self.assertEqual(data["quote"]["text"], "早睡早起")

        png = self.client.get("/dashboard.png")
        self.assertEqual(png.status_code, 200)
        self.assertEqual(png.mimetype, "image/png")
        self.assertTrue(png.data.startswith(b"\x89PNG"))
        hidden = self.client.get("/dashboard.png?page=almanac")
        self.assertEqual(hidden.status_code, 200)
        self.assertTrue(hidden.data.startswith(b"\x89PNG"))

        device = self.client.get("/admin/api/device").get_json()["data"]
        self.assertEqual(device["delivery_state"], "delivered")
        self.assertEqual(device["online_state"], "online")
        self.assertEqual(device["delivered_settings_version"], version)
        self.assertEqual(device["last_user_agent"], "Kindle/2.1")

        bad = self.client.post(
            "/admin/api/settings/save",
            json={"pages": []},
            headers=self._headers(),
        )
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.get_json()["error"]["code"], "SETTINGS_VALIDATION_FAILED")
        again = self.client.get("/api/v1/dashboard.env").get_data(as_text=True)
        self.assertIn(f"SETTINGS_VERSION={version}", again)

    def test_import_export_reset(self):
        self._login()
        loaded = self.client.get("/admin/api/settings").get_json()["data"]
        default_name = loaded["defaults"]["location"]["name"]
        original = loaded["settings"]
        original["location"] = {
            "name": "杭州",
            "latitude": 30.2741,
            "longitude": 120.1551,
            "timezone": "Asia/Shanghai",
        }
        moved = self.client.post("/admin/api/settings/save", json=original, headers=self._headers())
        self.assertEqual(moved.status_code, 200, moved.get_data(as_text=True))
        self.assertTrue(moved.get_json()["data"]["location_changed"])
        self.assertTrue(moved.get_json()["data"]["weather_refreshed"])
        health = self.client.get("/health").get_json()
        self.assertEqual(health["location"], "杭州")

        exported = self.client.get("/admin/api/settings/export")
        self.assertEqual(exported.status_code, 200)
        self.assertIn("kindle-calendar-settings-", exported.headers["Content-Disposition"])
        blob = exported.get_data()

        hangzhou = self.client.get("/admin/api/settings").get_json()["data"]["settings"]
        hangzhou["location"]["name"] = "上海"
        hangzhou["location"]["latitude"] = 31.2304
        hangzhou["location"]["longitude"] = 121.4737
        self.client.post("/admin/api/settings/save", json=hangzhou, headers=self._headers())

        rejected = self.client.post(
            "/admin/api/settings/import",
            data=b"not-json",
            headers={"X-Requested-With": "kindle-admin", "Content-Type": "application/json"},
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.get_json()["error"]["code"], "SETTINGS_IMPORT_INVALID")
        self.assertEqual(self.client.get("/health").get_json()["location"], "上海")

        restored = self.client.post(
            "/admin/api/settings/import",
            data=blob,
            headers={"X-Requested-With": "kindle-admin", "Content-Type": "application/json"},
        )
        self.assertEqual(restored.status_code, 200, restored.get_data(as_text=True))
        self.assertEqual(self.client.get("/health").get_json()["location"], "杭州")

        reset = self.client.post("/admin/api/settings/reset", headers=self._headers())
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.get_json()["data"]["settings"]["location"]["name"], default_name)

    def test_corrupt_file_is_degraded(self):
        path = Path(os.environ["SETTINGS_PATH"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{", encoding="utf-8")
        client = create_app().test_client()
        client.post("/admin/api/login", json={"password": PASSWORD}, headers=self._headers())
        data = client.get("/admin/api/settings").get_json()["data"]
        self.assertTrue(data["degraded"])
        self.assertEqual(data["settings"]["location"]["name"], data["defaults"]["location"]["name"])

    def test_geocode_and_dash_contract(self):
        self._login()
        empty = self.client.get("/admin/api/geocode?q=")
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.get_json()["error"]["code"], "GEOCODE_QUERY_INVALID")

        class _Resp:
            status_code = 200
            is_redirect = False

            def json(self):
                return {
                    "results": [
                        {
                            "name": "杭州",
                            "admin1": "浙江省",
                            "country": "中国",
                            "latitude": 30.27415,
                            "longitude": 120.15515,
                            "timezone": "Asia/Shanghai",
                        }
                    ]
                }

        with patch("server.admin.requests.get", return_value=_Resp()):
            found = self.client.get("/admin/api/geocode?q=杭州")
        self.assertEqual(found.status_code, 200)
        item = found.get_json()["data"]["candidates"][0]
        self.assertEqual(item["latitude"], 30.2741)
        self.assertEqual(item["timezone"], "Asia/Shanghai")

        dash = Path("kindle/dash.sh").read_text(encoding="utf-8")
        self.assertNotIn("LOCAL_ROTATE", dash)
        self.assertIn("ROTATE_${upper}_S", dash)
        self.assertNotIn('[ "$CUR_PAGE" = "almanac" ]', dash)
        example = Path("kindle/config.sh.example").read_text(encoding="utf-8")
        self.assertIn("兜底", example)


if __name__ == "__main__":
    unittest.main()

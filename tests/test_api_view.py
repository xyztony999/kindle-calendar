"""接口阅读页：浏览器看到 HTML，机器请求仍是 JSON 或 env。不访问外网。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from markupsafe import escape

from server.reading import prefer_html
from server.service import DashboardService
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData

FAKE_WEATHER = WeatherData(
    current=CurrentWeather(temperature=20.0, humidity=50, wind_speed=3.0, code=0, description="晴"),
    daily=[DailyForecast(date="2026-10-11", temp_max=22.0, temp_min=15.0, code=0, description="晴")],
    hourly=[HourlyPoint(time="2026-10-11T15:00", temperature=20.0, precipitation_probability=10, code=0)],
)

HTML = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
JSON_ACCEPT = {"Accept": "application/json"}
ANY = {"Accept": "*/*"}


def _offline():
    return (
        patch("server.service.fetch_weather", return_value=FAKE_WEATHER),
        patch("server.service.fetch_aqi", return_value=None),
        patch("server.quotes.get_quote", return_value={"text": "测试一言", "from": "单测"}),
    )


class PreferHtmlTests(unittest.TestCase):
    def test_format_wins_over_accept(self):
        self.assertFalse(prefer_html("json", "text/html"))
        self.assertFalse(prefer_html(" JSON ", HTML["Accept"]))
        self.assertTrue(prefer_html("html", "*/*"))
        self.assertFalse(prefer_html("xml", "text/html"))

    def test_only_explicit_html_beats_json(self):
        self.assertTrue(prefer_html(None, HTML["Accept"]))
        self.assertTrue(prefer_html("", "text/html, application/json;q=0.9"))
        self.assertFalse(prefer_html(None, "*/*"))
        self.assertFalse(prefer_html(None, None))
        self.assertFalse(prefer_html(None, "text/html, application/json"))
        self.assertFalse(prefer_html(None, "application/json"))
        self.assertFalse(prefer_html(None, "text/html;q=0"))


class ReadingRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SETTINGS_PATH"] = str(Path(self.tmp.name) / "settings.json")
        self.patches = _offline()
        for item in self.patches:
            item.start()
        from server.app import create_app

        self.client = create_app().test_client()

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.tmp.cleanup()

    def test_browser_gets_reading_pages(self):
        dashboard = self.client.get("/api/v1/dashboard.json", headers=HTML)
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("text/html", dashboard.content_type)
        body = dashboard.get_data(as_text=True)
        self.assertIn("<h1>", body)
        self.assertIn("测试一言", body)
        self.assertIn("查看逐时", body)
        self.assertNotIn("<img", body)
        self.assertTrue(body.lstrip().startswith("<!DOCTYPE html>"))

        weather = self.client.get("/weather", headers=HTML)
        self.assertIn("text/html", weather.content_type)
        self.assertIn("逐时", weather.get_data(as_text=True))
        self.assertIn("15:00", weather.get_data(as_text=True))

        health = self.client.get("/health", headers=HTML)
        self.assertIn("服务状态", health.get_data(as_text=True))
        self.assertNotIn('{"status"', health.get_data(as_text=True))

        env = self.client.get("/api/v1/dashboard.env", headers=HTML)
        page = env.get_data(as_text=True)
        self.assertIn("设备清单", page)
        self.assertIn("打开本页会计一次拉取", page)
        self.assertIn("<details>", page)
        self.assertTrue(page.lstrip().startswith("<!DOCTYPE html>"))

    def test_machines_keep_original_bodies(self):
        for headers in (None, ANY, JSON_ACCEPT):
            dash = self.client.get("/api/v1/dashboard.json", headers=headers)
            self.assertTrue(dash.is_json, headers)
            self.assertEqual(dash.get_json()["quote"]["text"], "测试一言")
            self.assertEqual(dash.get_json()["weather"]["current"]["description"], "晴")
            self.assertEqual(dash.headers.get("Vary"), "Accept")

            weather = self.client.get("/weather", headers=headers)
            self.assertTrue(weather.is_json)
            self.assertEqual(set(weather.get_json()), {"current", "daily", "hourly"})
            self.assertNotIn("precip_prob", weather.get_json())

            health = self.client.get("/health", headers=headers)
            self.assertEqual(health.get_json()["status"], "ok")
            self.assertIn("screen", health.get_json())

            env = self.client.get("/api/v1/dashboard.env", headers=headers)
            text = env.get_data(as_text=True)
            self.assertTrue(text.startswith("DASH_DATE=") or "DASH_DATE=" in text.splitlines()[0])
            self.assertNotIn("<html", text)
            self.assertIn("PAGES=", text)
            self.assertTrue(env.content_type.startswith("text/plain"))

        forced = self.client.get("/api/v1/dashboard.json?format=json", headers=HTML)
        self.assertTrue(forced.is_json)
        forced_env = self.client.get("/api/v1/dashboard.env?format=json", headers=HTML)
        self.assertNotIn("<html", forced_env.get_data(as_text=True))
        self.assertIn("SCREEN_W=", forced_env.get_data(as_text=True))

    def test_format_html_and_unknown_format(self):
        page = self.client.get("/health?format=html", headers=ANY)
        self.assertIn("服务状态", page.get_data(as_text=True))
        raw = self.client.get("/health?format=xml", headers=HTML)
        self.assertTrue(raw.is_json)

    def test_web_language_does_not_change_machine_body(self):
        self.client.set_cookie("kc_lang", "en")
        machine = self.client.get("/weather", headers={**JSON_ACCEPT, "Accept-Language": "en"})
        self.assertEqual(machine.get_json()["current"]["description"], "晴")
        self.assertIsNone(machine.headers.get("Set-Cookie"))

        page = self.client.get("/weather", headers={**HTML, "Accept-Language": "zh-CN"})
        body = page.get_data(as_text=True)
        self.assertIn("Clear sky", body)
        self.assertIn(">Humidity<", body)
        self.assertIn('href="/weather?format=json&amp;lang=en"', body)

        explicit = self.client.get("/weather?lang=zh", headers=HTML)
        self.assertIn("晴", explicit.get_data(as_text=True))
        self.assertIn("kc_lang=zh", explicit.headers.get("Set-Cookie", ""))
        english_raw = self.client.get("/weather?lang=en")
        self.assertEqual(english_raw.get_json()["current"]["description"], "Clear sky")
        self.assertIsNone(english_raw.headers.get("Set-Cookie"))

    def test_env_source_matches_machine_text_and_counts_one_heartbeat(self):
        calls = []
        real = DashboardService.note_heartbeat

        def wrapped(self, ip, ua):
            calls.append(ua)
            return real(self, ip, ua)

        with patch.object(DashboardService, "note_heartbeat", wrapped):
            raw = self.client.get("/api/v1/dashboard.env")
            page = self.client.get("/api/v1/dashboard.env", headers=HTML)
        self.assertEqual(len(calls), 2)
        self.assertIn(str(escape(raw.get_data(as_text=True))), page.get_data(as_text=True))

    def test_html_failure_hides_stack_and_skips_heartbeat(self):
        calls = []

        def boom(self, *args, **kwargs):
            raise RuntimeError("secret-stack")

        with patch.object(DashboardService, "get_payload", boom), patch.object(
            DashboardService, "note_heartbeat", lambda *args, **kwargs: calls.append(1)
        ):
            machine = self.client.get("/weather")
            page = self.client.get("/weather", headers=HTML)
            env_page = self.client.get("/api/v1/dashboard.env", headers=HTML)
        self.assertEqual(machine.status_code, 500)
        self.assertNotIn("天气暂时读不到", machine.get_data(as_text=True))
        self.assertEqual(page.status_code, 500)
        self.assertIn("天气暂时读不到", page.get_data(as_text=True))
        self.assertNotIn("secret-stack", page.get_data(as_text=True))
        self.assertEqual(env_page.status_code, 500)
        self.assertEqual(calls, [])

    def test_escapes_untrusted_text(self):
        real = DashboardService.get_payload

        def wrapped(self, lang="zh"):
            data = real(self, lang)
            data["location"] = "<img src=x onerror=alert(1)>"
            return data

        real_health = DashboardService.health_info

        def health(self):
            info = real_health(self)
            info["last_error"] = "<script>alert(1)</script>"
            return info

        with patch.object(DashboardService, "get_payload", wrapped), patch.object(DashboardService, "health_info", health):
            page = self.client.get("/api/v1/dashboard.json", headers=HTML)
            status = self.client.get("/health", headers=HTML)
        self.assertIn("&lt;img", page.get_data(as_text=True))
        self.assertNotIn("<img", page.get_data(as_text=True))
        self.assertIn("&lt;script&gt;", status.get_data(as_text=True))
        self.assertNotIn("<script>", status.get_data(as_text=True))

    def test_png_and_admin_api_stay_machine_readable(self):
        png = self.client.get("/r/today/clock/0.png", headers=HTML)
        self.assertEqual(png.mimetype, "image/png")
        self.assertTrue(png.data.startswith(b"\x89PNG"))
        admin = self.client.get("/admin/api/settings", headers=HTML)
        self.assertTrue(admin.is_json)

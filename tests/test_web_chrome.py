"""网页外观：顶栏、两态明暗、三个图地址的承载页。不访问外网。"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.service import DashboardService
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData

FAKE_WEATHER = WeatherData(
    current=CurrentWeather(temperature=20.0, humidity=50, wind_speed=3.0, code=0, description="晴"),
    daily=[DailyForecast(date="2026-10-15", temp_max=22.0, temp_min=15.0, code=0, description="晴")],
    hourly=[HourlyPoint(time="2026-10-15T15:00", temperature=20.0, precipitation_probability=10, code=0)],
)

HTML = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
ANY = {"Accept": "*/*"}
IMAGE = {"Accept": "image/png,image/webp,image/*;q=0.8,*/*;q=0.5"}


def _offline():
    return (
        patch("server.service.fetch_weather", return_value=FAKE_WEATHER),
        patch("server.service.fetch_aqi", return_value=None),
        patch("server.quotes.get_quote", return_value={"text": "测试一言", "from": "单测"}),
    )


class WebChromeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SETTINGS_PATH"] = str(Path(self.tmp.name) / "settings.json")
        os.environ["ADMIN_PASSWORD"] = "test-only-not-a-secret"
        self.patches = _offline()
        for item in self.patches:
            item.start()
        from server.app import create_app

        self.client = create_app().test_client()

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.tmp.cleanup()

    def test_admin_login_chrome_is_one_language_button(self):
        body = self.client.get("/admin").get_data(as_text=True)
        nav = body[body.index('class="topbar"'):body.index("</nav>")]
        self.assertLess(nav.index("theme-btn"), nav.index("lang-link"))
        self.assertLess(nav.index("lang-link"), nav.index("back-home"))
        self.assertIn(">English<", nav)
        self.assertIn(">返回首页<", nav)
        self.assertNotIn("lang-seg", body)
        self.assertNotIn(">中<", nav)
        self.assertNotIn(">EN<", nav)
        self.assertEqual(body.count("返回首页"), 1)
        self.assertIn("Kindle 台历 · 管理端", body)
        self.assertIn("#2a2622", body)
        self.assertIn("#f4f1ea", body)
        self.assertIn("#8a8175", body)
        self.assertNotIn("THEME_ORDER", body)
        self.assertNotIn('"auto"', body)

    def test_theme_cookie_is_only_light_or_dark(self):
        self.client.set_cookie("kc_theme", "dark")
        dark = self.client.get("/admin").get_data(as_text=True)
        self.assertIn('data-theme="dark"', dark)
        self.client.set_cookie("kc_theme", "light")
        light = self.client.get("/").get_data(as_text=True)
        self.assertIn('data-theme="light"', light)
        self.client.set_cookie("kc_theme", "auto")
        follow = self.client.get("/admin").get_data(as_text=True)
        self.assertNotRegex(follow, r"<html[^>]*data-theme=")
        reading = self.client.get("/health", headers=HTML).get_data(as_text=True)
        self.assertNotRegex(reading, r"<html[^>]*data-theme=")
        self.assertIn("切换到深色", reading)
        self.assertIn("原始数据", reading)
        self.assertLess(reading.index("theme-btn"), reading.index("原始数据"))
        self.assertLess(reading.index("原始数据"), reading.index("返回首页"))

    def test_shared_brand_and_browser_icons_are_served_on_web_pages(self):
        import re

        for url in ("/", "/admin", "/health", "/dashboard.png?format=html"):
            page = self.client.get(url, headers=HTML)
            self.assertEqual(page.status_code, 200, url)
            body = page.get_data(as_text=True)
            self.assertIn('class="brand-icon"', body, url)
            for icon_url in re.findall(r'<link rel="(?:icon|apple-touch-icon)" href="([^"]+)"', body):
                with self.client.get(icon_url) as icon:
                    self.assertEqual(icon.status_code, 200, icon_url)
                    self.assertTrue(icon.data, icon_url)
            self.assertIn('/static/brand/favicon.svg', body, url)
            self.assertIn('/static/brand/favicon.ico', body, url)
            self.assertIn('/static/brand/apple-touch-icon.png', body, url)

        with self.client.get('/static/brand/favicon.svg') as response:
            favicon = response.get_data(as_text=True)
        self.assertIn('prefers-color-scheme: dark', favicon)
        self.assertLess(favicon.index('color: #1a1814'), favicon.index('color: #f4f1ea'))

    def test_quote_library_reference_links_serve_current_document_and_example(self):
        docs = Path(__file__).resolve().parents[1] / 'docs'
        for name in ('quote-library.md', 'quote-library.example.json'):
            with self.client.get('/static/docs/' + name) as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, (docs / name).read_bytes())

    def test_image_urls_negotiate_html_or_png(self):
        urls = (
            "/r/today/header.png",
            "/r/today/clock/0.png",
            "/dashboard.png?page=today",
        )
        for url in urls:
            page = self.client.get(url, headers=HTML)
            self.assertEqual(page.status_code, 200, url)
            self.assertIn("text/html", page.content_type, url)
            body = page.get_data(as_text=True)
            self.assertIn("返回首页", body)
            self.assertIn("查看原图", body)
            self.assertIn("format=png", body)
            self.assertIn("Accept", page.headers["Vary"])
            self.assertFalse(page.data.startswith(b"\x89PNG"))

            machine = self.client.get(url, headers=ANY)
            forced = self.client.get(url + ("&" if "?" in url else "?") + "format=png", headers=HTML)
            image = self.client.get(url, headers=IMAGE)
            for resp in (machine, forced, image):
                self.assertEqual(resp.mimetype, "image/png", url)
                self.assertTrue(resp.data.startswith(b"\x89PNG"), url)
                self.assertEqual(resp.headers["ETag"], machine.headers["ETag"], url)
                self.assertEqual(resp.data, machine.data, url)
                self.assertIn("Accept", resp.headers["Vary"])

        html_forced = self.client.get("/dashboard.png?format=html", headers=ANY)
        self.assertIn("text/html", html_forced.content_type)

    def test_png_miss_stays_plain_text_without_html_accept(self):
        browser = self.client.get("/r/today/no-such.png", headers=HTML)
        self.assertEqual(browser.status_code, 404)
        self.assertIn("text/html", browser.content_type)
        self.assertIn("返回首页", browser.get_data(as_text=True))
        device = self.client.get("/r/today/no-such.png", headers=ANY)
        self.assertEqual(device.status_code, 404)
        self.assertEqual(device.get_data(as_text=True), "not found")

    def test_image_page_does_not_count_as_heartbeat(self):
        with patch.object(DashboardService, "note_heartbeat") as beat:
            self.client.get("/dashboard.png", headers=HTML)
            self.client.get("/r/today/header.png", headers=ANY)
            beat.assert_not_called()

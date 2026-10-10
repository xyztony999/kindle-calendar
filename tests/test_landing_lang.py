"""落地页语言与 JSON 清单。不访问外网。"""

from __future__ import annotations

import unittest

from server.app import create_app
from server.landing import resolve_landing_lang

HTML = {"Accept": "text/html"}


class ResolveLangTests(unittest.TestCase):
    def test_default_and_explicit(self):
        self.assertEqual(resolve_landing_lang(None, None), "zh")
        self.assertEqual(resolve_landing_lang("", ""), "zh")
        self.assertEqual(resolve_landing_lang("en", "zh-CN"), "en")
        self.assertEqual(resolve_landing_lang("zh", "en"), "zh")
        self.assertEqual(resolve_landing_lang("fr", None), "zh")
        self.assertEqual(resolve_landing_lang("fr", "en"), "en")
        self.assertEqual(resolve_landing_lang(None, "zh-CN", "en"), "en")
        self.assertEqual(resolve_landing_lang("zh", "en", "en"), "zh")

    def test_accept_language_quality(self):
        self.assertEqual(resolve_landing_lang(None, "en-US,en;q=0.9"), "en")
        self.assertEqual(resolve_landing_lang(None, "zh-CN,zh;q=0.9,en;q=0.8"), "zh")
        self.assertEqual(resolve_landing_lang(None, "en;q=0.5,zh;q=0.5"), "en")
        self.assertEqual(resolve_landing_lang(None, "fr,de;q=0.8"), "zh")


class LandingRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_chinese_is_default(self):
        res = self.client.get("/", headers=HTML)
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn('lang="zh-CN"', body)
        self.assertIn("把闲置 Kindle", body)
        self.assertIn("今日", body)
        self.assertIn("一周", body)
        self.assertIn('href="/?lang=en"', body)
        self.assertIn(">English<", body)
        self.assertIn(">管理端<", body)
        self.assertIn("github.com/xyztony999/kindle-calendar", body)
        self.assertIn('href="/?format=json"', body)

    def test_english_query_and_link(self):
        res = self.client.get("/?lang=en", headers=HTML)
        body = res.get_data(as_text=True)
        self.assertIn('lang="en"', body)
        self.assertIn("Turn an idle Kindle", body)
        self.assertIn(">Today<", body)
        self.assertIn(">Week<", body)
        self.assertIn('href="/?lang=zh"', body)
        self.assertIn(">中文<", body)
        self.assertIn(">Admin<", body)
        self.assertNotIn("把闲置 Kindle", body)
        self.assertNotIn(">管理端<", body)
        self.assertIn("github.com/xyztony999/kindle-calendar", body)
        self.assertIn('data-page="almanac"', body)

    def test_explicit_chinese_beats_accept_language(self):
        res = self.client.get("/?lang=zh", headers={**HTML, "Accept-Language": "en"})
        self.assertIn("把闲置 Kindle", res.get_data(as_text=True))

    def test_accept_language_english(self):
        res = self.client.get("/", headers={**HTML, "Accept-Language": "en-US,en;q=0.9,zh;q=0.5"})
        self.assertIn("Turn an idle Kindle", res.get_data(as_text=True))

    def test_cookie_remembers_english(self):
        first = self.client.get("/?lang=en", headers=HTML)
        self.assertIn("kc_lang=en", first.headers.get("Set-Cookie", ""))
        self.client.set_cookie("kc_lang", "en")
        again = self.client.get("/", headers={**HTML, "Accept-Language": "zh-CN"})
        self.assertIn("Turn an idle Kindle", again.get_data(as_text=True))

    def test_admin_follows_cookie_and_keeps_codes(self):
        page = self.client.get("/admin?lang=en", headers=HTML)
        body = page.get_data(as_text=True)
        self.assertIn('lang="en"', body)
        self.assertTrue("Admin is off" in body or "Enter the admin password" in body)
        self.assertIn('href="/admin?lang=zh"', body)
        fresh = create_app().test_client()
        zh = fresh.get("/admin", headers=HTML)
        self.assertTrue("管理端未启用" in zh.get_data(as_text=True) or "请输入管理员口令" in zh.get_data(as_text=True))
        self.assertIn('lang="zh-CN"', zh.get_data(as_text=True))

    def test_json_catalog_unchanged(self):
        for path, headers in (
            ("/?format=json", HTML),
            ("/?lang=en&format=json", HTML),
            ("/", {"Accept": "application/json"}),
        ):
            res = self.client.get(path, headers=headers)
            self.assertEqual(res.status_code, 200, path)
            self.assertTrue(res.is_json, path)
            data = res.get_json()
            self.assertEqual(data["name"], "kindle-calendar")
            self.assertEqual(data["endpoints"]["/health"], "健康检查")
            self.assertNotIn("<html", res.get_data(as_text=True))

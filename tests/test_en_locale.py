"""设备语言、英文界面词与中文缺省契约。不访问外网。"""

from __future__ import annotations

import unittest

from server.locale import device_lang, localize_payload, translate_message, with_lang_query, zodiac_en
from server.render.pages import almanac, common
from server.render.regions import Rect
from server.weather import describe_weather


def _date() -> dict:
    return {
        "iso": "2026-10-10",
        "month_day_cn": "十月十日",
        "weekday": "六",
        "festivals": ["重阳"],
        "lunar": "八月廿九",
        "ganzhi_year": "丙午",
        "zodiac": "马",
        "yi": ["祭祀"],
        "ji": ["嫁娶"],
        "wuhou": "鸿雁来",
        "next_solar_term": "霜降",
        "solar_term": {"name": "寒露", "days_since": 3},
    }


class LocaleContractTests(unittest.TestCase):
    def test_device_lang_defaults_chinese(self):
        self.assertEqual(device_lang(None), "zh")
        self.assertEqual(device_lang(""), "zh")
        self.assertEqual(device_lang("zh-CN"), "zh")
        self.assertEqual(device_lang("fr"), "zh")
        self.assertEqual(device_lang("en-US"), "en")

    def test_english_urls_only(self):
        self.assertEqual(with_lang_query("http://h/r/today/header.png", "zh"), "http://h/r/today/header.png")
        self.assertEqual(with_lang_query("http://h/r/today/header.png", "en"), "http://h/r/today/header.png?lang=en")
        self.assertEqual(
            with_lang_query("http://h/r/month/title.png?offset={o}", "en"),
            "http://h/r/month/title.png?offset={o}&lang=en",
        )

    def test_payload_keeps_almanac_and_quote(self):
        payload = {
            "quote": {"text": "欲把西湖比西子", "from": "苏轼"},
            "weather": {"current": {"code": 0, "description": "晴"}, "daily": [{"code": 61, "description": "小雨"}]},
            "date": _date(),
        }
        english = localize_payload(payload)
        self.assertEqual(payload["weather"]["current"]["description"], "晴")
        self.assertEqual(english["weather"]["current"]["description"], "Clear sky")
        self.assertEqual(english["weather"]["daily"][0]["description"], "Slight rain")
        self.assertEqual(english["date"]["yi"], ["祭祀"])
        self.assertEqual(english["date"]["solar_term"]["name"], "寒露")
        self.assertEqual(english["quote"]["text"], "欲把西湖比西子")
        self.assertEqual(describe_weather(99, "en"), "Thunderstorm with heavy hail")
        self.assertEqual(describe_weather(99), "雷暴伴大冰雹")
        self.assertEqual(zodiac_en("龙"), "Dragon")

    def test_validation_message_keeps_code_text_separate(self):
        self.assertEqual(translate_message("zh", "配置校验失败"), "配置校验失败")
        self.assertEqual(translate_message("en", "配置校验失败"), "Settings are invalid")
        self.assertEqual(translate_message("en", "停留秒数须为 5–3600 的整数"), "Dwell must be an integer from 5 to 3600")
        self.assertEqual(translate_message("en", "宜忌原文"), "宜忌原文")

    def test_english_header_differs_and_almanac_draws(self):
        base = {"date": _date(), "holiday": {"name": "国庆节", "note": "休"}, "pages": ["today", "week", "month", "detail", "almanac"]}
        rect = Rect(0, 0, 758, 78)
        zh = common.render_header(base, rect, "", "today")
        en = common.render_header({**base, "ui_lang": "en"}, rect, "", "today")
        self.assertNotEqual(zh.tobytes(), en.tobytes())
        main = Rect(0, 0, 758, 800)
        zh_main = almanac.render_main(base, main, "")
        en_main = almanac.render_main({**base, "ui_lang": "en"}, main, "")
        self.assertNotEqual(zh_main.tobytes(), en_main.tobytes())

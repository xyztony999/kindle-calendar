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

    def test_payload_translates_almanac_and_keeps_chinese_source(self):
        from datetime import datetime

        payload = {
            "quote": {"text": "欲把西湖比西子", "from": "苏轼"},
            "holiday": {"name": "国庆节", "note": "休"},
            "weather": {"current": {"code": 0, "description": "晴"}, "daily": [{"code": 61, "description": "小雨"}]},
            "date": _date(),
        }
        english = localize_payload(payload, "offline", None, datetime(2026, 10, 10))
        self.assertEqual(payload["weather"]["current"]["description"], "晴")
        self.assertEqual(payload["date"]["yi"], ["祭祀"])
        self.assertEqual(english["weather"]["current"]["description"], "Clear sky")
        self.assertEqual(english["weather"]["daily"][0]["description"], "Slight rain")
        self.assertEqual(english["date"]["yi"], ["Worship"])
        self.assertEqual(english["date"]["ji"], ["Marry"])
        self.assertEqual(english["date"]["solar_term"]["name"], "Cold Dew")
        self.assertEqual(english["date"]["next_solar_term"], "Frost's Descent")
        self.assertEqual(english["date"]["wuhou"], "Wild geese arrive")
        self.assertEqual(english["date"]["lunar"], "29th day, 8th lunar month")
        self.assertEqual(english["date"]["ganzhi_year"], "Bingwu")
        self.assertEqual(english["date"]["festivals"], ["重阳"])
        self.assertEqual(english["holiday"]["name"], "National Day")
        self.assertIn(english["quote"]["text"], {
            "To be, or not to be.",
            "All the world's a stage.",
            "Parting is such sweet sorrow.",
            "I wandered lonely as a cloud.",
            "The child is father of the man.",
            "If Winter comes, can Spring be far behind?",
            "A thing of beauty is a joy for ever.",
            "Beauty is truth, truth beauty.",
            "Tyger, tyger, burning bright.",
            "Hope is the thing with feathers.",
            "I celebrate myself.",
            "I am the master of my fate.",
        })
        self.assertNotIn("zenquotes", english["quote"]["from"].lower())
        self.assertEqual(describe_weather(99, "en"), "Thunderstorm with heavy hail")
        self.assertEqual(describe_weather(99), "雷暴伴大冰雹")
        self.assertEqual(zodiac_en("龙"), "Dragon")

    def test_validation_message_keeps_code_text_separate(self):
        self.assertEqual(translate_message("zh", "配置校验失败"), "配置校验失败")
        self.assertEqual(translate_message("en", "配置校验失败"), "Settings are invalid")
        self.assertEqual(translate_message("en", "停留秒数须为 5–3600 的整数"), "Dwell must be an integer from 5 to 3600")
        self.assertEqual(translate_message("en", "宜忌原文"), "宜忌原文")

    def test_english_header_differs_and_almanac_draws(self):
        from datetime import datetime

        base = {
            "date": _date(),
            "holiday": {"name": "国庆节", "note": "休"},
            "quote": {"text": "原文", "from": "出处"},
            "pages": ["today", "week", "month", "detail", "almanac"],
        }
        english = localize_payload(base, "offline", None, datetime(2026, 10, 10))
        rect = Rect(0, 0, 758, 78)
        zh = common.render_header(base, rect, "", "today")
        en = common.render_header(english, rect, "", "today")
        self.assertNotEqual(zh.tobytes(), en.tobytes())
        main = Rect(0, 0, 758, 800)
        zh_main = almanac.render_main(base, main, "")
        en_main = almanac.render_main(english, main, "")
        self.assertNotEqual(zh_main.tobytes(), en_main.tobytes())

    def test_zenquotes_today_falls_back_when_request_fails(self):
        from datetime import datetime
        from unittest.mock import patch

        from server.quotes import english_quote

        now = datetime(2026, 10, 11, 8, 0)
        with patch("server.quotes.requests.get", side_effect=TimeoutError("slow")):
            quote = english_quote(now, "online")
        self.assertIn(quote["from"], {"Shakespeare", "Wordsworth", "Shelley", "Keats", "Blake", "Dickinson", "Whitman", "Henley"})
        self.assertNotIn("http", quote["from"])
        with patch("server.quotes.requests.get") as get:
            response = get.return_value
            response.raise_for_status.return_value = None
            response.json.return_value = [{"q": "A short line.", "a": "Ada"}]
            fresh = datetime(2026, 10, 12, 8, 0)
            quote = english_quote(fresh, "online")
            self.assertEqual(quote, {"text": "A short line.", "from": "Ada"})
            self.assertEqual(get.call_args.args[0], "https://zenquotes.io/api/today")
            self.assertFalse(get.call_args.kwargs["allow_redirects"])
            self.assertEqual(get.call_args.kwargs["timeout"], 8)
            again = english_quote(fresh, "online")
            self.assertEqual(again["text"], "A short line.")
            self.assertEqual(get.call_count, 1)

    def test_custom_quote_stays_and_wide_line_uses_local(self):
        from datetime import datetime
        from unittest.mock import patch

        from server.quotes import english_quote

        now = datetime(2026, 10, 11, 8, 0)
        custom = english_quote(now, "custom", [{"text": "用户原文", "from": "我"}])
        self.assertEqual(custom, {"text": "用户原文", "from": "我"})
        with patch("server.quotes.requests.get") as get:
            response = get.return_value
            response.raise_for_status.return_value = None
            response.json.return_value = [{"q": "word " * 80, "a": "Someone"}]
            quote = english_quote(datetime(2026, 10, 13, 8, 0), "online")
        self.assertNotIn("word word", quote["text"])
        self.assertIn(quote["from"], {"Shakespeare", "Wordsworth", "Shelley", "Keats", "Blake", "Dickinson", "Whitman", "Henley"})

    def test_unknown_yiji_stays_chinese_and_leap_month(self):
        from server.almanac_en import festival_en, lunar_cell, lunar_phrase, yiji_en

        self.assertEqual(yiji_en(["没有这个词"]), ["没有这个词"])
        self.assertEqual(festival_en("龙头节"), "龙头节")
        self.assertEqual(lunar_phrase("闰六月初二"), "2nd day, leap 6th lunar month")
        self.assertEqual(lunar_cell("闰六月"), "leap 6th")
        self.assertEqual(lunar_cell("九月"), "9th month")
        self.assertEqual(lunar_cell("初二"), "2nd")

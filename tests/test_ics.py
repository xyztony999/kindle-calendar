"""ICS 数据源与纪念日：解析、重复规则、窗口合并、缓存降级与配置校验。"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from server import ics
from server.settings import defaults_from_config, normalize, validate

TZ = ZoneInfo("Asia/Shanghai")

ICS_FIXTURE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
SUMMARY:周会
DTSTART:20261026T020000Z
DTEND:20261026T030000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:全天活动
DTSTART;VALUE=DATE:20261027
END:VEVENT
BEGIN:VEVENT
SUMMARY:每周站会
DTSTART:20261025T060000Z
RRULE:FREQ=WEEKLY;COUNT=4
END:VEVENT
END:VCALENDAR
"""


class IcsTests(unittest.TestCase):
    def tearDown(self):
        ics._events = []
        ics._fetched_at = 0.0

    def test_parse_events(self):
        now = datetime(2026, 10, 26, 9, 0, tzinfo=TZ)
        events = ics._parse_events(
            ICS_FIXTURE,
            now.astimezone(ics.dt_timezone.utc) - timedelta(days=1),
            now.astimezone(ics.dt_timezone.utc) + timedelta(days=8),
            TZ,
        )
        by_title: dict[str, list[dict]] = {}
        for e in events:
            by_title.setdefault(e["title"], []).append(e)
        meeting = by_title["周会"][0]
        self.assertEqual(meeting["iso_date"], "2026-10-26")
        self.assertEqual(meeting["time"], "10:00")  # 02:00Z → 10:00 +08
        self.assertFalse(meeting["all_day"])
        allday = by_title["全天活动"][0]
        self.assertTrue(allday["all_day"])
        self.assertEqual(allday["iso_date"], "2026-10-27")
        self.assertGreaterEqual(len(by_title["每周站会"]), 2)  # RRULE 展开

    def test_occurrences(self):
        today = date(2026, 10, 26)
        self.assertEqual(ics._occurrences("", "2026-12-25", "none", today), [date(2026, 12, 25)])
        self.assertEqual(ics._occurrences("", "2026-01-01", "none", today), [])
        self.assertEqual(ics._occurrences("", "10-28", "yearly", today), [date(2026, 10, 28), date(2027, 10, 28)])
        self.assertEqual(ics._occurrences("", "10-26", "yearly", today)[0], today)
        lunar = ics._occurrences("", "08-16", "lunar", today)
        self.assertTrue(lunar and all(d >= today for d in lunar))

    def test_anniversary_data_and_merge(self):
        today = date(2026, 10, 26)
        anniv = [
            {"id": "e1", "name": "妈妈生日", "date": "10-27", "repeat": "yearly"},
            {"id": "e2", "name": "纪念日", "date": "2027-05-01", "repeat": "none"},
        ]
        events, countdowns = ics.anniversary_data(anniv, today)
        self.assertEqual(events[0]["iso_date"], "2026-10-27")
        self.assertEqual(events[0]["source"], "anniv")
        self.assertEqual(countdowns[0]["days"], 1)
        merged = ics.merge([{"iso_date": "2026-10-26", "time": "09:00", "all_day": False, "title": "周会", "source": "ics"}], events, today)
        self.assertEqual([e["title"] for e in merged], ["周会", "妈妈生日"])

    def test_refresh_failure_keeps_old_and_ttl(self):
        ics.refresh([], TZ, datetime(2026, 10, 26, 8, 0, tzinfo=TZ))
        self.assertFalse(ics.health()["enabled"])
        ics._events = [{"iso_date": "2026-10-26", "time": None, "all_day": True, "title": "旧", "source": "ics"}]
        ics._fetched_at = 0.0
        now = datetime(2026, 10, 26, 9, 0, tzinfo=TZ)
        with patch.object(ics, "_fetch_ics", side_effect=RuntimeError("boom")):
            out = ics.refresh(["https://example.com/a.ics"], TZ, now)
        self.assertEqual(out[0]["title"], "旧")
        self.assertFalse(ics.health()["ok"])
        with patch.object(ics, "_fetch_ics", return_value=ICS_FIXTURE) as fetch:
            out = ics.refresh(["https://example.com/a.ics"], TZ, now)
            self.assertTrue(fetch.called)
            self.assertTrue(ics.health()["ok"])
            self.assertTrue(ics.health()["enabled"])
            fetch.reset_mock()
            ics.refresh(["https://example.com/a.ics"], TZ, now)
            self.assertFalse(fetch.called)  # TTL 内不再发请求

    def test_settings_new_keys_validation(self):
        raw = defaults_from_config({"location_name": "北京", "latitude": 39.9, "longitude": 116.4, "timezone": "Asia/Shanghai"})
        self.assertEqual(validate(raw), [])
        raw["ics"] = {"urls": ["http://insecure/x.ics"]}
        self.assertTrue(any(d["code"] == "ICS_INVALID" for d in validate(raw)))
        raw["ics"] = {"urls": ["https://ok.example/x.ics"]}
        raw["anniversaries"] = [{"id": "e1", "name": "生日", "date": "8-16", "repeat": "yearly"}]
        self.assertTrue(any(".date" in d["field"] for d in validate(raw)))
        raw["anniversaries"] = [{"id": "e1", "name": "生日", "date": "08-16", "repeat": "yearly"}]
        self.assertEqual(validate(raw), [])
        raw["presets"] = [{"id": "p1", "name": "简洁", "created_at": "2026-10-26 10:00", "snapshot": {"pages": [], "widget_defs": [], "assets": []}}]
        self.assertEqual(validate(raw), [])
        out = normalize(raw)
        self.assertEqual(out["anniversaries"][0]["repeat"], "yearly")
        self.assertEqual(out["presets"][0]["name"], "简洁")
        self.assertEqual(out["ics"]["urls"], ["https://ok.example/x.ics"])
        # 旧配置缺失新键：不报错，normalize 补默认
        del raw["ics"]
        del raw["anniversaries"]
        del raw["presets"]
        self.assertEqual(validate(raw), [])
        out = normalize(raw)
        self.assertEqual(out["ics"], {"urls": []})
        self.assertEqual(out["anniversaries"], [])
        self.assertEqual(out["presets"], [])


if __name__ == "__main__":
    unittest.main()

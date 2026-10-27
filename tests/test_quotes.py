"""一言在线获取韧性：拆分超时、失败重试一次、上次成功粘性缓存（中英两路）。"""

from __future__ import annotations

import threading
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from zoneinfo import ZoneInfo

import requests

from server import quotes

# 带时区：与 service.py 实际传入一致，覆盖 _days_old 的 aware 归一路径
NOW = datetime(2026, 10, 26, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def _resp(payload: str, status: int = 200) -> requests.Response:
    resp = requests.Response()
    resp.status_code = status
    resp._content = payload.encode("utf-8")
    return resp


class QuoteResilienceTests(unittest.TestCase):
    def tearDown(self):
        quotes._day_cache.clear()
        quotes._en_cache.clear()
        quotes._last_good = None
        quotes._last_good_at = ""
        quotes._en_last_good = None
        quotes._en_last_good_at = ""
        quotes._status.update(ok=True, at=None, error="", enabled=True)

    def test_success_records_last_good(self):
        with patch.object(quotes.requests, "get", return_value=_resp('{"hitokoto":"测试一言","from":"测试"}')) as fetch:
            quote = quotes.get_quote(NOW)
        self.assertEqual(quote["text"], "测试一言")
        self.assertTrue(quotes.health()["ok"])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(quotes._last_good["text"], "测试一言")

    def test_failure_retries_then_uses_sticky(self):
        quotes._last_good = {"text": "上次成功", "from": "旧"}
        quotes._last_good_at = NOW.strftime("%Y-%m-%d")
        with patch.object(quotes.requests, "get", side_effect=requests.exceptions.ReadTimeout("Read timed out. (read timeout=12)")) as fetch, \
                patch.object(quotes.time, "sleep") as sleeper:
            quote = quotes.get_quote(NOW)
        self.assertEqual(fetch.call_count, 2)  # 失败重试一次
        self.assertEqual(sleeper.call_count, 1)
        self.assertEqual(quote["text"], "上次成功")  # 粘性缓存而非离线库
        self.assertFalse(quotes.health()["ok"])  # 健康卡如实显示失败
        self.assertIn("Read timed out", quotes.health()["error"])

    def test_retry_succeeds_on_second_attempt(self):
        with patch.object(quotes.requests, "get", side_effect=[requests.exceptions.ConnectTimeout("t"), _resp('{"hitokoto":"第二次成功","from":"x"}')]) as fetch, \
                patch.object(quotes.time, "sleep"):
            quote = quotes.get_quote(NOW)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(quote["text"], "第二次成功")
        self.assertTrue(quotes.health()["ok"])

    def test_sticky_expires_after_seven_days(self):
        quotes._last_good = {"text": "上次成功", "from": "旧"}
        quotes._last_good_at = (NOW - timedelta(days=8)).strftime("%Y-%m-%d")
        with patch.object(quotes.requests, "get", side_effect=requests.exceptions.ReadTimeout("t")), \
                patch.object(quotes.time, "sleep"):
            quote = quotes.get_quote(NOW)
        self.assertIn(quote["text"], [item["text"] for item in quotes.OFFLINE_QUOTES])  # 超龄回退离线库
        self.assertFalse(quotes.health()["ok"])

    def test_english_sticky_fallback(self):
        quotes._en_last_good = {"text": "Old good line.", "from": "Someone"}
        quotes._en_last_good_at = NOW.strftime("%Y-%m-%d")
        with patch.object(quotes.requests, "get", side_effect=requests.exceptions.ReadTimeout("t")), \
                patch.object(quotes.time, "sleep"):
            quote = quotes.english_quote(NOW)
        self.assertEqual(quote["text"], "Old good line.")


class QuoteLibraryTests(unittest.TestCase):
    def tearDown(self):
        quotes._library_sentences = None
        quotes._day_cache.clear()

    def test_library_deterministic_and_type_filtered(self):
        first = quotes.library_quote(NOW, ["i", "d"])
        self.assertEqual(first, quotes.library_quote(NOW, ["i", "d"]))  # 同日同句
        pool_k = [s for s in quotes._load_library() if s["type"] == "k"]
        pick_k = pool_k[NOW.timetuple().tm_yday % len(pool_k)]
        self.assertEqual(quotes.library_quote(NOW, ["k"])["text"], pick_k["hitokoto"].strip())
        # get_quote 走 library 分支且健康状态为未启用
        self.assertEqual(quotes.get_quote(NOW, "library", None, ["i", "d"])["text"], first["text"])
        self.assertFalse(quotes.health()["enabled"])

    def test_library_empty_pool_falls_back(self):
        quotes._library_sentences = []
        out = quotes.library_quote(NOW, None)
        self.assertIn(out["text"], [item["text"] for item in quotes.OFFLINE_QUOTES])

    def test_settings_migration_and_validation(self):
        from server.settings import defaults_from_config, normalize, validate

        raw = defaults_from_config({"location_name": "北京", "latitude": 39.9, "longitude": 116.4, "timezone": "Asia/Shanghai"})
        self.assertEqual(raw["quote"]["mode"], "library")
        self.assertEqual(raw["quote"]["library_types"], ["i", "d"])
        raw["quote"] = {"mode": "offline", "custom": []}
        out = normalize(raw)
        self.assertEqual(out["quote"]["mode"], "library")  # 旧 offline 迁移
        self.assertEqual(out["quote"]["library_types"], ["i", "d"])  # 缺失补默认
        raw["quote"] = {"mode": "library", "custom": [], "library_types": ["x"]}
        self.assertTrue(any(d["field"] == "quote.library_types" for d in validate(raw)))
        raw["quote"]["library_types"] = ["a", "k"]
        self.assertEqual(validate(raw), [])


class QuoteLibraryRefreshTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        from pathlib import Path

        self.data_dir = Path(self.tmp.name)
        self.old_paths = (quotes.LIBRARY_DATA_PATH, quotes.LIBRARY_META_PATH)
        quotes.LIBRARY_DATA_PATH = self.data_dir / "quotes_library.json"
        quotes.LIBRARY_META_PATH = self.data_dir / "quotes_meta.json"
        quotes._library_sentences = None
        quotes._library_meta.update(updated="", count=0, fetched_at=None, last_error="", refreshed_at=None)
        quotes._library_refreshing.clear()

    def tearDown(self):
        quotes.LIBRARY_DATA_PATH, quotes.LIBRARY_META_PATH = self.old_paths
        quotes._library_refreshing.clear()
        quotes._library_sentences = None
        quotes._library_meta.update(updated="", count=0, fetched_at=None, last_error="", refreshed_at=None)

    def test_refresh_builds_writes_and_hot_swaps(self):
        import json as jsonlib

        payload = [
            {"hitokoto": "  这是一条全新句子！ ", "from": "来源", "type": "i"},
            {"hitokoto": "这是一条全新句子！", "from": "重复", "type": "d"},  # 归一去重
            {"hitokoto": "短", "from": "", "type": "a"},  # 长度过滤
        ]
        # 产品要求 built >= 100 才落盘，补足不重复填充句
        payload += [{"hitokoto": f"全新填充句子{i:03d}", "from": "来源", "type": "i"} for i in range(120)]
        # refresh_library 内部为函数级 `from server.ics import _fetch_ics`，须 patch 定义处
        with patch("server.ics._fetch_ics", return_value=jsonlib.dumps(payload, ensure_ascii=False)):
            result = quotes.refresh_library(force=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 121)
        texts = [s["hitokoto"] for s in quotes._load_library()]
        self.assertEqual(texts.count("这是一条全新句子！"), 1)  # 归一去重生效
        self.assertNotIn("短", texts)  # 长度过滤生效
        self.assertEqual(quotes._load_library()[0]["hitokoto"], "全新填充句子000")  # 热替换生效
        self.assertTrue(quotes.LIBRARY_DATA_PATH.exists())
        meta = jsonlib.loads(quotes.LIBRARY_META_PATH.read_text(encoding="utf-8"))
        self.assertEqual(meta["count"], 121)
        self.assertEqual(quotes.health()["library_count"], 121)

    def test_refresh_failure_keeps_old(self):
        quotes._library_sentences = [{"type": "i", "hitokoto": "旧库句子", "from": ""}]
        with patch("server.ics._fetch_ics", side_effect=RuntimeError("boom")):
            result = quotes.refresh_library(force=True)
        self.assertFalse(result["ok"])
        self.assertIn("boom", result["error"])
        self.assertEqual(quotes._load_library()[0]["hitokoto"], "旧库句子")  # 失败保旧
        self.assertFalse(quotes.LIBRARY_DATA_PATH.exists())

    def test_ttl_skips_fetch(self):
        import json as jsonlib

        meta = {"updated": "2026-10-20", "count": 10, "refreshed_at": datetime.utcnow().isoformat(timespec="seconds")}
        quotes.LIBRARY_META_PATH.write_text(jsonlib.dumps(meta), encoding="utf-8")
        with patch("server.ics._fetch_ics", side_effect=AssertionError("TTL 内不应拉取")):
            result = quotes.refresh_library(force=False)
        self.assertEqual(result.get("skipped"), True)
        self.assertEqual(result["count"], 10)

    def test_falls_back_to_builtin_when_no_data_file(self):
        from datetime import datetime

        quote = quotes.get_quote(datetime(2026, 10, 27), "library", None, ["i", "d"])
        self.assertTrue(quote["text"])  # data/ 无库时回落镜像内置
        self.assertEqual(quotes.health()["library_count"], 7684)


if __name__ == "__main__":
    unittest.main()

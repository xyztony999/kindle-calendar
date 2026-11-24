"""admin-content-pack 契约测试：个人语录库上传（V1–V6）/ personal 取句 / 备份恢复 / 健康数值折线换算。"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from server import health_history, quotes
from server.aqi import AirQuality
from server.settings import defaults_from_config, normalize, validate
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData

PASSWORD = "test-only-not-a-secret"
DEPLOY = {"location_name": "北京", "latitude": 39.9042, "longitude": 116.4074, "timezone": "Asia/Shanghai"}
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
FAKE_WEATHER = WeatherData(
    current=CurrentWeather(temperature=24.0, humidity=50, wind_speed=3.0, code=0, description="晴"),
    daily=[DailyForecast(date="2026-11-24", temp_max=26.0, temp_min=18.0, code=0, description="晴")],
    hourly=[HourlyPoint(time="2026-11-24T12:00", temperature=24.0, precipitation_probability=0, code=0)],
)
FAKE_AQI = AirQuality(us_aqi=42, level="优", cn_aqi=57, cn_level="良")

PERSONAL_OK = {"schema_version": 1, "quotes": [
    {"text": "此心安处是吾乡。", "from": "苏轼《定风波》"},
    {"text": "今天也留一点时间读书。", "from": ""},
    {"text": "早睡早起。", "from": "家里"},
]}


def _offline_network():
    return (
        patch("server.service.fetch_weather", return_value=FAKE_WEATHER),
        patch("server.service.fetch_aqi", return_value=FAKE_AQI),
        patch("server.quotes.requests.get", side_effect=AssertionError("personal/library 不应联网")),
    )


class PersonalSettingsTests(unittest.TestCase):
    """枚举扩展必须走通 validate → normalize 白名单链路（历史教训：options 被静默丢弃）。"""

    def test_personal_mode_valid_without_file(self):
        raw = defaults_from_config(DEPLOY)
        raw["quote"] = {"mode": "personal", "custom": [], "library_types": ["i"]}
        self.assertEqual(validate(raw), [])  # 不要求个人库文件已存在
        out = normalize(raw)
        self.assertEqual(out["quote"]["mode"], "personal")  # normalize 不丢 personal
        self.assertEqual(out["quote"]["library_types"], ["i"])

    def test_offline_alias_and_invalid_mode(self):
        raw = defaults_from_config(DEPLOY)
        raw["quote"] = {"mode": "offline", "custom": []}
        self.assertEqual(normalize(raw)["quote"]["mode"], "library")
        raw["quote"]["mode"] = "nope"
        self.assertTrue(any(d["code"] == "QUOTE_MODE_INVALID" for d in validate(raw)))

    def test_custom_empty_constraint_only_for_custom(self):
        raw = defaults_from_config(DEPLOY)
        raw["quote"] = {"mode": "personal", "custom": []}
        self.assertEqual(validate(raw), [])
        raw["quote"]["mode"] = "custom"
        self.assertTrue(any(d["field"] == "quote.custom" for d in validate(raw)))


class PersonalValidationTests(unittest.TestCase):
    def test_valid_passes(self):
        self.assertEqual(quotes.validate_personal(PERSONAL_OK), [])

    def test_v1_not_object(self):
        for bad in ([], "x", None, 3):
            details = quotes.validate_personal(bad)
            self.assertEqual(len(details), 1)
            self.assertIsNone(details[0]["index"])

    def test_v2_schema_version(self):
        for bad in (2, "1", True, 1.5, None):
            raw = json.loads(json.dumps(PERSONAL_OK))
            raw["schema_version"] = bad
            details = quotes.validate_personal(raw)
            self.assertTrue(any(d["field"] == "schema_version" for d in details), bad)

    def test_v3_count_bounds(self):
        raw = {"schema_version": 1, "quotes": []}
        self.assertTrue(any(d["field"] == "quotes" for d in quotes.validate_personal(raw)))
        raw["quotes"] = [{"text": f"句子{i}", "from": ""} for i in range(101)]
        self.assertTrue(any(d["field"] == "quotes" for d in quotes.validate_personal(raw)))
        raw["quotes"] = [{"text": "一条", "from": ""}]
        self.assertEqual(quotes.validate_personal(raw), [])

    def test_v4_v5_v6_per_item_details(self):
        raw = {"schema_version": 1, "quotes": [
            {"text": "正常", "from": ""},
            {"text": "长" * 33, "from": ""},          # index 1 text 越界
            {"text": "正常", "from": "出" * 17},      # index 2 from 越界
            {"text": "带\n换行", "from": ""},         # index 3 text 换行
            {"text": "正常", "from": "带\r回车"},     # index 4 from 回车
            "not-an-object",                          # index 5 项格式
            {"text": "   ", "from": ""},              # index 6 空文本
        ]}
        details = quotes.validate_personal(raw)
        got = {(d["index"], d["field"]) for d in details}
        self.assertEqual(got, {(1, "text"), (2, "from"), (3, "text"), (4, "from"), (5, ""), (6, "text")})
        self.assertTrue(all(d["code"] == "QUOTES_PERSONAL_INVALID" for d in details))

    def test_unicode_chars_not_bytes(self):
        raw = {"schema_version": 1, "quotes": [{"text": "字" * 32, "from": "出" * 16}]}
        self.assertEqual(quotes.validate_personal(raw), [])  # 32/16 个 Unicode 字符合规（UTF-8 字节远超）


class PersonalQuoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._old_env = os.environ.get("SETTINGS_PATH")
        os.environ["SETTINGS_PATH"] = str(Path(self.tmp.name) / "settings.json")
        quotes._personal_sentences = None
        quotes._personal_meta.update(count=0, updated=None)

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("SETTINGS_PATH", None)
        else:
            os.environ["SETTINGS_PATH"] = self._old_env
        quotes._personal_sentences = None
        quotes._personal_meta.update(count=0, updated=None)
        self.tmp.cleanup()

    def test_rotation_and_hot_swap(self):
        quotes.save_personal(PERSONAL_OK["quotes"], "2026-11-24T04:00:00+00:00")
        pool = PERSONAL_OK["quotes"]
        pick = pool[NOW.timetuple().tm_yday % len(pool)]
        self.assertEqual(quotes.get_quote(NOW, "personal"), {"text": pick["text"], "from": pick["from"]})
        self.assertEqual(quotes.get_quote(NOW, "personal"), quotes.get_quote(NOW, "personal"))  # 同日同句
        self.assertEqual(quotes.english_quote(NOW, "personal")["text"], pick["text"])  # 中英共用
        self.assertFalse(quotes.health()["enabled"])  # 仅 online 为 True
        self.assertEqual(quotes.health()["personal_count"], 3)
        self.assertEqual(quotes.health()["personal_updated"], "2026-11-24T04:00:00+00:00")
        # 热替换：重传即替换
        quotes.save_personal([{"text": "新句。", "from": ""}], "2026-11-24T05:00:00+00:00")
        self.assertEqual(quotes.get_quote(NOW, "personal")["text"], "新句。")
        self.assertEqual(quotes.health()["personal_count"], 1)
        # 落盘文件可被冷启动重读
        quotes._personal_sentences = None
        self.assertEqual(quotes.get_quote(NOW, "personal")["text"], "新句。")

    def test_empty_pool_fallback(self):
        self.assertIn(quotes.get_quote(NOW, "personal")["text"], [q["text"] for q in quotes.OFFLINE_QUOTES])
        self.assertIn(quotes.english_quote(NOW, "personal")["text"], [q["text"] for q in quotes.EN_QUOTES])
        self.assertEqual(quotes.health()["personal_count"], 0)
        self.assertIsNone(quotes.health()["personal_updated"])

    def test_corrupt_file_empty_pool(self):
        quotes.personal_path().write_text("{broken", encoding="utf-8")
        self.assertIn(quotes.get_quote(NOW, "personal")["text"], [q["text"] for q in quotes.OFFLINE_QUOTES])

    def test_file_missing_does_not_break_library(self):
        self.assertTrue(quotes.get_quote(NOW, "library", None, ["i"])["text"])


class AdminContentPackApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SETTINGS_PATH"] = str(Path(self.tmp.name) / "settings.json")
        os.environ["ADMIN_PASSWORD"] = PASSWORD
        os.environ["SECRET_KEY"] = "unit-test-secret"
        self.patches = _offline_network()
        for item in self.patches:
            item.start()
        from server.app import create_app

        self.app = create_app()
        self.client = self.app.test_client()
        self.client.post("/admin/api/login", json={"password": PASSWORD}, headers=self._headers())
        quotes._personal_sentences = None
        quotes._personal_meta.update(count=0, updated=None)

    def tearDown(self):
        for item in self.patches:
            item.stop()
        quotes._personal_sentences = None
        quotes._personal_meta.update(count=0, updated=None)
        self.tmp.cleanup()

    def _headers(self):
        return {"X-Requested-With": "kindle-admin"}

    def _upload(self, payload, name="personal.json"):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return self.client.post(
            "/admin/api/quotes-personal",
            data={"file": (io.BytesIO(raw), name)},
            headers=self._headers(),
            content_type="multipart/form-data",
        )

    def _settings(self):
        return self.client.get("/admin/api/settings", headers=self._headers()).get_json()["data"]["settings"]

    def _save(self, settings):
        return self.client.post("/admin/api/settings/save", json=settings, headers={**self._headers(), "Content-Type": "application/json"})

    def test_upload_success_no_mode_switch(self):
        res = self._upload(PERSONAL_OK)
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        data = res.get_json()["data"]
        self.assertEqual(data["count"], 3)
        self.assertTrue(data["uploaded_at"])
        self.assertTrue(quotes.personal_path().exists())
        self.assertEqual(self._settings()["quote"]["mode"], "library")  # 不偷跑配置
        sources = self.client.get("/admin/api/sources", headers=self._headers()).get_json()["data"]["sources"]
        quote = next(s for s in sources if s["id"] == "quote")
        self.assertEqual(quote["personal_count"], 3)
        self.assertTrue(quote["personal_updated"])

    def test_upload_guards(self):
        no_csrf = self.client.post("/admin/api/quotes-personal", data={"file": (io.BytesIO(b"{}"), "x.json")}, content_type="multipart/form-data")
        self.assertEqual(no_csrf.status_code, 403)
        fresh = self.app.test_client()
        anon = fresh.post("/admin/api/quotes-personal", data={"file": (io.BytesIO(b"{}"), "x.json")}, headers=self._headers(), content_type="multipart/form-data")
        self.assertEqual(anon.status_code, 401)
        missing = self.client.post("/admin/api/quotes-personal", data={}, headers=self._headers(), content_type="multipart/form-data")
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.get_json()["error"]["code"], "QUOTES_PERSONAL_INVALID")

    def test_upload_invalid_details_and_original_intact(self):
        self.assertEqual(self._upload(PERSONAL_OK).status_code, 200)
        before = quotes.personal_path().read_bytes()
        bad = {"schema_version": 1, "quotes": [{"text": "好", "from": ""}] * 1 + [{"text": "长" * 33, "from": ""}, {"text": "好", "from": "出" * 17}]}
        res = self._upload(bad)
        self.assertEqual(res.status_code, 400)
        error = res.get_json()["error"]
        self.assertEqual(error["code"], "QUOTES_PERSONAL_INVALID")
        self.assertEqual({(d["index"], d["field"]) for d in error["details"]}, {(1, "text"), (2, "from")})
        self.assertEqual(quotes.personal_path().read_bytes(), before)  # 原文件不被破坏
        self.assertEqual(quotes.health()["personal_count"], 3)
        schema_bad = self._upload({"schema_version": 2, "quotes": [{"text": "好", "from": ""}]})
        self.assertEqual(schema_bad.status_code, 400)
        self.assertTrue(any(d["field"] == "schema_version" for d in schema_bad.get_json()["error"]["details"]))
        not_json = self._upload(b"{broken")
        self.assertEqual(not_json.status_code, 400)

    def test_personal_mode_serves_quotes(self):
        self.assertEqual(self._upload(PERSONAL_OK).status_code, 200)
        settings = self._settings()
        settings["quote"]["mode"] = "personal"
        self.assertEqual(self._save(settings).status_code, 200)
        pool = PERSONAL_OK["quotes"]
        expected = pool[datetime.now(ZoneInfo("Asia/Shanghai")).timetuple().tm_yday % len(pool)]
        dash = self.client.get("/api/v1/dashboard.json").get_json()
        self.assertEqual(dash["quote"]["text"], expected["text"])
        en = self.client.get("/api/v1/dashboard.json?lang=en").get_json()
        self.assertEqual(en["quote"]["text"], expected["text"])  # 中英共用个人库

    def test_backup_restore_personal_roundtrip(self):
        self.assertEqual(self._upload(PERSONAL_OK).status_code, 200)
        settings = self._settings()
        settings["quote"]["mode"] = "personal"
        settings["location"]["name"] = "备份城市"
        self.assertEqual(self._save(settings).status_code, 200)
        backup = self.client.get("/admin/api/backup", headers=self._headers())
        zf = zipfile.ZipFile(io.BytesIO(backup.get_data()))
        self.assertIn("quotes_personal.json", zf.namelist())
        # 破坏现状后恢复
        quotes.save_personal([{"text": "被覆盖。", "from": ""}], "2026-11-24T06:00:00+00:00")
        settings["location"]["name"] = "北京"
        self._save(settings)
        restored = self.client.post(
            "/admin/api/backup/restore",
            data={"file": (io.BytesIO(backup.get_data()), "backup.zip")},
            headers=self._headers(),
            content_type="multipart/form-data",
        )
        self.assertEqual(restored.status_code, 200, restored.get_data(as_text=True))
        data = restored.get_json()["data"]
        self.assertTrue(data["restored_personal"])
        self.assertEqual(data["settings"]["location"]["name"], "备份城市")
        self.assertEqual(quotes.health()["personal_count"], 3)  # 热替换立即取句
        pool = PERSONAL_OK["quotes"]
        expected = pool[datetime.now(ZoneInfo("Asia/Shanghai")).timetuple().tm_yday % len(pool)]
        self.assertEqual(self.client.get("/api/v1/dashboard.json").get_json()["quote"]["text"], expected["text"])

    def test_restore_rejects_invalid_personal_member(self):
        self.assertEqual(self._upload(PERSONAL_OK).status_code, 200)
        before = quotes.personal_path().read_bytes()
        settings_raw = json.dumps(self._settings(), ensure_ascii=False).encode("utf-8")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("settings.json", settings_raw)
            zf.writestr("quotes_personal.json", json.dumps({"schema_version": 1, "quotes": [{"text": "长" * 33, "from": ""}]}, ensure_ascii=False))
        res = self.client.post(
            "/admin/api/backup/restore",
            data={"file": (io.BytesIO(buf.getvalue()), "bad.zip")},
            headers=self._headers(),
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error"]["code"], "BACKUP_INVALID")
        self.assertEqual(quotes.personal_path().read_bytes(), before)  # 不落盘

    def test_restore_old_backup_without_personal(self):
        settings_raw = json.dumps(self._settings(), ensure_ascii=False).encode("utf-8")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("settings.json", settings_raw)
        res = self.client.post(
            "/admin/api/backup/restore",
            data={"file": (io.BytesIO(buf.getvalue()), "old.zip")},
            headers=self._headers(),
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        self.assertFalse(res.get_json()["data"]["restored_personal"])


class HealthValueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SETTINGS_PATH"] = str(Path(self.tmp.name) / "settings.json")
        os.environ["ADMIN_PASSWORD"] = PASSWORD
        os.environ["SECRET_KEY"] = "unit-test-secret"
        self.patches = _offline_network()
        for item in self.patches:
            item.start()
        from server.app import create_app

        self.app = create_app()
        self.client = self.app.test_client()
        self.client.post("/admin/api/login", json={"password": PASSWORD}, headers=self._headers())

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.tmp.cleanup()

    def _headers(self):
        return {"X-Requested-With": "kindle-admin"}

    def _record(self, weather_value=24.0, aqi_value=42, cn_value=57, at=None):
        sources = {"sources": [
            {"id": "weather", "ok": True, "error": "", **({"value": weather_value} if weather_value is not None else {})},
            {"id": "aqi", "ok": True, "error": "", **({"value": aqi_value} if aqi_value is not None else {}), **({"cn_value": cn_value} if cn_value is not None else {})},
            {"id": "quote", "ok": True, "error": ""},
            {"id": "ics", "ok": True, "error": ""},
        ]}
        health_history.record(sources)

    def _history(self):
        return self.client.get("/admin/api/sources/history", headers=self._headers()).get_json()["data"]

    def _save_units(self, units):
        settings = self.client.get("/admin/api/settings", headers=self._headers()).get_json()["data"]["settings"]
        settings["units"] = units
        res = self.client.post("/admin/api/settings/save", json=settings, headers={**self._headers(), "Content-Type": "application/json"})
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))

    def test_record_keeps_numeric_values_only(self):
        self._record()
        point = health_history.series()["sources"]["weather"][-1]
        self.assertEqual(point["value"], 24.0)
        aqi = health_history.series()["sources"]["aqi"][-1]
        self.assertEqual((aqi["value"], aqi["cn_value"]), (42, 57))
        # bool / 字符串 / NaN 不存
        health_history.record({"sources": [{"id": "weather", "ok": True, "value": True}, {"id": "aqi", "ok": True, "value": "42", "cn_value": float("nan")}]})
        series = health_history.series()["sources"]
        self.assertNotIn("value", series["weather"][-1])
        self.assertNotIn("value", series["aqi"][-1])
        self.assertNotIn("cn_value", series["aqi"][-1])

    def test_history_converts_with_current_units(self):
        self._record()
        data = self._history()
        self.assertEqual(data["units"], {"temp": "c", "aqi": "us"})
        self.assertEqual(data["sources"]["weather"][-1]["value"], 24)
        self.assertEqual(data["sources"]["aqi"][-1]["value"], 42)
        self.assertNotIn("cn_value", data["sources"]["aqi"][-1])  # 原值不外露
        self._save_units({"temp": "f", "wind": "kmh", "aqi": "cn"})
        data = self._history()
        self.assertEqual(data["units"], {"temp": "f", "aqi": "cn"})
        self.assertEqual(data["sources"]["weather"][-1]["value"], 75)  # 24℃ → 75℉
        self.assertEqual(data["sources"]["aqi"][-1]["value"], 57)  # 国标
        self._save_units({"temp": "c", "wind": "kmh", "aqi": "us"})
        self.assertEqual(self._history()["sources"]["weather"][-1]["value"], 24)  # 历史拍按当前口径重释

    def test_history_cn_missing_falls_back_us_and_gaps_keep_no_value(self):
        self._record(cn_value=None)  # 国标缺失
        self._record(weather_value=None, aqi_value=None, cn_value=None)  # 无值拍
        self._save_units({"temp": "f", "wind": "kmh", "aqi": "cn"})
        data = self._history()
        aqi_points = data["sources"]["aqi"]
        self.assertEqual(aqi_points[0]["value"], 42)  # 回退美标
        self.assertNotIn("value", aqi_points[1])  # 无值拍保持无值（断线）
        self.assertNotIn("value", data["sources"]["weather"][-1])

    def test_old_history_file_without_values_loads(self):
        path = Path(os.environ["SETTINGS_PATH"]).with_name("health_history.json")
        at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
        path.write_text(json.dumps({"points": [{"at": at, "sources": {"weather": {"ok": True, "error": ""}, "aqi": {"ok": False, "error": "x"}}}]}), encoding="utf-8")
        health_history.init(path)
        data = self._history()
        self.assertNotIn("value", data["sources"]["weather"][-1])
        self.assertEqual(data["sources"]["aqi"][-1]["ok"], False)

    def test_sources_health_weather_value_and_aqi_cn_value(self):
        from server import aqi as aqi_mod

        self.client.get("/api/v1/dashboard.json")  # 触发 _ensure_weather → 快照一拍
        aqi_mod._status.update(ok=True, value=42, cn_value=57, error="")
        sources = self.client.get("/admin/api/sources", headers=self._headers()).get_json()["data"]["sources"]
        weather = next(s for s in sources if s["id"] == "weather")
        self.assertEqual(weather["value"], 24.0)
        aqi = next(s for s in sources if s["id"] == "aqi")
        self.assertEqual((aqi["value"], aqi["cn_value"]), (42, 57))
        history = self._history()
        self.assertEqual(history["sources"]["weather"][-1]["value"], 24)


if __name__ == "__main__":
    unittest.main()

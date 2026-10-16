"""Device communication, application confirmation, and offline timing."""
import unittest
import json
import tempfile
from pathlib import Path
from urllib.parse import quote
from unittest.mock import patch

from server.settings import HeartbeatLog
from tests import test_web_admin as admin_tests

DEVICE = {"X-Kindle-Device": "dash", "X-Kindle-Interval": "900"}


class DeviceApiTests(unittest.TestCase):
    setUp = admin_tests.AdminApiTests.setUp
    tearDown = admin_tests.AdminApiTests.tearDown
    _login = admin_tests.AdminApiTests._login
    _headers = admin_tests.AdminApiTests._headers

    def status(self):
        return self.client.get("/admin/api/device").get_json()["data"]

    def report(self, **fields):
        body = {"interval_s": 900, "mode": "v2", **fields}
        return self.client.post("/api/v1/device/heartbeat", json=body, headers=DEVICE)

    def test_browser_and_old_unmarked_clients_do_not_count(self):
        self._login()
        self.client.get("/api/v1/dashboard.env")
        self.client.get("/api/v1/dashboard.env", headers={**DEVICE, "Accept": "text/html"})
        self.client.get("/dashboard.png")
        self.assertEqual(self.status()["online_state"], "unknown")

    def test_fetch_then_application_confirmation(self):
        self._login()
        self.client.get("/api/v1/dashboard.env", headers=DEVICE)
        fetched = self.status()
        self.assertEqual(fetched["online_state"], "online")
        self.assertEqual(fetched["delivery_state"], "pending")
        self.assertIsNotNone(fetched["last_fetch_at"])
        self.assertIsNone(fetched["last_applied_at"])
        self.assertEqual(self.report(applied_version="old").status_code, 200)
        self.assertEqual(self.status()["delivery_state"], "pending")
        version = fetched["current_settings_version"]
        self.assertEqual(self.report(applied_version=version).status_code, 200)
        applied = self.status()
        self.assertEqual(applied["delivery_state"], "delivered")
        self.assertIsNotNone(applied["last_applied_at"])
        self.report()  # A failed later sync must retain the earlier confirmed version.
        self.assertEqual(self.status()["delivered_settings_version"], version)
        self.assertEqual(self.status()["last_applied_at"], applied["last_applied_at"])

    def test_v1_png_reports_contact_without_claiming_configuration_applied(self):
        self._login()
        self.client.get("/dashboard.png", headers=DEVICE)
        self.assertEqual(self.report(mode="v1", applied_version="").status_code, 200)
        status = self.status()
        self.assertEqual(status["mode"], "v1")
        self.assertEqual(status["online_state"], "online")
        self.assertEqual(status["delivery_state"], "unknown")
        self.assertIsNone(status["last_applied_at"])

    def test_invalid_reports_do_not_update_state(self):
        self._login()
        cases = [{"interval_s": True}, {"interval_s": 59}, {"interval_s": 86401},
                 {"interval_s": "900"}, {"mode": "browser"}, {"applied_version": []},
                 {"mode": "v1", "applied_version": "version"}]
        for fields in cases:
            with self.subTest(fields=fields):
                self.assertEqual(self.report(**fields).status_code, 400)
        missing = self.client.post("/api/v1/device/heartbeat", json={"interval_s": 900, "mode": "v2"})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(self.status()["online_state"], "unknown")

    def test_status_requires_admin_session(self):
        self.assertEqual(self.client.get("/admin/api/device").status_code, 401)

    def test_form_and_old_busybox_json_compatibility(self):
        self._login()
        version = self.status()["current_settings_version"]
        body = {"interval_s": 900, "mode": "v2", "applied_version": version}
        raw = json.dumps(body, separators=(",", ":"))
        cases = [("interval_s=900&mode=v2&applied_version=" + version, "application/x-www-form-urlencoded"),
                 (raw, "application/x-www-form-urlencoded"),
                 (quote(raw, safe=""), "application/x-www-form-urlencoded"),
                 (quote(raw, safe=""), "application/json")]
        for payload, content_type in cases:
            with self.subTest(content_type=content_type, payload=payload):
                response = self.client.post("/api/v1/device/heartbeat", data=payload,
                                            content_type=content_type, headers=DEVICE)
                self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
                self.assertEqual(self.status()["delivery_state"], "delivered")

    def test_malformed_duplicate_double_encoding_and_oversize_rejected(self):
        self._login()
        cases = [("interval_s=900&interval_s=60&mode=v2", "application/x-www-form-urlencoded", 400),
                 ('{"interval_s":900,"interval_s":60,"mode":"v2"}', "application/json", 400),
                 (quote(quote('{"interval_s":900,"mode":"v2"}', safe=""), safe=""), "application/json", 400),
                 ("interval_s=9.0&mode=v2", "application/x-www-form-urlencoded", 400),
                 ('{"interval_s":900,"mode":"v2","applied_version":"bad&value"}', "application/json", 400),
                 ("interval_s=900&mode=v2", "text/plain", 400),
                 ("x" * 2049, "application/json", 413)]
        for payload, content_type, expected in cases:
            with self.subTest(payload=payload[:50]):
                response = self.client.post("/api/v1/device/heartbeat", data=payload,
                                            content_type=content_type, headers=DEVICE)
                self.assertEqual(response.status_code, expected)
                self.assertIn("code", response.get_json()["error"])
                self.assertEqual(self.status()["online_state"], "unknown")

    def test_restart_restores_status_and_failed_report_does_not_overwrite(self):
        self._login()
        version = self.status()["current_settings_version"]
        self.report(applied_version=version)
        path = Path(self.tmp.name) / "device-status.json"
        saved = path.read_bytes()
        self.report(interval_s=59)
        self.assertEqual(path.read_bytes(), saved)
        restored = HeartbeatLog(path).snapshot(version, "UTC")
        self.assertEqual(restored["delivery_state"], "delivered")
        self.assertIsNotNone(restored["last_seen_at"])
        restarted = admin_tests.create_app().test_client()
        login = restarted.post("/admin/api/login", json={"password": admin_tests.PASSWORD}, headers=self._headers())
        self.assertEqual(login.status_code, 200)
        status = restarted.get("/admin/api/device").get_json()["data"]
        self.assertEqual(status["delivery_state"], "delivered")
        self.assertEqual(status["delivered_settings_version"], version)
        self.assertIsNotNone(status["last_applied_at"])


class HeartbeatTimingTests(unittest.TestCase):
    def test_fast_requests_keep_declared_cycle_and_offline_boundary(self):
        beats = HeartbeatLog()
        with patch("server.settings.time.time", return_value=1000):
            beats.record("ip", "ua", 900, fetched=True)
        with patch("server.settings.time.time", return_value=1001):
            beats.record("ip", "ua", 900, fetched=True)
        with patch("server.settings.time.time", return_value=2860):
            self.assertEqual(beats.snapshot("v", "UTC")["online_state"], "online")
        with patch("server.settings.time.time", return_value=2861):
            self.assertEqual(beats.snapshot("v", "UTC")["online_state"], "offline")
        self.assertEqual(beats.snapshot("v", "UTC")["interval_estimate_s"], 900)

    def test_new_process_unknown_and_configuration_change_pending(self):
        self.assertEqual(HeartbeatLog().snapshot("v", "UTC")["online_state"], "unknown")
        beats = HeartbeatLog()
        beats.record("ip", "ua", applied_version="v1")
        self.assertEqual(beats.snapshot("v1", "UTC")["delivery_state"], "delivered")
        self.assertEqual(beats.snapshot("v2", "UTC")["delivery_state"], "pending")

    def test_v1_fallback_keeps_history_without_claiming_layout_applied(self):
        beats = HeartbeatLog()
        beats.record("ip", "ua", mode="v2", applied_version="v1")
        beats.record("ip", "ua", mode="v1", fetched=True)
        status = beats.snapshot("v1", "UTC")
        self.assertEqual(status["online_state"], "online")
        self.assertEqual(status["delivery_state"], "unknown")
        self.assertEqual(status["delivered_settings_version"], "v1")
        self.assertIsNotNone(status["last_applied_at"])


class DevicePersistenceTests(unittest.TestCase):
    def test_restore_uses_saved_timing_and_retains_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "device-status.json"
            beats = HeartbeatLog(path)
            with patch("server.settings.time.time", return_value=1000):
                beats.record("ip", "ua", 900, fetched=True, applied_version="current")
            with patch("server.settings.time.time", return_value=3000):
                restored = HeartbeatLog(path).snapshot("current", "UTC")
                self.assertEqual(restored["online_state"], "offline")
                self.assertEqual(restored["delivery_state"], "delivered")
            self.assertFalse(path.with_name("device-status.json.tmp").exists())

    def test_invalid_files_degrade_to_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "device-status.json"
            for value in ["{broken", "[]", "{}", '{"ts":false}', "x" * 4097]:
                path.write_text(value, encoding="utf-8")
                with self.assertLogs("server.settings", level="WARNING"):
                    self.assertEqual(HeartbeatLog(path).snapshot("v", "UTC")["online_state"], "unknown")

    def test_saved_record_types_and_confirmation_pairs_are_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "device-status.json"
            base = {"ts": 1000, "ip": "ip", "ua": "ua", "interval": 900, "mode": "v2"}
            cases = [{"ts": True}, {"ts": float("nan")}, {"interval": True},
                     {"interval": 59}, {"mode": "browser"}, {"ua": []},
                     {"applied_version": "version"},
                     {"applied_version": "bad&version", "applied_ts": 1000},
                     {"fetch_ts": -1}, {"unexpected": "value"}]
            for fields in cases:
                with self.subTest(fields=fields):
                    path.write_text(json.dumps({**base, **fields}), encoding="utf-8")
                    with self.assertLogs("server.settings", level="WARNING"):
                        self.assertEqual(HeartbeatLog(path).snapshot("v", "UTC")["online_state"], "unknown")

    def test_write_failure_keeps_live_status_and_other_settings_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "device-status.json"
            settings = Path(directory) / "settings.json"
            settings.write_text("untouched", encoding="utf-8")
            beats = HeartbeatLog(path)
            with patch("server.settings.os.replace", side_effect=OSError("read-only disk")):
                with self.assertLogs("server.settings", level="WARNING"):
                    beats.record("ip", "ua", applied_version="current")
            self.assertEqual(beats.snapshot("current", "UTC")["delivery_state"], "delivered")
            self.assertEqual(settings.read_text(encoding="utf-8"), "untouched")

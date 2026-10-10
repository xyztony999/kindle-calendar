"""Web 管理端：口令会话、配置读写、城市搜索与设备状态。"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
from flask import Blueprint, Response, jsonify, render_template, request, session

from server.settings import SettingsError, env_int, limits

log = logging.getLogger(__name__)

CSRF_HEADER = "kindle-admin"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
GEOCODE_HOSTS = {"geocoding-api.open-meteo.com"}
GEOCODE_TIMEOUT_S = 6
GEOCODE_COUNT = 10


class GeocodeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class LoginLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, dict] = {}

    def retry_after(self, ip: str) -> int | None:
        with self._lock:
            return self._locked_for(ip)

    def fail(self, ip: str) -> int | None:
        threshold = max(1, env_int("ADMIN_LOCK_THRESHOLD", 5))
        seconds = max(1, env_int("ADMIN_LOCK_SECONDS", 900))
        with self._lock:
            locked = self._locked_for(ip)
            if locked is not None:
                return locked
            state = self._state.setdefault(ip, {"fails": 0, "until": 0.0})
            state["fails"] += 1
            if state["fails"] >= threshold:
                state["fails"] = 0
                state["until"] = time.time() + seconds
                return seconds
            return None

    def success(self, ip: str) -> None:
        with self._lock:
            self._state.pop(ip, None)

    def _locked_for(self, ip: str) -> int | None:
        state = self._state.get(ip)
        if not state:
            return None
        remain = state.get("until", 0.0) - time.time()
        if remain > 0:
            return max(1, int(remain + 0.999))
        return None


def _password() -> str:
    return os.environ.get("ADMIN_PASSWORD", "")


def _password_ok(given: str, expected: str) -> bool:
    actual = hashlib.sha256(given.encode("utf-8")).digest()
    wanted = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(actual, wanted)


def _client_ip() -> str:
    return request.remote_addr or "unknown"


def _api_ok(data: dict, status: int = 200):
    resp = jsonify({"ok": True, "data": data})
    resp.status_code = status
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _api_error(code: str, message: str, status: int, details: list | None = None):
    resp = jsonify({"ok": False, "error": {"code": code, "message": message, "details": details or []}})
    resp.status_code = status
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _csrf_ok() -> bool:
    return request.headers.get("X-Requested-With") == CSRF_HEADER


def search_places(query: str) -> list[dict]:
    text = query.strip()
    if not text or len(text) > 50:
        raise GeocodeError("GEOCODE_QUERY_INVALID", "查询须为 1–50 字")
    parts = urlsplit(GEOCODE_URL)
    if parts.scheme != "https" or parts.hostname not in GEOCODE_HOSTS:
        raise GeocodeError("GEOCODE_UPSTREAM_FAILED", "搜索服务暂不可用，请手动填写")
    try:
        resp = requests.get(
            GEOCODE_URL,
            params={"name": text, "count": GEOCODE_COUNT, "language": "zh", "format": "json"},
            timeout=GEOCODE_TIMEOUT_S,
            allow_redirects=False,
        )
        if resp.is_redirect or resp.status_code != 200:
            raise GeocodeError("GEOCODE_UPSTREAM_FAILED", "搜索服务暂不可用，请手动填写")
        payload = resp.json()
    except GeocodeError:
        raise
    except Exception as exc:
        log.warning("geocoding 失败: %s", exc)
        raise GeocodeError("GEOCODE_UPSTREAM_FAILED", "搜索服务暂不可用，请手动填写") from exc

    candidates = []
    for item in (payload.get("results") or [])[:GEOCODE_COUNT]:
        if not isinstance(item, dict):
            continue
        try:
            latitude = round(float(item["latitude"]), 4)
            longitude = round(float(item["longitude"]), 4)
        except (KeyError, TypeError, ValueError):
            continue
        candidates.append(
            {
                "name": item.get("name") or "",
                "admin1": item.get("admin1") or "",
                "country": item.get("country") or "",
                "latitude": latitude,
                "longitude": longitude,
                "timezone": item.get("timezone") or "",
            }
        )
    return candidates


def create_admin_blueprint(service) -> Blueprint:
    bp = Blueprint("admin", __name__, template_folder="templates")
    limiter = LoginLimiter()

    def enabled() -> bool:
        return bool(_password())

    def require_session():
        if not enabled():
            return _api_error("ADMIN_DISABLED", "管理端未启用，请设置 ADMIN_PASSWORD", 503)
        if not session.get("admin"):
            return _api_error("ADMIN_AUTH_REQUIRED", "请先登录", 401)
        return None

    def require_write():
        if not enabled():
            return _api_error("ADMIN_DISABLED", "管理端未启用，请设置 ADMIN_PASSWORD", 503)
        if not _csrf_ok():
            return _api_error("ADMIN_CSRF_REJECTED", "缺少防护头", 403)
        if not session.get("admin"):
            return _api_error("ADMIN_AUTH_REQUIRED", "请先登录", 401)
        return None

    def save_body(payload: dict):
        try:
            saved, version, changed, refreshed = service.store.save(payload)
        except SettingsError as exc:
            status = 500 if exc.code == "SETTINGS_IO_FAILED" else 400
            return _api_error(exc.code, exc.message, status, exc.details)
        return _api_ok(
            {
                "settings": saved,
                "settings_version": version,
                "location_changed": changed,
                "weather_refreshed": refreshed,
            }
        )

    @bp.get("/admin")
    def admin_page():
        if not enabled():
            boot = {"view": "disabled"}
            status = 503
        elif session.get("admin"):
            boot = {"view": "settings"}
            status = 200
        else:
            boot = {"view": "login"}
            status = 200
        html = render_template("admin.html", boot=boot)
        resp = Response(html, status=status, mimetype="text/html; charset=utf-8")
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @bp.post("/admin/api/login")
    def login():
        if not enabled():
            return _api_error("ADMIN_DISABLED", "管理端未启用，请设置 ADMIN_PASSWORD", 503)
        if not _csrf_ok():
            return _api_error("ADMIN_CSRF_REJECTED", "缺少防护头", 403)
        ip = _client_ip()
        locked = limiter.retry_after(ip)
        if locked is not None:
            return _api_error(
                "ADMIN_AUTH_LOCKED",
                "失败次数过多，请稍后再试",
                429,
                [{"retry_after_s": locked}],
            )
        body = request.get_json(silent=True) or {}
        password = body.get("password") if isinstance(body, dict) else None
        if not isinstance(password, str) or not _password_ok(password, _password()):
            retry = limiter.fail(ip)
            log.info("管理端登录失败 ip=%s", ip)
            if retry is not None:
                return _api_error(
                    "ADMIN_AUTH_LOCKED",
                    "失败次数过多，请稍后再试",
                    429,
                    [{"retry_after_s": retry}],
                )
            return _api_error("ADMIN_AUTH_INVALID", "口令错误", 401)
        limiter.success(ip)
        session.clear()
        session["admin"] = True
        session.permanent = True
        days = max(1, env_int("ADMIN_SESSION_DAYS", 7))
        expires = datetime.now(timezone.utc) + timedelta(days=days)
        log.info("管理端登录成功 ip=%s", ip)
        return _api_ok({"expires_at": expires.isoformat(timespec="seconds")})

    @bp.post("/admin/api/logout")
    def logout():
        blocked = require_write()
        if blocked:
            return blocked
        session.clear()
        return _api_ok({"ok": True})

    @bp.get("/admin/api/settings")
    def get_settings():
        blocked = require_session()
        if blocked:
            return blocked
        current, degraded, version = service.store.current()
        return _api_ok(
            {
                "settings": current,
                "settings_version": version,
                "degraded": degraded,
                "defaults": service.store.defaults(),
                "limits": limits(),
            }
        )

    @bp.post("/admin/api/settings/save")
    def save_settings():
        blocked = require_write()
        if blocked:
            return blocked
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _api_error(
                "SETTINGS_VALIDATION_FAILED",
                "请求体须为 JSON 对象",
                400,
                [{"field": "", "code": "PAGES_SET_INVALID", "message": "请求体须为 JSON 对象"}],
            )
        return save_body(body)

    @bp.post("/admin/api/settings/reset")
    def reset_settings():
        blocked = require_write()
        if blocked:
            return blocked
        return save_body(service.store.defaults())

    @bp.get("/admin/api/settings/export")
    def export_settings():
        blocked = require_session()
        if blocked:
            return blocked
        current, _degraded, _version = service.store.current()
        try:
            day = datetime.now(ZoneInfo(current["location"]["timezone"])).strftime("%Y%m%d")
        except Exception:
            day = datetime.now(timezone.utc).strftime("%Y%m%d")
        raw = json.dumps(current, ensure_ascii=False, indent=2) + "\n"
        resp = Response(raw, mimetype="application/json; charset=utf-8")
        resp.headers["Content-Disposition"] = f'attachment; filename="kindle-calendar-settings-{day}.json"'
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @bp.post("/admin/api/settings/import")
    def import_settings():
        blocked = require_write()
        if blocked:
            return blocked
        upload = request.files.get("file")
        if upload is not None:
            raw = upload.read()
        else:
            raw = request.get_data(cache=False) or b""
        if len(raw) > 32 * 1024:
            return _api_error("SETTINGS_IMPORT_INVALID", "导入文件过大或不是受支持的配置", 400)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return _api_error("SETTINGS_IMPORT_INVALID", "导入文件不是有效的 JSON", 400)
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            return _api_error("SETTINGS_IMPORT_INVALID", "导入文件的 schema_version 不受支持", 400)
        return save_body(payload)

    @bp.get("/admin/api/geocode")
    def geocode():
        blocked = require_session()
        if blocked:
            return blocked
        try:
            candidates = search_places(request.args.get("q") or "")
        except GeocodeError as exc:
            status = 400 if exc.code == "GEOCODE_QUERY_INVALID" else 502
            return _api_error(exc.code, exc.message, status)
        return _api_ok({"candidates": candidates})

    @bp.get("/admin/api/device")
    def device():
        blocked = require_session()
        if blocked:
            return blocked
        return _api_ok(service.device_status())

    return bp

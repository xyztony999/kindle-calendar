"""Kindle 天气台历 HTTP 服务（v2：JSON 数据 + 分区图 + 整页兼容）。"""

from __future__ import annotations

import hashlib
import logging
import json
import os
import re
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote

import yaml
from flask import Flask, Response, jsonify, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from server.admin import create_admin_blueprint
from server.landing import endpoint_rows, landing_copy, resolve_landing_lang
from server.locale import LANG_COOKIE, LANG_MAX_AGE, THEME_COOKIE, device_lang, explicit_lang, web_lang, web_theme
from server.reading import (
    prefer_html,
    render_dashboard,
    render_env,
    render_health,
    render_unavailable,
    render_weather,
)
from server.service import DashboardService
from server.settings import env_int
from server.viewer import render_viewer, render_viewer_missing, viewer_wants_html

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_config() -> dict:
    path = CONFIG_PATH
    if not path.exists():
        path = ROOT / "config.example.yaml"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    # 环境变量覆盖（云端部署时使用，无需 config.yaml）
    if _env("LOCATION_NAME"):
        config["location_name"] = _env("LOCATION_NAME")
    if _env("LATITUDE"):
        config["latitude"] = float(_env("LATITUDE"))
    if _env("LONGITUDE"):
        config["longitude"] = float(_env("LONGITUDE"))
    if _env("TIMEZONE"):
        config["timezone"] = _env("TIMEZONE")
    if _env("FONT_PATH"):
        config["font_path"] = _env("FONT_PATH")

    screen = config.setdefault("screen", {})
    if _env("SCREEN_WIDTH"):
        screen["width"] = int(_env("SCREEN_WIDTH"))
    if _env("SCREEN_HEIGHT"):
        screen["height"] = int(_env("SCREEN_HEIGHT"))

    server = config.setdefault("server", {})
    if _env("PORT"):
        server["port"] = int(_env("PORT"))
    server.setdefault("host", "0.0.0.0")
    server.setdefault("port", 8080)

    config.setdefault("location_name", "北京")
    config.setdefault("latitude", 39.9042)
    config.setdefault("longitude", 116.4074)
    config.setdefault("timezone", "Asia/Shanghai")
    config.setdefault("font_path", "")
    screen.setdefault("width", 758)
    screen.setdefault("height", 1024)

    return config


_REGION_RE = re.compile(r"^[a-z0-9-]+$")
_GLYPH_RE = re.compile(r"^(?:[0-9:]|am|pm)$")


def _apply_lang_cookie(resp: Response) -> Response:
    chosen = explicit_lang(request.args.get("lang"))
    if chosen is None:
        return resp
    resp.set_cookie(
        LANG_COOKIE,
        chosen,
        max_age=LANG_MAX_AGE,
        path="/",
        samesite="Lax",
        httponly=True,
        secure=request.is_secure,
    )
    return resp


def _machine_json(payload: dict) -> Response:
    resp = jsonify(payload)
    resp.headers["Vary"] = "Accept"
    return resp


def _machine_text(body: str) -> Response:
    resp = Response(body, mimetype="text/plain")
    resp.headers["Vary"] = "Accept"
    return resp


def _html_page(body: str, status: int = 200) -> Response:
    resp = Response(body, status=status, mimetype="text/html")
    resp.headers["Vary"] = "Accept"
    return _apply_lang_cookie(resp)


def _reading_lang(html: bool) -> str:
    if html:
        return web_lang(
            request.args.get("lang"),
            request.cookies.get(LANG_COOKIE),
            request.headers.get("Accept-Language"),
        )
    return device_lang(request.args.get("lang"))


def _png_response(png: bytes, etag: str | None = None, max_age: int = 300) -> Response:
    if etag is not None and request.headers.get("If-None-Match") == etag:
        resp = Response(status=304)
    else:
        resp = Response(png, mimetype="image/png")
    resp.headers["ETag"] = etag or ""
    resp.headers["Cache-Control"] = f"public, max-age={max_age}"
    resp.headers["Vary"] = "Accept"
    return resp


def create_app() -> Flask:
    config = load_config()
    service = DashboardService(config)

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
    app.permanent_session_lifetime = timedelta(days=max(1, env_int("ADMIN_SESSION_DAYS", 7)))
    app.register_blueprint(create_admin_blueprint(service))
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

    @app.errorhandler(413)
    def _request_too_large(_error):
        return jsonify({"ok": False, "error": {"code": "REQUEST_TOO_LARGE", "message": "请求体过大"}}), 413

    @app.before_request
    def _secure_session_cookie():
        if request.is_secure:
            app.config["SESSION_COOKIE_SECURE"] = True

    @app.get("/")
    def index():
        payload = {
            "name": "kindle-calendar",
            "version": 2.1,
            "endpoints": {
                "/api/v1/dashboard.json": "台历数据 JSON",
                "/api/v1/dashboard.env": "设备端 POSIX env 配置（五页分区+轮播参数）",
                "/r/<page>/<region>.png": "页面分区图（today/week/month/detail/almanac）",
                "/r/today/clock/<glyph>.png": "时钟字形（0-9 与冒号）",
                "/dashboard.png?page=": "整页合成图（v1 兼容，默认 today）",
                "/admin": "管理端（口令登录）",
                "/weather": "当前天气 JSON",
                "/health": "健康检查",
            },
        }
        wants_json = request.args.get("format") == "json" or (
            request.accept_mimetypes.best_match(["text/html", "application/json"]) == "application/json"
        )
        if wants_json:
            return jsonify(payload)
        lang = resolve_landing_lang(
            request.args.get("lang"),
            request.headers.get("Accept-Language"),
            request.cookies.get(LANG_COOKIE),
        )
        copy = landing_copy(lang)
        resp = Response(
            render_template(
                "index.html",
                version=payload["version"],
                endpoints=endpoint_rows(lang, payload["endpoints"]),
                copy=copy,
                theme=web_theme(request.cookies.get(THEME_COOKIE)),
            )
        )
        return _apply_lang_cookie(resp)

    @app.get("/health")
    def health():
        info = {"status": "ok", **service.health_info()}
        if prefer_html(request.args.get("format"), request.headers.get("Accept")):
            return _html_page(render_health(info, _reading_lang(True)))
        return _machine_json(info)

    @app.get("/api/v1/dashboard.json")
    def dashboard_json():
        html = prefer_html(request.args.get("format"), request.headers.get("Accept"))
        try:
            payload = service.get_payload(_reading_lang(html))
        except Exception:
            if html:
                log.exception("台历阅读页暂时读不到")
                return _html_page(render_unavailable(_reading_lang(True), "dashboard"), 500)
            raise
        if html:
            return _html_page(render_dashboard(payload, _reading_lang(True)))
        return _machine_json(payload)

    def _device_interval():
        if request.headers.get("X-Kindle-Device") != "dash":
            return None
        raw = request.headers.get("X-Kindle-Interval", "900")
        if not re.fullmatch(r"[0-9]{1,5}", raw) or not 60 <= int(raw) <= 86400:
            return None
        return int(raw)

    def _note_device_fetch(mode):
        interval = _device_interval()
        if interval is not None:
            service.note_heartbeat(request.remote_addr or "", request.headers.get("User-Agent", ""), interval, mode)

    @app.post("/api/v1/device/heartbeat")
    def device_heartbeat():
        def reject(code, reason, status=400):
            log.warning("Device heartbeat rejected: %s (%s)", code, reason)
            return jsonify({"ok": False, "error": {"code": code, "message": reason}}), status

        if request.headers.get("X-Kindle-Device") != "dash":
            return reject("DEVICE_MARKER_REQUIRED", "X-Kindle-Device must be dash")
        if request.content_length is not None and request.content_length > 2048:
            return reject("HEARTBEAT_TOO_LARGE", "Request body exceeds 2048 bytes", 413)
        raw = request.stream.read(2049)
        if len(raw) > 2048:
            return reject("HEARTBEAT_TOO_LARGE", "Request body exceeds 2048 bytes", 413)
        if request.mimetype not in ("application/json", "application/x-www-form-urlencoded"):
            return reject("HEARTBEAT_CONTENT_TYPE", "Use application/json or application/x-www-form-urlencoded")

        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate field: " + key)
                result[key] = value
            return result

        try:
            text = raw.decode("utf-8").strip()
            if text[:3].lower() == "%7b":
                text = unquote(text, encoding="utf-8", errors="strict")
            is_json = request.mimetype == "application/json" or text.startswith("{")
            if is_json:
                data = json.loads(text, object_pairs_hook=unique_pairs)
            else:
                data = unique_pairs(parse_qsl(text, keep_blank_values=True, strict_parsing=True))
                value = data.get("interval_s", "")
                if not re.fullmatch(r"[0-9]{1,5}", value):
                    return reject("HEARTBEAT_INTERVAL", "interval_s must be an integer from 60 to 86400")
                data["interval_s"] = int(value)
        except (ValueError, UnicodeError) as exc:
            return reject("HEARTBEAT_BODY_INVALID", "Malformed payload or duplicate fields")
        if not isinstance(data, dict) or data.keys() - {"interval_s", "mode", "applied_version"}:
            return reject("HEARTBEAT_BODY_INVALID", "Expected an object containing only interval_s, mode, applied_version")
        interval = data.get("interval_s")
        mode = data.get("mode")
        version = data.get("applied_version")
        if type(interval) is not int or not 60 <= interval <= 86400:
            return reject("HEARTBEAT_INTERVAL", "interval_s must be an integer from 60 to 86400")
        if mode not in ("v1", "v2"):
            return reject("HEARTBEAT_MODE", "mode must be v1 or v2")
        if version is not None and (not isinstance(version, str) or
                (version and not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", version))):
            return reject("HEARTBEAT_VERSION", "applied_version must be empty or use 1-128 letters, digits, dots, underscores or hyphens")
        if mode == "v1" and version:
            return reject("HEARTBEAT_VERSION", "v1 cannot confirm a layout version")
        service.note_heartbeat(request.remote_addr or "", request.headers.get("User-Agent", ""),
                               interval, mode, fetched=False, applied_version=version)
        log.info("Device heartbeat accepted: mode=%s applied_version=%s", mode, version or "unchanged")
        return jsonify({"ok": True})

    @app.get("/api/v1/dashboard.env")
    def dashboard_env():
        html = prefer_html(request.args.get("format"), request.headers.get("Accept"))
        try:
            env = service.build_env(request.host_url, _reading_lang(html))
        except Exception:
            if html:
                log.exception("设备清单阅读页暂时读不到")
                return _html_page(render_unavailable(_reading_lang(True), "env"), 500)
            raise
        if not html:
            _note_device_fetch("v2")
        if html:
            return _html_page(render_env(env, _reading_lang(True)))
        return _machine_text(env)

    def _image_missing():
        if viewer_wants_html():
            return _html_page(render_viewer_missing(), 404)
        return Response("not found", status=404)

    @app.get("/api/v1/script")
    def device_script():
        """下发镜像内 dash.sh（供设备端自更新校验比对）。"""
        try:
            body = (ROOT / "kindle" / "dash.sh").read_bytes()
        except OSError:
            return _machine_text("script missing"), 404
        # md5 仅作内容校验和：busybox md5sum 是设备端唯一保证可用的工具；传输走自有服务器 https，非对抗场景
        digest = hashlib.md5(body).hexdigest()
        resp = Response(body, mimetype="text/plain; charset=utf-8")
        resp.headers["ETag"] = f'"{digest}"'
        resp.headers["X-Script-Md5"] = digest
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Vary"] = "Accept"
        return resp

    @app.get("/r/<page>/<region>.png")
    def region_png(page: str, region: str):
        if not _REGION_RE.match(region) or not service.has_page(page):
            return _image_missing()
        record = service.page_record(page)
        from server.layout import http_region_names

        if record is None or region not in http_region_names(record):
            return _image_missing()
        # 月历 title/grid 支持任意月偏移（跨月浏览）
        offset = request.args.get("offset", type=int) or 0
        if viewer_wants_html():
            return _html_page(render_viewer("region", page=page, region=region, offset=offset))
        rendered = service.get_region(page, region, offset, device_lang(request.args.get("lang")))
        if rendered is None:
            return _image_missing()
        return _png_response(rendered.png, f"{rendered.etag}-{offset}" if offset else rendered.etag)

    @app.get("/r/<page>/clock/<glyph>.png")
    def clock_glyph_png(page: str, glyph: str):
        if not service.has_page(page) or not _GLYPH_RE.match(glyph):
            return _image_missing()
        if viewer_wants_html():
            return _html_page(render_viewer("clock", glyph=glyph))
        glyphs = service.get_glyphs(page)
        if glyph not in glyphs:
            return _image_missing()
        return _png_response(glyphs[glyph], f"glyph-{page}-{glyph}")

    @app.get("/dashboard.png")
    def dashboard_png():
        page = request.args.get("page", "today")
        if not service.has_page(page):
            log.warning("未知页面参数 page=%s，回退 today", page)
            page = "today"
        offset = request.args.get("offset", type=int) or 0
        if viewer_wants_html():
            return _html_page(render_viewer("page", page=page, offset=offset))
        png = service.get_composite(page, device_lang(request.args.get("lang")))
        _note_device_fetch("v1")
        return _png_response(png, max_age=60)

    @app.get("/weather")
    def weather_json():
        html = prefer_html(request.args.get("format"), request.headers.get("Accept"))
        try:
            payload = service.get_payload(_reading_lang(html))
        except Exception:
            if html:
                log.exception("天气阅读页暂时读不到")
                return _html_page(render_unavailable(_reading_lang(True), "weather"), 500)
            raise
        body = {
            "current": payload["weather"]["current"],
            "daily": payload["weather"]["daily"],
            "hourly": payload["weather"]["hourly"],
        }
        if html:
            return _html_page(render_weather(payload, _reading_lang(True)))
        return _machine_json(body)

    return app


def main() -> None:
    config = load_config()
    host = config["server"]["host"]
    port = config["server"]["port"]
    log.info("服务启动: http://%s:%d/dashboard.png", host, port)
    log.info("城市: %s (%.2f, %.2f)", config["location_name"], config["latitude"], config["longitude"])
    create_app().run(host=host, port=port, debug=False)


# nginx TLS 终结后经 X-Forwarded-Proto 传递真实协议，
# 否则 dashboard.env 里的分区图 URL 会退化为 http://（或反代未传 Host 时退化为 127.0.0.1）
app = ProxyFix(create_app(), x_proto=1)


if __name__ == "__main__":
    main()

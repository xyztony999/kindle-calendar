"""Kindle 天气台历 HTTP 服务（v2：JSON 数据 + 分区图 + 整页兼容）。"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import yaml
from flask import Flask, Response, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from server.service import DashboardService

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


_REGION_RE = re.compile(r"^[a-z]+$")
_GLYPH_RE = re.compile(r"^[0-9:]$")


def _png_response(png: bytes, etag: str | None = None, max_age: int = 300) -> Response:
    if etag is not None and request.headers.get("If-None-Match") == etag:
        resp = Response(status=304)
    else:
        resp = Response(png, mimetype="image/png")
    resp.headers["ETag"] = etag or ""
    resp.headers["Cache-Control"] = f"public, max-age={max_age}"
    return resp


def create_app() -> Flask:
    config = load_config()
    service = DashboardService(config)

    app = Flask(__name__)

    @app.get("/")
    def index():
        return jsonify(
            {
                "name": "kindle-calendar",
                "version": 2,
                "endpoints": {
                    "/api/v1/dashboard.json": "台历数据 JSON",
                    "/api/v1/dashboard.env": "设备端 POSIX env 配置",
                    "/r/today/<region>.png": "今日页分区图",
                    "/r/today/clock/<glyph>.png": "时钟字形（0-9 与冒号）",
                    "/dashboard.png": "整页合成图（v1 兼容）",
                    "/weather": "当前天气 JSON",
                    "/health": "健康检查",
                },
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", **service.health_info()})

    @app.get("/api/v1/dashboard.json")
    def dashboard_json():
        return jsonify(service.get_payload())

    @app.get("/api/v1/dashboard.env")
    def dashboard_env():
        env = service.build_env(request.host_url)
        return Response(env, mimetype="text/plain")

    @app.get("/r/<page>/<region>.png")
    def region_png(page: str, region: str):
        if page != "today" or not _REGION_RE.match(region):
            return Response("not found", status=404)
        rendered = service.get_region(region)
        if rendered is None:
            return Response("not found", status=404)
        return _png_response(rendered.png, rendered.etag)

    @app.get("/r/<page>/clock/<glyph>.png")
    def clock_glyph_png(page: str, glyph: str):
        if page != "today" or not _GLYPH_RE.match(glyph):
            return Response("not found", status=404)
        glyphs = service.get_glyphs()
        return _png_response(glyphs[glyph], f"glyph-{glyph}")

    @app.get("/dashboard.png")
    def dashboard_png():
        png = service.get_composite()
        return _png_response(png, max_age=60)

    @app.get("/weather")
    def weather_json():
        payload = service.get_payload()
        cur = payload["weather"]["current"]
        return jsonify(
            {
                "current": cur,
                "daily": payload["weather"]["daily"],
                "hourly": payload["weather"]["hourly"],
            }
        )

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

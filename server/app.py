"""Kindle 天气台历 HTTP 服务。"""

from __future__ import annotations

import io
import logging
import os
import threading
import time
from pathlib import Path

import yaml
from flask import Flask, Response, jsonify

from server.renderer import render_dashboard
from server.weather import WeatherData, fetch_weather

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
    else:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

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


class DashboardCache:
    """缓存渲染结果，避免每次请求都拉取天气。"""

    def __init__(self, refresh_seconds: int = 900) -> None:
        self.refresh_seconds = refresh_seconds
        self._lock = threading.Lock()
        self._png: bytes | None = None
        self._weather: WeatherData | None = None
        self._updated_at: float = 0

    def get_png(self, config: dict) -> bytes:
        with self._lock:
            if self._png is None or time.time() - self._updated_at > self.refresh_seconds:
                self._refresh(config)
            assert self._png is not None
            return self._png

    def get_weather(self, config: dict) -> WeatherData:
        with self._lock:
            if self._weather is None or time.time() - self._updated_at > self.refresh_seconds:
                self._refresh(config)
            assert self._weather is not None
            return self._weather

    def _refresh(self, config: dict) -> None:
        log.info("刷新天气与台历图像…")
        weather = fetch_weather(
            config["latitude"],
            config["longitude"],
            config["timezone"],
        )
        screen = config["screen"]
        img = render_dashboard(
            weather,
            width=screen["width"],
            height=screen["height"],
            location_name=config["location_name"],
            timezone=config["timezone"],
            font_path=config.get("font_path", ""),
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self._png = buf.getvalue()
        self._weather = weather
        self._updated_at = time.time()
        log.info("图像已更新 (%d bytes)", len(self._png))


def create_app() -> Flask:
    config = load_config()
    cache = DashboardCache()

    app = Flask(__name__)

    @app.get("/")
    def index():
        return jsonify(
            {
                "name": "kindle-calendar",
                "endpoints": {
                    "/dashboard.png": "Kindle 台历 PNG 图像",
                    "/health": "健康检查",
                    "/weather": "当前天气 JSON",
                },
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/dashboard.png")
    def dashboard_png():
        png = cache.get_png(config)
        return Response(png, mimetype="image/png")

    @app.get("/weather")
    def weather_json():
        w = cache.get_weather(config)
        return jsonify(
            {
                "current": {
                    "temperature": w.current.temperature,
                    "humidity": w.current.humidity,
                    "wind_speed": w.current.wind_speed,
                    "description": w.current.description,
                },
                "daily": [
                    {
                        "date": d.date,
                        "temp_min": d.temp_min,
                        "temp_max": d.temp_max,
                        "description": d.description,
                    }
                    for d in w.daily
                ],
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


app = create_app()

if __name__ == "__main__":
    main()

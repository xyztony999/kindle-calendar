"""服务编排：天气拉取（stale-while-revalidate）、payload 构建、分区渲染与缓存。"""

from __future__ import annotations

import hashlib
import io
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime

from PIL import Image
from zoneinfo import ZoneInfo

from server import data as data_mod
from server.render import compose, render_glyphs, render_regions, clock_metrics, today_regions
from server.render.regions import Rect
from server.weather import WeatherData, fetch_weather

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegionRender:
    rect: Rect
    png: bytes
    etag: str


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class DashboardService:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.refresh_seconds = 900
        self.error_backoff_seconds = 60

        screen = config["screen"]
        self.width = screen["width"]
        self.height = screen["height"]
        self.font_path = config.get("font_path", "")

        self._lock = threading.Lock()  # 保护 payload / regions / glyphs
        self._weather: WeatherData | None = None
        self._weather_at = 0.0
        self._last_error: str | None = None
        self._refreshing = False
        self._weather_cond = threading.Condition()  # 保护天气状态与刷新标志

        self._payload: dict | None = None
        self._payload_fingerprint = ""
        self._regions: dict[str, RegionRender] = {}
        self._regions_fingerprint = ""
        self._glyphs: dict[str, bytes] = {}
        self._glyphs_key: tuple | None = None

    # ── 天气（stale-while-revalidate，沿用 v1 DashboardCache 策略）──

    def _fetch_weather(self) -> WeatherData | None:
        return fetch_weather(
            self.config["latitude"],
            self.config["longitude"],
            self.config["timezone"],
        )

    def _refresh_weather(self) -> None:
        try:
            weather = self._fetch_weather()
        except Exception as exc:
            log.exception("天气拉取失败: %s", exc)
            with self._weather_cond:
                self._last_error = str(exc)
            return
        now = time.time()
        with self._weather_cond:
            self._weather = weather
            self._weather_at = now
            self._last_error = None
        log.info("天气已更新")

    def _ensure_weather(self) -> None:
        with self._weather_cond:
            fresh = self._weather is not None and time.time() - self._weather_at <= self.refresh_seconds
            if fresh:
                return
            first_load = self._weather is None
            if not first_load:
                if not self._refreshing:
                    self._refreshing = True
                    threading.Thread(target=self._background_refresh, daemon=True, name="weather-refresh").start()
                return
            if self._refreshing:
                while self._refreshing and self._weather is None:
                    self._weather_cond.wait(timeout=1.0)
                return
            self._refreshing = True

        try:
            self._refresh_weather()
        finally:
            with self._weather_cond:
                self._refreshing = False
                self._weather_cond.notify_all()

    def _background_refresh(self) -> None:
        try:
            self._refresh_weather()
        finally:
            with self._weather_cond:
                self._refreshing = False
                self._weather_cond.notify_all()

    # ── payload / 渲染 ──

    def get_payload(self) -> dict:
        self._ensure_weather()
        now = datetime.now(ZoneInfo(self.config["timezone"]))
        with self._weather_cond:
            weather = self._weather
        if weather is None:
            raise RuntimeError(self._last_error or "天气数据不可用")

        payload = data_mod.build_payload(self.config, weather, now)
        fingerprint = data_mod.data_fingerprint(payload)
        with self._lock:
            self._payload = payload
            self._payload_fingerprint = fingerprint
        return payload

    def _get_regions(self) -> dict[str, RegionRender]:
        payload = self.get_payload()
        fingerprint = self._payload_fingerprint
        with self._lock:
            if self._regions and self._regions_fingerprint == fingerprint:
                return self._regions

        images = render_regions(payload, self.width, self.height, self.font_path)
        rects = today_regions(self.width, self.height)
        regions: dict[str, RegionRender] = {}
        for name, img in images.items():
            png = _png_bytes(img)
            regions[name] = RegionRender(rect=rects[name], png=png, etag=hashlib.sha256(png).hexdigest()[:32])

        with self._lock:
            self._regions = regions
            self._regions_fingerprint = fingerprint
        return regions

    def get_region(self, name: str) -> RegionRender | None:
        regions = self._get_regions()
        return regions.get(name)

    def get_glyphs(self) -> dict[str, bytes]:
        key = (self.width, self.height, self.font_path)
        with self._lock:
            if self._glyphs and self._glyphs_key == key:
                return self._glyphs

        metrics = clock_metrics(self.width, self.height)
        glyphs = {ch: _png_bytes(img) for ch, img in render_glyphs(metrics, self.font_path).items()}
        with self._lock:
            self._glyphs = glyphs
            self._glyphs_key = key
        return glyphs

    def get_composite(self) -> bytes:
        payload = self.get_payload()
        img = compose(payload, self.width, self.height, self.font_path)
        return _png_bytes(img)

    # ── 设备端 env ──

    def build_env(self, base_url: str) -> str:
        base = base_url.rstrip("/")
        regions = self._get_regions()
        payload = self._payload or {}
        metrics = clock_metrics(self.width, self.height)

        lines = [
            f"DASH_DATE={payload.get('date', {}).get('iso', '').replace('-', '')}",
            f"REGIONS_VERSION={self._regions_fingerprint}",
            f"SCREEN_W={self.width}",
            f"SCREEN_H={self.height}",
        ]
        for name, region in regions.items():
            key = name.upper()
            lines += [
                f"R_{key}_X={region.rect.x}",
                f"R_{key}_Y={region.rect.y}",
                f"R_{key}_W={region.rect.w}",
                f"R_{key}_H={region.rect.h}",
                f'R_{key}_URL="{base}/r/today/{name}.png"',
                f'R_{key}_ETAG="{region.etag}"',
            ]

        x0 = (self.width - metrics.total_w()) // 2
        lines += [
            f"CLOCK_X={x0}",
            f"CLOCK_Y={today_regions(self.width, self.height)['clock'].y + (today_regions(self.width, self.height)['clock'].h - metrics.digit_h) // 2}",
            f"CLOCK_DIGIT_W={metrics.digit_w}",
            f"CLOCK_DIGIT_H={metrics.digit_h}",
            f"CLOCK_COLON_W={metrics.colon_w}",
            f"CLOCK_GAP={metrics.gap}",
            f'CLOCK_GLYPH_URL_PREFIX="{base}/r/today/clock/"',
            f'LEGACY_URL="{base}/dashboard.png"',
        ]
        return "\n".join(lines) + "\n"

    def health_info(self) -> dict:
        with self._weather_cond:
            return {
                "has_weather": self._weather is not None,
                "weather_age_seconds": None if self._weather_at == 0 else round(time.time() - self._weather_at, 1),
                "refreshing": self._refreshing,
                "last_error": self._last_error,
                "screen": f"{self.width}x{self.height}",
            }

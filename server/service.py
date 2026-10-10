"""服务编排：天气拉取（stale-while-revalidate）、payload 构建、五页分区渲染与缓存。

分区资产键：(page, region)；月历含三月预裁（title/grid × prev/cur/next）。
env 契约：R_{PAGE}_{REGION}_* 坐标/URL/ETAG + 每页分区清单 + 轮播参数；
P1 旧名（R_HEADER_* 等）保留一个版本作兼容别名。
"""

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
from server.render import (
    PAGE_REGION_LISTS,
    PAGES,
    compose_page,
    page_region_names,
    page_regions,
    render_glyphs,
    render_page_regions,
)
from server.render.regions import Rect, clock_metrics
from server.weather import WeatherData, fetch_weather

log = logging.getLogger(__name__)

# P1 env 变量名 → v2 名（兼容别名，保留一个版本）
_LEGACY_ALIASES = {
    "R_HEADER": "R_TODAY_HEADER",
    "R_WEATHER": "R_TODAY_WEATHER",
    "R_SUN": "R_TODAY_SUN",
    "R_SCENE": "R_TODAY_SCENE",
    "R_QUOTE": "R_TODAY_QUOTE",
}


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
        self._regions: dict[tuple[str, str], RegionRender] = {}
        self._regions_fingerprint = ""
        self._month_offset_cache: dict[tuple, RegionRender] = {}  # (region, offset, fingerprint)
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

    def _get_regions(self) -> dict[tuple[str, str], RegionRender]:
        payload = self.get_payload()
        fingerprint = self._payload_fingerprint
        with self._lock:
            if self._regions and self._regions_fingerprint == fingerprint:
                return self._regions

        regions: dict[tuple[str, str], RegionRender] = {}
        for page in PAGES:
            images = render_page_regions(page, payload, self.width, self.height, self.font_path)
            rects = page_regions(page, self.width, self.height)
            for key, img in images.items():
                base = key.split("-")[0] if key in ("title-prev", "title-next", "grid-prev", "grid-next") else key
                png = _png_bytes(img)
                regions[(page, key)] = RegionRender(
                    rect=rects[base], png=png, etag=hashlib.sha256(png).hexdigest()[:32]
                )

        with self._lock:
            self._regions = regions
            self._regions_fingerprint = fingerprint
        return regions

    def get_region(self, page: str, region: str, offset: int = 0) -> RegionRender | None:
        if page not in PAGES or region not in page_region_names(page):
            return None
        # 月历 title/grid 支持任意月偏移（跨月浏览），独立小缓存
        if page == "month" and region in ("title", "grid") and offset != 0:
            return self._get_month_offset_region(region, offset)
        regions = self._get_regions()
        return regions.get((page, region))

    def _get_month_offset_region(self, region: str, offset: int) -> RegionRender:
        offset = max(-120, min(120, int(offset)))
        payload = self.get_payload()
        key = (region, offset, self._payload_fingerprint)
        with self._lock:
            cached = self._month_offset_cache.get(key)
        if cached is not None:
            return cached

        from server.render.pages import month as month_page

        rects = page_regions("month", self.width, self.height)
        if region == "title":
            img = month_page.render_title(payload, rects["title"], self.font_path, offset=offset)
        else:
            img = month_page.render_grid(payload, rects["grid"], self.font_path, offset=offset)
        png = _png_bytes(img)
        rendered = RegionRender(rect=rects[region], png=png, etag=hashlib.sha256(png).hexdigest()[:32])

        with self._lock:
            if len(self._month_offset_cache) > 64:  # 两年跨度的 LRU 上限
                self._month_offset_cache.clear()
            self._month_offset_cache[key] = rendered
        return rendered

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

    def get_composite(self, page: str = "today") -> bytes:
        if page not in PAGES:
            page = "today"
        payload = self.get_payload()
        img = compose_page(page, payload, self.width, self.height, self.font_path)
        return _png_bytes(img)

    # ── 设备端 env ──

    def build_env(self, base_url: str) -> str:
        base = base_url.rstrip("/")
        regions = self._get_regions()
        payload = self._payload or {}
        metrics = clock_metrics(self.width, self.height)
        clock_rect = page_regions("today", self.width, self.height)["clock"]

        def region_lines(var_prefix: str, page: str, key: str, region: RegionRender) -> list[str]:
            return [
                f"{var_prefix}_X={region.rect.x}",
                f"{var_prefix}_Y={region.rect.y}",
                f"{var_prefix}_W={region.rect.w}",
                f"{var_prefix}_H={region.rect.h}",
                f'{var_prefix}_URL="{base}/r/{page}/{key}.png"',
                f'{var_prefix}_ETAG="{region.etag}"',
            ]

        lines = [
            f"DASH_DATE={payload.get('date', {}).get('iso', '').replace('-', '')}",
            f"REGIONS_VERSION={self._regions_fingerprint}",
            f"SCREEN_W={self.width}",
            f"SCREEN_H={self.height}",
            f'PAGES="{" ".join(PAGES)}"',
        ]

        # 每页分区清单 + 各分区变量（month 的 title/grid 统一三预裁键 PREV/CUR/NEXT）
        _MONTH_KEYS = {"title": "TITLE_CUR", "grid": "GRID_CUR", "title-prev": "TITLE_PREV", "grid-prev": "GRID_PREV", "title-next": "TITLE_NEXT", "grid-next": "GRID_NEXT"}
        for page in PAGES:
            upper = page.upper()
            lines.append(f'R_{upper}_REGIONS="{" ".join(r.upper() for r in PAGE_REGION_LISTS[page])}"')
            for key in page_region_names(page):
                region = regions.get((page, key))
                if region is None:
                    continue
                var_key = _MONTH_KEYS.get(key, key.upper().replace("-", "_")) if page == "month" else key.upper().replace("-", "_")
                lines += region_lines(f"R_{upper}_{var_key}", page, key, region)

        # 时钟（仅 today）
        x0 = (self.width - metrics.total_w()) // 2
        lines += [
            f"CLOCK_X={x0}",
            f"CLOCK_Y={clock_rect.y + (clock_rect.h - metrics.digit_h) // 2}",
            f"CLOCK_DIGIT_W={metrics.digit_w}",
            f"CLOCK_DIGIT_H={metrics.digit_h}",
            f"CLOCK_COLON_W={metrics.colon_w}",
            f"CLOCK_GAP={metrics.gap}",
            f'CLOCK_GLYPH_URL_PREFIX="{base}/r/today/clock/"',
            # 轮播默认值（设备 config.sh 可覆盖）
            "ROTATE_TODAY_S=120",
            "ROTATE_OTHER_S=30",
            "ROTATE_SUPPRESS_S=120",
            # 翻月范围（±N 月）：±1 用预裁资产零流量，超出经 TMPL 按需拉取
            "MONTH_LIMIT=24",
            f'R_MONTH_TITLE_TMPL="{base}/r/month/title.png?offset={{o}}"',
            f'R_MONTH_GRID_TMPL="{base}/r/month/grid.png?offset={{o}}"',
            f'LEGACY_URL="{base}/dashboard.png"',
        ]

        # P1 旧名兼容别名（保留一个版本）
        legacy_block: list[str] = []
        for old, new in _LEGACY_ALIASES.items():
            page, key = "today", new.split("R_TODAY_")[1].lower()
            region = regions.get((page, key))
            if region is None:
                continue
            legacy_block += region_lines(old, page, key, region)
        lines += legacy_block

        return "\n".join(lines) + "\n"

    def health_info(self) -> dict:
        with self._weather_cond:
            return {
                "has_weather": self._weather is not None,
                "weather_age_seconds": None if self._weather_at == 0 else round(time.time() - self._weather_at, 1),
                "refreshing": self._refreshing,
                "last_error": self._last_error,
                "screen": f"{self.width}x{self.height}",
                "pages": list(PAGES),
            }

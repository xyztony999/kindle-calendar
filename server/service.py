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
from server.aqi import AirQuality, fetch_aqi
from server.settings import (
    HeartbeatLog,
    SettingsStore,
    copy_settings,
    enabled_pages,
    location_changed,
    settings_path,
    settings_version as content_version,
)
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
        self._aqi: AirQuality | None = None
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

        self.heartbeat = HeartbeatLog()
        deploy = {
            "location_name": config["location_name"],
            "latitude": config["latitude"],
            "longitude": config["longitude"],
            "timezone": config["timezone"],
        }
        self.store = SettingsStore(settings_path(), deploy, on_change=self._on_settings_changed)
        loaded = self.store.load()
        self._settings = loaded.settings
        self._degraded = loaded.degraded
        self._overlay_location(self._settings)
        log.info("台历配置 version=%s degraded=%s", content_version(self._settings), self._degraded)

    def _overlay_location(self, settings: dict) -> None:
        loc = settings["location"]
        self.config["location_name"] = loc["name"]
        self.config["latitude"] = float(loc["latitude"])
        self.config["longitude"] = float(loc["longitude"])
        self.config["timezone"] = loc["timezone"]

    def _on_settings_changed(self, old: dict, new: dict) -> bool:
        return self.apply_settings(new, location_changed(old, new))

    def apply_settings(self, new: dict, location_was_changed: bool) -> bool:
        """写入运行中的城市与缓存失效。城市变化时同步重拉天气，失败保留旧数据。"""
        self._overlay_location(new)
        with self._lock:
            self._settings = new
            self._degraded = False
            self._regions.clear()
            self._regions_fingerprint = ""
            self._month_offset_cache.clear()
            self._payload = None
        if not location_was_changed:
            return False
        return self._sync_weather(timeout=8.0)

    def _sync_weather(self, timeout: float = 8.0) -> bool:
        deadline = time.monotonic() + timeout
        with self._weather_cond:
            self._refreshing = True
        try:
            weather = fetch_weather(
                self.config["latitude"],
                self.config["longitude"],
                self.config["timezone"],
                timeout=max(1.0, timeout),
            )
        except Exception as exc:
            log.warning("城市变更后天气重拉失败，保留旧数据: %s", exc)
            with self._weather_cond:
                if self._weather is not None:
                    self._weather_at = time.time() - self.refresh_seconds - 1
                self._refreshing = False
                self._weather_cond.notify_all()
            return False
        remaining = max(0.5, deadline - time.monotonic())
        aqi = fetch_aqi(self.config["latitude"], self.config["longitude"], timeout=min(4.0, remaining))
        with self._weather_cond:
            self._weather = weather
            self._aqi = aqi
            self._weather_at = time.time()
            self._last_error = None
            self._refreshing = False
            self._weather_cond.notify_all()
        log.info("城市变更后天气已更新")
        return True

    def note_heartbeat(self, ip: str, ua: str) -> None:
        self.heartbeat.record(ip, ua, self.settings_version(), self.regions_version())

    def settings_version(self) -> str:
        with self._lock:
            return content_version(self._settings)

    def regions_version(self) -> str:
        with self._lock:
            return self._regions_fingerprint

    def device_status(self) -> dict:
        with self._lock:
            settings = self._settings
        return self.heartbeat.snapshot(content_version(settings), settings["location"]["timezone"])

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
        # AQI 独立 try（PRD FR-1：失败不阻塞天气）
        aqi = fetch_aqi(self.config["latitude"], self.config["longitude"])
        with self._weather_cond:
            self._weather = weather
            self._aqi = aqi
            self._weather_at = now
            self._last_error = None
        log.info("天气已更新 (aqi=%s)", aqi.us_aqi if aqi else "无")

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
            aqi = self._aqi
        if weather is None:
            raise RuntimeError(self._last_error or "天气数据不可用")

        with self._lock:
            settings = copy_settings(self._settings)
        payload = data_mod.build_payload(self.config, weather, now, aqi, settings)
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
        with self._lock:
            settings = copy_settings(self._settings)
        pages = enabled_pages(settings) or ["today"]
        dwell = {item["page_id"]: int(item["dwell_s"]) for item in settings["pages"]}
        other = 30
        for page_id in pages:
            if page_id != "today":
                other = dwell.get(page_id, 30)
                break
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
            f'PAGES="{" ".join(pages)}"',
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
            # 轮播与配置版本来自台历配置；旧变量名保留给 v2.1 dash.sh
            f"SETTINGS_VERSION={content_version(settings)}",
            f"ROTATE_ENABLED={1 if settings['rotation']['enabled'] else 0}",
            f"ROTATE_OTHER_S={other}",
            f"ROTATE_SUPPRESS_S={int(settings['rotation']['suppress_s'])}",
        ]
        for page_id in pages:
            lines.append(f"ROTATE_{page_id.upper()}_S={dwell.get(page_id, 30)}")
        lines += [
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
        with self._lock:
            version = content_version(self._settings)
            pages = enabled_pages(self._settings)
            location = self.config["location_name"]
        with self._weather_cond:
            return {
                "has_weather": self._weather is not None,
                "weather_age_seconds": None if self._weather_at == 0 else round(time.time() - self._weather_at, 1),
                "refreshing": self._refreshing,
                "last_error": self._last_error,
                "screen": f"{self.width}x{self.height}",
                "location": location,
                "settings_version": version,
                "pages": pages,
            }

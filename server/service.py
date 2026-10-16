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
from server.render import render_glyphs
from server.layout import clock_block, draw_region_keys, find_block, http_region_names, scale_box
from server.render.placed import paste_page, placed_rect, render_placed
from server.render.regions import Rect, metrics_in
from server.catalog import fetch_center_items
from server import storage
from server.locale import localize_payload, with_lang_query
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
        self._payloads: dict[str, dict] = {}
        self._fingerprints: dict[str, str] = {}
        self._regions: dict[tuple[str, str], RegionRender] = {}
        self._regions_fingerprint = ""
        self._regions_by_lang: dict[str, tuple[str, dict[tuple[str, str], RegionRender]]] = {}
        self._month_offset_cache: dict[tuple, RegionRender] = {}  # (region, offset, fingerprint)
        self._glyph_sets: dict[tuple, dict[str, bytes]] = {}
        self._asset_images: dict[str, Image.Image] = {}

        self.heartbeat = HeartbeatLog(settings_path().with_name("device-status.json"))
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
            self._regions_by_lang.clear()
            self._payloads.clear()
            self._fingerprints.clear()
            self._month_offset_cache.clear()
            self._payload = None
            self._glyph_sets.clear()
            self._asset_images = {}
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

    def note_heartbeat(self, ip: str, ua: str, interval: int = 900, mode: str = "v2",
                       *, fetched: bool = True, applied_version: str | None = None) -> None:
        self.heartbeat.record(ip, ua, interval, mode, fetched=fetched, applied_version=applied_version)

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

    def get_payload(self, lang: str = "zh") -> dict:
        lang = "en" if lang == "en" else "zh"
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
        if lang == "en":
            mode = "online"
            custom = None
            if settings:
                mode = settings["quote"]["mode"]
                custom = settings["quote"].get("custom")
            width = int((self.config.get("screen") or {}).get("width") or 758)
            payload = localize_payload(payload, mode, custom, now, width)
        fingerprint = data_mod.data_fingerprint(payload)
        with self._lock:
            self._payloads[lang] = payload
            self._fingerprints[lang] = fingerprint
            if lang == "zh":
                self._payload = payload
                self._payload_fingerprint = fingerprint
        return payload

    def _settings_now(self) -> dict:
        with self._lock:
            return copy_settings(self._settings)

    def page_record(self, page_id: str) -> dict | None:
        for page in self._settings_now().get("pages") or []:
            if page.get("page_id") == page_id:
                return page
        return None

    def has_page(self, page_id: str) -> bool:
        return self.page_record(page_id) is not None

    def _definitions(self, settings: dict) -> dict[str, dict]:
        found = {item["id"]: item for item in settings.get("widget_defs") or []}
        try:
            center = fetch_center_items()
        except Exception:
            log.warning("模板中心读取失败，自定义积木仅使用本机定义")
            center = []
        for item in center:
            if item.get("kind") == "data":
                found.setdefault(item["id"], item)
        return found

    def _asset_images_for(self, settings: dict) -> dict[str, Image.Image]:
        images: dict[str, Image.Image] = {}
        for asset in settings.get("assets") or []:
            asset_id = asset.get("id")
            key = asset.get("key")
            if not asset_id or not key:
                continue
            with self._lock:
                cached = self._asset_images.get(key)
            if cached is None:
                raw = storage.get_object(key)
                if not raw:
                    continue
                try:
                    cached = Image.open(io.BytesIO(raw))
                    cached.load()
                except Exception:
                    log.warning("素材无法解码 key=%s", key)
                    continue
                with self._lock:
                    self._asset_images[key] = cached
            images[asset_id] = cached
        return images

    def _get_regions(self, lang: str = "zh") -> dict[tuple[str, str], RegionRender]:
        lang = "en" if lang == "en" else "zh"
        payload = self.get_payload(lang)
        settings = self._settings_now()
        token = self._fingerprints[lang] + ":" + content_version(settings)
        with self._lock:
            cached = self._regions_by_lang.get(lang)
            if cached and cached[0] == token:
                return cached[1]

        definitions = self._definitions(settings)
        images = self._asset_images_for(settings)
        regions: dict[tuple[str, str], RegionRender] = {}
        for page in settings.get("pages") or []:
            page_id = page["page_id"]
            rendered = render_placed(page, payload, self.width, self.height, self.font_path, definitions, images)
            for key, img in rendered.items():
                png = _png_bytes(img)
                regions[(page_id, key)] = RegionRender(
                    rect=placed_rect(page, key, self.width, self.height),
                    png=png,
                    etag=hashlib.sha256(png).hexdigest()[:32],
                )

        with self._lock:
            self._regions_by_lang[lang] = (token, regions)
            if lang == "zh":
                self._regions = regions
                self._regions_fingerprint = token
        return regions

    def get_region(self, page: str, region: str, offset: int = 0, lang: str = "zh") -> RegionRender | None:
        lang = "en" if lang == "en" else "zh"
        record = self.page_record(page)
        if record is None or region not in http_region_names(record):
            return None
        if region in ("title", "grid") and offset != 0 and find_block(record, region) is not None:
            return self._get_month_offset_region(page, region, offset, lang)
        regions = self._get_regions(lang)
        return regions.get((page, region))

    def _get_month_offset_region(self, page: str, region: str, offset: int, lang: str = "zh") -> RegionRender:
        from server.render.placed import paint_system

        lang = "en" if lang == "en" else "zh"
        offset = max(-120, min(120, int(offset)))
        record = self.page_record(page)
        payload = self.get_payload(lang)
        rect = placed_rect(record, region, self.width, self.height)
        key = (page, region, offset, rect.x, rect.y, rect.w, rect.h, self._fingerprints[lang], lang)
        with self._lock:
            cached = self._month_offset_cache.get(key)
        if cached is not None:
            return cached

        img = paint_system(region, payload, rect, self.font_path, page, offset)
        png = _png_bytes(img)
        rendered = RegionRender(rect=rect, png=png, etag=hashlib.sha256(png).hexdigest()[:32])
        with self._lock:
            if len(self._month_offset_cache) > 64:
                self._month_offset_cache.clear()
            self._month_offset_cache[key] = rendered
        return rendered

    def get_glyphs(self, page: str = "today") -> dict[str, bytes]:
        record = self.page_record(page)
        block = clock_block(record) if record else None
        if block is None:
            return {}
        x, y, w, h = scale_box(int(block["x"]), int(block["y"]), int(block["w"]), int(block["h"]), self.width, self.height)
        metrics = metrics_in(Rect(x, y, w, h))
        key = (page, metrics.digit_w, metrics.digit_h, metrics.colon_w, metrics.gap, self.font_path)
        with self._lock:
            cached = self._glyph_sets.get(key)
            if cached:
                return cached
        glyphs = {ch: _png_bytes(img) for ch, img in render_glyphs(metrics, self.font_path).items()}
        with self._lock:
            self._glyph_sets[key] = glyphs
        return glyphs

    def render_page_image(self, page: dict, payload: dict, definitions: dict | None = None, images: dict | None = None) -> Image.Image:
        settings = self._settings_now()
        return paste_page(
            page,
            payload,
            self.width,
            self.height,
            self.font_path,
            definitions if definitions is not None else self._definitions(settings),
            images if images is not None else self._asset_images_for(settings),
            None,
            metrics_in,
        )

    def get_composite(self, page: str = "today", lang: str = "zh") -> bytes:
        lang = "en" if lang == "en" else "zh"
        record = self.page_record(page) or self.page_record("today")
        payload = self.get_payload(lang)
        return _png_bytes(self.render_page_image(record, payload))

    # ── 设备端 env ──

    def build_env(self, base_url: str, lang: str = "zh") -> str:
        lang = "en" if lang == "en" else "zh"
        base = base_url.rstrip("/")
        regions = self._get_regions(lang)
        payload = self._payloads.get(lang) or {}
        with self._lock:
            settings = copy_settings(self._settings)
        pages = enabled_pages(settings) or ["today"]
        dwell = {item["page_id"]: int(item["dwell_s"]) for item in settings["pages"]}
        other = 30
        for page_id in pages:
            if page_id != "today":
                other = dwell.get(page_id, 30)
                break

        def region_lines(var_prefix: str, page: str, key: str, region: RegionRender) -> list[str]:
            return [
                f"{var_prefix}_X={region.rect.x}",
                f"{var_prefix}_Y={region.rect.y}",
                f"{var_prefix}_W={region.rect.w}",
                f"{var_prefix}_H={region.rect.h}",
                f'{var_prefix}_URL="{with_lang_query(f"{base}/r/{page}/{key}.png", lang)}"',
                f'{var_prefix}_ETAG="{region.etag}"',
            ]

        lines = [
            f"DASH_DATE={payload.get('date', {}).get('iso', '').replace('-', '')}",
            f"REGIONS_VERSION={self._fingerprints.get(lang, self._regions_fingerprint)}",
        ]
        if lang == "en":
            lines.append("lang=en")
        lines += [
            f"SCREEN_W={self.width}",
            f"SCREEN_H={self.height}",
            f'PAGES="{" ".join(pages)}"',
        ]

        # 每页分区清单 + 各分区变量（title/grid 统一三预裁键 PREV/CUR/NEXT）
        _MONTH_KEYS = {
            "title": "TITLE_CUR",
            "grid": "GRID_CUR",
            "title-prev": "TITLE_PREV",
            "grid-prev": "GRID_PREV",
            "title-next": "TITLE_NEXT",
            "grid-next": "GRID_NEXT",
        }
        page_records = {item["page_id"]: item for item in settings.get("pages") or []}
        clock_legacy: list[str] = []
        month_templates: list[str] = []
        for page_id in pages:
            record = page_records.get(page_id)
            if record is None:
                continue
            upper = page_id.upper()
            keys = draw_region_keys(record)
            lines.append(f'R_{upper}_REGIONS="{" ".join(key.upper() for key in keys)}"')
            for key in http_region_names(record):
                region = regions.get((page_id, key))
                if region is None:
                    continue
                var_key = _MONTH_KEYS.get(key, key.upper().replace("-", "_"))
                lines += region_lines(f"R_{upper}_{var_key}", page_id, key, region)
            if "title" in keys:
                month_templates.append(
                    f'R_{upper}_TITLE_TMPL="{with_lang_query(f"{base}/r/{page_id}/title.png?offset={{o}}", lang)}"'
                )
            if "grid" in keys:
                month_templates.append(
                    f'R_{upper}_GRID_TMPL="{with_lang_query(f"{base}/r/{page_id}/grid.png?offset={{o}}", lang)}"'
                )
            block = clock_block(record)
            if block is None:
                lines.append(f"CLOCK_{upper}_ENABLED=0")
                if page_id == "today":
                    clock_legacy.append("CLOCK_ENABLED=0")
                continue
            x, y, w, h = scale_box(int(block["x"]), int(block["y"]), int(block["w"]), int(block["h"]), self.width, self.height)
            clock_metrics = metrics_in(Rect(x, y, w, h))
            prefix = f"{base}/r/{page_id}/clock/"
            clock_lines = [
                f"CLOCK_{upper}_ENABLED=1",
                f"CLOCK_{upper}_X={clock_metrics.x}",
                f"CLOCK_{upper}_Y={clock_metrics.y}",
                f"CLOCK_{upper}_DIGIT_W={clock_metrics.digit_w}",
                f"CLOCK_{upper}_DIGIT_H={clock_metrics.digit_h}",
                f"CLOCK_{upper}_COLON_W={clock_metrics.colon_w}",
                f"CLOCK_{upper}_GAP={clock_metrics.gap}",
                f'CLOCK_{upper}_GLYPH_URL_PREFIX="{prefix}"',
            ]
            lines += clock_lines
            if page_id == "today":
                clock_legacy = [
                    "CLOCK_ENABLED=1",
                    f"CLOCK_X={clock_metrics.x}",
                    f"CLOCK_Y={clock_metrics.y}",
                    f"CLOCK_DIGIT_W={clock_metrics.digit_w}",
                    f"CLOCK_DIGIT_H={clock_metrics.digit_h}",
                    f"CLOCK_COLON_W={clock_metrics.colon_w}",
                    f"CLOCK_GAP={clock_metrics.gap}",
                    f'CLOCK_GLYPH_URL_PREFIX="{prefix}"',
                ]

        lines += clock_legacy
        lines += [
            f"SETTINGS_VERSION={content_version(settings)}",
            f"ROTATE_ENABLED={1 if settings['rotation']['enabled'] else 0}",
            f"ROTATE_OTHER_S={other}",
            f"ROTATE_SUPPRESS_S={int(settings['rotation']['suppress_s'])}",
        ]
        for page_id in pages:
            lines.append(f"ROTATE_{page_id.upper()}_S={dwell.get(page_id, 30)}")
        lines.append("MONTH_LIMIT=24")
        lines += month_templates
        if "R_MONTH_TITLE_TMPL=" not in "\n".join(month_templates):
            lines.append(f'R_MONTH_TITLE_TMPL="{with_lang_query(f"{base}/r/month/title.png?offset={{o}}", lang)}"')
        if "R_MONTH_GRID_TMPL=" not in "\n".join(month_templates):
            lines.append(f'R_MONTH_GRID_TMPL="{with_lang_query(f"{base}/r/month/grid.png?offset={{o}}", lang)}"')
        lines.append(f'LEGACY_URL="{with_lang_query(f"{base}/dashboard.png", lang)}"')

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

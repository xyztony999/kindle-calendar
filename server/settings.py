"""台历配置：单例 JSON 存储、校验、内容版本、部署默认值与设备心跳。"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

from server.layout import (
    CUSTOM_PAGE_RE,
    MAX_PAGES,
    PRESET_IDS,
    SYSTEM_OPTIONS,
    default_page,
    drop_unreferenced_assets,
    validate_layout_fields,
)

PAGE_IDS = PRESET_IDS
SYSTEM_OPTION_WIDGETS = frozenset(SYSTEM_OPTIONS)
QUOTE_MODES = ("online", "library", "offline", "custom")  # offline 仅兼容旧数据，normalize 迁移为 library
QUOTE_CATEGORIES = tuple("abcdefghijkl")
SCHEMA_VERSION = 3
ACCEPTED_SCHEMAS = (1, 2, 3)

DWELL_MIN = 5
DWELL_MAX = 3600
SUPPRESS_MAX = 3600
CUSTOM_MAX = 100
TEXT_MAX = 32
FROM_MAX = 16
NAME_MAX = 20
BLOCK_TEXT_MAX = 200
SETTINGS_MAX_BYTES = 64 * 1024

DEFAULT_INTERVAL_S = 900
HEARTBEAT_ONLINE_FACTOR = 2

OnChange = Callable[[dict, dict], bool]


class SettingsError(Exception):
    def __init__(self, code: str, message: str, details: list[dict]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


@dataclass
class LoadResult:
    settings: dict
    degraded: bool


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        log.warning("环境变量 %s=%r 不是整数，使用默认 %s", name, raw, default)
        return default


def settings_path() -> Path:
    root = Path(__file__).resolve().parent.parent
    raw = os.environ.get("SETTINGS_PATH", "").strip()
    if not raw:
        return root / "data" / "settings.json"
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    return path


def limits() -> dict[str, int]:
    return {
        "dwell_min": DWELL_MIN,
        "dwell_max": DWELL_MAX,
        "suppress_max": SUPPRESS_MAX,
        "custom_max": CUSTOM_MAX,
        "text_max": TEXT_MAX,
        "from_max": FROM_MAX,
        "name_max": NAME_MAX,
        "block_text_max": BLOCK_TEXT_MAX,
        "max_pages": MAX_PAGES,
        "max_blocks": 24,
        "max_defs": 12,
    }


def copy_settings(settings: dict) -> dict:
    return json.loads(json.dumps(settings, ensure_ascii=False))


def defaults_from_config(config: dict) -> dict:
    pages = [default_page(page_id, True, 120 if page_id == "today" else 30) for page_id in PAGE_IDS]
    return {
        "schema_version": SCHEMA_VERSION,
        "pages": pages,
        "widget_defs": [],
        "assets": [],
        "rotation": {"enabled": True, "suppress_s": 120},
        "quote": {"mode": "library", "custom": [], "library_types": ["i", "d"]},
        "presets": [],
        "ics": {"urls": []},
        "anniversaries": [],
        "location": {
            "name": str(config.get("location_name") or "北京"),
            "latitude": float(config.get("latitude", 39.9042)),
            "longitude": float(config.get("longitude", 116.4074)),
            "timezone": str(config.get("timezone") or "Asia/Shanghai"),
        },
    }


def settings_version(settings: dict) -> str:
    """内容哈希前 12 位；不含 updated_at，相同内容必同版本。"""
    body = {k: v for k, v in settings.items() if k != "updated_at"}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def enabled_pages(settings: dict) -> list[str]:
    return [item["page_id"] for item in settings.get("pages") or [] if item.get("enabled")]


def location_changed(old: dict, new: dict) -> bool:
    left = old.get("location") or {}
    right = new.get("location") or {}
    if left.get("name") != right.get("name") or left.get("timezone") != right.get("timezone"):
        return True
    try:
        if abs(float(left.get("latitude")) - float(right.get("latitude"))) > 1e-6:
            return True
        if abs(float(left.get("longitude")) - float(right.get("longitude"))) > 1e-6:
            return True
    except (TypeError, ValueError):
        return True
    return False


def _detail(field: str, code: str, message: str) -> dict:
    return {"field": field, "code": code, "message": message}


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or isinstance(value, str):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def validate(data: Any) -> list[dict]:
    """收集全部字段错误，不短路。"""
    details: list[dict] = []
    if not isinstance(data, dict):
        return [_detail("", "PAGES_SET_INVALID", "配置必须是对象")]

    schema = data.get("schema_version", 1)
    if schema not in ACCEPTED_SCHEMAS:
        details.append(_detail("schema_version", "PAGES_SET_INVALID", "配置 schema 不受支持"))

    pages = data.get("pages")
    if not isinstance(pages, list) or not 5 <= len(pages) <= MAX_PAGES:
        details.append(_detail("pages", "PAGES_SET_INVALID", "页面数量须为 5–12，且包含全部预设页"))
        pages = []
    else:
        ids: list[Any] = []
        for index, item in enumerate(pages):
            if not isinstance(item, dict):
                ids.append(None)
                details.append(_detail("pages", "PAGES_SET_INVALID", "页面项格式不正确"))
                continue
            page_id = item.get("page_id")
            ids.append(page_id)
            if not isinstance(item.get("enabled"), bool):
                details.append(_detail(f"pages[{index}].enabled", "PAGES_SET_INVALID", "启用标记须为布尔值"))
            dwell = _as_int(item.get("dwell_s"))
            if dwell is None or not DWELL_MIN <= dwell <= DWELL_MAX:
                details.append(
                    _detail(
                        f"pages[{index}].dwell_s",
                        "DWELL_OUT_OF_RANGE",
                        f"停留秒数须为 {DWELL_MIN}–{DWELL_MAX} 的整数",
                    )
                )
            if isinstance(page_id, str) and CUSTOM_PAGE_RE.match(page_id):
                name = _clean_text(item.get("name"))
                if not name or len(name) > NAME_MAX or "\n" in name or "\r" in name:
                    details.append(_detail(f"pages[{index}].name", "PAGES_SET_INVALID", f"页面名称须为 1–{NAME_MAX} 字"))
            elif page_id not in PAGE_IDS:
                details.append(_detail(f"pages[{index}].page_id", "PAGES_SET_INVALID", "页面 id 无效"))
        first = pages[0] if isinstance(pages[0], dict) else {}
        if not ids or ids[0] != "today" or first.get("enabled") is not True:
            details.append(_detail("pages[0]", "TODAY_MUST_BE_FIRST_ENABLED", "今日页必须固定在首位且保持启用"))
        if len(ids) != len(set(ids)) or not set(PAGE_IDS).issubset(set(ids)):
            details.append(_detail("pages", "PAGES_SET_INVALID", "页面须互不重复且覆盖今日、一周、月历、详情、黄历"))

    widget_defs = data.get("widget_defs", [])
    assets = data.get("assets", [])
    try:
        from server.catalog import approved_data_items

        center_items = approved_data_items()
    except Exception:
        log.warning("读取模板中心失败，校验时按空目录处理")
        center_items = []
    validate_layout_fields(pages if isinstance(pages, list) else [], widget_defs, assets, center_items, details)

    rotation = data.get("rotation")
    if not isinstance(rotation, dict) or not isinstance(rotation.get("enabled"), bool):
        details.append(_detail("rotation.enabled", "ROTATION_INVALID", "轮播开关须为布尔值"))
    suppress = _as_int(rotation.get("suppress_s")) if isinstance(rotation, dict) else None
    if suppress is None or not 0 <= suppress <= SUPPRESS_MAX:
        details.append(
            _detail("rotation.suppress_s", "SUPPRESS_OUT_OF_RANGE", f"让位秒数须为 0–{SUPPRESS_MAX} 的整数")
        )
    fetch_interval = rotation.get("fetch_interval_s") if isinstance(rotation, dict) else None
    if fetch_interval is not None:
        value = _as_int(fetch_interval)
        if value is None or not 300 <= value <= 86400:
            details.append(
                _detail("rotation.fetch_interval_s", "FETCH_INTERVAL_INVALID", "拉取间隔须为 300–86400 秒的整数，留空使用设备配置")
            )

    quote = data.get("quote")
    mode = quote.get("mode") if isinstance(quote, dict) else None
    if mode not in QUOTE_MODES:
        details.append(_detail("quote.mode", "QUOTE_MODE_INVALID", "一言来源无效"))
    library_types = quote.get("library_types") if isinstance(quote, dict) else None
    if library_types is not None and (not isinstance(library_types, list) or not library_types or any(t not in QUOTE_CATEGORIES for t in library_types)):
        details.append(_detail("quote.library_types", "QUOTE_LIBRARY_INVALID", "语料分类无效（至少一个，限 a–l）"))
    custom = quote.get("custom") if isinstance(quote, dict) else None
    if not isinstance(custom, list):
        details.append(_detail("quote.custom", "QUOTE_CUSTOM_INVALID", "自定义文案须为列表"))
    else:
        if len(custom) > CUSTOM_MAX:
            details.append(_detail("quote.custom", "QUOTE_CUSTOM_INVALID", f"自定义文案最多 {CUSTOM_MAX} 条"))
        if mode == "custom" and len(custom) < 1:
            details.append(_detail("quote.custom", "QUOTE_CUSTOM_INVALID", "自定义模式至少需要一条文案"))
        for index, item in enumerate(custom):
            if not isinstance(item, dict):
                details.append(_detail(f"quote.custom[{index}]", "QUOTE_CUSTOM_INVALID", "文案项格式不正确"))
                continue
            text = _clean_text(item.get("text"))
            if not text or len(text) > TEXT_MAX or "\n" in text or "\r" in text:
                details.append(
                    _detail(f"quote.custom[{index}].text", "QUOTE_CUSTOM_INVALID", f"文案须为 1–{TEXT_MAX} 字且不含换行")
                )
            source = _clean_text(item.get("from"))
            if len(source) > FROM_MAX or "\n" in source or "\r" in source:
                details.append(
                    _detail(f"quote.custom[{index}].from", "QUOTE_CUSTOM_INVALID", f"出处最多 {FROM_MAX} 字且不含换行")
                )

    location = data.get("location")
    if not isinstance(location, dict):
        details.append(_detail("location.name", "LOCATION_NAME_INVALID", "城市信息不完整"))
        details.append(_detail("location.latitude", "LOCATION_COORD_INVALID", "纬度超出范围"))
        details.append(_detail("location.longitude", "LOCATION_COORD_INVALID", "经度超出范围"))
        details.append(_detail("location.timezone", "LOCATION_TZ_INVALID", "时区无法识别"))
        return details

    name = _clean_text(location.get("name"))
    if not name or len(name) > NAME_MAX or "\n" in name or "\r" in name:
        details.append(_detail("location.name", "LOCATION_NAME_INVALID", f"城市名须为 1–{NAME_MAX} 字"))
    latitude = _as_float(location.get("latitude"))
    if latitude is None or not -90 <= latitude <= 90:
        details.append(_detail("location.latitude", "LOCATION_COORD_INVALID", "纬度须在 -90 到 90 之间"))
    longitude = _as_float(location.get("longitude"))
    if longitude is None or not -180 <= longitude <= 180:
        details.append(_detail("location.longitude", "LOCATION_COORD_INVALID", "经度须在 -180 到 180 之间"))
    tz_name = _clean_text(location.get("timezone"))
    if not tz_name:
        details.append(_detail("location.timezone", "LOCATION_TZ_INVALID", "时区无法识别"))
    else:
        try:
            ZoneInfo(tz_name)
        except Exception:
            details.append(_detail("location.timezone", "LOCATION_TZ_INVALID", "时区无法识别"))

    # 以下新键对旧配置缺失容错（缺失=默认，不降级）
    presets = data.get("presets") or []
    if not isinstance(presets, list):
        details.append(_detail("presets", "PRESET_INVALID", "版面方案须为列表"))
    else:
        if len(presets) > 8:
            details.append(_detail("presets", "PRESET_INVALID", "版面方案最多 8 套"))
        for index, item in enumerate(presets):
            if not isinstance(item, dict):
                details.append(_detail(f"presets[{index}]", "PRESET_INVALID", "方案项格式不正确"))
                continue
            name = _clean_text(item.get("name"))
            if not name or len(name) > 20 or "\n" in name or "\r" in name:
                details.append(_detail(f"presets[{index}].name", "PRESET_INVALID", "方案名须为 1–20 字"))
            snapshot = item.get("snapshot")
            if not isinstance(snapshot, dict) or not isinstance(snapshot.get("pages"), list):
                details.append(_detail(f"presets[{index}].snapshot", "PRESET_INVALID", "方案快照结构不完整"))

    ics_raw = data.get("ics") or {}
    urls = ics_raw.get("urls", []) if isinstance(ics_raw, dict) else []
    if not isinstance(urls, list) or len(urls) > 3:
        details.append(_detail("ics.urls", "ICS_INVALID", "订阅链接最多 3 个且须为列表"))
    else:
        for index, entry in enumerate(urls):
            url = entry.get("url") if isinstance(entry, dict) else entry
            if not isinstance(url, str) or not url.startswith("https://") or len(url) > 500:
                details.append(_detail(f"ics.urls[{index}].url", "ICS_INVALID", "订阅链接须为 https 且不超过 500 字符"))
            elif isinstance(entry, dict) and not isinstance(entry.get("enabled", True), bool):
                details.append(_detail(f"ics.urls[{index}].enabled", "ICS_INVALID", "启停开关须为布尔值"))

    anniversaries = data.get("anniversaries") or []
    if not isinstance(anniversaries, list) or len(anniversaries) > 20:
        details.append(_detail("anniversaries", "ANNIV_INVALID", "纪念日最多 20 条"))
    else:
        for index, item in enumerate(anniversaries):
            if not isinstance(item, dict):
                details.append(_detail(f"anniversaries[{index}]", "ANNIV_INVALID", "纪念日项格式不正确"))
                continue
            name = _clean_text(item.get("name"))
            if not name or len(name) > 20 or "\n" in name or "\r" in name:
                details.append(_detail(f"anniversaries[{index}].name", "ANNIV_INVALID", "纪念日名称须为 1–20 字"))
            repeat = item.get("repeat")
            date_text = _clean_text(item.get("date"))
            if repeat not in ("none", "yearly", "lunar"):
                details.append(_detail(f"anniversaries[{index}].repeat", "ANNIV_INVALID", "重复方式无效"))
                continue
            if repeat == "none":
                from datetime import date as _date

                try:
                    _date.fromisoformat(date_text)
                except ValueError:
                    details.append(_detail(f"anniversaries[{index}].date", "ANNIV_INVALID", "日期须为 YYYY-MM-DD"))
            elif len(date_text) != 5 or date_text[2] != "-" or not date_text[:2].isdigit() or not date_text[3:].isdigit() or not 1 <= int(date_text[:2]) <= 12 or not 1 <= int(date_text[3:]) <= 31:
                details.append(_detail(f"anniversaries[{index}].date", "ANNIV_INVALID", "每年重复的日期须为 MM-DD"))
    return details


def _normalize_block(block: dict) -> dict:
    widget = block["widget"]
    item = {
        "widget": widget,
        "id": widget if widget in ("header", "clock", "weather", "sun", "scene", "quote", "list", "chart", "title", "grid", "hourly", "indices", "main", "schedule", "countdown", "wallpaper") else block["id"],
        "x": _as_int(block["x"]),
        "y": _as_int(block["y"]),
        "w": _as_int(block["w"]),
        "h": _as_int(block["h"]),
        "z": _as_int(block["z"]),
    }
    if widget in SYSTEM_OPTION_WIDGETS and isinstance(block.get("options"), dict) and block["options"]:
        item["options"] = block["options"]
    if widget == "image":
        item["asset"] = block["asset"]
    elif widget == "wallpaper" and isinstance(block.get("asset"), str) and block["asset"]:
        item["asset"] = block["asset"]
    elif widget == "text":
        item["text"] = _clean_text(block.get("text"))
        item["align"] = block.get("align") if block.get("align") in ("left", "center", "right") else "left"
        item["size"] = block.get("size") if block.get("size") in ("lg", "md", "sm") else "md"
    elif widget == "custom":
        item["def"] = block["def"]
        if "style" in block:
            item["style"] = block["style"]
    return item


def normalize(data: dict) -> dict:
    """校验通过后的规范化：去空白、整数化、今日页强制启用，并补上默认布局。"""
    pages = []
    for item in data["pages"]:
        page_id = item["page_id"]
        page = {
            "page_id": page_id,
            "enabled": True if page_id == "today" else item["enabled"] is True,
            "dwell_s": _as_int(item["dwell_s"]),
        }
        if CUSTOM_PAGE_RE.match(page_id):
            page["name"] = _clean_text(item.get("name"))
        if "layout" in item and isinstance(item.get("layout"), list):
            page["layout"] = [_normalize_block(block) for block in item["layout"]]
        else:
            page["layout"] = default_page(page_id, True, 30)["layout"] if page_id in PAGE_IDS else []
        pages.append(page)
    custom = []
    for item in data["quote"]["custom"]:
        custom.append({"text": _clean_text(item.get("text")), "from": _clean_text(item.get("from"))})
    quote_mode = data["quote"].get("mode", "online")
    if quote_mode == "offline":
        quote_mode = "library"
    if quote_mode not in QUOTE_MODES:
        quote_mode = "library"
    library_types = [t for t in (data["quote"].get("library_types") or ["i", "d"]) if t in QUOTE_CATEGORIES]
    if not library_types:
        library_types = ["i", "d"]
    location = data["location"]
    defs = []
    for item in data.get("widget_defs") or []:
        defs.append(
            {
                "id": item["id"],
                "name": _clean_text(item.get("name")),
                "style": item["style"],
                "fields": list(item["fields"]),
            }
        )
    assets = []
    for item in data.get("assets") or []:
        assets.append({"id": item["id"], "key": item["key"], "content_type": item["content_type"]})
    presets_out = []
    for item in data.get("presets") or []:
        if isinstance(item, dict) and isinstance(item.get("snapshot"), dict):
            presets_out.append({
                "id": item.get("id"),
                "name": _clean_text(item.get("name")),
                "created_at": _clean_text(item.get("created_at")),
                "snapshot": copy_settings(item["snapshot"]),
            })
    ics_data = data.get("ics") if isinstance(data.get("ics"), dict) else {}
    ics_urls = []
    for entry in (ics_data.get("urls") or []):
        if isinstance(entry, str):
            ics_urls.append({"url": entry, "enabled": True})
        elif isinstance(entry, dict) and isinstance(entry.get("url"), str) and entry["url"].startswith("https://"):
            ics_urls.append({"url": entry["url"], "enabled": entry.get("enabled", True) is not False})
    ics_urls = ics_urls[:3]
    anniversaries_out = []
    for item in data.get("anniversaries") or []:
        if isinstance(item, dict):
            anniversaries_out.append({
                "id": item.get("id"),
                "name": _clean_text(item.get("name")),
                "date": _clean_text(item.get("date")),
                "repeat": item.get("repeat") if item.get("repeat") in ("none", "yearly", "lunar") else "none",
            })
    return {
        "schema_version": SCHEMA_VERSION,
        "pages": pages,
        "widget_defs": defs,
        "assets": assets,
        "rotation": {
            "enabled": data["rotation"]["enabled"] is True,
            "suppress_s": _as_int(data["rotation"]["suppress_s"]),
            "fetch_interval_s": _as_int(data["rotation"].get("fetch_interval_s")),
        },
        "quote": {"mode": quote_mode, "custom": custom, "library_types": library_types},
        "presets": presets_out,
        "ics": {"urls": ics_urls},
        "anniversaries": anniversaries_out,
        "location": {
            "name": _clean_text(location.get("name")),
            "latitude": round(float(location["latitude"]), 6),
            "longitude": round(float(location["longitude"]), 6),
            "timezone": _clean_text(location.get("timezone")),
        },
    }


class SettingsStore:
    def __init__(self, path: Path, config: dict, on_change: OnChange | None = None) -> None:
        self.path = path
        self._deploy = {
            "location_name": config.get("location_name", "北京"),
            "latitude": config.get("latitude", 39.9042),
            "longitude": config.get("longitude", 116.4074),
            "timezone": config.get("timezone", "Asia/Shanghai"),
        }
        self._on_change = on_change
        self._lock = threading.Lock()
        self._settings: dict | None = None
        self._degraded = True

    def defaults(self) -> dict:
        return defaults_from_config(self._deploy)

    def load(self) -> LoadResult:
        with self._lock:
            return self._load_unlocked()

    def _load_unlocked(self) -> LoadResult:
        fallback = self.defaults()
        if not self.path.exists():
            log.info("配置文件不存在，使用部署默认值: %s", self.path)
            return self._use(fallback, degraded=True)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("配置文件损坏，使用部署默认值: %s", exc)
            return self._use(fallback, degraded=True)
        if not isinstance(raw, dict) or raw.get("schema_version") not in ACCEPTED_SCHEMAS:
            log.warning("配置 schema 不支持，使用部署默认值")
            return self._use(fallback, degraded=True)
        details = validate(raw)
        if details:
            log.warning("已保存配置校验失败，使用部署默认值")
            return self._use(fallback, degraded=True)
        normalized = normalize(raw)
        updated = raw.get("updated_at")
        if isinstance(updated, str) and updated:
            normalized["updated_at"] = updated
        if raw.get("schema_version") != SCHEMA_VERSION:
            try:
                raw_bytes = (json.dumps(normalized, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                self._atomic_write(raw_bytes)
                log.info("配置已从 schema %s 迁移到 %s", raw.get("schema_version"), SCHEMA_VERSION)
            except Exception as exc:
                log.warning("配置迁移后写回失败，本次仍使用内存中的新结构: %s", exc)
        return self._use(normalized, degraded=False)

    def _use(self, settings: dict, degraded: bool) -> LoadResult:
        self._settings = settings
        self._degraded = degraded
        return LoadResult(copy_settings(settings), degraded)

    def current(self) -> tuple[dict, bool, str]:
        with self._lock:
            if self._settings is None:
                self._load_unlocked()
            assert self._settings is not None
            return copy_settings(self._settings), self._degraded, settings_version(self._settings)

    def save(self, incoming: dict, *, gc_assets: bool = True) -> tuple[dict, str, bool, bool]:
        """校验并原子写入。返回 (settings, version, location_changed, weather_refreshed)。"""
        details = validate(incoming)
        if details:
            raise SettingsError("SETTINGS_VALIDATION_FAILED", "配置校验失败", details)
        normalized = normalize(incoming)
        if gc_assets:
            normalized = drop_unreferenced_assets(normalized)
        tz_name = normalized["location"]["timezone"]
        normalized["updated_at"] = datetime.now(ZoneInfo(tz_name)).isoformat(timespec="seconds")
        raw = (json.dumps(normalized, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(raw) > SETTINGS_MAX_BYTES:
            raise SettingsError(
                "SETTINGS_VALIDATION_FAILED",
                "配置超过 64KB",
                [_detail("", "SETTINGS_TOO_LARGE", "配置体积超过 64KB")],
            )

        with self._lock:
            if self._settings is None:
                self._load_unlocked()
            assert self._settings is not None
            old = copy_settings(self._settings)
            try:
                self._atomic_write(raw)
            except Exception as exc:
                log.exception("配置写入失败: %s", exc)
                raise SettingsError("SETTINGS_IO_FAILED", "配置写入失败，未改动", []) from exc
            self._settings = normalized
            self._degraded = False
            new = copy_settings(normalized)

        changed = location_changed(old, new)
        weather_refreshed = False
        if self._on_change is not None:
            try:
                weather_refreshed = bool(self._on_change(old, new))
            except Exception:
                log.exception("配置已写入，但通知下游失败")
                weather_refreshed = False
        return new, settings_version(new), changed, weather_refreshed

    def _atomic_write(self, raw: bytes) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            tmp.write_bytes(raw)
            os.replace(tmp, self.path)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise


class HeartbeatLog:
    """Latest device communication and application, persisted for one worker."""

    def __init__(self, path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._state: dict = {}
        self.path = path
        if path is not None:
            try:
                if path.stat().st_size > 4096:
                    raise ValueError("device status file too large")
                state = json.loads(path.read_text(encoding="utf-8"))
                self._validate_state(state)
                self._state = state
                log.info("Device status restored: %s", path)
            except FileNotFoundError:
                pass
            except (OSError, ValueError, TypeError, OverflowError) as exc:
                log.warning("Ignoring invalid device status file %s: %s", path, exc)

    @staticmethod
    def _validate_state(state: dict) -> None:
        required = {"ts", "ip", "ua", "interval", "mode"}
        optional = {"fetch_ts", "applied_ts", "applied_version"}
        if not isinstance(state, dict) or not required <= state.keys() or state.keys() - required - optional:
            raise ValueError("invalid device status structure")
        if type(state["interval"]) is not int or not 60 <= state["interval"] <= 86400:
            raise ValueError("invalid device interval")
        if state["mode"] not in ("v1", "v2"):
            raise ValueError("invalid device mode")
        for key in ("ts", "fetch_ts", "applied_ts"):
            if key in state and (type(state[key]) not in (int, float) or not math.isfinite(state[key])
                                 or not 0 <= state[key] <= 253402214399):
                raise ValueError("invalid device timestamp")
        for key, limit in (("ip", 128), ("ua", 80)):
            if state[key] is not None and (not isinstance(state[key], str) or len(state[key]) > limit):
                raise ValueError("invalid device source")
        if ("applied_version" in state) != ("applied_ts" in state):
            raise ValueError("incomplete device confirmation")
        if "applied_version" in state and (not isinstance(state["applied_version"], str)
                or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", state["applied_version"])):
            raise ValueError("invalid applied version")

    def _save(self) -> None:
        if self.path is None:
            return
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self._state, ensure_ascii=True), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log.warning("Could not persist device status %s: %s", self.path, exc)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def record(self, ip: str | None, ua: str | None, interval: int = DEFAULT_INTERVAL_S,
               mode: str = "v2", *, fetched: bool = False, applied_version: str | None = None) -> None:
        now = time.time()
        with self._lock:
            self._state.update(ts=now, ip=(ip or "").strip()[:128] or None,
                               ua=(ua or "").strip()[:80] or None, interval=interval, mode=mode)
            if fetched:
                self._state["fetch_ts"] = now
            if applied_version:
                self._state.update(applied_ts=now, applied_version=applied_version)
            self._save()

    def snapshot(self, current_version: str, tz_name: str) -> dict:
        with self._lock:
            state = dict(self._state)
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone.utc
        def stamp(key):
            value = state.get(key)
            return datetime.fromtimestamp(value, tz).isoformat(timespec="seconds") if value is not None else None
        interval = state.get("interval", DEFAULT_INTERVAL_S)
        seen = state.get("ts")
        applied = state.get("applied_version")
        online = "unknown" if seen is None else (
            "online" if time.time() - seen < HEARTBEAT_ONLINE_FACTOR * interval + 60 else "offline")
        delivery = "unknown" if seen is None or state.get("mode") == "v1" else (
            "delivered" if applied == current_version else "pending")
        fetch_ts = state.get("fetch_ts")
        eta = math.ceil(max(0.0, fetch_ts + interval - time.time()) / 60) if fetch_ts is not None else 0
        return {
            "online_state": online, "delivery_state": delivery,
            "last_seen_at": stamp("ts"), "last_fetch_at": stamp("fetch_ts"),
            "last_applied_at": stamp("applied_ts"), "mode": state.get("mode"),
            "last_ip": state.get("ip"), "last_user_agent": state.get("ua"),
            "delivered_settings_version": applied, "current_settings_version": current_version,
            "interval_estimate_s": interval, "eta_minutes": int(eta),
        }

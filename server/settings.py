"""台历配置：单例 JSON 存储、校验、内容版本、部署默认值与设备心跳。"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

PAGE_IDS = ("today", "week", "month", "detail", "almanac")
QUOTE_MODES = ("online", "offline", "custom")
SCHEMA_VERSION = 1

DWELL_MIN = 5
DWELL_MAX = 3600
SUPPRESS_MAX = 3600
CUSTOM_MAX = 100
TEXT_MAX = 32
FROM_MAX = 16
NAME_MAX = 20
SETTINGS_MAX_BYTES = 32 * 1024

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
    }


def copy_settings(settings: dict) -> dict:
    return json.loads(json.dumps(settings, ensure_ascii=False))


def defaults_from_config(config: dict) -> dict:
    pages = [
        {
            "page_id": page_id,
            "enabled": True,
            "dwell_s": 120 if page_id == "today" else 30,
        }
        for page_id in PAGE_IDS
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "pages": pages,
        "rotation": {"enabled": True, "suppress_s": 120},
        "quote": {"mode": "online", "custom": []},
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

    pages = data.get("pages")
    if not isinstance(pages, list) or len(pages) != 5:
        details.append(_detail("pages", "PAGES_SET_INVALID", "页面须恰好 5 项且覆盖全部页面"))
    else:
        ids: list[Any] = []
        for index, item in enumerate(pages):
            if not isinstance(item, dict):
                ids.append(None)
                details.append(_detail("pages", "PAGES_SET_INVALID", "页面项格式不正确"))
                continue
            ids.append(item.get("page_id"))
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
        first = pages[0] if isinstance(pages[0], dict) else {}
        if ids[0] != "today" or first.get("enabled") is not True:
            details.append(_detail("pages[0]", "TODAY_MUST_BE_FIRST_ENABLED", "今日页必须固定在首位且保持启用"))
        if set(ids) != set(PAGE_IDS):
            details.append(_detail("pages", "PAGES_SET_INVALID", "页面须互不重复且覆盖今日、一周、月历、详情、黄历"))

    rotation = data.get("rotation")
    if not isinstance(rotation, dict) or not isinstance(rotation.get("enabled"), bool):
        details.append(_detail("rotation.enabled", "ROTATION_INVALID", "轮播开关须为布尔值"))
    suppress = _as_int(rotation.get("suppress_s")) if isinstance(rotation, dict) else None
    if suppress is None or not 0 <= suppress <= SUPPRESS_MAX:
        details.append(
            _detail("rotation.suppress_s", "SUPPRESS_OUT_OF_RANGE", f"让位秒数须为 0–{SUPPRESS_MAX} 的整数")
        )

    quote = data.get("quote")
    mode = quote.get("mode") if isinstance(quote, dict) else None
    if mode not in QUOTE_MODES:
        details.append(_detail("quote.mode", "QUOTE_MODE_INVALID", "一言来源无效"))
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
    return details


def normalize(data: dict) -> dict:
    """校验通过后的规范化：去空白、整数化、今日页强制启用。"""
    pages = []
    for item in data["pages"]:
        page_id = item["page_id"]
        pages.append(
            {
                "page_id": page_id,
                "enabled": True if page_id == "today" else item["enabled"] is True,
                "dwell_s": _as_int(item["dwell_s"]),
            }
        )
    custom = []
    for item in data["quote"]["custom"]:
        custom.append({"text": _clean_text(item.get("text")), "from": _clean_text(item.get("from"))})
    location = data["location"]
    return {
        "schema_version": SCHEMA_VERSION,
        "pages": pages,
        "rotation": {
            "enabled": data["rotation"]["enabled"] is True,
            "suppress_s": _as_int(data["rotation"]["suppress_s"]),
        },
        "quote": {"mode": data["quote"]["mode"], "custom": custom},
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
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
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

    def save(self, incoming: dict) -> tuple[dict, str, bool, bool]:
        """校验并原子写入。返回 (settings, version, location_changed, weather_refreshed)。"""
        details = validate(incoming)
        if details:
            raise SettingsError("SETTINGS_VALIDATION_FAILED", "配置校验失败", details)
        normalized = normalize(incoming)
        tz_name = normalized["location"]["timezone"]
        normalized["updated_at"] = datetime.now(ZoneInfo(tz_name)).isoformat(timespec="seconds")
        raw = (json.dumps(normalized, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(raw) > SETTINGS_MAX_BYTES:
            raise SettingsError(
                "SETTINGS_VALIDATION_FAILED",
                "配置超过 32KB",
                [_detail("quote.custom", "QUOTE_CUSTOM_INVALID", "配置体积超过 32KB")],
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


@dataclass
class _Beat:
    ts: float
    ip: str | None
    ua: str | None
    settings_version: str
    regions_version: str


class HeartbeatLog:
    """进程内最近两次 env 拉取。重启后状态为 unknown。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._beats: list[_Beat] = []

    def record(self, ip: str | None, ua: str | None, settings_version_value: str, regions_version: str) -> None:
        agent = (ua or "").strip()[:80] or None
        beat = _Beat(time.time(), (ip or "").strip() or None, agent, settings_version_value, regions_version)
        with self._lock:
            self._beats.append(beat)
            del self._beats[:-2]

    def snapshot(self, current_version: str, tz_name: str) -> dict:
        with self._lock:
            beats = list(self._beats)
        base = {
            "online_state": "unknown",
            "delivery_state": "unknown",
            "last_seen_at": None,
            "last_ip": None,
            "last_user_agent": None,
            "delivered_settings_version": None,
            "current_settings_version": current_version,
            "interval_estimate_s": DEFAULT_INTERVAL_S,
            "eta_minutes": 0,
        }
        if not beats:
            return base
        last = beats[-1]
        if len(beats) >= 2:
            interval = max(1, int(round(last.ts - beats[-2].ts)))
        else:
            interval = DEFAULT_INTERVAL_S
        age = time.time() - last.ts
        online = "online" if age < HEARTBEAT_ONLINE_FACTOR * interval else "offline"
        delivery = "delivered" if last.settings_version == current_version else "pending"
        eta = math.ceil(max(0.0, last.ts + interval - time.time()) / 60.0)
        try:
            seen = datetime.fromtimestamp(last.ts, ZoneInfo(tz_name)).isoformat(timespec="seconds")
        except Exception:
            seen = datetime.fromtimestamp(last.ts, timezone.utc).isoformat(timespec="seconds")
        base.update(
            {
                "online_state": online,
                "delivery_state": delivery,
                "last_seen_at": seen,
                "last_ip": last.ip,
                "last_user_agent": last.ua,
                "delivered_settings_version": last.settings_version,
                "interval_estimate_s": interval,
                "eta_minutes": int(eta),
            }
        )
        return base

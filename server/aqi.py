"""空气质量数据（Open-Meteo Air Quality，US AQI 现值）。"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import requests

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ALLOWED_HOSTS = {"air-quality-api.open-meteo.com"}

# US EPA 六级 → 中文（api-v2-aqi.md BR-1）
LEVELS = [
    (50, "优"),
    (100, "良"),
    (150, "轻度敏感"),
    (200, "中度"),
    (300, "重度"),
    (1000, "严重"),
]


def _check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"blocked request target: {url}")


def level_zh(us_aqi: int) -> str:
    for bound, name in LEVELS:
        if us_aqi <= bound:
            return name
    return "严重"


@dataclass
class AirQuality:
    us_aqi: int
    level: str


# 数据源健康状态（内存态，供管理端展示）
_status: dict = {"ok": False, "at": None, "error": "", "enabled": True, "value": None}


def health() -> dict:
    return dict(_status)


def fetch_aqi(latitude: float, longitude: float, timeout: float = 10) -> AirQuality | None:
    """拉取 US AQI 现值；失败/越界返回 None（PRD FR-1 优雅降级）。"""
    from datetime import datetime, timezone

    _check_url(AIR_QUALITY_URL)
    try:
        resp = requests.get(
            AIR_QUALITY_URL,
            params={"latitude": latitude, "longitude": longitude, "current": "us_aqi", "timezone": "auto"},
            timeout=timeout,
            allow_redirects=False,
        )
        resp.raise_for_status()
        value = resp.json()["current"]["us_aqi"]
        if not isinstance(value, (int, float)) or not 0 <= value <= 500:
            _status.update(ok=False, at=datetime.now(timezone.utc).isoformat(timespec="seconds"), error="AQI 数值缺失或越界")
            return None
        us_aqi = int(round(value))
        _status.update(ok=True, at=datetime.now(timezone.utc).isoformat(timespec="seconds"), error="", value=us_aqi)
        return AirQuality(us_aqi=us_aqi, level=level_zh(us_aqi))
    except Exception as exc:
        log.warning("AQI 拉取失败: %s", exc)
        _status.update(ok=False, at=datetime.now(timezone.utc).isoformat(timespec="seconds"), error=str(exc))
        return None

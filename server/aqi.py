"""空气质量数据（Open-Meteo Air Quality）：US AQI 现值 + 六项污染物，并按 HJ 633-2012 计算中国 AQI。"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ALLOWED_HOSTS = {"air-quality-api.open-meteo.com"}
CURRENT_FIELDS = "us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"

# US EPA 六级 → 中文（api-v2-aqi.md BR-1）
LEVELS = [
    (50, "优"),
    (100, "良"),
    (150, "轻度敏感"),
    (200, "中度"),
    (300, "重度"),
    (1000, "严重"),
]

# HJ 633-2012：IAQI 分段点与各污染物浓度限值（µg/m³；CO 为 mg/m³）
_IAQI = (0, 50, 100, 150, 200, 300, 400, 500)
_BP = {
    "so2_1h": (0, 150, 500, 650, 800),
    "so2_24h": (0, 50, 150, 475, 800, 1600, 2100, 2620),
    "no2_1h": (0, 100, 200, 700, 1200, 2340, 3090, 3840),
    "co_1h": (0, 5, 10, 35, 60, 90, 120, 150),
    "o3_1h": (0, 160, 200, 300, 400, 800, 1000, 1200),
    "pm10_24h": (0, 50, 150, 250, 350, 420, 500, 600),
    "pm25_24h": (0, 35, 75, 115, 150, 250, 350, 500),
}
CN_LEVELS = [
    (50, "优", "Excellent"),
    (100, "良", "Good"),
    (150, "轻度污染", "Light"),
    (200, "中度污染", "Moderate"),
    (300, "重度污染", "Heavy"),
    (math.inf, "严重污染", "Severe"),
]
_CN_LEVEL_EN = {zh: en for _bound, zh, en in CN_LEVELS}


def _check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"blocked request target: {url}")


def level_zh(us_aqi: int) -> str:
    for bound, name in LEVELS:
        if us_aqi <= bound:
            return name
    return "严重"


def iaqi(concentration: float, breakpoints: tuple) -> int:
    """单项空气质量分指数：分段线性插值后向上取整；超出最高限值记 500。"""
    if concentration >= breakpoints[-1]:
        return 500 if len(breakpoints) == len(_IAQI) else _IAQI[len(breakpoints) - 1]
    for i in range(1, len(breakpoints)):
        if concentration <= breakpoints[i]:
            lo_c, hi_c = breakpoints[i - 1], breakpoints[i]
            lo_i, hi_i = _IAQI[i - 1], _IAQI[i]
            # 先修约到 6 位小数再向上取整：恰在分段点时浮点误差（如 50.0000000001）不应进位
            return math.ceil(round((hi_i - lo_i) / (hi_c - lo_c) * (concentration - lo_c) + lo_i, 6))
    return 500


def cn_aqi_from(pm2_5=None, pm10=None, o3=None, no2=None, so2=None, co=None) -> int | None:
    """实时 AQI：SO2/NO2/CO/O3 用 1 小时限值，PM 小时浓度套 24 小时限值（国家实时发布口径）。
    PM2.5 与 PM10 缺一则不计算；co 为 µg/m³。"""
    if pm2_5 is None or pm10 is None:
        return None
    parts = [iaqi(pm2_5, _BP["pm25_24h"]), iaqi(pm10, _BP["pm10_24h"])]
    if o3 is not None:
        parts.append(iaqi(o3, _BP["o3_1h"]))
    if no2 is not None:
        parts.append(iaqi(no2, _BP["no2_1h"]))
    if so2 is not None:
        # 1 小时 SO2 超过 800 时 HJ 633 改按 24 小时限值计算
        parts.append(iaqi(so2, _BP["so2_1h"]) if so2 <= 800 else iaqi(so2, _BP["so2_24h"]))
    if co is not None:
        parts.append(iaqi(co / 1000, _BP["co_1h"]))
    return max(parts)


def cn_level(value: int) -> str:
    for bound, zh, _en in CN_LEVELS:
        if value <= bound:
            return zh
    return CN_LEVELS[-1][1]


def cn_level_en(level: str) -> str:
    return _CN_LEVEL_EN.get(level, level)


@dataclass
class AirQuality:
    us_aqi: int
    level: str
    pm2_5: float | None = None
    pm10: float | None = None
    o3: float | None = None
    no2: float | None = None
    so2: float | None = None
    co: float | None = None
    cn_aqi: int | None = None
    cn_level: str | None = None


# 数据源健康状态（内存态，供管理端展示）
_status: dict = {"ok": False, "at": None, "error": "", "enabled": True, "value": None}


def health() -> dict:
    return dict(_status)


def _pollutant(current: dict, key: str) -> float | None:
    value = current.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return float(value)


def fetch_aqi(latitude: float, longitude: float, timeout: float = 10) -> AirQuality | None:
    """拉取 US AQI 现值与六项污染物；失败/越界返回 None（PRD FR-1 优雅降级）。"""
    from datetime import datetime, timezone

    _check_url(AIR_QUALITY_URL)
    try:
        resp = requests.get(
            AIR_QUALITY_URL,
            params={"latitude": latitude, "longitude": longitude, "current": CURRENT_FIELDS, "timezone": "auto"},
            timeout=timeout,
            allow_redirects=False,
        )
        resp.raise_for_status()
        current = resp.json()["current"]
        value = current["us_aqi"]
        if not isinstance(value, (int, float)) or not 0 <= value <= 500:
            _status.update(ok=False, at=datetime.now(timezone.utc).isoformat(timespec="seconds"), error="AQI 数值缺失或越界")
            return None
        us_aqi = int(round(value))
        pollutants = {
            "pm2_5": _pollutant(current, "pm2_5"),
            "pm10": _pollutant(current, "pm10"),
            "o3": _pollutant(current, "ozone"),
            "no2": _pollutant(current, "nitrogen_dioxide"),
            "so2": _pollutant(current, "sulphur_dioxide"),
            "co": _pollutant(current, "carbon_monoxide"),
        }
        cn_value = cn_aqi_from(**pollutants)
        _status.update(ok=True, at=datetime.now(timezone.utc).isoformat(timespec="seconds"), error="", value=us_aqi)
        return AirQuality(
            us_aqi=us_aqi,
            level=level_zh(us_aqi),
            **pollutants,
            cn_aqi=cn_value,
            cn_level=cn_level(cn_value) if cn_value is not None else None,
        )
    except Exception as exc:
        log.warning("AQI 拉取失败: %s", exc)
        _status.update(ok=False, at=datetime.now(timezone.utc).isoformat(timespec="seconds"), error=str(exc))
        return None

"""显示单位与格式化：温度/风速/AQI 出图时的唯一换算入口。

数据层（payload 数值、/weather、dashboard.json）始终是 ℃ / km/h / 美标原值，
只有出图文字经这里按 payload["units"] 换算；未配置 = 现状（℃ / km/h / 美标）。
"""

from __future__ import annotations

import math

from server.aqi import cn_level_en
from server.locale import aqi_en, is_en

DEFAULT_UNITS = {"temp": "c", "wind": "kmh", "aqi": "us"}
UNIT_CHOICES = {"temp": ("c", "f"), "wind": ("kmh", "ms", "bft"), "aqi": ("us", "cn")}
# 蒲福风级下限（m/s）：风速达到第 i 个阈值即为 i+1 级
_BEAUFORT_MS = (0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7)
# AQI 六段（美标与国标分段点相同）：0–50 / 51–100 / 101–150 / 151–200 / 201–300 / >300
_AQI_BANDS = (50, 100, 150, 200, 300)


def normalize_units(raw: object) -> dict:
    data = raw if isinstance(raw, dict) else {}
    return {key: data[key] if data.get(key) in choices else DEFAULT_UNITS[key] for key, choices in UNIT_CHOICES.items()}


def units_of(payload: dict | None) -> dict:
    return normalize_units((payload or {}).get("units"))


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or math.isnan(value):
        return None
    return float(value)


def half_up(value: float) -> int:
    """四舍五入取整。返回 int——int 没有负零，"-0°" 由此根除。"""
    return int(math.floor(value + 0.5))


def temp_number(celsius, payload: dict | None) -> int | None:
    value = _number(celsius)
    if value is None:
        return None
    if units_of(payload)["temp"] == "f":
        value = value * 9 / 5 + 32
    return half_up(value)


def fmt_temp(celsius, payload: dict | None) -> str:
    value = temp_number(celsius, payload)
    return "" if value is None else f"{value}°"


def fmt_temp_delta(delta_c, payload: dict | None) -> str:
    """温差（如较昨日降温）：华氏只乘 9/5，不加 32。"""
    value = _number(delta_c)
    if value is None:
        return ""
    if units_of(payload)["temp"] == "f":
        value = value * 9 / 5
    return f"{half_up(value)}°"


def beaufort(kmh: float) -> int:
    ms = kmh / 3.6
    return sum(1 for bound in _BEAUFORT_MS if ms >= bound)


def fmt_wind(kmh, payload: dict | None) -> str:
    value = _number(kmh)
    if value is None:
        return ""
    unit = units_of(payload)["wind"]
    if unit == "ms":
        return f"{value / 3.6:.1f} m/s"
    if unit == "bft":
        level = beaufort(value)
        return f"Force {level}" if is_en(payload) else f"{level}级"
    return f"{half_up(value)} km/h"


def aqi_view(payload: dict | None) -> tuple[int, str] | None:
    """按 units.aqi 取 (数值, 本地化等级)；选国标但国标数据缺失时回退美标。"""
    aqi = (payload or {}).get("aqi")
    if not isinstance(aqi, dict):
        return None
    english = is_en(payload)
    cn_value = aqi.get("cn_aqi")
    if units_of(payload)["aqi"] == "cn" and isinstance(cn_value, int) and not isinstance(cn_value, bool):
        level = str(aqi.get("cn_level") or "")
        return cn_value, cn_level_en(level) if english else level
    us_value = _number(aqi.get("us_aqi"))
    if us_value is None:
        return None
    level = str(aqi.get("level_zh") or "")
    return int(us_value), aqi_en(level) if english else level


def aqi_band(value: int) -> int:
    """AQI 数值所在的段（0–5），供六段刻度条定位当前段。"""
    return sum(1 for bound in _AQI_BANDS if value > bound)


# 风向为「风的来向」（气象惯例，0=北风），8 方位
_DIRS_CN = ("北", "东北", "东", "东南", "南", "西南", "西", "西北")
_DIRS_EN = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def fmt_wind_dir(degrees, payload: dict | None) -> str:
    value = _number(degrees)
    if value is None:
        return ""
    index = int(((value % 360) + 22.5) // 45) % 8
    return _DIRS_EN[index] if is_en(payload) else _DIRS_CN[index] + "风"


def fmt_visibility(km) -> str:
    value = _number(km)
    if value is None:
        return ""
    return f"{half_up(value)} km" if value >= 10 else f"{value:.1f} km"


def fmt_pressure(hpa) -> str:
    value = _number(hpa)
    return "" if value is None else f"{half_up(value)} hPa"


def fmt_int(value) -> str:
    number = _number(value)
    return "" if number is None else str(half_up(number))

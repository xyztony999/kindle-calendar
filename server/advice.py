"""生活建议（派生、主观，非官方指数）：按契约 api-block-options-2.md §7 的规则由天气/空气数据推算。

出图时计算（AQI 跟随 units.aqi 标准）。主要输入缺失时返回空串（显示「—」）；
次要输入缺失时其相关条件不触发（结果偏保守）。
"""

from __future__ import annotations

import math

from server.locale import is_en
from server.units import aqi_view

ADVICE_KEYS = ("dress", "laundry", "exercise", "carwash", "cold", "sunscreen")

# 穿衣：体感温度下限 → (中文, 英文)
_DRESS = (
    (28, "短袖", "Shorts"),
    (23, "薄长袖", "Light layers"),
    (18, "长袖衬衫", "Long sleeves"),
    (12, "薄外套", "Light jacket"),
    (5, "厚外套", "Warm jacket"),
    (-5, "棉衣", "Padded coat"),
    (-math.inf, "羽绒服", "Down jacket"),
)
_SUIT = {
    "no": ("不宜", "Not advised"),
    "less": ("较不宜", "Less suitable"),
    "fair": ("较适宜", "Fairly suitable"),
    "yes": ("适宜", "Suitable"),
}
_COLD = {"likely": ("易发", "Likely"), "possible": ("较易发", "Possible"), "unlikely": ("少发", "Unlikely")}
# 紫外线强度：指数下限 → (中文, 英文)
_UV = ((11, "极强", "Extreme"), (8, "很强", "Very high"), (6, "强", "High"), (3, "中等", "Moderate"), (-math.inf, "弱", "Low"))
# WMO 天气码中的降水类（毛毛雨/雨/冻雨/雪/阵雨/阵雪/雷暴）
_WET_CODES = set(range(51, 68)) | set(range(71, 78)) | set(range(80, 87)) | set(range(95, 100))


def _num(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or math.isnan(value):
        return None
    return float(value)


def _ge(value: float | None, bound: float) -> bool:
    return value is not None and value >= bound


def _le(value: float | None, bound: float) -> bool:
    return value is not None and value <= bound


def _lt(value: float | None, bound: float) -> bool:
    return value is not None and value < bound


def uv_level(uv: float, english: bool = False) -> str:
    for bound, zh, en in _UV:
        if uv >= bound:
            return en if english else zh
    return _UV[-1][2] if english else _UV[-1][1]


def uv_today(payload: dict) -> float | None:
    """今日紫外线：优先当日最大值（夜间实况为 0 没有参考意义），缺失回退实况。"""
    weather = payload.get("weather") or {}
    daily = weather.get("daily") or []
    value = _num(daily[0].get("uv_max")) if daily and isinstance(daily[0], dict) else None
    return value if value is not None else _num((weather.get("current") or {}).get("uv"))


def _inputs(payload: dict) -> dict:
    weather = payload.get("weather") or {}
    current = weather.get("current") or {}
    daily = weather.get("daily") or []
    today = daily[0] if daily and isinstance(daily[0], dict) else {}
    tomorrow = daily[1] if len(daily) > 1 and isinstance(daily[1], dict) else {}
    temp = _num(current.get("apparent"))
    if temp is None:
        temp = _num(current.get("temperature"))
    precip = _num(today.get("precip_prob"))
    if precip is None:
        precip = _num(weather.get("precip_prob"))
    uv = uv_today(payload)
    high, low = _num(today.get("temp_max")), _num(today.get("temp_min"))
    view = aqi_view(payload)
    code = current.get("code")
    return {
        "T": temp,
        "P": precip,
        "P1": _num(tomorrow.get("precip_prob")),
        "H": _num(current.get("humidity")),
        "U": uv,
        "W": _num(current.get("wind_speed")),
        "S": None if high is None or low is None else high - low,
        "AQI": float(view[0]) if view else None,
        "wet": isinstance(code, int) and code in _WET_CODES,
        "cool": any(isinstance(a, dict) and a.get("kind") == "cool" for a in payload.get("weather_alerts") or []),
    }


def _dress(v: dict) -> tuple[str, str] | None:
    if v["T"] is None:
        return None
    for bound, zh, en in _DRESS:
        if v["T"] >= bound:
            return zh, en
    return None


def _laundry(v: dict) -> tuple[str, str] | None:
    if v["P"] is None:
        return None
    if _ge(v["P"], 50) or v["wet"]:
        return _SUIT["no"]
    if _ge(v["P"], 30) or _ge(v["H"], 85):
        return _SUIT["less"]
    if _ge(v["U"], 3) and _lt(v["H"], 70) and _lt(v["P"], 20):
        return _SUIT["yes"]
    return _SUIT["fair"]


def _exercise(v: dict) -> tuple[str, str] | None:
    if v["T"] is None:
        return None
    t, p, aqi = v["T"], v["P"], v["AQI"]
    if (aqi is not None and aqi > 150) or _ge(p, 60) or t >= 35 or t <= -10:
        return _SUIT["no"]
    if (aqi is not None and aqi > 100) or _ge(p, 30) or t >= 30 or t <= 0 or _ge(v["W"], 39):
        return _SUIT["less"]
    if 10 <= t <= 26 and _le(aqi, 50) and _lt(p, 20):
        return _SUIT["yes"]
    return _SUIT["fair"]


def _carwash(v: dict) -> tuple[str, str] | None:
    if v["P"] is None:
        return None
    if _ge(v["P"], 30) or _ge(v["P1"], 50):
        return _SUIT["no"]
    if (v["AQI"] is not None and v["AQI"] > 150) or _ge(v["W"], 39):
        return _SUIT["less"]
    return _SUIT["yes"]


def _cold(v: dict) -> tuple[str, str] | None:
    if v["T"] is None:
        return None
    if _ge(v["S"], 10) or v["T"] <= 5 or v["cool"]:
        return _COLD["likely"]
    if _ge(v["S"], 7) or v["T"] <= 10 or _le(v["H"], 30):
        return _COLD["possible"]
    return _COLD["unlikely"]


def _sunscreen(v: dict) -> tuple[str, str] | None:
    if v["U"] is None:
        return None
    return uv_level(v["U"]), uv_level(v["U"], english=True)


_RULES = {
    "dress": _dress,
    "laundry": _laundry,
    "exercise": _exercise,
    "carwash": _carwash,
    "cold": _cold,
    "sunscreen": _sunscreen,
}


def advice_text(payload: dict, key: str) -> str:
    """某项生活建议的本地化文本；数据不足返回空串。"""
    rule = _RULES.get(key)
    if rule is None:
        return ""
    result = rule(_inputs(payload))
    if result is None:
        return ""
    return result[1] if is_en(payload) else result[0]

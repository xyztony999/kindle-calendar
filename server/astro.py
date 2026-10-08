"""天文计算：日出日落（NOAA 算法内联实现）与月相。

不依赖第三方库，精度约 ±1~2 分钟，对台历显示足够。
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

# 平朔望月（天）与参考新月时刻（2000-01-06 18:14 UTC）
SYNODIC_MONTH = 29.530588853
REF_NEW_MOON = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)

MOON_NAMES = [
    (0.033, "新月"),
    (0.216, "娥眉月"),
    (0.284, "上弦月"),
    (0.466, "盈凸月"),
    (0.534, "满月"),
    (0.716, "亏凸月"),
    (0.784, "下弦月"),
    (0.966, "残月"),
]


def _julian_day(d: date) -> float:
    # 12:00 UT of that day
    y, m = d.year, d.month
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d.day + b - 1524.5


def sun_times(d: date, latitude: float, longitude: float, tz_offset_minutes: float = 0.0) -> tuple[float | None, float | None]:
    """返回指定时区偏移下的日出/日落分钟数（自当地午夜起算）。

    longitude 为东经正；tz_offset_minutes 为显示时区相对 UTC 的偏移（如北京 +480）。
    极昼/极夜返回 (None, None)。
    """
    # _julian_day 返回当日 00:00 UT 的 JD；+0.5 归算到 J2000 正午纪元的天计数
    n = _julian_day(d) - 2451545.0 + 0.0008 + 0.5
    jstar = n - longitude / 360.0

    m = (357.5291 + 0.98560028 * jstar) % 360.0
    c = 1.9148 * math.sin(math.radians(m)) + 0.02 * math.sin(math.radians(2 * m)) + 0.0003 * math.sin(math.radians(3 * m))
    lam = (m + c + 180.0 + 102.9372) % 360.0

    j_transit = 2451545.0 + jstar + 0.0053 * math.sin(math.radians(m)) - 0.0069 * math.sin(math.radians(2 * lam))

    delta = math.degrees(math.asin(math.sin(math.radians(lam)) * math.sin(math.radians(23.4397))))
    cos_omega = (
        math.sin(math.radians(-0.833)) - math.sin(math.radians(latitude)) * math.sin(math.radians(delta))
    ) / (math.cos(math.radians(latitude)) * math.cos(math.radians(delta)))
    if cos_omega < -1 or cos_omega > 1:
        return None, None
    omega = math.degrees(math.acos(cos_omega))

    # 儒略日以 UT 计；换算到显示时区
    rise_min = ((j_transit - omega / 360.0 + 0.5) % 1.0) * 1440.0 + tz_offset_minutes
    set_min = ((j_transit + omega / 360.0 + 0.5) % 1.0) * 1440.0 + tz_offset_minutes
    return rise_min % 1440.0, set_min % 1440.0


def _fmt(minute: float | None) -> str:
    if minute is None:
        return "--:--"
    m = int(round(minute)) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def moon_info(now: datetime) -> dict:
    """月相：phase ∈ [0,1)，0=新月 0.5=满月。"""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age = (now - REF_NEW_MOON).total_seconds() / 86400.0 % SYNODIC_MONTH
    phase = age / SYNODIC_MONTH
    illumination = (1 - math.cos(2 * math.pi * phase)) / 2
    name = MOON_NAMES[-1][1]
    for bound, n in MOON_NAMES:
        if phase < bound:
            name = n
            break
    return {"phase": round(phase, 3), "name": name, "illumination": round(illumination * 100)}


def day_summary(now: datetime, latitude: float, longitude: float) -> dict:
    """今日日出日落 + 月相（供页面渲染与 JSON 输出）。"""
    offset = now.utcoffset()
    tz_minutes = 0.0 if offset is None else offset.total_seconds() / 60.0
    rise, set_ = sun_times(now.date(), latitude, longitude, tz_minutes)
    return {
        "sunrise": _fmt(rise),
        "sunset": _fmt(set_),
        "sunrise_minutes": None if rise is None else round(rise),
        "sunset_minutes": None if set_ is None else round(set_),
        **moon_info(now),
    }


def next_change(now: datetime) -> datetime:
    """下一天的开始（本地），用于调度每日数据的重算。"""
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

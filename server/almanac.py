"""农历 / 干支 / 节气 / 宜忌 / 物候 — lunar-python 封装（纯本地计算）。"""

from __future__ import annotations

from datetime import datetime

from lunar_python import Solar

CN_DIGITS = "〇一二三四五六七八九"


def _year_cn(year: int) -> str:
    return "".join(CN_DIGITS[int(c)] for c in str(year))


def almanac_for(now: datetime) -> dict:
    solar = Solar.fromYmdHms(now.year, now.month, now.day, now.hour, now.minute, 0)
    lunar = solar.getLunar()

    month = lunar.getMonth()
    leap = "闰" if month < 0 else ""
    lunar_str = f"{leap}{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"

    prev = lunar.getPrevJieQi()
    prev_date = datetime(prev.getSolar().getYear(), prev.getSolar().getMonth(), prev.getSolar().getDay())
    days_since = (now.date() - prev_date.date()).days

    festivals = list(dict.fromkeys(lunar.getFestivals() + solar.getFestivals()))

    return {
        "iso": now.strftime("%Y-%m-%d"),
        "year_cn": _year_cn(now.year),
        "month_day_cn": f"{_month_cn(now.month)}月{_day_cn(now.day)}",
        "weekday": "一二三四五六日"[now.weekday()],
        "lunar": lunar_str,
        "ganzhi_year": lunar.getYearInGanZhi(),
        "zodiac": lunar.getYearShengXiao(),
        "solar_term": {"name": prev.getName(), "date": prev_date.strftime("%Y-%m-%d"), "days_since": days_since},
        "next_solar_term": lunar.getNextJieQi().getName(),
        "festivals": festivals,
        "yi": [x for x in lunar.getDayYi() if x != "无"][:6],
        "ji": [x for x in lunar.getDayJi() if x != "无"][:6],
        "wuhou": lunar.getWuHou(),
    }


def _month_cn(m: int) -> str:
    if m == 10:
        return "十"
    if m == 11:
        return "十一"
    if m == 12:
        return "十二"
    return CN_DIGITS[m]


def _day_cn(d: int) -> str:
    if d < 10:
        return CN_DIGITS[d]
    if d < 20:
        return "十" + (CN_DIGITS[d - 10] if d > 10 else "")
    if d == 20:
        return "二十"
    if d < 30:
        return "廿" + CN_DIGITS[d - 20]
    if d == 30:
        return "三十"
    return "三十一"

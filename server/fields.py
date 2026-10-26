"""用户数据积木的字段取值。只读现有 payload，不接受任意路径。"""

from __future__ import annotations

from server.locale import badge_en, is_en, short_date, weekday_en, zodiac_en

_WEEKDAY = "一二三四五六日"
DASH = "—"


def _join(values) -> str:
    if not isinstance(values, list):
        return ""
    text = "、".join(str(item) for item in values if item)
    return text


def _temp(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    return f"{value:.0f}°"


def field_text(payload: dict, field_id: str) -> str:
    english = is_en(payload)
    weather = payload.get("weather") or {}
    current = weather.get("current") or {}
    daily = (weather.get("daily") or [{}])[0] or {}
    date = payload.get("date") or {}
    sun = payload.get("sun") or {}
    aqi = payload.get("aqi") or {}
    quote = payload.get("quote") or {}
    holiday = payload.get("holiday") or {}
    events = payload.get("events") or []

    if field_id == "weather.temperature":
        text = _temp(current.get("temperature"))
    elif field_id == "weather.description":
        text = str(current.get("description") or "")
    elif field_id == "weather.humidity":
        humidity = current.get("humidity")
        text = f"{humidity}%" if isinstance(humidity, (int, float)) and not isinstance(humidity, bool) else ""
    elif field_id == "weather.wind_speed":
        wind = current.get("wind_speed")
        text = f"{wind:.0f} km/h" if isinstance(wind, (int, float)) and not isinstance(wind, bool) else ""
    elif field_id == "weather.precip_prob":
        precip = weather.get("precip_prob")
        text = f"{precip}%" if isinstance(precip, (int, float)) and not isinstance(precip, bool) else ""
    elif field_id == "weather.apparent":
        text = _temp(current.get("apparent"))
    elif field_id == "weather.temp_min":
        text = _temp(daily.get("temp_min"))
    elif field_id == "weather.temp_max":
        text = _temp(daily.get("temp_max"))
    elif field_id == "date.month_day":
        iso = str(date.get("iso") or "")
        text = short_date(iso) if english and iso else str(date.get("month_day_cn") or "")
    elif field_id == "date.weekday":
        raw = str(date.get("weekday") or "")
        if english and raw in _WEEKDAY:
            text = weekday_en(_WEEKDAY.index(raw))
        else:
            text = f"星期{raw}" if raw else ""
    elif field_id == "date.lunar":
        text = str(date.get("lunar") or "")
    elif field_id == "date.ganzhi":
        year = str(date.get("ganzhi_year") or "")
        zodiac = str(date.get("zodiac") or "")
        if english and zodiac:
            zodiac = zodiac_en(zodiac)
        text = f"{year} {zodiac}".strip() if english else f"{year}{zodiac}年" if year or zodiac else ""
    elif field_id == "date.solar_term":
        term = date.get("solar_term") or {}
        text = str(term.get("name") or "") if isinstance(term, dict) else ""
    elif field_id == "date.festivals":
        text = _join(date.get("festivals"))
    elif field_id == "date.holiday":
        if isinstance(holiday, dict) and holiday.get("name"):
            note = str(holiday.get("note") or "")
            if english and note:
                note = badge_en(note)
            text = f"{holiday['name']} {note}".strip() if english else f"{holiday['name']}{note}"
        else:
            text = ""
    elif field_id == "sun.sunrise":
        text = str(sun.get("sunrise") or "")
    elif field_id == "sun.sunset":
        text = str(sun.get("sunset") or "")
    elif field_id == "sun.moon":
        text = str(sun.get("name") or "")
    elif field_id == "sun.illumination":
        illum = sun.get("illumination")
        text = f"{illum}%" if isinstance(illum, (int, float)) and not isinstance(illum, bool) else ""
    elif field_id == "aqi.value":
        value = aqi.get("us_aqi") if isinstance(aqi, dict) else None
        text = str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else ""
    elif field_id == "aqi.level":
        text = str(aqi.get("level_zh") or "") if isinstance(aqi, dict) else ""
    elif field_id == "quote.text":
        text = str(quote.get("text") or "")
    elif field_id == "quote.from":
        text = str(quote.get("from") or "")
    elif field_id == "almanac.yi":
        text = _join(date.get("yi"))
    elif field_id == "almanac.ji":
        text = _join(date.get("ji"))
    elif field_id == "location.name":
        text = str(payload.get("location") or "")
    elif field_id == "events.today_count":
        iso = str(date.get("iso") or "")
        text = str(sum(1 for e in events if isinstance(e, dict) and e.get("iso_date") == iso)) if iso else ""
    elif field_id in ("events.next_title", "events.next_time"):
        iso = str(date.get("iso") or "")
        day = [e for e in events if isinstance(e, dict) and e.get("iso_date") == iso]
        day.sort(key=lambda e: (0 if e.get("all_day") else 1, str(e.get("time") or "00:00")))
        nxt = day[0] if day else None
        if field_id == "events.next_title":
            text = str(nxt.get("title") or "") if nxt else ""
        else:
            text = str(nxt.get("time") or "") if nxt and not nxt.get("all_day") else ""
    else:
        text = ""
    return text or DASH

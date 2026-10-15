"""四个公开数据地址的浏览器阅读页。机器请求仍走原来的 JSON 或 env。"""

from __future__ import annotations

from flask import render_template, request

from server.locale import THEME_COOKIE, page_label, web_theme

_ZH = {
    "html_lang": "zh-CN",
    "mark": "Kindle 台历",
    "theme_title": "主题",
    "theme_to_dark": "切换到深色",
    "theme_to_light": "切换到浅色",
    "foot_note": "数据每 15 分钟左右更新一次",
    "switch_label": "English",
    "raw": "原始数据",
    "home": "返回首页",
    "none": "无",
    "no_data": "暂无",
    "suitable": "宜",
    "avoid": "忌",
    "date": "日期",
    "solar": "节气",
    "weather_now": "当前天气",
    "hourly_link": "查看逐时",
    "sun": "日出与日落",
    "moon": "月相",
    "aqi": "空气质量",
    "quote": "一言",
    "pages": "页面与配置",
    "enabled": "已启用页面",
    "version": "配置版本",
    "generated": "生成时间",
    "humidity": "湿度",
    "wind": "风速",
    "daily": "逐日",
    "hourly": "逐时",
    "col_date": "日期",
    "col_weather": "天气",
    "col_high": "最高",
    "col_low": "最低",
    "col_time": "时间",
    "col_temp": "温度",
    "col_precip": "降水概率",
    "health_title": "服务状态",
    "online": "服务在线",
    "weather_ok": "天气已更新",
    "weather_bad": "天气暂不可用",
    "refreshing": "正在更新",
    "seconds": "秒",
    "screen": "画面尺寸",
    "city": "城市",
    "env_title": "设备清单",
    "screen_size": "画面宽高",
    "page_order": "页面顺序",
    "rotate": "轮播",
    "dwell": "停留",
    "suppress": "触摸后让位",
    "language": "语言",
    "lang_unset": "未声明，设备按中文",
    "on": "开",
    "off": "关",
    "missing": "未提供",
    "regions": "{n} 条",
    "heartbeat": "打开本页会计一次拉取，和管理端里的最近拉取是同一件事。",
    "source": "查看原文",
    "unavailable": "暂时读不到",
    "weather_unavailable": "天气暂时读不到",
    "unavailable_body": "这一页需要的数据还没有准备好。",
    "days": "已过 {n} 天",
    "days_label": "已过天数",
    "regions_label": "分区地址",
    "next_term": "下一节气",
    "weekday": "星期",
    "lunar": "农历",
    "festival": "节日",
    "badge": "班休",
}

_EN = {
    "html_lang": "en",
    "mark": "Kindle Calendar",
    "theme_title": "Theme",
    "theme_to_dark": "Switch to dark",
    "theme_to_light": "Switch to light",
    "foot_note": "Data refreshes roughly every 15 minutes",
    "switch_label": "中文",
    "raw": "Raw data",
    "home": "Back to home",
    "none": "None",
    "no_data": "No data",
    "suitable": "Suitable",
    "avoid": "Avoid",
    "date": "Date",
    "solar": "Solar term",
    "weather_now": "Weather now",
    "hourly_link": "Hour by hour",
    "sun": "Sunrise and sunset",
    "moon": "Moon",
    "aqi": "Air quality",
    "quote": "Quote",
    "pages": "Pages",
    "enabled": "Enabled pages",
    "version": "Settings version",
    "generated": "Generated",
    "humidity": "Humidity",
    "wind": "Wind",
    "daily": "Daily",
    "hourly": "Hourly",
    "col_date": "Date",
    "col_weather": "Weather",
    "col_high": "High",
    "col_low": "Low",
    "col_time": "Time",
    "col_temp": "Temperature",
    "col_precip": "Chance of rain",
    "health_title": "Service status",
    "online": "Service online",
    "weather_ok": "Weather is current",
    "weather_bad": "Weather is unavailable",
    "refreshing": "Updating",
    "seconds": "s",
    "screen": "Screen",
    "city": "City",
    "env_title": "Device manifest",
    "screen_size": "Screen size",
    "page_order": "Page order",
    "rotate": "Carousel",
    "dwell": "Dwell",
    "suppress": "Pause after touch",
    "language": "Language",
    "lang_unset": "Not set. The device uses Chinese",
    "on": "On",
    "off": "Off",
    "missing": "Not available",
    "regions": "{n}",
    "heartbeat": "Opening this page counts as a fetch, the same event the admin page shows as the latest pull.",
    "source": "Show source",
    "unavailable": "Unavailable for now",
    "weather_unavailable": "Weather is unavailable",
    "unavailable_body": "The data for this page is not ready.",
    "days": "Day {n}",
    "days_label": "Days into the term",
    "regions_label": "Region addresses",
    "next_term": "Next",
    "weekday": "Weekday",
    "lunar": "Lunar",
    "festival": "Festival",
    "badge": "Holiday mark",
}


def prefer_html(format_value: str | None, accept: str | None) -> bool:
    """只有明确要网页时才返回阅读页。`*/*` 不算。"""
    kind = (format_value or "").strip().lower()
    if kind == "json":
        return False
    if kind == "html":
        return True
    if kind:
        return False
    html_q = _explicit_quality(accept, "text/html")
    json_q = _explicit_quality(accept, "application/json")
    return html_q > json_q and html_q > 0


def _explicit_quality(accept: str | None, mime: str) -> float:
    best = 0.0
    found = False
    for part in (accept or "").split(","):
        bits = [bit.strip() for bit in part.split(";") if bit.strip()]
        if not bits or bits[0].lower() != mime:
            continue
        quality = 1.0
        for bit in bits[1:]:
            if bit.lower().startswith("q="):
                try:
                    quality = float(bit.split("=", 1)[1])
                except ValueError:
                    quality = 0.0
        found = True
        if quality > best:
            best = quality
    return best if found else 0.0


def _copy(lang: str) -> dict[str, str]:
    return _EN if lang == "en" else _ZH


def _chrome(lang: str, path: str, *, raw: bool) -> dict:
    theme = web_theme(request.cookies.get(THEME_COOKIE))
    text = _copy(lang)
    other = "zh" if lang == "en" else "en"
    if not raw:
        raw_href = ""
    elif path == "/health":
        raw_href = "/health?format=json"
    elif lang == "en":
        raw_href = f"{path}?format=json&lang=en"
    else:
        raw_href = f"{path}?format=json"
    return {
        "html_lang": text["html_lang"],
        "theme": theme,
        "theme_title": text["theme_title"],
        "theme_to_dark": text["theme_to_dark"],
        "theme_to_light": text["theme_to_light"],
        "foot_note": text["foot_note"],
        "mark": text["mark"],
        "switch_href": f"{path}?lang={other}",
        "switch_label": text["switch_label"],
        "raw_href": raw_href,
        "raw_label": text["raw"],
        "home_label": text["home"],
    }


def _page(lang: str, path: str, **extra) -> str:
    view = {
        **_chrome(lang, path, raw=extra.pop("raw", True)),
        "lede": "",
        "aside": "",
        "note": "",
        "source": None,
        "source_label": "",
        "blocks": [],
    }
    view.update(extra)
    return render_template("reading.html", view=view)


def _names(pages: list, lang: str) -> str:
    payload = {"ui_lang": "en"} if lang == "en" else {}
    labels = [page_label(str(page), payload) for page in pages]
    return ", ".join(labels) if lang == "en" else "、".join(labels)


def _temp(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:g}°C"


def _clock(value: str) -> str:
    text = str(value or "")
    if "T" in text:
        return text.split("T", 1)[1][:5]
    return text


def render_unavailable(lang: str, kind: str) -> str:
    text = _copy(lang)
    path = {"weather": "/weather", "env": "/api/v1/dashboard.env"}.get(kind, "/api/v1/dashboard.json")
    title = text["weather_unavailable"] if kind == "weather" else text["unavailable"]
    return _page(
        lang,
        path,
        raw=False,
        title=title,
        lede=text["unavailable_body"],
        blocks=[],
    )


def render_dashboard(payload: dict, lang: str) -> str:
    text = _copy(lang)
    date = payload.get("date") or {}
    holiday = payload.get("holiday") or {}
    weather = (payload.get("weather") or {}).get("current") or {}
    sun = payload.get("sun") or {}
    term = date.get("solar_term") or {}
    aqi = payload.get("aqi") or {}
    quote = payload.get("quote") or {}
    festivals = date.get("festivals") or []
    date_rows = [
        {"label": text["generated"], "value": str(payload.get("generated_at") or "")},
        {"label": text["date"], "value": str(date.get("iso") or "")},
        {"label": text["weekday"], "value": str(date.get("weekday") or "")},
        {"label": text["lunar"], "value": " ".join(
            part for part in (str(date.get("lunar") or ""), str(date.get("ganzhi_year") or ""), str(date.get("zodiac") or "")) if part
        )},
    ]
    if festivals:
        date_rows.append({"label": text["festival"], "value": "、".join(str(item) for item in festivals)})
    if holiday:
        mark = " ".join(part for part in (str(holiday.get("name") or ""), str(holiday.get("note") or "")) if part)
        if mark:
            date_rows.append({"label": text["badge"], "value": mark})
    yi = [str(item) for item in (date.get("yi") or [])]
    ji = [str(item) for item in (date.get("ji") or [])]
    aqi_value = text["no_data"]
    if aqi:
        level = aqi.get("level_zh") or aqi.get("level") or ""
        aqi_value = " ".join(part for part in (str(aqi.get("us_aqi", "")), str(level)) if part)
    weather_href = "/weather?lang=en" if lang == "en" else "/weather"
    blocks = [
        {"type": "facts", "title": text["date"], "rows": date_rows},
        {
            "type": "pair",
            "left_title": text["suitable"],
            "left": yi,
            "right_title": text["avoid"],
            "right": ji,
            "empty": text["none"],
        },
        {
            "type": "facts",
            "title": text["solar"],
            "rows": [
                {"label": text["solar"], "value": str(term.get("name") or "")},
                {"label": text["days_label"], "value": text["days"].format(n=term.get("days_since", ""))},
                {"label": text["next_term"], "value": str(date.get("next_solar_term") or "")},
            ],
        },
        {
            "type": "facts",
            "title": text["weather_now"],
            "rows": [
                {"label": text["col_temp"], "value": _temp(weather.get("temperature"))},
                {"label": text["col_weather"], "value": str(weather.get("description") or "")},
            ],
        },
        {"type": "link", "href": weather_href, "label": text["hourly_link"]},
        {
            "type": "facts",
            "title": text["sun"],
            "rows": [
                {"label": text["sun"], "value": f"{sun.get('sunrise') or '—'} – {sun.get('sunset') or '—'}"},
                {"label": text["moon"], "value": str(sun.get("name") or "")},
            ],
        },
        {"type": "facts", "title": text["aqi"], "rows": [{"label": text["aqi"], "value": aqi_value}]},
        {
            "type": "prose",
            "title": text["quote"],
            "text": str(quote.get("text") or ""),
            "meta": str(quote.get("from") or ""),
        },
        {
            "type": "facts",
            "title": text["pages"],
            "rows": [
                {"label": text["enabled"], "value": _names(list(payload.get("pages") or []), lang)},
                {"label": text["version"], "value": str(payload.get("settings_version") or "")},
            ],
        },
    ]
    return _page(lang, "/api/v1/dashboard.json", title=str(payload.get("location") or text["mark"]), lede="", blocks=blocks)


def render_weather(payload: dict, lang: str) -> str:
    text = _copy(lang)
    weather = payload.get("weather") or {}
    current = weather.get("current") or {}
    daily_rows = [
        [str(day.get("date") or ""), str(day.get("description") or ""), _temp(day.get("temp_max")), _temp(day.get("temp_min"))]
        for day in weather.get("daily") or []
    ]
    hourly_rows = [
        [_clock(str(hour.get("time") or "")), _temp(hour.get("temperature")), f"{hour.get('precip', '')}%"]
        for hour in weather.get("hourly") or []
    ]
    blocks = [
        {
            "type": "facts",
            "title": text["weather_now"],
            "rows": [
                {"label": text["col_temp"], "value": _temp(current.get("temperature"))},
                {"label": text["col_weather"], "value": str(current.get("description") or "")},
                {"label": text["humidity"], "value": f"{current.get('humidity', '')}%"},
                {"label": text["wind"], "value": f"{current.get('wind_speed', '')} km/h"},
            ],
        },
        {
            "type": "table",
            "caption": text["daily"],
            "headers": [text["col_date"], text["col_weather"], text["col_high"], text["col_low"]],
            "rows": daily_rows,
        },
        {
            "type": "table",
            "caption": text["hourly"],
            "headers": [text["col_time"], text["col_temp"], text["col_precip"]],
            "rows": hourly_rows,
        },
    ]
    return _page(lang, "/weather", title=str(payload.get("location") or text["mark"]), lede="", blocks=blocks)


def render_health(info: dict, lang: str) -> str:
    text = _copy(lang)
    parts = [text["online"]]
    if info.get("has_weather"):
        age = info.get("weather_age_seconds")
        if age is None:
            parts.append(text["weather_ok"])
        else:
            parts.append(f"{text['weather_ok']} · {age} {text['seconds']}")
    else:
        parts.append(text["weather_bad"])
    if info.get("refreshing"):
        parts.append(text["refreshing"])
    blocks = [
        {
            "type": "facts",
            "title": text["health_title"],
            "rows": [
                {"label": text["screen"], "value": str(info.get("screen") or "")},
                {"label": text["city"], "value": str(info.get("location") or "")},
                {"label": text["version"], "value": str(info.get("settings_version") or "")},
                {"label": text["enabled"], "value": _names(list(info.get("pages") or []), lang)},
            ],
        }
    ]
    return _page(
        lang,
        "/health",
        title=text["health_title"],
        lede=" · ".join(parts),
        aside=str(info.get("last_error") or ""),
        blocks=blocks,
    )


def _env_map(source: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in source.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        found[key] = value
    return found


def render_env(source: str, lang: str) -> str:
    text = _copy(lang)
    mapping = _env_map(source)
    pages = [part for part in mapping.get("PAGES", "").split() if part]
    dwell_lines = []
    for page in pages:
        key = f"ROTATE_{page.upper()}_S"
        seconds = mapping.get(key)
        label = page_label(page, {"ui_lang": "en"} if lang == "en" else {})
        if seconds is None:
            dwell_lines.append(f"{label} {text['missing']}")
        else:
            dwell_lines.append(f"{label} {seconds} {text['seconds']}")
    rotate = mapping.get("ROTATE_ENABLED")
    if rotate == "1":
        rotate_label = text["on"]
    elif rotate == "0":
        rotate_label = text["off"]
    else:
        rotate_label = rotate or text["missing"]
    width = mapping.get("SCREEN_W")
    height = mapping.get("SCREEN_H")
    screen = f"{width} × {height}" if width and height else text["missing"]
    suppress = mapping.get("ROTATE_SUPPRESS_S")
    suppress_value = f"{suppress} {text['seconds']}" if suppress else text["missing"]
    declared = mapping.get("lang")
    url_count = sum(1 for line in source.splitlines() if "_URL=" in line)
    blocks = [
        {
            "type": "facts",
            "title": text["env_title"],
            "rows": [
                {"label": text["screen_size"], "value": screen},
                {"label": text["page_order"], "value": _names(pages, lang) or text["missing"]},
                {"label": text["rotate"], "value": rotate_label},
                {"label": text["dwell"], "value": "、".join(dwell_lines) if lang != "en" else ", ".join(dwell_lines)},
                {"label": text["suppress"], "value": suppress_value},
                {"label": text["version"], "value": mapping.get("SETTINGS_VERSION") or text["missing"]},
                {"label": text["language"], "value": declared or text["lang_unset"]},
                {"label": text["regions_label"], "value": text["regions"].format(n=url_count)},
            ],
        }
    ]
    return _page(
        lang,
        "/api/v1/dashboard.env",
        title=text["env_title"],
        lede="",
        note=text["heartbeat"],
        source=source,
        source_label=text["source"],
        blocks=blocks,
    )

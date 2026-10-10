"""界面语言。设备只看查询参数；网页按地址、Cookie、浏览器语言。无新增依赖。"""

from __future__ import annotations

import copy
import re

from server.weather import describe_weather

LANG_COOKIE = "kc_lang"
LANG_MAX_AGE = 31_536_000

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTHS_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_ZODIAC = {
    "鼠": "Rat",
    "牛": "Ox",
    "虎": "Tiger",
    "兔": "Rabbit",
    "龙": "Dragon",
    "蛇": "Snake",
    "马": "Horse",
    "羊": "Goat",
    "猴": "Monkey",
    "鸡": "Rooster",
    "狗": "Dog",
    "猪": "Pig",
}
_AQI = {
    "优": "Good",
    "良": "Moderate",
    "轻度敏感": "USG",
    "中度": "Unhealthy",
    "重度": "Very Unhealthy",
    "严重": "Hazardous",
}
_PAGE_EN = {"today": "Today", "week": "Week", "month": "Month", "detail": "Detail", "almanac": "Almanac"}

_EXACT = {
    "管理端未启用，请设置 ADMIN_PASSWORD": "Admin is off. Set ADMIN_PASSWORD",
    "请先登录": "Sign in first",
    "口令错误": "Wrong password",
    "缺少防护头": "Missing protection header",
    "失败次数过多，请稍后再试": "Too many attempts. Try again later",
    "配置校验失败": "Settings are invalid",
    "配置超过 32KB": "Settings are larger than 32KB",
    "配置写入失败，未改动": "Could not save settings. Nothing was changed",
    "导入文件过大或不是受支持的配置": "Import file is too large or not a supported settings file",
    "导入文件不是有效的 JSON": "Import file is not valid JSON",
    "导入文件的 schema_version 不受支持": "Import file schema_version is not supported",
    "配置必须是对象": "Settings must be an object",
    "请求体须为 JSON 对象": "Body must be a JSON object",
    "页面须恰好 5 项且覆盖全部页面": "There must be exactly 5 pages covering every page",
    "页面项格式不正确": "A page entry is invalid",
    "启用标记须为布尔值": "Enabled must be true or false",
    "页面须互不重复且覆盖今日、一周、月历、详情、黄历": "Pages must be unique and cover Today, Week, Month, Detail, and Almanac",
    "今日页必须固定在首位且保持启用": "Today must stay first and enabled",
    "轮播开关须为布尔值": "Carousel switch must be true or false",
    "一言来源无效": "Quote source is invalid",
    "自定义文案须为列表": "Custom quotes must be a list",
    "自定义模式至少需要一条文案": "Custom mode needs at least one quote",
    "文案项格式不正确": "A quote entry is invalid",
    "配置体积超过 32KB": "Settings are larger than 32KB",
    "城市信息不完整": "City details are incomplete",
    "纬度超出范围": "Latitude must be from -90 to 90",
    "纬度须在 -90 到 90 之间": "Latitude must be from -90 to 90",
    "经度超出范围": "Longitude must be from -180 to 180",
    "经度须在 -180 到 180 之间": "Longitude must be from -180 to 180",
    "时区无法识别": "Time zone is not recognized",
    "查询须为 1–50 字": "Search text must be 1–50 characters",
    "搜索服务暂不可用，请手动填写": "Search is unavailable. Enter the city manually",
}

_PATTERNS = (
    (re.compile(r"^停留秒数须为 (\d+)–(\d+) 的整数$"), "Dwell must be an integer from {0} to {1}"),
    (re.compile(r"^让位秒数须为 0–(\d+) 的整数$"), "Pause must be an integer from 0 to {0}"),
    (re.compile(r"^自定义文案最多 (\d+) 条$"), "At most {0} custom quotes"),
    (re.compile(r"^文案须为 1–(\d+) 字且不含换行$"), "Quote text must be 1–{0} characters and have no line break"),
    (re.compile(r"^出处最多 (\d+) 字且不含换行$"), "Source must be at most {0} characters and have no line break"),
    (re.compile(r"^城市名须为 1–(\d+) 字$"), "City name must be 1–{0} characters"),
)


def explicit_lang(raw: str | None) -> str | None:
    text = (raw or "").strip().lower().replace("_", "-")
    if text.startswith("en"):
        return "en"
    if text.startswith("zh"):
        return "zh"
    return None


def device_lang(raw: str | None) -> str:
    """设备与调试图。缺省、空、无法识别都是中文。"""
    return explicit_lang(raw) or "zh"


def _family(tag: str) -> str | None:
    if tag.startswith("en"):
        return "en"
    if tag.startswith("zh"):
        return "zh"
    return None


def lang_from_accept(header: str | None) -> str:
    best = "zh"
    best_q = -1.0
    seen = False
    for part in (header or "").split(","):
        bits = [bit.strip() for bit in part.split(";") if bit.strip()]
        if not bits:
            continue
        family = _family(bits[0].lower())
        if family is None:
            continue
        quality = 1.0
        for bit in bits[1:]:
            if bit.lower().startswith("q="):
                try:
                    quality = float(bit.split("=", 1)[1])
                except ValueError:
                    quality = 0.0
        if quality <= 0:
            continue
        seen = True
        if quality > best_q:
            best = family
            best_q = quality
    return best if seen else "zh"


def web_lang(explicit: str | None, cookie: str | None, accept_language: str | None) -> str:
    """地址里的 zh/en 优先，其次 Cookie，再是浏览器语言，最后中文。"""
    chosen = explicit_lang(explicit)
    if chosen:
        return chosen
    remembered = explicit_lang(cookie)
    if remembered:
        return remembered
    return lang_from_accept(accept_language)


def with_lang_query(url: str, lang: str) -> str:
    """只有英文才追加 lang=en。中文地址保持原样。"""
    if lang != "en" or "lang=" in url:
        return url
    return url + ("&lang=en" if "?" in url else "?lang=en")


def is_en(payload: dict | None) -> bool:
    return bool(payload) and payload.get("ui_lang") == "en"


def page_label(page: str, payload: dict) -> str:
    if is_en(payload):
        return _PAGE_EN.get(page, page)
    return {"today": "今日", "week": "一周", "month": "月历", "detail": "详情", "almanac": "黄历"}.get(page, page)


def short_date(iso: str) -> str:
    year, month, day = (int(part) for part in iso.split("-"))
    return f"{day} {_MONTHS_SHORT[month - 1]}"


def month_title(year: int, month: int) -> str:
    return f"{_MONTHS[month - 1]} {year}"


def weekday_en(index: int) -> str:
    return _WEEKDAYS[index % 7]


def zodiac_en(name: str) -> str:
    return _ZODIAC.get(name, name)


def aqi_en(level_zh: str) -> str:
    return _AQI.get(level_zh, level_zh)


def badge_en(note: str) -> str:
    if note == "休":
        return "Off"
    if note == "班":
        return "Work"
    return note


def localize_payload(payload: dict) -> dict:
    """英文载荷只改天气描述和语言标记。历法专名与一言保持原文。"""
    out = copy.deepcopy(payload)
    out["ui_lang"] = "en"
    weather = out.get("weather") or {}
    current = weather.get("current")
    if isinstance(current, dict) and "code" in current:
        current["description"] = describe_weather(int(current["code"]), "en")
    for day in weather.get("daily") or []:
        if isinstance(day, dict) and "code" in day:
            day["description"] = describe_weather(int(day["code"]), "en")
    return out


def translate_message(lang: str, message: str) -> str:
    if lang != "en" or not message:
        return message
    mapped = _EXACT.get(message)
    if mapped:
        return mapped
    for pattern, template in _PATTERNS:
        found = pattern.match(message)
        if found:
            return template.format(*found.groups())
    return message


def admin_ui(lang: str) -> dict:
    english = lang == "en"
    if english:
        text = {
            "html_lang": "en",
            "title": "Kindle Calendar · Admin",
            "disabled_h1": "Admin is off",
            "disabled_p": "Set the ADMIN_PASSWORD environment variable and restart.",
            "disabled_hint": "Docker: add ADMIN_PASSWORD to .env. Render: add it in Environment.",
            "h1": "Kindle Calendar · Admin",
            "login_prompt": "Enter the admin password",
            "password": "Password",
            "login": "Sign in",
            "version": "Version",
            "unsaved": "Unsaved",
            "logout": "Sign out",
            "degraded": "Settings file is missing or damaged. Defaults are in use; saving will recreate it.",
            "pages_h2": "Pages and carousel",
            "rotate": "Carousel",
            "only_today": "Today only: no carousel and no page turns",
            "suppress": "Seconds to pause the carousel after a touch",
            "loc_flag": "Weather will refresh after you save",
            "city_h2": "City",
            "geo_ph": "Search for a city, for example Hangzhou",
            "search": "Search",
            "city_name": "City name",
            "tz": "Time zone",
            "lat": "Latitude",
            "lon": "Longitude",
            "quote_h2": "Quote",
            "add_quote": "Add one",
            "device_h2": "Device",
            "preview_h2": "Preview",
            "preview_hint": "Preview shows the saved settings and updates after you save",
            "save": "Save",
            "reset": "Restore defaults",
            "export": "Export",
            "import_": "Import",
            "page_label": dict(_PAGE_EN),
            "quote_mode": {
                "online": "Online quote (falls back to offline verse)",
                "offline": "Offline verse",
                "custom": "Custom text",
            },
            "delivery": {"pending": "Pending", "delivered": "Delivered", "unknown": "Unknown"},
            "online": {"online": "Online", "offline": "Offline", "unknown": "Unknown"},
            "expired": "Sign-in expired. Sign in again",
            "source_ph": "Source",
            "need_quote": "Custom mode needs at least one quote",
            "showing": "Today shows item {n}: “{text}”",
            "rendering": "Rendering…",
            "device_unknown": ["Online —", "Last fetch —", "Delivery unknown", "Version —"],
            "last_fetch": "Last fetch {when}",
            "delivery_word": "Delivery",
            "eta": "Applies within {n} minutes",
            "version_line": "Version {v}",
            "device_versions": "Device {device} · current {current}",
            "just_now": "just now",
            "minutes_ago": "{n} minutes ago",
            "hours_ago": "{n} hours ago",
            "days_ago": "{n} days ago",
            "status_unavailable": "Status is unavailable",
            "dwell": "Dwell must be {min}–{max} seconds",
            "pause": "Pause must be 0–{max}",
            "name_len": "City name must be 1–20 characters",
            "lat_range": "Latitude is out of range",
            "lon_range": "Longitude is out of range",
            "need_tz": "Enter a time zone",
            "quote_len": "Quote text must be 1–{max} characters",
            "saved": "Saved. The device applies it within {n} minutes",
            "weather_later": ". Weather was not refreshed and will be tried again",
            "need_password": "Enter the password",
            "bad_password": "Wrong password",
            "login_failed": "Sign-in failed",
            "locked": "Too many attempts. Try again in {n} minutes",
            "save_failed": "Could not save",
            "confirm_reset": "Restore defaults?\nCity: {city}\nAll five pages on, 120/30",
            "reset_failed": "Could not restore defaults",
            "import_failed": "Import failed",
            "query_len": "Search text must be 1–50 characters",
            "searching": "Searching…",
            "no_city": "No matching city",
            "geo_failed": "Search is unavailable. Enter the city manually",
            "load_failed": "Could not load settings",
        }
    else:
        text = {
            "html_lang": "zh-CN",
            "title": "Kindle 台历 · 管理端",
            "disabled_h1": "管理端未启用",
            "disabled_p": "请在服务端设置环境变量 ADMIN_PASSWORD 后重启服务。",
            "disabled_hint": "Docker：.env 增加 ADMIN_PASSWORD=…；Render：Environment 面板添加。",
            "h1": "Kindle 台历 · 管理端",
            "login_prompt": "请输入管理员口令",
            "password": "口令",
            "login": "登录",
            "version": "版本",
            "unsaved": "未保存",
            "logout": "退出登录",
            "degraded": "配置文件缺失或损坏，当前为默认值运行；保存后将重新创建",
            "pages_h2": "页面与轮播",
            "rotate": "自动轮播",
            "only_today": "仅今日页：不轮播、无翻页",
            "suppress": "触摸后暂停轮播的秒数",
            "loc_flag": "保存后天气将重新拉取",
            "city_h2": "城市",
            "geo_ph": "搜索城市，例如杭州",
            "search": "搜索",
            "city_name": "城市名",
            "tz": "时区",
            "lat": "纬度",
            "lon": "经度",
            "quote_h2": "一言",
            "add_quote": "添加一条",
            "device_h2": "设备状态",
            "preview_h2": "预览",
            "preview_hint": "预览反映已保存配置，保存后更新",
            "save": "保存",
            "reset": "恢复默认",
            "export": "导出",
            "import_": "导入",
            "page_label": {"today": "今日", "week": "一周", "month": "月历", "detail": "详情", "almanac": "黄历"},
            "quote_mode": {
                "online": "在线一言（失败回退离线诗词）",
                "offline": "离线诗词",
                "custom": "自定义文案",
            },
            "delivery": {"pending": "待下发", "delivered": "已下发", "unknown": "未知"},
            "online": {"online": "在线", "offline": "离线", "unknown": "未知"},
            "expired": "登录已过期，请重新登录",
            "source_ph": "出处",
            "need_quote": "自定义模式至少需要一条文案",
            "showing": "今日将显示：第 {n} 条「{text}」",
            "rendering": "渲染中…",
            "device_unknown": ["在线 —", "最近拉取 —", "下发状态 未知", "版本 —"],
            "last_fetch": "最近拉取 {when}",
            "delivery_word": "下发",
            "eta": "预计最迟 {n} 分钟后生效",
            "version_line": "版本 {v}",
            "device_versions": "设备 {device} · 当前 {current}",
            "just_now": "刚刚",
            "minutes_ago": "{n} 分钟前",
            "hours_ago": "{n} 小时前",
            "days_ago": "{n} 天前",
            "status_unavailable": "状态暂不可用",
            "dwell": "停留须为 {min}–{max} 秒",
            "pause": "让位秒数须为 0–{max}",
            "name_len": "城市名须为 1–20 字",
            "lat_range": "纬度超出范围",
            "lon_range": "经度超出范围",
            "need_tz": "请填写时区",
            "quote_len": "文案须为 1–{max} 字",
            "saved": "已保存，设备最迟 {n} 分钟后生效",
            "weather_later": "。天气暂未更新，将稍后重试",
            "need_password": "请填写口令",
            "bad_password": "口令错误",
            "login_failed": "登录失败",
            "locked": "失败次数过多，请 {n} 分钟后再试",
            "save_failed": "保存失败",
            "confirm_reset": "恢复默认？\n城市：{city}\n五页全启用 120/30",
            "reset_failed": "恢复失败",
            "import_failed": "导入失败",
            "query_len": "查询须为 1–50 字",
            "searching": "搜索中…",
            "no_city": "没有匹配的城市",
            "geo_failed": "搜索服务暂不可用，请手动填写",
            "load_failed": "加载配置失败",
        }
    text["lang"] = "en" if english else "zh"
    return text

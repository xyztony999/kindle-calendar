"""界面语言。设备只看查询参数；网页按地址、Cookie、浏览器语言。无新增依赖。"""

from __future__ import annotations

import copy
import re

from server.weather import describe_weather

LANG_COOKIE = "kc_lang"
THEME_COOKIE = "kc_theme"
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
    "配置超过 64KB": "Settings are larger than 64KB",
    "配置体积超过 64KB": "Settings are larger than 64KB",
    "配置 schema 不受支持": "Settings schema is not supported",
    "页面数量须为 5–12，且包含全部预设页": "There must be 5 to 12 pages, including every preset page",
    "页面 id 无效": "Page id is invalid",
    "积木项格式不正确": "A block entry is invalid",
    "积木类型无效": "Block type is invalid",
    "系统积木的 id 须与类型相同": "A system block id must match its type",
    "积木 id 无效": "Block id is invalid",
    "积木位置或层次不正确": "Block position or layer is invalid",
    "积木须落在屏幕内且避开顶部状态栏": "Blocks must stay on screen and below the status bar",
    "积木尺寸过小": "Block is too small",
    "图片积木引用的素材不存在": "Image block points at a missing asset",
    "文字对齐无效": "Text alignment is invalid",
    "数据积木定义不存在或未通过审核": "Data block is missing or not approved",
    "素材列表格式不正确": "Asset list is invalid",
    "素材最多 30 个": "At most 30 assets",
    "素材项格式不正确": "An asset entry is invalid",
    "素材 id 无效或重复": "Asset id is invalid or duplicated",
    "素材对象键无效": "Asset key is invalid",
    "素材类型无效": "Asset type is invalid",
    "数据积木列表格式不正确": "Data block list is invalid",
    "数据积木格式不正确": "A data block entry is invalid",
    "数据积木 id 无效或重复": "Data block id is invalid or duplicated",
    "数据积木名称须为 1–20 字": "Data block name must be 1–20 characters",
    "数据积木版式无效": "Data block style is invalid",
    "数据积木字段无效": "Data block fields are invalid",
    "数据积木字段数量与版式不符": "Field count does not match the style",
    "布局须为列表": "Layout must be a list",
    "同一页积木 id 重复": "Duplicate block id on one page",
    "同一页每种系统积木只能有一块": "Only one of each system block per page",
    "时钟不能与其他积木重叠": "The clock cannot overlap another block",
    "未配置阿里云 OSS，暂时不能上传图片": "Aliyun OSS is not configured, so images cannot be uploaded",
    "服务器未安装 OSS 组件": "The OSS library is not installed",
    "图片须小于 2MB": "Image must be smaller than 2MB",
    "只接受 JPEG 或 PNG": "Only JPEG or PNG is accepted",
    "图片边长不能超过 4096": "Image edge must be at most 4096",
    "图片上传失败": "Image upload failed",
    "预览需要页面和布局": "Preview needs a page and a layout",
    "预览暂时画不出来": "Preview could not be drawn",
    "页面名称须为 1–20 字": "Page name must be 1–20 characters",
    "文字须为 1–200 字且不含换行": "Text must be 1–200 characters without line breaks",
    "数据积木最多 12 个": "At most 12 data blocks",
    "每页最多 24 块": "At most 24 blocks on a page",
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


def web_theme(cookie: str | None) -> str:
    """点过明暗按钮后记住的外观。只有 light / dark。其它值（含空、auto）表示跟随系统。"""
    value = (cookie or "").strip().lower()
    return value if value in ("light", "dark") else ""


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
    names = payload.get("page_names") if isinstance(payload, dict) else None
    if isinstance(names, dict) and names.get(page):
        return str(names[page])
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


def localize_payload(
    payload: dict,
    quote_mode: str = "online",
    custom: list | None = None,
    now=None,
    width: int = 758,
) -> dict:
    """英文载荷改天气描述、历法专名和一言。中文原文留在调用方的那一份里。"""
    from datetime import datetime

    from server.almanac_en import festival_en, ganzhi_pinyin, lunar_phrase, solar_term_en, wuhou_en, yiji_en
    from server.quotes import english_quote

    out = copy.deepcopy(payload)
    out["ui_lang"] = "en"
    weather = out.get("weather") or {}
    current = weather.get("current")
    if isinstance(current, dict) and "code" in current:
        current["description"] = describe_weather(int(current["code"]), "en")
    for day in weather.get("daily") or []:
        if isinstance(day, dict) and "code" in day:
            day["description"] = describe_weather(int(day["code"]), "en")

    date = out.get("date")
    if isinstance(date, dict):
        date["lunar"] = lunar_phrase(date.get("lunar") or "")
        date["ganzhi_year"] = ganzhi_pinyin(date.get("ganzhi_year") or "")
        term = date.get("solar_term")
        if isinstance(term, dict):
            term["name"] = solar_term_en(term.get("name") or "")
        if date.get("next_solar_term"):
            date["next_solar_term"] = solar_term_en(date["next_solar_term"])
        date["yi"] = yiji_en(date.get("yi") or [])
        date["ji"] = yiji_en(date.get("ji") or [])
        if date.get("wuhou"):
            date["wuhou"] = wuhou_en(date["wuhou"])
        date["festivals"] = [festival_en(name) for name in (date.get("festivals") or [])]

    holiday = out.get("holiday")
    if isinstance(holiday, dict) and holiday.get("name"):
        holiday["name"] = festival_en(holiday["name"])

    when = now
    if when is None:
        iso = (date or {}).get("iso") if isinstance(date, dict) else None
        when = datetime.fromisoformat(iso) if iso else datetime.now()
    out["quote"] = english_quote(when, quote_mode, custom, width)
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


def admin_ui(lang: str, theme: str = "") -> dict:
    if theme not in ("light", "dark"):
        theme = ""
    english = lang == "en"
    if english:
        text = {
            "html_lang": "en",
            "theme": theme,
            "site_name": "Kindle Calendar",
            "theme_title": "Theme",
            "theme_to_dark": "Switch to dark",
            "theme_to_light": "Switch to light",
            "switch_label": "中文",
            "login_title": "Admin Console",
            "title": "Kindle Calendar · Admin",
            "back_home": "Back to home",
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
            "add_page": "Add page",
            "edit_page": "Edit layout",
            "close_editor": "Done",
            "cancel_editor": "Cancel",
                        "settings_actions": "Settings actions",
            "saved_state": "All changes saved",
            "page_name_ph": "Page name",
            "delete_page": "Delete",
            "system_blocks": "System blocks",
            "my_blocks": "My blocks",
            "center_blocks": "Template center",
            "add_text": "Text",
            "upload_image": "Upload image",
            "new_data": "New data block",
            "widget_name": "Name",
            "style_hero": "Highlight first value",
            "style_rows": "Data list",
            "hero_help": "Up to 3 fields. The first value is large; others show names and values.",
            "rows_help": "Up to 6 fields. Each row shows a name and its value.",
            "first_field": "First field: {name} · Field-list order determines the first value",
                        "sample_temperature": "Temp",
            "sample_humidity": "Humidity",
            "manage_widget": "Manage {name}",
            "delete_widget_confirm": "Delete “{name}”? It will be removed from {n} pages. Cancel in the editor can undo this.",
            "save_widget": "Save block",
            "delete_widget": "Delete block",
            "rename_widget": "Rename",
            "image_asset": "Image asset",
            "widgets_h2": "My blocks",
            "add_data_widget": "New data block",
            "cancel_widget": "Cancel",
            "edit_widget": "Edit",
            "used_pages": "On {n} page(s)",
            "unused_widget": "Unused",
            "widget_fields_invalid": "Enter a name and pick 1-6 fields",
            "max_defs": "At most 12 data blocks",
            "image_assets_h2": "Image assets",
            "delete_asset": "Delete asset",
            "delete_asset_confirm": "Delete image asset {id}? It will be removed from {n} page(s) and erased from cloud storage after you save.",
            "manage_widgets": "Manage my blocks",
            "snap_align": "Snap",
            "snap_hint": "Snaps to margins and other blocks while dragging; hold Alt to disable; arrow keys nudge, Shift x10",
            "asset_discard_confirm": "Images uploaded in this session are unsaved and will be deleted if you cancel. Cancel anyway?",
            "week_mon": "Monday",
            "week_sun": "Sunday",
            "manage_back": "Back to blocks",
            "layer_up": "Move up a layer",
            "layer_down": "Move down a layer",
            "place_block": "Place",
            "align_label": "Align",
            "align_left": "Left",
            "align_center": "Center",
            "align_right": "Right",
            "font_size": "Font size",
            "presets_h2": "Layout presets",
            "save_preset": "Save current as preset",
            "preset_name_ph": "Preset name",
            "apply_preset": "Apply",
            "overwrite_preset": "Overwrite",
            "delete_preset_confirm": "Delete preset \"{name}\"?",
            "max_presets": "At most 8 presets",
            "preset_applied": "Preset \"{name}\" applied. Save to take effect",
            "preset_overwritten": "Preset \"{name}\" updated to the current layout",
            "schedule_h2": "Schedule and countdown",
            "ics_h2": "ICS subscription",
            "add_ics": "Add subscription link",
            "ics_ph": "https://…/calendar.ics",
            "ics_hint": "Links stay on this server only; refreshed every 6 hours; the last result is kept on failure.",
            "anniv_h2": "Anniversaries · countdown",
            "add_anniv": "Add anniversary",
            "anniv_name": "Name",
            "anniv_date": "Date",
            "repeat_none": "Once",
            "repeat_yearly": "Yearly",
            "repeat_lunar": "Lunar yearly",
            "days_left": "in {n} days",
            "days_today": "is today",
            "no_events": "No events today",
            "all_day": "All day",
            "tomorrow": "Tomorrow",
            "max_ics": "At most 3 links",
            "max_anniv": "At most 20 anniversaries",
            "no_countdowns": "No countdowns",
            "sources_h2": "Data sources",
            "source_weather": "Weather",
            "source_aqi": "AQI",
            "source_quote": "Quote",
            "source_ics": "ICS schedule",
            "source_ok": "OK",
            "source_fail": "Failed",
            "source_off": "Not configured",
            "source_never": "Never refreshed",
            "refresh_library": "Refresh library",
            "refresh_library_busy": "Refreshing…",
            "library_refresh_ok": "Library updated ({n} entries)",
            "library_refresh_fail": "Library refresh failed",
            "library_refreshing": "Refreshing library",
            "library_count_unit": "entries",
            "system_options_title": "Appearance options",
            "system_options_hint": "Hidden elements disappear from the canvas at once",
            "size_lg": "Large",
            "size_md": "Medium",
            "size_sm": "Small",
            "draft_preview": "Refresh preview",
            "preview_note": "Updates automatically · Unsaved · Preview does not apply changes to the device",
            "display_style": "Display style",
            "block_appearance": "Selected block appearance",
            "select_data_block": "No block selected",
            "fixed_style": "Fixed style",
            "appearance_scope": "{name} · Only this block on this page",
            "inherited_style": "Original layout: {name}",
            "current_style": "Current layout: {name}",
            "legacy_style": "This existing layout is preserved. Choose a compatible layout above to change it.",
            "text_style_reason": "These fields fit a list. Long text wraps within the block; resize it to show more.",
            "style_preview_help": "Choices match the selected fields. The canvas preview uses actual data; resize the block if needed.",
            "restore_block_style": "Restore original layout",
            "recommended": "Recommended for these fields",
            "clock_overlap": "The clock overlaps another block",
            "used": "In use",
            "remove_block": "Remove from page",
                        "text_ph": "Text on this page",
            "oss_missing": "Image upload needs Aliyun OSS on the server",
            "center_wait": "Not placeable yet",
            "max_pages": "At most 12 pages",
            "rotate": "Carousel",
            "only_today": "Today only: no carousel and no page turns",
            "suppress": "Seconds to pause the carousel after a touch",
            "loc_flag": "Weather will refresh after you save",
            "city_h2": "City",
            "geo_ph": "Search for a city, for example Hangzhou",
            "search": "Search",
                        "quote_plan": "Quote-library integration is planned.",
            "quote_format": "Library format",
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
                "library": "Local library (built-in, offline)",
                "online": "Online (hitokoto, with fallback)",
                "custom": "Custom text",
            },
            "quote_types": {
                "a": "Anime", "b": "Comics", "c": "Games", "d": "Literature", "e": "Original",
                "f": "Internet", "g": "Others", "h": "Movies", "i": "Poetry", "j": "Music",
                "k": "Philosophy", "l": "Humor",
            },
            "quote_types_need": "Pick at least one category",
            "delivery": {"pending": "Pending confirmation", "delivered": "Applied", "unknown": "Unknown"},
            "online": {"online": "Online", "offline": "Offline", "unknown": "Unknown"},
            "expired": "Sign-in expired. Sign in again",
            "source_ph": "Source",
            "need_quote": "Custom mode needs at least one quote",
            "showing": "Today shows item {n}: “{text}”",
            "rendering": "Rendering…",
            "device_unknown": ["Online —", "Last fetch —", "Delivery unknown", "Version —"],
            "last_fetch": "Last fetch {when}",
            "last_contact": "Last contact {when}",
            "last_applied": "Last confirmed {when}",
            "connection_word": "Connection",
            "device_mode": {"v1": "Full-image mode · Layout confirmation unavailable", "v2": "Region mode"},
                        "delivery_word": "Configuration",
            "eta": "Next contact expected in {n} minutes",
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
            "theme": theme,
            "site_name": "Kindle 台历",
            "theme_title": "主题",
            "theme_to_dark": "切换到深色",
            "theme_to_light": "切换到浅色",
            "switch_label": "English",
            "login_title": "管理端",
            "title": "Kindle 台历 · 管理端",
            "back_home": "返回首页",
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
            "add_page": "新增页面",
            "edit_page": "编辑版面",
            "close_editor": "完成",
            "cancel_editor": "取消",
                        "settings_actions": "配置操作",
            "saved_state": "所有更改已保存",
            "page_name_ph": "页面名称",
            "delete_page": "删除",
            "system_blocks": "系统积木",
            "my_blocks": "我的积木",
            "center_blocks": "模板中心",
            "add_text": "文字",
            "upload_image": "上传图片",
            "new_data": "新建数据积木",
            "widget_name": "名称",
            "style_hero": "突出首个数据",
            "style_rows": "逐行数据列表",
            "hero_help": "最多3项。首个值放大，其余显示名称与数值。",
            "rows_help": "最多6项。每行显示一个字段名称与数值。",
            "first_field": "首个字段：{name} · 按字段列表顺序确定首项",
                        "sample_temperature": "温度",
            "sample_humidity": "湿度",
            "manage_widget": "管理{name}",
            "delete_widget_confirm": "删除「{name}」？将从{n}个页面移除。编辑器内取消可撤销本次删除。",
            "save_widget": "保存积木",
            "delete_widget": "删除积木",
            "rename_widget": "重命名",
            "image_asset": "图片素材",
            "widgets_h2": "我的积木",
            "add_data_widget": "新建数据积木",
            "cancel_widget": "取消",
            "edit_widget": "编辑",
            "used_pages": "用于 {n} 个页面",
            "unused_widget": "未使用",
            "widget_fields_invalid": "名称必填，字段选 1–6 项",
            "max_defs": "最多 12 个数据积木",
            "image_assets_h2": "图片素材",
            "delete_asset": "删除素材",
            "delete_asset_confirm": "删除图片素材 {id}？将从 {n} 个页面移除；保存后从云端存储一并清除。",
            "manage_widgets": "管理我的积木",
            "snap_align": "对齐吸附",
            "snap_hint": "拖动时自动对齐边距与其他积木；按住 Alt 临时关闭；选中后方向键微调（Shift ×10）",
            "asset_discard_confirm": "本次上传的图片素材尚未保存，取消编辑将一并删除。仍要取消？",
            "week_mon": "周一",
            "week_sun": "周日",
            "manage_back": "返回放置",
            "layer_up": "上移一层",
            "layer_down": "下移一层",
            "place_block": "放置",
            "align_label": "对齐",
            "align_left": "左",
            "align_center": "中",
            "align_right": "右",
            "font_size": "字号",
            "presets_h2": "版面方案",
            "save_preset": "保存当前为方案",
            "preset_name_ph": "方案名称",
            "apply_preset": "应用",
            "overwrite_preset": "覆盖",
            "delete_preset_confirm": "删除方案「{name}」？",
            "max_presets": "最多 8 套方案",
            "preset_applied": "已应用方案「{name}」，保存后生效",
            "preset_overwritten": "方案「{name}」已更新为当前版面",
            "schedule_h2": "日程与倒计时",
            "ics_h2": "ICS 订阅",
            "add_ics": "添加订阅链接",
            "ics_ph": "https://…/calendar.ics",
            "ics_hint": "订阅链接只保存在本服务器；每 6 小时自动刷新，失败时沿用上次结果。",
            "anniv_h2": "纪念日 · 倒计时",
            "add_anniv": "添加纪念日",
            "anniv_name": "名称",
            "anniv_date": "日期",
            "repeat_none": "不重复",
            "repeat_yearly": "公历每年",
            "repeat_lunar": "农历每年",
            "days_left": "{n} 天后",
            "days_today": "就是今天",
            "no_events": "今日无日程",
            "all_day": "全天",
            "tomorrow": "明天",
            "max_ics": "最多 3 个订阅链接",
            "max_anniv": "最多 20 条纪念日",
            "no_countdowns": "暂无纪念日",
            "sources_h2": "数据源",
            "source_weather": "天气",
            "source_aqi": "AQI",
            "source_quote": "一言",
            "source_ics": "日程 ICS",
            "source_ok": "正常",
            "source_fail": "失败",
            "source_off": "未配置",
            "source_never": "从未刷新",
            "refresh_library": "刷新语料库",
            "refresh_library_busy": "刷新中…",
            "library_refresh_ok": "语料库已更新（{n} 条）",
            "library_refresh_fail": "语料库刷新失败",
            "library_refreshing": "语料刷新中",
            "library_count_unit": "条",
            "system_options_title": "外观选项",
            "system_options_hint": "关闭的元素立即从画面上隐藏",
            "size_lg": "大",
            "size_md": "中",
            "size_sm": "小",
            "draft_preview": "刷新预览",
            "preview_note": "自动更新 · 未保存 · 预览不会下发到设备",
            "display_style": "显示样式",
            "block_appearance": "当前积木外观",
            "select_data_block": "未选中积木",
            "fixed_style": "固定样式",
            "appearance_scope": "{name} · 仅当前页面中的这块积木",
            "inherited_style": "原有样式：{name}",
            "current_style": "当前样式：{name}",
            "legacy_style": "保留这块积木的旧版外观；选上方适用样式才会改变。",
            "text_style_reason": "这些字段适合列表。长文本会在积木内换行，可调大尺寸以显示更多。",
            "style_preview_help": "候选按所选字段筛选；画布预览使用真实数据，可调整积木尺寸。",
            "restore_block_style": "恢复原有样式",
            "recommended": "适合这些字段，推荐使用",
            "clock_overlap": "时钟与其他积木重叠",
            "used": "已使用",
            "remove_block": "从页面移除",
                        "text_ph": "这一页上的文字",
            "oss_missing": "上传图片需要服务器配置阿里云 OSS",
            "center_wait": "暂不可放置",
            "max_pages": "最多 12 页",
            "rotate": "自动轮播",
            "only_today": "仅今日页：不轮播、无翻页",
            "suppress": "触摸后暂停轮播的秒数",
            "loc_flag": "保存后天气将重新拉取",
            "city_h2": "城市",
            "geo_ph": "搜索城市，例如杭州",
            "search": "搜索",
                        "quote_plan": "语录库接入规划中。",
            "quote_format": "查看统一格式",
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
                "library": "本地语料库（内置，不联网）",
                "online": "在线一言（hitokoto，失败回退）",
                "custom": "自定义文案",
            },
            "quote_types": {
                "a": "动画", "b": "漫画", "c": "游戏", "d": "文学", "e": "原创",
                "f": "网络", "g": "其他", "h": "影视", "i": "诗词", "j": "网易云",
                "k": "哲学", "l": "抖机灵",
            },
            "quote_types_need": "至少选择一个分类",
            "delivery": {"pending": "待确认", "delivered": "已应用", "unknown": "未知"},
            "online": {"online": "在线", "offline": "离线", "unknown": "未知"},
            "expired": "登录已过期，请重新登录",
            "source_ph": "出处",
            "need_quote": "自定义模式至少需要一条文案",
            "showing": "今日将显示：第 {n} 条「{text}」",
            "rendering": "渲染中…",
            "device_unknown": ["在线 —", "最近拉取 —", "下发状态 未知", "版本 —"],
            "last_fetch": "最近拉取 {when}",
            "last_contact": "最近通信 {when}",
            "last_applied": "最近确认 {when}",
            "connection_word": "连接状态",
            "device_mode": {"v1": "整图模式 · 无分区布局确认", "v2": "分区模式"},
                        "delivery_word": "配置状态",
            "eta": "预计 {n} 分钟后再次通信",
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

"""浏览器落地页的语言选择与文案。无新增依赖。"""

from __future__ import annotations

_PAGES = (
    {"id": "today", "zh": "今日", "en": "Today", "zh_name": "今日页", "en_name": "Today", "frame": "TODAY"},
    {"id": "week", "zh": "一周", "en": "Week", "zh_name": "一周页", "en_name": "Week", "frame": "WEEK"},
    {"id": "month", "zh": "月历", "en": "Month", "zh_name": "月历页", "en_name": "Month", "frame": "MONTH"},
    {"id": "detail", "zh": "详情", "en": "Detail", "zh_name": "详情页", "en_name": "Detail", "frame": "DETAIL"},
    {"id": "almanac", "zh": "黄历", "en": "Almanac", "zh_name": "黄历页", "en_name": "Almanac", "frame": "ALMANAC"},
)

_ZH = {
    "title": "Kindle 电子天气台历",
    "description": "把闲置 Kindle 变成常亮的电子翻页天气台历。云端渲染，设备自行拉取。",
    "mark": "Kindle 台历",
    "admin": "管理端",
    "admin_cta": "配置页面与城市",
    "h1": "把闲置 Kindle<br>变成常亮台历",
    "lede": "云端把天气、农历和节假日画成灰度图，Kindle 只在画面变化时拉取。五页可翻：今日、一周、月历、详情、黄历。城市、页序和轮播在管理端改，设备下次拉取即生效。",
    "see": "看实机画面",
    "status_pending": "正在读取服务状态…",
    "pages_label": "台历页面",
    "rendering": "正在渲染{name}…",
    "alt": "{name}预览",
    "render_fail": "这一页暂时渲染不出来",
    "online": "服务在线",
    "screen": " · 画面 {screen}",
    "weather_ok": " · 天气已更新",
    "weather_bad": " · 天气暂不可用",
    "cards": (
        {"title": "五页一轮", "body": "今日看天气和时钟，一周看趋势，月历找假期，详情看逐时变化，黄历看宜忌。无触摸时按停留时间轮播。"},
        {"title": "分钟时钟不联网", "body": "数字在设备上本地拼装，每分钟只刷新时钟区域。天气分区按内容指纹变化才重新拉取。"},
        {"title": "浏览器里改配置", "body": "管理端可以调整启用的页面、每页停留、城市和页脚一言。口令只放在服务器环境变量里。"},
    ),
    "endpoints_heading": "接口",
    "raw_json": "原始 JSON",
    "credits": "开源组件",
}

_CREDITS_ZH = {
    "title": "开源组件 · Kindle 台历",
    "description": "本项目使用的开源库、数据来源与许可证说明。",
    "mark": "Kindle 台历",
    "h1": "开源组件",
    "lede": "Kindle 台历建立在众多开源项目与公开数据之上，在此一并致谢。许可以各上游项目最新声明为准。",
    "project_note": "本项目以 GPL-3.0 发布；内置一言语料筛选自 hitokoto.cn 开放句子库（AGPL-3.0，保留文件内署名字段）。",
    "groups": (
        {
            "title": "Python 依赖",
            "items": (
                {"name": "Flask", "license": "BSD-3-Clause", "note": "Web 框架与路由"},
                {"name": "Pillow", "license": "MIT-CMU", "note": "E-Ink 画面渲染"},
                {"name": "PyYAML", "license": "MIT", "note": "配置解析"},
                {"name": "Requests", "license": "Apache-2.0", "note": "天气、一言等 HTTP 拉取"},
                {"name": "tzdata", "license": "Apache-2.0", "note": "时区数据库"},
                {"name": "oss2", "license": "MIT", "note": "阿里云 OSS 图片素材存储"},
                {"name": "lunar-python", "license": "MIT", "note": "农历、干支与节气"},
                {"name": "icalendar", "license": "BSD-2-Clause", "note": "ICS 日历解析"},
                {"name": "recurring-ical-events", "license": "LGPL-3.0-or-later", "note": "重复日程（RRULE）展开"},
                {"name": "gunicorn", "license": "MIT", "note": "WSI 服务器"},
            ),
        },
        {
            "title": "数据与内容",
            "items": (
                {"name": "Open-Meteo", "license": "CC-BY-4.0（数据）", "note": "天气与空气质量数据", "url": "https://open-meteo.com"},
                {"name": "hitokoto.cn 开放句子库", "license": "AGPL-3.0", "note": "一言语料（筛选后内置）", "url": "https://github.com/hitokoto-osc/sentences-bundle"},
                {"name": "holiday-cn", "license": "MIT", "note": "中国法定节假日数据", "url": "https://github.com/NateScarlet/holiday-cn"},
            ),
        },
        {
            "title": "设备端与字体",
            "items": (
                {"name": "FBInk", "license": "GPL-3.0-or-later", "note": "E-Ink 绘制（独立二进制经命令行调用）", "url": "https://github.com/NiLuJe/FBInk"},
                {"name": "Noto Serif CJK", "license": "OFL-1.1", "note": "思源宋体（服务端渲染字体）", "url": "https://github.com/notofonts/noto-cjk"},
                {"name": "tapread", "license": "GPL-3.0", "note": "本项目自研的触摸事件读取工具"},
            ),
        },
    ),
}

_CREDITS_EN = {
    "title": "Open-source credits · Kindle Calendar",
    "description": "Libraries, data sources, and licenses used by this project.",
    "mark": "Kindle Calendar",
    "h1": "Open-source credits",
    "lede": "This project is built on many open-source projects and public datasets. Thank you all. Licenses follow each upstream project's latest statement.",
    "project_note": "This project is released under GPL-3.0. The built-in quote corpus is filtered from the hitokoto.cn open sentence library (AGPL-3.0; attribution fields preserved in the file).",
    "groups": (
        {
            "title": "Python packages",
            "items": (
                {"name": "Flask", "license": "BSD-3-Clause", "note": "Web framework and routing"},
                {"name": "Pillow", "license": "MIT-CMU", "note": "E-Ink page rendering"},
                {"name": "PyYAML", "license": "MIT", "note": "Configuration parsing"},
                {"name": "Requests", "license": "Apache-2.0", "note": "HTTP client for weather and quotes"},
                {"name": "tzdata", "license": "Apache-2.0", "note": "Time zone database"},
                {"name": "oss2", "license": "MIT", "note": "Aliyun OSS image storage"},
                {"name": "lunar-python", "license": "MIT", "note": "Lunar calendar, ganzhi, solar terms"},
                {"name": "icalendar", "license": "BSD-2-Clause", "note": "ICS calendar parsing"},
                {"name": "recurring-ical-events", "license": "LGPL-3.0-or-later", "note": "Recurring event (RRULE) expansion"},
                {"name": "gunicorn", "license": "MIT", "note": "WSGI server"},
            ),
        },
        {
            "title": "Data and content",
            "items": (
                {"name": "Open-Meteo", "license": "CC-BY-4.0 (data)", "note": "Weather and air quality", "url": "https://open-meteo.com"},
                {"name": "hitokoto.cn sentence library", "license": "AGPL-3.0", "note": "Quote corpus (filtered and bundled)", "url": "https://github.com/hitokoto-osc/sentences-bundle"},
                {"name": "holiday-cn", "license": "MIT", "note": "Chinese public holiday data", "url": "https://github.com/NateScarlet/holiday-cn"},
            ),
        },
        {
            "title": "Device side and fonts",
            "items": (
                {"name": "FBInk", "license": "GPL-3.0-or-later", "note": "E-Ink drawing (standalone binary, invoked via CLI)", "url": "https://github.com/NiLuJe/FBInk"},
                {"name": "Noto Serif CJK", "license": "OFL-1.1", "note": "Server-side rendering font", "url": "https://github.com/notofonts/noto-cjk"},
                {"name": "tapread", "license": "GPL-3.0", "note": "Touch event reader, developed in this project"},
            ),
        },
    ),
}

_EN = {
    "title": "Kindle weather calendar",
    "description": "Turn an idle Kindle into an e-ink weather calendar that stays on. The server renders the pages. The device pulls them.",
    "mark": "Kindle Calendar",
    "admin": "Admin",
    "admin_cta": "Set pages and city",
    "h1": "Turn an idle Kindle<br>into a calendar that stays on",
    "lede": "The server draws weather, the lunar calendar, and holidays as grayscale images. The Kindle downloads a region only when the picture changes. Five pages: Today, Week, Month, Detail, and Almanac. City, page order, and timing are set in Admin and apply on the next fetch.",
    "see": "See the pages",
    "status_pending": "Checking the service…",
    "pages_label": "Calendar pages",
    "rendering": "Rendering {name}…",
    "alt": "{name} preview",
    "render_fail": "This page could not be rendered",
    "online": "Service online",
    "screen": " · screen {screen}",
    "weather_ok": " · weather is current",
    "weather_bad": " · weather is unavailable",
    "cards": (
        {"title": "Five pages", "body": "Today is weather and the clock. Week is the trend. Month finds holidays. Detail is hour by hour. Almanac is the traditional day. Without touch, pages advance on a timer."},
        {"title": "A clock that stays offline", "body": "Digits are assembled on the device. Only the clock region refreshes each minute. Weather regions download again when their fingerprint changes."},
        {"title": "Change it in the browser", "body": "Admin sets which pages are on, how long each stays, the city, and the footer quote. The password lives only in the server environment."},
    ),
    "endpoints_heading": "Endpoints",
    "raw_json": "Raw JSON",
    "credits": "Open-source credits",
}

_EN_ENDPOINTS = {
    "/api/v1/dashboard.json": "Calendar JSON",
    "/api/v1/dashboard.env": "POSIX env for the device (five page regions and carousel)",
    "/r/<page>/<region>.png": "Page region image (today/week/month/detail/almanac)",
    "/r/today/clock/<glyph>.png": "Clock glyph (0-9 and colon)",
    "/dashboard.png?page=": "Full-page image (v1 compatible, default today)",
    "/admin": "Admin (password login)",
    "/credits": "Open-source credits",
    "/weather": "Current weather JSON",
    "/health": "Health check",
}


def resolve_landing_lang(explicit: str | None, accept_language: str | None = None, cookie: str | None = None) -> str:
    """网页语言。地址 zh/en，其次 Cookie，再是 Accept-Language，最后中文。"""
    from server.locale import web_lang

    return web_lang(explicit, cookie, accept_language)


def landing_copy(lang: str) -> dict:
    english = lang == "en"
    text = _EN if english else _ZH
    pages = [
        {
            "id": item["id"],
            "label": item["en" if english else "zh"],
            "name": item["en_name" if english else "zh_name"],
            "frame": item["frame"],
        }
        for item in _PAGES
    ]
    today = pages[0]
    return {
        **text,
        "lang": "en" if english else "zh",
        "html_lang": "en" if english else "zh-CN",
        "switch_href": "/?lang=zh" if english else "/?lang=en",
        "switch_label": "中文" if english else "English",
        "theme_to_dark": "Switch to dark" if english else "切换到深色",
        "theme_to_light": "Switch to light" if english else "切换到浅色",
        "preview_query": "&lang=en" if english else "",
        "pages": pages,
        "wait_today": text["rendering"].format(name=today["name"]),
        "alt_today": text["alt"].format(name=today["name"]),
        "ui": {
            "rendering": text["rendering"],
            "alt": text["alt"],
            "render_fail": text["render_fail"],
            "online": text["online"],
            "screen": text["screen"],
            "weather_ok": text["weather_ok"],
            "weather_bad": text["weather_bad"],
        },
    }


def credits_copy(lang: str) -> dict:
    english = lang == "en"
    text = _CREDITS_EN if english else _CREDITS_ZH
    return {
        **text,
        "lang": "en" if english else "zh",
        "html_lang": "en" if english else "zh-CN",
        "switch_href": "/credits?lang=zh" if english else "/credits?lang=en",
        "switch_label": "中文" if english else "English",
        "theme_to_dark": "Switch to dark" if english else "切换到深色",
        "theme_to_light": "Switch to light" if english else "切换到浅色",
    }


def endpoint_rows(lang: str, endpoints: dict[str, str]) -> list[dict[str, str]]:
    translated = _EN_ENDPOINTS if lang == "en" else {}
    return [{"path": path, "desc": translated.get(path, desc)} for path, desc in endpoints.items()]

"""自由画布：设计坐标、默认横条、字段白名单、布局校验。

坐标空间是 758×1024。渲染时再按设备分辨率缩放。
"""

from __future__ import annotations

import re
from typing import Any

from server.render.regions import BASE_H, BASE_W

STATUS_Y = 44
MARGIN_X = 56
CONTENT_W = BASE_W - 2 * MARGIN_X
MAX_PAGES = 12
MAX_BLOCKS = 24
MAX_DEFS = 12
BLOCK_TEXT_MAX = 200
MIN_FREE = 48
PRESET_IDS = ("today", "week", "month", "detail", "almanac")
SYSTEM_WIDGETS = (
    "header",
    "clock",
    "weather",
    "sun",
    "scene",
    "quote",
    "list",
    "chart",
    "title",
    "grid",
    "hourly",
    "indices",
    "main",
    "schedule",
    "countdown",
)
CUSTOM_PAGE_RE = re.compile(r"^c[0-9a-f]{8}$")
DEF_RE = re.compile(r"^w[0-9a-f]{8}$")
BLOCK_RE = re.compile(r"^b[0-9a-f]{8}$")
ASSET_RE = re.compile(r"^a[0-9a-f]{8}$")
CENTER_RE = re.compile(r"^center\.[a-z0-9][a-z0-9-]{0,32}$")
ASSET_KEY_RE = re.compile(r"^[A-Za-z0-9_./-]{1,200}$")
DATA_STYLES = ("hero", "rows", "horizontal", "grid")
ALIGNS = ("left", "center", "right")
TEXT_SIZES = ("lg", "md", "sm")
FORBIDDEN_CENTER_KEYS = {"script", "code", "url", "entry", "callback", "command", "href", "src"}

# 设计尺寸（宽, 高），与 regions.py 的横条一致。
DESIGN: dict[str, tuple[int, int]] = {
    "header": (CONTENT_W, 78),
    "clock": (CONTENT_W, 242),
    "weather": (CONTENT_W, 244),
    "sun": (CONTENT_W, 132),
    "scene": (CONTENT_W, 124),
    "quote": (CONTENT_W, 52),
    "list": (CONTENT_W, 490),
    "chart": (CONTENT_W, 290),
    "title": (CONTENT_W, 60),
    "grid": (CONTENT_W, 730),
    "hourly": (CONTENT_W, 430),
    "indices": (CONTENT_W, 350),
    "main": (CONTENT_W, 800),
    "schedule": (CONTENT_W, 244),
    "countdown": (CONTENT_W, 132),
}

_DEFAULT_BANDS: dict[str, list[tuple[str, int, int]]] = {
    "today": [
        ("header", 44, 122),
        ("clock", 130, 372),
        ("weather", 392, 636),
        ("sun", 656, 788),
        ("scene", 808, 932),
        ("quote", 948, 1000),
    ],
    "week": [
        ("header", 44, 122),
        ("list", 130, 620),
        ("chart", 640, 930),
        ("quote", 948, 1000),
    ],
    "month": [
        ("header", 44, 122),
        ("title", 130, 190),
        ("grid", 200, 930),
        ("quote", 948, 1000),
    ],
    "detail": [
        ("header", 44, 122),
        ("hourly", 130, 560),
        ("indices", 580, 930),
        ("quote", 948, 1000),
    ],
    "almanac": [
        ("header", 44, 122),
        ("main", 130, 930),
        ("quote", 948, 1000),
    ],
}

FIELD_DEFS: tuple[tuple[str, str, str], ...] = (
    ("weather.temperature", "当前温度", "Temperature"),
    ("weather.description", "天气描述", "Conditions"),
    ("weather.humidity", "湿度", "Humidity"),
    ("weather.wind_speed", "风速", "Wind"),
    ("weather.precip_prob", "降水概率", "Rain chance"),
    ("weather.temp_min", "今日最低温", "Today's low"),
    ("weather.temp_max", "今日最高温", "Today's high"),
    ("date.month_day", "公历月日", "Date"),
    ("date.weekday", "星期", "Weekday"),
    ("date.lunar", "农历", "Lunar date"),
    ("date.ganzhi", "干支年与生肖", "Year and zodiac"),
    ("date.solar_term", "节气", "Solar term"),
    ("date.festivals", "节日", "Festivals"),
    ("date.holiday", "假期", "Holiday"),
    ("sun.sunrise", "日出", "Sunrise"),
    ("sun.sunset", "日落", "Sunset"),
    ("sun.moon", "月相名", "Moon"),
    ("sun.illumination", "月面照亮比例", "Illumination"),
    ("aqi.value", "AQI 数值", "AQI"),
    ("aqi.level", "AQI 等级", "AQI level"),
    ("quote.text", "一言正文", "Quote"),
    ("quote.from", "一言出处", "Source"),
    ("almanac.yi", "宜", "Good for"),
    ("almanac.ji", "忌", "Avoid"),
    ("location.name", "地点名", "Place"),
    ("events.today_count", "今日日程数", "Events today"),
    ("events.next_title", "下一场日程", "Next event"),
    ("events.next_time", "下一场时间", "Next event time"),
)
FIELD_IDS = {item[0] for item in FIELD_DEFS}
_FIELD_LABEL = {item[0]: (item[1], item[2]) for item in FIELD_DEFS}

_NUMERIC_FIELDS = {"weather.temperature", "weather.humidity", "weather.wind_speed", "weather.precip_prob", "weather.temp_min", "weather.temp_max", "sun.illumination", "aqi.value", "events.today_count"}
_TIME_FIELDS = {"sun.sunrise", "sun.sunset", "events.next_time"}
_SHORT_FIELDS = {"weather.description", "date.weekday", "date.solar_term", "sun.moon", "aqi.level", "events.next_title"}
FIELD_KINDS = {field: ("number" if field in _NUMERIC_FIELDS else "time" if field in _TIME_FIELDS else "date" if field == "date.month_day" else "short_text" if field in _SHORT_FIELDS else "text") for field in FIELD_IDS}


def field_kind(field_id: str) -> str:
    return FIELD_KINDS.get(field_id, "text")


def data_style_catalog(lang: str = "zh") -> list[dict]:
    compact = ["number", "time", "date", "short_text"]
    primary = ["number", "time", "date"]
    labels = {
        "hero": ("突出首个数据", "首项放大，其余显示名称和数值。", "Large first value", "Enlarge the first value; label the remaining values."),
        "rows": ("逐行数据列表", "每行显示名称和数值，适合文字与混合内容。", "Labelled rows", "Label each value, including text and mixed content."),
        "horizontal": ("横向并列", "紧凑数据横向排列，数值在上、名称在下。", "Horizontal values", "Place compact values above their labels in equal columns."),
        "grid": ("数据网格", "将紧凑数据排列成多列网格。", "Value grid", "Arrange compact values in a grid."),
    }
    rules = {"hero": (1, 3, compact, primary), "rows": (1, 6, compact + ["text"], []), "horizontal": (2, 3, compact, []), "grid": (2, 6, compact, [])}
    result = []
    for style_id in DATA_STYLES:
        minimum, maximum, kinds, first = rules[style_id]
        text = labels[style_id]
        offset = 2 if lang == "en" else 0
        result.append({"id": style_id, "label": text[offset], "description": text[offset + 1], "min_fields": minimum, "max_fields": maximum, "allowed_kinds": list(kinds), "first_kinds": list(first)})
    return result


def applicable_data_styles(fields: list[str]) -> dict:
    """Stable field capabilities, independent of today's values or missing data."""
    kinds = [field_kind(field) for field in fields]
    styles = [rule["id"] for rule in data_style_catalog() if rule["min_fields"] <= len(fields) <= rule["max_fields"] and all(kind in rule["allowed_kinds"] for kind in kinds) and (not rule["first_kinds"] or kinds[0] in rule["first_kinds"])]
    preferred = "hero" if len(fields) == 1 else "horizontal" if len(fields) <= 3 else "grid"
    return {"styles": styles, "recommended": preferred if preferred in styles else "rows" if "rows" in styles else None}

SYSTEM_LABELS = {
    "header": ("页眉", "Header"),
    "clock": ("时钟", "Clock"),
    "weather": ("天气", "Weather"),
    "sun": ("日出月相", "Sun and moon"),
    "scene": ("场景", "Scene"),
    "quote": ("一言", "Quote"),
    "list": ("一周列表", "Week list"),
    "chart": ("一周曲线", "Week chart"),
    "title": ("月历标题", "Month title"),
    "grid": ("月历网格", "Month grid"),
    "hourly": ("逐时", "Hourly"),
    "indices": ("指数", "Indices"),
    "main": ("黄历", "Almanac"),
    "schedule": ("日程", "Schedule"),
    "countdown": ("倒计时", "Countdown"),
}

# 系统积木外观选项（有限可配）：key → (中文标签, 英文标签, 类型, 默认值, 选项枚举)
# type "bool" 为开关；"choice" 为单选档位。未配置 = 默认值 = 现有版式不变。
SYSTEM_OPTIONS: dict[str, dict[str, tuple[str, str, str, object, tuple | None]]] = {
    "header": {
        "show_tabs": ("页面指示点", "Page indicator dots", "bool", True, None),
        "show_lunar": ("农历与干支行", "Lunar and ganzhi line", "bool", True, None),
        "show_notes": ("节日与假期备注", "Festival and holiday notes", "bool", True, None),
    },
    "clock": {
        "size": ("数字大小", "Digit size", "choice", "lg", ("lg", "md", "sm")),
        "hour12": ("12 小时制（1-12 + AM/PM）", "12-hour clock (1-12 + AM/PM)", "bool", False, None),
    },
    "weather": {
        "show_humidity": ("湿度", "Humidity", "bool", True, None),
        "show_wind": ("风速", "Wind", "bool", True, None),
        "show_precip": ("降水概率", "Precipitation", "bool", True, None),
        "show_range": ("今日高低温", "Today's high and low", "bool", True, None),
        "show_icon": ("天气图标", "Weather icon", "bool", True, None),
    },
    "sun": {
        "show_arc": ("日出日落弧线", "Sun arc", "bool", True, None),
        "show_aqi": ("AQI 卡", "AQI card", "bool", True, None),
    },
    "quote": {
        "size": ("字号", "Font size", "choice", "md", ("lg", "md", "sm")),
    },
    "grid": {
        "show_badges": ("班休徽标", "Work/rest badges", "bool", True, None),
        "show_lunar": ("农历节气角标", "Lunar and term captions", "bool", True, None),
        "week_start": ("周起始日", "Week starts on", "choice", "mon", ("mon", "sun")),
        "show_event_dots": ("日程标记", "Event dots", "bool", False, None),
    },
    "main": {
        "show_yiji": ("宜忌双栏", "Yi/Ji columns", "bool", True, None),
        "show_wuhou": ("节气物候", "Solar term and phenology", "bool", True, None),
    },
    "schedule": {
        "show_tomorrow": ("显示明日", "Show tomorrow", "bool", False, None),
    },
    "countdown": {},
}
# 通用边框选项：paint_system 统一绘制；时钟走设备端字形拼装，边框无效，不提供
_BORDER_OPTION = ("显示边框", "Show border", "bool", False, None)
for _widget in SYSTEM_WIDGETS:
    if _widget != "clock":
        SYSTEM_OPTIONS.setdefault(_widget, {})["border"] = _BORDER_OPTION

CLOCK_SIZE_FACTOR = {"lg": 1.0, "md": 0.75, "sm": 0.55}


def system_options_catalog(widget: str, lang: str) -> list[dict]:
    """把某系统积木的选项 schema 输出为前端可用的列表。"""
    out: list[dict] = []
    for key, (zh, en, kind, default, choices) in SYSTEM_OPTIONS.get(widget, {}).items():
        item: dict = {"key": key, "label": en if lang == "en" else zh, "kind": kind, "default": default}
        if choices is not None:
            item["choices"] = list(choices)
        out.append(item)
    return out


def block_options(widget: str, raw: object) -> dict:
    """读取并收敛积木 options：非法值回退默认，输出仅含已知键。"""
    options: dict = {}
    schema = SYSTEM_OPTIONS.get(widget, {})
    if not isinstance(raw, dict):
        return options
    for key, (_zh, _en, kind, default, choices) in schema.items():
        value = raw.get(key)
        if kind == "bool":
            options[key] = default if not isinstance(value, bool) else value
        elif kind == "choice":
            options[key] = default if value not in (choices or ()) else value
    return options


def clock_rect_for_options(x: int, y: int, w: int, h: int, options: dict) -> tuple[int, int, int, int]:
    """时钟字号档位 → 调整后的字形矩形（居中收缩）。"""
    factor = CLOCK_SIZE_FACTOR.get(str(options.get("size") or "lg"), 1.0)
    if factor >= 1.0:
        return x, y, w, h
    nh = max(32, round(h * factor))
    return x, y + (h - nh) // 2, w, nh


def field_label(field_id: str, lang: str) -> str:
    zh, en = _FIELD_LABEL[field_id]
    return en if lang == "en" else zh


def system_label(widget: str, lang: str) -> str:
    zh, en = SYSTEM_LABELS[widget]
    return en if lang == "en" else zh


def default_layout(page_id: str) -> list[dict]:
    bands = _DEFAULT_BANDS.get(page_id)
    if not bands:
        return []
    layout = []
    for index, (widget, y0, y1) in enumerate(bands):
        layout.append(
            {
                "widget": widget,
                "id": widget,
                "x": MARGIN_X,
                "y": y0,
                "w": CONTENT_W,
                "h": y1 - y0,
                "z": index,
            }
        )
    return layout


def default_page(page_id: str, enabled: bool, dwell_s: int) -> dict:
    return {
        "page_id": page_id,
        "enabled": enabled,
        "dwell_s": dwell_s,
        "layout": default_layout(page_id),
    }


def _detail(field: str, code: str, message: str) -> dict:
    return {"field": field, "code": code, "message": message}


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or isinstance(value, str):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _intersects(a: dict, b: dict) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def _min_size(widget: str) -> tuple[int, int]:
    if widget in DESIGN:
        dw, dh = DESIGN[widget]
        return max(1, int(dw * 0.4)), max(1, int(dh * 0.4))
    return MIN_FREE, MIN_FREE


def accept_center_item(raw: Any) -> dict | None:
    """机器校验一条模板中心目录。不通过则丢弃，不执行其中任何载荷。"""
    if not isinstance(raw, dict):
        return None
    if FORBIDDEN_CENTER_KEYS.intersection(raw):
        return None
    if raw.get("review") != "approved":
        return None
    if raw.get("source") not in (None, "center"):
        return None
    item_id = raw.get("id")
    if not isinstance(item_id, str) or not CENTER_RE.match(item_id):
        return None
    kind = raw.get("kind")
    name = str(raw.get("name") or "").strip()
    if not name or len(name) > 20 or "\n" in name or "\r" in name:
        return None
    version = raw.get("version", 1)
    version_n = _as_int(version)
    if version_n is None or version_n < 1:
        return None
    if kind == "image":
        return {
            "id": item_id,
            "kind": "image",
            "source": "center",
            "review": "approved",
            "name": name,
            "version": version_n,
            "placeable": False,
        }
    if kind != "data":
        return None
    style = raw.get("style")
    fields = raw.get("fields")
    if style not in DATA_STYLES or not isinstance(fields, list):
        return None
    if any(not isinstance(field, str) or field not in FIELD_IDS for field in fields):
        return None
    limit = 3 if style == "hero" else 6
    if not 1 <= len(fields) <= limit:
        return None
    return {
        "id": item_id,
        "kind": "data",
        "source": "center",
        "review": "approved",
        "name": name,
        "style": style,
        "fields": list(fields),
        "version": version_n,
        "placeable": True,
    }


def _validate_block(
    block: Any,
    index: int,
    page_index: int,
    details: list[dict],
    asset_ids: set[str],
    def_ids: set[str],
    center_defs: set[str],
    definitions: dict[str, dict],
) -> dict | None:
    prefix = f"pages[{page_index}].layout[{index}]"
    if not isinstance(block, dict):
        details.append(_detail(prefix, "LAYOUT_INVALID", "积木项格式不正确"))
        return None
    widget = block.get("widget")
    if "style" in block and widget != "custom":
        details.append(_detail(f"{prefix}.style", "LAYOUT_INVALID", "仅数据积木允许设置外观"))
    if "options" in block:
        if widget not in SYSTEM_WIDGETS or not isinstance(block["options"], dict):
            details.append(_detail(f"{prefix}.options", "LAYOUT_INVALID", "仅系统积木可配置外观选项"))
        else:
            schema = SYSTEM_OPTIONS.get(str(widget), {})
            for key, value in block["options"].items():
                if key not in schema:
                    details.append(_detail(f"{prefix}.options.{key}", "LAYOUT_INVALID", "未知外观选项"))
                elif schema[key][2] == "bool" and not isinstance(value, bool):
                    details.append(_detail(f"{prefix}.options.{key}", "LAYOUT_INVALID", "开关选项须为布尔值"))
                elif schema[key][2] == "choice" and value not in (schema[key][4] or ()):
                    details.append(_detail(f"{prefix}.options.{key}", "LAYOUT_INVALID", "选项取值无效"))
    if widget not in SYSTEM_WIDGETS and widget not in ("image", "text", "custom"):
        details.append(_detail(f"{prefix}.widget", "LAYOUT_INVALID", "积木类型无效"))
        return None
    block_id = block.get("id")
    if widget in SYSTEM_WIDGETS:
        if block_id != widget:
            details.append(_detail(f"{prefix}.id", "LAYOUT_INVALID", "系统积木的 id 须与类型相同"))
    elif not isinstance(block_id, str) or not BLOCK_RE.match(block_id):
        details.append(_detail(f"{prefix}.id", "LAYOUT_INVALID", "积木 id 无效"))
    x, y, w, h = (_as_int(block.get(key)) for key in ("x", "y", "w", "h"))
    z = _as_int(block.get("z"))
    if None in (x, y, w, h, z) or w < 1 or h < 1 or z < 0 or z > 99:
        details.append(_detail(prefix, "LAYOUT_INVALID", "积木位置或层次不正确"))
        return None
    if x < 0 or y < STATUS_Y or x + w > BASE_W or y + h > BASE_H:
        details.append(_detail(prefix, "LAYOUT_INVALID", "积木须落在屏幕内且避开顶部状态栏"))
    min_w, min_h = _min_size(widget)
    if w < min_w or h < min_h:
        details.append(_detail(prefix, "LAYOUT_INVALID", "积木尺寸过小"))
    if widget == "image":
        asset = block.get("asset")
        if not isinstance(asset, str) or asset not in asset_ids:
            details.append(_detail(f"{prefix}.asset", "ASSET_INVALID", "图片积木引用的素材不存在"))
    if widget == "text":
        text = str(block.get("text") or "")
        if not text.strip() or len(text) > BLOCK_TEXT_MAX or "\n" in text or "\r" in text:
            details.append(_detail(f"{prefix}.text", "LAYOUT_INVALID", f"文字须为 1–{BLOCK_TEXT_MAX} 字且不含换行"))
        if block.get("align", "left") not in ALIGNS:
            details.append(_detail(f"{prefix}.align", "LAYOUT_INVALID", "文字对齐无效"))
        if block.get("size", "md") not in TEXT_SIZES:
            details.append(_detail(f"{prefix}.size", "LAYOUT_INVALID", "文字字号无效"))
    if widget == "custom":
        def_id = block.get("def")
        if not isinstance(def_id, str) or (def_id not in def_ids and def_id not in center_defs):
            details.append(_detail(f"{prefix}.def", "WIDGET_DEF_INVALID", "数据积木定义不存在或未通过审核"))
        if "style" in block:
            chosen = block["style"]
            definition = definitions.get(def_id) if isinstance(def_id, str) else None
            fields = definition.get("fields") if definition else None
            if not isinstance(chosen, str) or chosen not in DATA_STYLES:
                details.append(_detail(f"{prefix}.style", "LAYOUT_INVALID", "数据积木外观无效"))
            elif isinstance(fields, list) and all(isinstance(field, str) for field in fields) and chosen not in applicable_data_styles(fields)["styles"]:
                details.append(_detail(f"{prefix}.style", "LAYOUT_INVALID", "所选外观不适用于这些字段的数量或类型"))
    return {"x": x, "y": y, "w": w, "h": h, "widget": widget}


def validate_layout_fields(
    pages: list,
    widget_defs: list,
    assets: list,
    center_items: list[dict],
    details: list[dict],
) -> None:
    asset_ids: set[str] = set()
    if not isinstance(assets, list):
        details.append(_detail("assets", "ASSET_INVALID", "素材列表格式不正确"))
        assets = []
    elif len(assets) > 30:
        details.append(_detail("assets", "ASSET_INVALID", "素材最多 30 个"))
    for index, asset in enumerate(assets if isinstance(assets, list) else []):
        if not isinstance(asset, dict):
            details.append(_detail(f"assets[{index}]", "ASSET_INVALID", "素材项格式不正确"))
            continue
        asset_id = asset.get("id")
        key = asset.get("key")
        content_type = asset.get("content_type")
        if not isinstance(asset_id, str) or not ASSET_RE.match(asset_id) or asset_id in asset_ids:
            details.append(_detail(f"assets[{index}].id", "ASSET_INVALID", "素材 id 无效或重复"))
        elif isinstance(asset_id, str):
            asset_ids.add(asset_id)
        if not isinstance(key, str) or not ASSET_KEY_RE.match(key) or ".." in key:
            details.append(_detail(f"assets[{index}].key", "ASSET_INVALID", "素材对象键无效"))
        if content_type not in ("image/jpeg", "image/png"):
            details.append(_detail(f"assets[{index}].content_type", "ASSET_INVALID", "素材类型无效"))

    def_ids: set[str] = set()
    if not isinstance(widget_defs, list):
        details.append(_detail("widget_defs", "WIDGET_DEF_INVALID", "数据积木列表格式不正确"))
        widget_defs = []
    elif len(widget_defs) > MAX_DEFS:
        details.append(_detail("widget_defs", "WIDGET_DEF_INVALID", f"数据积木最多 {MAX_DEFS} 个"))
    for index, item in enumerate(widget_defs if isinstance(widget_defs, list) else []):
        prefix = f"widget_defs[{index}]"
        if not isinstance(item, dict):
            details.append(_detail(prefix, "WIDGET_DEF_INVALID", "数据积木格式不正确"))
            continue
        def_id = item.get("id")
        if not isinstance(def_id, str) or not DEF_RE.match(def_id) or def_id in def_ids:
            details.append(_detail(f"{prefix}.id", "WIDGET_DEF_INVALID", "数据积木 id 无效或重复"))
        else:
            def_ids.add(def_id)
        name = str(item.get("name") or "").strip()
        if not name or len(name) > 20 or "\n" in name or "\r" in name:
            details.append(_detail(f"{prefix}.name", "WIDGET_DEF_INVALID", "数据积木名称须为 1–20 字"))
        style = item.get("style")
        fields = item.get("fields")
        if style not in DATA_STYLES:
            details.append(_detail(f"{prefix}.style", "WIDGET_DEF_INVALID", "数据积木版式无效"))
            continue
        if not isinstance(fields, list) or any(not isinstance(field, str) or field not in FIELD_IDS for field in fields):
            details.append(_detail(f"{prefix}.fields", "WIDGET_DEF_INVALID", "数据积木字段无效"))
            continue
        limit = 3 if style == "hero" else 6
        if not 1 <= len(fields) <= limit:
            details.append(_detail(f"{prefix}.fields", "WIDGET_DEF_INVALID", "数据积木字段数量与版式不符"))

    approved_center = [accepted for item in center_items if (accepted := accept_center_item(item)) and accepted.get("kind") == "data" and accepted.get("placeable")]
    center_defs = {item["id"] for item in approved_center}
    definitions = {item["id"]: item for item in approved_center}
    definitions.update({item["id"]: item for item in widget_defs if isinstance(item, dict) and isinstance(item.get("id"), str)})
    if not isinstance(pages, list):
        return
    for page_index, page in enumerate(pages):
        if not isinstance(page, dict) or "layout" not in page:
            continue
        layout = page.get("layout")
        if not isinstance(layout, list):
            details.append(_detail(f"pages[{page_index}].layout", "LAYOUT_INVALID", "布局须为列表"))
            continue
        if len(layout) > MAX_BLOCKS:
            details.append(_detail(f"pages[{page_index}].layout", "LAYOUT_INVALID", f"每页最多 {MAX_BLOCKS} 块"))
        seen_system: set[str] = set()
        seen_ids: set[str] = set()
        placed: list[dict] = []
        for index, block in enumerate(layout):
            parsed = _validate_block(block, index, page_index, details, asset_ids, def_ids, center_defs, definitions)
            if not isinstance(block, dict):
                continue
            block_id = block.get("id")
            widget = block.get("widget")
            if isinstance(block_id, str):
                if block_id in seen_ids:
                    details.append(_detail(f"pages[{page_index}].layout[{index}].id", "LAYOUT_INVALID", "同一页积木 id 重复"))
                seen_ids.add(block_id)
            if widget in SYSTEM_WIDGETS:
                if widget in seen_system:
                    details.append(_detail(f"pages[{page_index}].layout[{index}]", "LAYOUT_INVALID", "同一页每种系统积木只能有一块"))
                seen_system.add(widget)
            if parsed is not None:
                placed.append(parsed)
        for block in placed:
            if block["widget"] != "clock":
                continue
            for other in placed:
                if other is block:
                    continue
                if _intersects(block, other):
                    details.append(_detail(f"pages[{page_index}].layout", "LAYOUT_INVALID", "时钟不能与其他积木重叠"))
                    break


def referenced_asset_ids(settings: dict) -> set[str]:
    found: set[str] = set()
    for page in settings.get("pages") or []:
        if not isinstance(page, dict):
            continue
        for block in page.get("layout") or []:
            if isinstance(block, dict) and block.get("widget") == "image" and isinstance(block.get("asset"), str):
                found.add(block["asset"])
    return found


def drop_unreferenced_assets(settings: dict) -> dict:
    used = referenced_asset_ids(settings)
    settings["assets"] = [item for item in settings.get("assets") or [] if item.get("id") in used]
    return settings


def scale_box(x: int, y: int, w: int, h: int, width: int, height: int) -> tuple[int, int, int, int]:
    sx, sy = width / BASE_W, height / BASE_H
    return round(x * sx), round(y * sy), max(1, round(w * sx)), max(1, round(h * sy))


def content_blank(width: int, height: int) -> tuple[int, int, int, int]:
    _x, y, _w, h = scale_box(0, STATUS_Y, BASE_W, BASE_H - STATUS_Y, width, height)
    return 0, y, width, h


def block_region_key(block: dict) -> str:
    widget = block["widget"]
    if widget in SYSTEM_WIDGETS:
        return widget
    return str(block["id"])


def iter_blocks(page: dict) -> list[dict]:
    layout = page.get("layout")
    if not isinstance(layout, list):
        layout = default_layout(page.get("page_id") or "")
    return sorted(
        [block for block in layout if isinstance(block, dict)],
        key=lambda block: int(block.get("z") or 0),
    )


def draw_region_keys(page: dict) -> list[str]:
    keys = ["pageblank"]
    for block in iter_blocks(page):
        if block.get("widget") == "clock":
            continue
        keys.append(block_region_key(block))
    return keys


def http_region_names(page: dict) -> list[str]:
    names = draw_region_keys(page)
    if "title" in names:
        names.extend(["title-prev", "title-next"])
    if "grid" in names:
        names.extend(["grid-prev", "grid-next"])
    return names


def find_block(page: dict, region: str) -> dict | None:
    base = region.split("-")[0] if region in ("title-prev", "title-next", "grid-prev", "grid-next") else region
    for block in iter_blocks(page):
        if block_region_key(block) == base:
            return block
    return None


def clock_block(page: dict) -> dict | None:
    for block in iter_blocks(page):
        if block.get("widget") == "clock":
            return block
    return None

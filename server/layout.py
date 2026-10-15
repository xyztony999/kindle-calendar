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
)
CUSTOM_PAGE_RE = re.compile(r"^c[0-9a-f]{8}$")
DEF_RE = re.compile(r"^w[0-9a-f]{8}$")
BLOCK_RE = re.compile(r"^b[0-9a-f]{8}$")
ASSET_RE = re.compile(r"^a[0-9a-f]{8}$")
CENTER_RE = re.compile(r"^center\.[a-z0-9][a-z0-9-]{0,32}$")
ASSET_KEY_RE = re.compile(r"^[A-Za-z0-9_./-]{1,200}$")
STYLES = ("hero", "rows")
ALIGNS = ("left", "center", "right")
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
)
FIELD_IDS = {item[0] for item in FIELD_DEFS}
_FIELD_LABEL = {item[0]: (item[1], item[2]) for item in FIELD_DEFS}

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
}


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
    if style not in STYLES or not isinstance(fields, list):
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
) -> dict | None:
    prefix = f"pages[{page_index}].layout[{index}]"
    if not isinstance(block, dict):
        details.append(_detail(prefix, "LAYOUT_INVALID", "积木项格式不正确"))
        return None
    widget = block.get("widget")
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
    if widget == "custom":
        def_id = block.get("def")
        if not isinstance(def_id, str) or (def_id not in def_ids and def_id not in center_defs):
            details.append(_detail(f"{prefix}.def", "WIDGET_DEF_INVALID", "数据积木定义不存在或未通过审核"))
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
        if style not in STYLES:
            details.append(_detail(f"{prefix}.style", "WIDGET_DEF_INVALID", "数据积木版式无效"))
            continue
        if not isinstance(fields, list) or any(not isinstance(field, str) or field not in FIELD_IDS for field in fields):
            details.append(_detail(f"{prefix}.fields", "WIDGET_DEF_INVALID", "数据积木字段无效"))
            continue
        limit = 3 if style == "hero" else 6
        if not 1 <= len(fields) <= limit:
            details.append(_detail(f"{prefix}.fields", "WIDGET_DEF_INVALID", "数据积木字段数量与版式不符"))

    center_defs = {item["id"] for item in center_items if item.get("kind") == "data" and item.get("placeable")}
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
            parsed = _validate_block(block, index, page_index, details, asset_ids, def_ids, center_defs)
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

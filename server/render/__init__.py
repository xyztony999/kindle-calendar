"""渲染包：五页面分区渲染、时钟字形、整页合成。

设备端经 env 契约按 (page, region) 拉取分区；月历页额外预裁上月/下月
（region 键 title-prev/grid-prev、title-next/grid-next）。
"""

from __future__ import annotations

from PIL import Image

from server.render.pages import almanac as _almanac_page
from server.render.pages import common, detail as _detail_page, month as _month_page, today, week as _week_page
from server.render.pages.today import render_glyphs
from server.render.regions import PAGES, Rect, clock_metrics, page_regions, today_regions

# 各页内容分区的渲染函数（quote 用公共共享资产）
_RENDERERS = {
    "today": {
        "header": today.render_header,
        "weather": today.render_weather,
        "sun": today.render_sun,
        "scene": today.render_scene_region,
        "quote": common.render_quote,
    },
    "week": {
        "header": lambda p, r, f: common.render_header(p, r, f, page="week"),
        "list": _week_page.render_list,
        "chart": _week_page.render_chart,
        "quote": common.render_quote,
    },
    "month": {
        "header": lambda p, r, f: common.render_header(p, r, f, page="month"),
        "title": lambda p, r, f: _month_page.render_title(p, r, f, offset=0),
        "title-prev": lambda p, r, f: _month_page.render_title(p, r, f, offset=-1),
        "title-next": lambda p, r, f: _month_page.render_title(p, r, f, offset=1),
        "grid": lambda p, r, f: _month_page.render_grid(p, r, f, offset=0),
        "grid-prev": lambda p, r, f: _month_page.render_grid(p, r, f, offset=-1),
        "grid-next": lambda p, r, f: _month_page.render_grid(p, r, f, offset=1),
        "quote": common.render_quote,
    },
    "detail": {
        "header": lambda p, r, f: common.render_header(p, r, f, page="detail"),
        "hourly": _detail_page.render_hourly,
        "indices": _detail_page.render_indices,
        "quote": common.render_quote,
    },
    "almanac": {
        "header": lambda p, r, f: common.render_header(p, r, f, page="almanac"),
        "main": _almanac_page.render_main,
        "quote": common.render_quote,
    },
}

# 设备端 env 下发的每页分区清单（月历的 title/grid 由设备按偏移月展开三预裁键）
PAGE_REGION_LISTS = {
    "today": ["header", "weather", "sun", "scene", "quote"],
    "week": ["header", "list", "chart", "quote"],
    "month": ["header", "title", "grid", "quote"],
    "detail": ["header", "hourly", "indices", "quote"],
    "almanac": ["header", "main", "quote"],
}

# (page, region) → 渲染键（月历偏移资产别名）
_REGION_ALIASES = {
    ("month", "grid-prev"): "grid-prev",
    ("month", "grid-next"): "grid-next",
    ("month", "title-prev"): "title-prev",
    ("month", "title-next"): "title-next",
}


def page_region_names(page: str) -> list[str]:
    """该页可经 HTTP 拉取的分区名全集。"""
    if page == "month":
        return list(_RENDERERS[page].keys())
    return PAGE_REGION_LISTS[page]


def render_page_regions(page: str, payload: dict, width: int, height: int, font_path: str) -> dict[str, Image.Image]:
    """渲染一页的全部分区（月历含三月预裁），键为分区渲染键。"""
    rects = page_regions(page, width, height)
    renderers = _RENDERERS[page]
    out: dict[str, Image.Image] = {}
    for key, fn in renderers.items():
        base = key.split("-")[0] if key in ("title-prev", "title-next", "grid-prev", "grid-next") else key
        out[key] = fn(payload, rects[base], font_path)
    return out


def compose_page(
    page: str,
    payload: dict,
    width: int,
    height: int,
    font_path: str,
    glyphs: dict[str, Image.Image] | None = None,
) -> Image.Image:
    """合成指定页整页（today 含时钟）。"""
    canvas = Image.new("L", (width, height), 0xFF)
    rects = page_regions(page, width, height)

    regions = PAGE_REGION_LISTS[page]
    rendered = render_page_regions(page, payload, width, height, font_path)
    for name in regions:
        rect = rects[name]
        canvas.paste(rendered[name], (rect.x, rect.y))

    if page == "today":
        if glyphs is None:
            glyphs = render_glyphs(clock_metrics(width, height), font_path)
        metrics = clock_metrics(width, height)
        x0 = (width - metrics.total_w()) // 2
        y0 = rects["clock"].y + (rects["clock"].h - metrics.digit_h) // 2
        hhmm = payload["clock"]["now"]
        x = x0
        for glyph in [hhmm[0], hhmm[1], ":", hhmm[3], hhmm[4]]:
            cell_w = metrics.colon_w if glyph == ":" else metrics.digit_w
            canvas.paste(glyphs[glyph], (x, y0))
            x += cell_w + metrics.gap
    return canvas


# ── 兼容旧入口（P1）──

def render_regions(payload: dict, width: int, height: int, font_path: str) -> dict[str, Image.Image]:
    return render_page_regions("today", payload, width, height, font_path)


def compose(payload: dict, width: int, height: int, font_path: str, glyphs=None) -> Image.Image:
    return compose_page("today", payload, width, height, font_path, glyphs)


__all__ = [
    "PAGES",
    "PAGE_REGION_LISTS",
    "page_region_names",
    "render_page_regions",
    "compose_page",
    "render_glyphs",
    "clock_metrics",
    "today_regions",
    "page_regions",
    "render_regions",
    "compose",
    "Rect",
]

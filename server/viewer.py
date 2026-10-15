"""三个图片地址的浏览器承载页。

设备（wget / Accept: */*）仍拿 PNG。浏览器声明要网页，或 format=html，才进入承载页。
format=png 强制原图。不看 User-Agent。分流与阅读页同一套 prefer_html。
"""

from __future__ import annotations

from flask import render_template, request

from server.locale import LANG_COOKIE, THEME_COOKIE, page_label, web_lang, web_theme
from server.reading import prefer_html

_ZH = {
    "html_lang": "zh-CN",
    "mark": "Kindle 台历",
    "theme_to_dark": "切换到深色",
    "theme_to_light": "切换到浅色",
    "home": "返回首页",
    "switch_label": "English",
    "raw": "查看原图",
    "note": "灰度图，与设备拉取的是同一张。",
    "missing": "找不到这张图",
    "glyph_title": "时钟字形",
    "region_title": "分区图",
    "page_title": "整页",
}

_EN = {
    "html_lang": "en",
    "mark": "Kindle Calendar",
    "theme_to_dark": "Switch to dark",
    "theme_to_light": "Switch to light",
    "home": "Back to home",
    "switch_label": "中文",
    "raw": "Raw image",
    "note": "Grayscale, the same image the device fetches.",
    "missing": "Image not found",
    "glyph_title": "Clock glyph",
    "region_title": "Region",
    "page_title": "Full page",
}


def viewer_wants_html() -> bool:
    """format=html 或 Accept 里写明要网页才进承载页。format=png 与 */* 为假。"""
    return prefer_html(request.args.get("format"), request.headers.get("Accept"))


def _page_lang() -> str:
    return web_lang(
        request.args.get("lang"),
        request.cookies.get(LANG_COOKIE),
        request.headers.get("Accept-Language"),
    )


def _self_href(
    kind: str,
    lang: str,
    *,
    page: str = "today",
    region: str = "",
    glyph: str = "",
    offset: int = 0,
    fmt: str = "html",
    force_lang: str | None = None,
) -> str:
    query: list[str] = []
    if kind == "page":
        path = "/dashboard.png"
        query.append(f"page={page}")
        if offset:
            query.append(f"offset={offset}")
    elif kind == "region":
        path = f"/r/{page}/{region}.png"
        if offset:
            query.append(f"offset={offset}")
    elif kind == "clock":
        path = f"/r/today/clock/{glyph}.png"
    else:
        path = request.path
    query.append(f"format={fmt}")
    if force_lang:
        query.append(f"lang={force_lang}")
    elif lang == "en":
        query.append("lang=en")
    return path + "?" + "&".join(query)


def _chrome(lang: str, switch_href: str) -> dict:
    text = _EN if lang == "en" else _ZH
    return {
        "html_lang": text["html_lang"],
        "theme": web_theme(request.cookies.get(THEME_COOKIE)),
        "theme_to_dark": text["theme_to_dark"],
        "theme_to_light": text["theme_to_light"],
        "mark": text["mark"],
        "switch_href": switch_href,
        "switch_label": text["switch_label"],
        "home_label": text["home"],
        "raw_label": text["raw"],
        "note": text["note"],
        "missing": False,
    }


def render_viewer(
    kind: str,
    *,
    page: str = "today",
    region: str = "",
    glyph: str = "",
    offset: int = 0,
) -> str:
    """kind 为 page、region 或 clock。只展示当前这一张图。"""
    lang = _page_lang()
    text = _EN if lang == "en" else _ZH
    other = "zh" if lang == "en" else "en"
    label = page_label(page, {"ui_lang": "en"} if lang == "en" else {})
    if kind == "page":
        title = f"{label} · {text['page_title']}"
    elif kind == "region":
        title = f"{label} · {region} · {text['region_title']}"
    else:
        title = f"{glyph} · {text['glyph_title']}"
    view = _chrome(
        lang,
        _self_href(kind, lang, page=page, region=region, glyph=glyph, offset=offset, fmt="html", force_lang=other),
    )
    view["title"] = title
    view["raw_link"] = _self_href(kind, lang, page=page, region=region, glyph=glyph, offset=offset, fmt="png")
    view["img_src"] = view["raw_link"]
    return render_template("viewer.html", view=view)


def render_viewer_missing() -> str:
    lang = _page_lang()
    text = _EN if lang == "en" else _ZH
    other = "zh" if lang == "en" else "en"
    view = _chrome(lang, _self_href("missing", lang, fmt="html", force_lang=other))
    view["title"] = text["missing"]
    view["missing"] = True
    view["note"] = text["missing"]
    view["raw_link"] = ""
    view["img_src"] = ""
    return render_template("viewer.html", view=view)

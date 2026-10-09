"""跨页公共分区：页眉（含页指示）与页脚一言。"""

from __future__ import annotations

from PIL import Image, ImageDraw

from server.render import style
from server.render.regions import PAGES, Rect

PAGE_LABELS = {"today": "今日", "week": "一周", "month": "月历", "detail": "详情", "almanac": "黄历"}


def _font(sx: float, base: int, font_path: str):
    return style.get_font(max(15, round(base * sx)), font_path)


def render_header(payload: dict, rect: Rect, font_path: str, page: str) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    date = payload["date"]
    holiday = payload.get("holiday")

    style.hairline(draw, 0, 2, rect.w)
    style.hairline(draw, 0, rect.h - 3, rect.w)

    f_big = _font(sx, 40, font_path)
    f_small = _font(sx, 22, font_path)
    f_page = _font(sx, 20, font_path)

    draw.text((2, 16), date["month_day_cn"], fill=style.INK, font=f_big)

    # 页指示（右上）：当前页实心，其余空心
    dot_r = 4
    dot_gap = int(46 * sx)
    labels_w = sum(style.tracked_width(draw, PAGE_LABELS[p], f_page, 2) + dot_gap for p in PAGES)
    x = rect.w - labels_w
    for p in PAGES:
        cx = x + dot_r
        cy = 16 + dot_r
        if p == page:
            draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=style.INK)
        else:
            draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), outline=style.RULE, width=1)
        style.draw_text(draw, (cx + dot_r + 4, 12), PAGE_LABELS[p], f_page, style.MID if p != page else style.INK, tracking=2)
        x += style.tracked_width(draw, PAGE_LABELS[p], f_page, 2) + dot_gap

    style.draw_text_right(draw, rect.w, 46, f"{date['lunar']} · {date['ganzhi_year']}{date['zodiac']}年", f_small, style.MID)
    weekday_line = f"星期{date['weekday']}"
    notes = list(date.get("festivals") or [])
    if holiday:
        notes.append(f"{holiday['name']}{holiday['note']}")
    if notes:
        weekday_line += " · " + " · ".join(notes[:2])
    style.draw_text_right(draw, int(rect.w - labels_w * 0.55), 16, weekday_line, f_small, style.INK)
    return img


def render_blank(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    """纯白底分区：进今日页时先铺在时钟区，盖掉上一页残留（字形只盖数字格，
    缝隙会漏旧内容）。"""
    return Image.new("L", (rect.w, rect.h), style.PAPER)


def render_quote(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    quote = payload["quote"]
    text = f"「{quote['text']}」"
    if quote.get("from"):
        text += f" ——{quote['from']}"

    # 长句自适应：字号从基准向下收缩直至放得下（最低 60%）
    size = 27
    f_quote = _font(sx, size, font_path)
    while size > 16 and style.tracked_width(draw, text, f_quote) > rect.w - 12:
        size -= 2
        f_quote = _font(sx, size, font_path)

    style.draw_text_center(
        draw, rect.w // 2, (rect.h - style.text_size(draw, text, f_quote)[1]) // 2, text, f_quote, style.MID
    )
    return img

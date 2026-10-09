"""黄历页：竖排大字日期 + 宜忌双栏 + 节气物候。"""

from __future__ import annotations

from PIL import Image, ImageDraw

from server.render import style
from server.render.regions import Rect


def _font(sx: float, base: int, font_path: str):
    return style.get_font(max(15, round(base * sx)), font_path)


def _draw_vertical(draw, x: int, y: int, text: str, font, fill: int) -> None:
    """竖排文字：逐字下排。"""
    cy = y
    for ch in text:
        _, ch_h = style.text_size(draw, ch, font)
        draw.text((x, cy), ch, fill=fill, font=font)
        cy += ch_h + 6


def render_main(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    date = payload["date"]

    f_big = _font(sx, 72, font_path)
    f_col = _font(sx, 30, font_path)
    f_item = _font(sx, 26, font_path)
    f_note = _font(sx, 24, font_path)

    # 左栏：竖排日期 + 农历
    left_w = int(170 * sx)
    draw.line((left_w, 8, left_w, rect.h - 8), fill=style.RULE, width=1)
    _draw_vertical(draw, int(28 * sx), int(20 * sx), date["month_day_cn"], f_big, style.INK)
    _draw_vertical(draw, int(112 * sx), int(26 * sx), date["lunar"], f_col, style.MID)
    _draw_vertical(draw, int(112 * sx), int(26 * sx) + (len(date["lunar"]) + 1) * int(44 * sx), f"{date['ganzhi_year']}{date['zodiac']}年", f_note, style.MID)

    # 右栏：宜 / 忌
    rx0 = left_w + int(24 * sx)
    col_w = (rect.w - rx0 - int(24 * sx)) // 2

    def draw_items(x: int, title: str, items: list[str], fill: int) -> None:
        draw.text((x, int(16 * sx)), title, fill=fill, font=f_col)
        style.hairline(draw, x, int(58 * sx), x + col_w - int(16 * sx))
        yy = int(76 * sx)
        for it in items[:6]:
            draw.text((x + int(6 * sx), yy), f"· {it}", fill=fill, font=f_item)
            yy += int(42 * sx)

    draw_items(rx0, "宜", date.get("yi") or [], style.INK)
    draw_items(rx0 + col_w + int(16 * sx), "忌", date.get("ji") or [], style.MID)

    # 底部：节气物候
    st = date["solar_term"]
    y0 = rect.h - int(150 * sx)
    style.hairline(draw, rx0, y0 - int(16 * sx), rect.w - int(16 * sx))
    draw.text((rx0, y0), f"节气 {st['name']} · 已过{st['days_since']}天 · 下一节气 {date.get('next_solar_term', '')}", fill=style.INK, font=f_note)
    draw.text((rx0, y0 + int(40 * sx)), f"物候 {date.get('wuhou', '')}", fill=style.MID, font=f_note)
    return img

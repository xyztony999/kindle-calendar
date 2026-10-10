"""月历页：月份标题 + 月历网格（农历角标/节气/节日/班休标注），支持上月/当月/下月预裁。"""

from __future__ import annotations

from datetime import date

from PIL import Image, ImageDraw

from server import almanac
from server.render import style
from server.render.regions import Rect

WEEKDAYS_CN = ["一", "二", "三", "四", "五", "六", "日"]


def _font(sx: float, base: int, font_path: str):
    return style.get_font(max(15, round(base * sx)), font_path)


def _shift_month(base: date, offset: int) -> date:
    total = base.year * 12 + (base.month - 1) + offset
    return date(total // 12, total % 12 + 1, 1)


def _month_cn(m: int) -> str:
    return {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二"}[m]


def render_title(payload: dict, rect: Rect, font_path: str, offset: int = 0) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    today = date.fromisoformat(payload["date"]["iso"])
    viewing = _shift_month(today, offset)

    f_title = _font(sx, 38, font_path)
    f_hint = _font(sx, 20, font_path)

    draw.text((2, 4), f"{today.year if viewing.year == today.year else viewing.year}年{_month_cn(viewing.month)}月", fill=style.INK, font=f_title)
    style.draw_text_right(draw, rect.w, 14, "‹ 上月      下月 ›", f_hint, style.MID)
    return img


def render_grid(payload: dict, rect: Rect, font_path: str, offset: int = 0) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    today = date.fromisoformat(payload["date"]["iso"])
    viewing = _shift_month(today, offset)
    grid = almanac.month_grid_info(viewing.year, viewing.month)

    header_h = int(rect.h * 0.07)
    n_weeks = len(grid["weeks"])
    row_h = (rect.h - header_h) // max(n_weeks, 1)
    col_w = rect.w // 7

    f_wd = _font(sx, 22, font_path)
    f_day = _font(sx, 30, font_path)
    f_sub = _font(sx, 19, font_path)

    # 表头（周一起始，周末 MID）
    for j, wd in enumerate(WEEKDAYS_CN):
        style.draw_text_center(draw, j * col_w + col_w // 2, 8, wd, f_wd, style.MID if j >= 5 else style.INK)

    style.hairline(draw, 0, header_h - 4, rect.w)

    for row, week in enumerate(grid["weeks"]):
        y0 = header_h + row * row_h
        for col, day in enumerate(week):
            if day == 0:
                continue
            info = grid["days"][day]
            x0 = col * col_w
            cx = x0 + col_w // 2
            is_weekend = col >= 5
            is_today = offset == 0 and day == today.day

            # 班休徽标：左上角（右上角会与两位数日期重叠）
            hol = info["holiday"]
            has_badge = hol is not None
            if has_badge:
                badge = hol["note"]
                bw, bh = int(30 * sx), int(24 * sx)
                bx = x0 + 4
                by = y0 + 2
                if hol["type"] == "holiday":
                    draw.rectangle((bx, by, bx + bw, by + bh), fill=style.INK)
                    style.draw_text_center(draw, bx + bw // 2, by + 1, badge, f_sub, style.PAPER)
                else:
                    draw.rectangle((bx, by, bx + bw, by + bh), outline=style.MID, width=2)
                    style.draw_text_center(draw, bx + bw // 2, by + 1, badge, f_sub, style.MID)

            # 公历数字：按真实宽度水平居中；有徽标时略下移避开左上角
            day_text = str(day)
            dw, dh = style.text_size(draw, day_text, f_day)
            dy = y0 + (34 if has_badge else 22)
            day_fill = style.MID if (is_weekend and not is_today) else style.INK
            draw.text((cx - dw // 2, dy), day_text, fill=day_fill, font=f_day)

            # 今日圈注：以数字实际包围盒为中心（而非行中心），保证套住数字
            if is_today:
                ncx = cx
                ncy = dy + dh // 2
                r = max(dw, dh) // 2 + int(9 * sx)
                draw.ellipse((ncx - r, ncy - r, ncx + r, ncy + r), outline=style.INK, width=3)

            # 角标文本：节气 > 节日 > 农历
            sub = info["jieqi"] or info["fest"] or info["lunar"]
            sub_fill = style.INK if (info["jieqi"] or info["fest"]) else style.MID
            style.draw_text_center(draw, cx, y0 + row_h - int(34 * sx), sub, f_sub, sub_fill)

        if row < n_weeks - 1:
            style.hairline(draw, 0, y0 + row_h, rect.w, style.RULE)
    return img

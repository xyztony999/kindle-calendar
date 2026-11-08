"""一周页：七天列表 + 高低温趋势曲线。"""

from __future__ import annotations

from datetime import date

from PIL import Image, ImageDraw

from server.icons import draw_weather_icon
from server.locale import is_en, weekday_en
from server.render import style
from server.render.regions import Rect
from server.units import fmt_temp

WEEKDAYS_CN = ["一", "二", "三", "四", "五", "六", "日"]


def _font(sx: float, base: int, font_path: str):
    return style.get_font(max(15, round(base * sx)), font_path)


def _drop(draw: ImageDraw.ImageDraw, x: int, cy: int, size: int, fill: int) -> None:
    """小水滴（降水概率前缀）：圆底 + 尖顶，纯几何绘制，不依赖字体里的符号。"""
    r = size // 2
    bottom = cy + r
    draw.ellipse((x, bottom - size, x + size, bottom), fill=fill)
    draw.polygon([(x + r, bottom - int(size * 1.6)), (x + 1, bottom - r - 1), (x + size - 1, bottom - r - 1)], fill=fill)


def render_list(payload: dict, rect: Rect, font_path: str, options: dict | None = None) -> Image.Image:
    opts = options or {}
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    daily = payload["weather"]["daily"][: 5 if str(opts.get("days")) == "5" else 7]
    row_h = rect.h // max(len(daily), 1)
    show_icon = opts.get("show_icon", True)
    show_precip = opts.get("show_precip", False)
    f_day = _font(sx, 30, font_path)
    f_temp = _font(sx, 28, font_path)
    f_desc = _font(sx, 24, font_path)
    f_date = _font(sx, 20, font_path)  # 日期小字：24px 时 descender 会压出今日行框

    today_iso = payload["date"]["iso"]
    for i, d in enumerate(daily):
        y0 = i * row_h
        is_today = d["date"] == today_iso
        if is_today:
            # 右/下边界收 1px：坐标等于分区宽高时 PIL 画线越界被裁，框会缺边
            draw.rectangle((0, y0 + 2, rect.w - 1, y0 + row_h - 4), outline=style.RULE, width=1)

        # 左：周几 + 日期（双行收进框内：date 底 ≈ y0+40+26 < 框底 y0+66）
        # 星期必须从日期计算——forecast 首行为今天，行号推星期会整体错位
        mday = d["date"][5:7].lstrip("0") or "0"
        dday = d["date"][8:10].lstrip("0") or "0"
        if is_en(payload):
            label = "Today" if is_today else weekday_en(date.fromisoformat(d["date"]).weekday())
        else:
            wd = WEEKDAYS_CN[date.fromisoformat(d["date"]).weekday()]
            label = "今天" if is_today else f"周{wd}"
        draw.text((10, y0 + row_h // 2 - 32), label, fill=style.INK, font=f_day)
        draw.text((10, y0 + row_h // 2 + 4), f"{mday}/{dday}", fill=style.MID, font=f_date)

        # 中：天气图标 + 描述（图标尺寸以 7 天行高为上限：5 天行更高时图标不放大、不压描述）
        if show_icon:
            icon_size = min(row_h, rect.h // 7) - 26
            draw_weather_icon(draw, d["code"], int(150 * sx + icon_size // 2), y0 + row_h // 2, icon_size)
            desc_x = int(200 * sx)
        else:
            desc_x = int(150 * sx)
        draw.text((desc_x, y0 + row_h // 2 - 14), d["description"], fill=style.INK, font=f_desc)

        # 右：高低温；降水概率与之同行、在其左侧（7 天行高仅 70px，放不下第二行）
        temp_line = f"{fmt_temp(d['temp_max'], payload)} / {fmt_temp(d['temp_min'], payload)}"
        style.draw_text_right(draw, rect.w - 12, y0 + row_h // 2 - 16, temp_line, f_temp, style.INK)
        prob = d.get("precip_prob")
        if show_precip and isinstance(prob, (int, float)) and not isinstance(prob, bool):
            text = f"{int(prob)}%"
            right = rect.w - 12 - style.text_size(draw, temp_line, f_temp)[0] - int(22 * sx)
            text_w = style.text_size(draw, text, f_desc)[0]
            style.draw_text_right(draw, right, y0 + row_h // 2 - 14, text, f_desc, style.MID)
            size = max(8, int(12 * sx))
            _drop(draw, right - text_w - size - int(5 * sx), y0 + row_h // 2 - 1, size, style.MID)

        if i < len(daily) - 1:
            style.hairline(draw, 12, y0 + row_h, rect.w - 12, style.RULE)
    return img


def render_chart(payload: dict, rect: Rect, font_path: str, options: dict | None = None) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    daily = payload["weather"]["daily"][: 5 if str((options or {}).get("days")) == "5" else 7]
    if not daily:
        return img

    f_label = _font(sx, 20, font_path)
    pad_l, pad_r, pad_t, pad_b = int(30 * sx), int(30 * sx), int(44 * sx), int(36 * sx)
    plot_w = rect.w - pad_l - pad_r
    plot_h = rect.h - pad_t - pad_b

    highs = [d["temp_max"] for d in daily]
    lows = [d["temp_min"] for d in daily]
    t_max, t_min = max(highs), min(lows)
    span = max(t_max - t_min, 1.0)

    def px(i: int) -> int:
        return pad_l + plot_w * i // max(len(daily) - 1, 1)

    def py(t: float) -> int:
        return pad_t + plot_h - int((t - t_min) / span * plot_h)

    # 网格线（上下边界）
    style.hairline(draw, pad_l, pad_t + plot_h, rect.w - pad_r, style.RULE)
    style.hairline(draw, pad_l, pad_t, rect.w - pad_r, 236)

    # 高低温双曲线
    draw.line([(px(i), py(highs[i])) for i in range(len(daily))], fill=style.INK, width=3)
    draw.line([(px(i), py(lows[i])) for i in range(len(daily))], fill=style.MID, width=3)

    today_iso = payload["date"]["iso"]
    # 日期刻度行的墨水顶：低温标注若会压到它（该点恰是一周最低时必然发生），改放到点的上方
    date_top = draw.textbbox((0, int(rect.h - pad_b + 10 * sx)), "0", font=f_label)[1]
    for i, d in enumerate(daily):
        is_today = d["date"] == today_iso
        r = 6 if is_today else 4
        draw.ellipse((px(i) - r, py(highs[i]) - r, px(i) + r, py(highs[i]) + r), fill=style.INK if is_today else style.PAPER, outline=style.INK, width=2)
        draw.ellipse((px(i) - r, py(lows[i]) - r, px(i) + r, py(lows[i]) + r), fill=style.MID if is_today else style.PAPER, outline=style.MID, width=2)
        # 温度标注（首尾与今日）
        if i == 0 or i == len(daily) - 1 or is_today:
            h_txt = fmt_temp(d["temp_max"], payload)
            l_txt = fmt_temp(d["temp_min"], payload)
            style.draw_text_center(draw, px(i), py(highs[i]) - 34 * sx, h_txt, f_label, style.INK)
            low_y = py(lows[i]) + 12 * sx
            if draw.textbbox((0, int(low_y)), l_txt, font=f_label)[3] > date_top - 2:
                low_y = py(lows[i]) - r - 4 - draw.textbbox((0, 0), l_txt, font=f_label)[3]
            style.draw_text_center(draw, px(i), low_y, l_txt, f_label, style.MID)
        # 日期刻度
        label = d["date"][8:10].lstrip("0")
        style.draw_text_center(draw, px(i), rect.h - pad_b + 10 * sx, label, f_label, style.MID)
    return img

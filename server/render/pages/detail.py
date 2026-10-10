"""详情页：24 小时温度与降水 + 生活指数卡。"""

from __future__ import annotations

from PIL import Image, ImageDraw

from server.render import style
from server.render.regions import Rect


def _font(sx: float, base: int, font_path: str):
    return style.get_font(max(15, round(base * sx)), font_path)


def render_hourly(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    hourly = payload["weather"]["hourly"][:24]
    if not hourly:
        return img

    f_label = _font(sx, 20, font_path)
    pad_t, pad_b = int(40 * sx), int(50 * sx)
    plot_h = rect.h - pad_t - pad_b
    temps = [h["temperature"] for h in hourly]
    t_max, t_min = max(temps), min(temps)
    span = max(t_max - t_min, 1.0)
    n = len(hourly)
    bar_w = max(6, int(rect.w / n * 0.5))
    step = rect.w / n

    style.hairline(draw, 8, rect.h - pad_b, rect.w - 8, style.RULE)

    for i, h in enumerate(hourly):
        cx = int(step * (i + 0.5))
        bh = int((h["temperature"] - t_min) / span * (plot_h - 20)) + 12
        x0 = cx - bar_w // 2
        y1 = rect.h - pad_b - 2
        draw.rectangle((x0, y1 - bh, x0 + bar_w, y1), fill=style.LIGHT, outline=style.MID, width=1)

        # 时间刻度（每 6 小时）
        if i % 6 == 0:
            hh = h["time"][11:13]
            style.draw_text_center(draw, cx, rect.h - pad_b + 12, f"{hh}时", f_label, style.MID)

        # 降水概率 ≥30% 标注
        if h["precip"] >= 30:
            draw.ellipse((cx - 3, y1 - bh - 12, cx + 3, y1 - bh - 6), fill=style.INK)
            if h["precip"] >= 50:
                style.draw_text_center(draw, cx, y1 - bh - 36, f"{h['precip']}%", f_label, style.INK)

    # 首尾温度标注
    for idx in (0, n - 1):
        cx = int(step * (idx + 0.5))
        ty = rect.h - pad_b - 2 - int((temps[idx] - t_min) / span * (plot_h - 20)) - 12 - 28
        style.draw_text_center(draw, cx, max(4, ty), f"{temps[idx]:.0f}°", f_label, style.INK)
    return img


def render_indices(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    cur = payload["weather"]["current"]
    sun = payload["sun"]
    aqi = payload.get("aqi")
    aqi_val = f"{aqi['us_aqi']} {aqi['level_zh']}" if aqi else "暂无数据"
    cards = [
        ("湿度", f"{cur['humidity']}%"),
        ("风速", f"{cur['wind_speed']:.0f} km/h"),
        ("降水概率", f"{payload['weather'].get('precip_prob', 0)}%"),
        ("日出", sun["sunrise"]),
        ("日落", sun["sunset"]),
        ("AQI", aqi_val),
    ]

    f_key = _font(sx, 22, font_path)
    f_val = _font(sx, 40, font_path)

    cols, gap = 2, int(16 * sx)
    # 网格整体收 2px：末列/末排边线坐标若等于分区宽高会越界被裁（框缺边）
    card_w = (rect.w - gap - 2) // cols
    rows = (len(cards) + cols - 1) // cols
    card_h = (rect.h - gap * (rows - 1) - 2) // rows

    for i, (key, val) in enumerate(cards):
        r, c = divmod(i, cols)
        x0 = c * (card_w + gap)
        y0 = r * (card_h + gap)
        draw.rectangle((x0, y0, x0 + card_w, y0 + card_h), outline=style.RULE, width=1)
        draw.text((x0 + int(20 * sx), y0 + int(16 * sx)), key, fill=style.MID, font=f_key)
        style.draw_text_right(draw, x0 + card_w - int(20 * sx), y0 + card_h - int(56 * sx), val, f_val, style.INK)
    return img

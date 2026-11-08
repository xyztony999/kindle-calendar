"""详情页：逐时温度与降水（柱形/折线/面积）+ 可自选项目的指数卡。"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

from server.advice import ADVICE_KEYS, advice_text, uv_level, uv_today
from server.indices import DEFAULT_INDEX_ITEMS, INDEX_ITEMS, INDEX_MAX
from server.locale import is_en
from server.render import style
from server.render.regions import Rect
from server.units import aqi_view, fmt_int, fmt_pressure, fmt_temp, fmt_visibility, fmt_wind, fmt_wind_dir

DASH = "—"
_INDEX_LABELS = {key: (zh, en) for key, zh, en in INDEX_ITEMS}


def _font(sx: float, base: int, font_path: str):
    return style.get_font(max(15, round(base * sx)), font_path)


def _text_center_clamped(draw: ImageDraw.ImageDraw, width: int, cx: int, y: int, text: str, font, fill: int, halo: bool = False) -> None:
    """居中绘制，但整段文字钳制在分区内（首尾柱心离边缘过近时不被裁掉）。
    halo：先铺一圈纸色衬底，折线/面积图里线条穿过标注时文字仍清晰。"""
    tw = style.tracked_width(draw, text, font)
    cx = min(max(cx, tw // 2 + 2), width - tw // 2 - 2)
    if halo:
        x0, y0, x1, y1 = draw.textbbox((cx - tw // 2, y), text, font=font)
        draw.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), fill=style.PAPER)
    style.draw_text_center(draw, cx, y, text, font, fill)


def render_hourly(payload: dict, rect: Rect, font_path: str, options: dict | None = None) -> Image.Image:
    opts = options or {}
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    hourly = payload["weather"]["hourly"][: 12 if str(opts.get("span")) == "12" else 24]
    if not hourly:
        return img
    chart = str(opts.get("chart") or "bar")
    precip_mode = str(opts.get("precip") or "dots")
    label_mode = str(opts.get("labels") or "ends")
    tick_every = 3 if str(opts.get("ticks")) == "3" else 6
    english = is_en(payload)

    f_label = _font(sx, 20, font_path)
    pad_t, pad_b = int(40 * sx), int(50 * sx)
    # 「底部细条」在基线上方单独占一条带，温度图形相应上移
    strip = int(28 * sx) if precip_mode == "bars" else 0
    plot_h = rect.h - pad_t - pad_b - strip
    base = rect.h - pad_b - 2
    y1 = base - strip
    temps = [h["temperature"] for h in hourly]
    t_max, t_min = max(temps), min(temps)
    span = max(t_max - t_min, 1.0)
    n = len(hourly)
    bar_w = max(6, int(rect.w / n * 0.5))
    step = rect.w / n
    points = [(int(step * (i + 0.5)), y1 - (int((temps[i] - t_min) / span * (plot_h - 20)) + 12)) for i in range(n)]

    style.hairline(draw, 8, rect.h - pad_b, rect.w - 8, style.RULE)

    # 温度标注位置先算出来：同一小时还要标降水百分比时，百分比叠放到温度标注上方
    if label_mode == "every3":
        marked = list(range(0, n, 3))
    elif label_mode == "extremes":
        marked = sorted({temps.index(t_max), temps.index(t_min)})
    else:
        marked = sorted({0, n - 1})
    halo = chart in ("line", "area")
    temp_texts = {idx: fmt_temp(temps[idx], payload) for idx in marked}

    if chart == "area" and n > 1:
        draw.polygon([(points[0][0], y1)] + points + [(points[-1][0], y1)], fill=style.LIGHT)
    if chart in ("line", "area") and n > 1:
        draw.line(points, fill=style.INK, width=3)
        for px, py in points:
            draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=style.INK)

    for i, h in enumerate(hourly):
        cx, top = points[i]
        if chart == "bar":
            x0 = cx - bar_w // 2
            draw.rectangle((x0, top, x0 + bar_w, y1), fill=style.LIGHT, outline=style.MID, width=1)

        # 时间刻度
        if i % tick_every == 0:
            hh = h["time"][11:13]
            _text_center_clamped(draw, rect.w, cx, rect.h - pad_b + 12, f"{hh}h" if english else f"{hh}时", f_label, style.MID)

        prob = h["precip"]
        if precip_mode == "dots" and prob >= 30:
            # 降水概率 ≥30% 打点，≥50% 标数字。该小时有温度标注时自下而上依次叠放：
            # 数据点 → 温度标注 → 圆点 → 百分比，互不压字；无标注的小时保持原位置
            if i in marked:
                dot_bottom = draw.textbbox((0, max(4, top - 28)), temp_texts[i], font=f_label)[1] - 3
            else:
                dot_bottom = top - 6
            draw.ellipse((cx - 3, dot_bottom - 6, cx + 3, dot_bottom), fill=style.INK)
            if prob >= 50:
                text = f"{prob}%"
                label_y = dot_bottom - 6 - 4 - draw.textbbox((0, 0), text, font=f_label)[3] if i in marked else top - 36
                _text_center_clamped(draw, rect.w, cx, max(4, label_y), text, f_label, style.INK, halo)
        elif precip_mode == "bars" and prob > 0:
            x0 = cx - bar_w // 2
            draw.rectangle((x0, base - max(1, int(prob / 100 * (strip - 6))), x0 + bar_w, base), fill=style.MID)

    for idx in marked:
        cx, top = points[idx]
        _text_center_clamped(draw, rect.w, cx, max(4, top - 28), temp_texts[idx], f_label, style.INK, halo)
    return img


def _index_value(key: str, payload: dict) -> str:
    weather = payload["weather"]
    current = weather["current"]
    sun = payload["sun"]
    english = is_en(payload)
    if key == "humidity":
        return f"{current['humidity']}%"
    if key == "wind":
        return fmt_wind(current["wind_speed"], payload)
    if key == "precip":
        return f"{weather.get('precip_prob', 0)}%"
    if key in ("sunrise", "sunset"):
        return str(sun.get(key) or "")
    if key == "aqi":
        view = aqi_view(payload)
        return f"{view[0]} {view[1]}" if view else ("No data" if english else "暂无数据")
    if key == "feels":
        return fmt_temp(current.get("apparent"), payload)
    if key == "range":
        today = (weather.get("daily") or [{}])[0] or {}
        low, high = fmt_temp(today.get("temp_min"), payload), fmt_temp(today.get("temp_max"), payload)
        return f"{low} / {high}" if low and high else ""
    if key == "moon":
        return str(sun.get("name") or "")
    if key == "uv":
        uv = uv_today(payload)
        return "" if uv is None else f"{fmt_int(uv)} {uv_level(uv, english)}"
    if key == "pressure":
        return fmt_pressure(current.get("pressure"))
    if key == "visibility":
        return fmt_visibility(current.get("visibility_km"))
    if key == "wind_dir":
        return fmt_wind_dir(current.get("wind_dir"), payload)
    if key in ("pm25", "pm10"):
        air = payload.get("aqi") if isinstance(payload.get("aqi"), dict) else {}
        value = fmt_int(air.get("pm2_5" if key == "pm25" else "pm10"))
        return f"{value} μg/m³" if value else ""
    if key in ADVICE_KEYS:
        return advice_text(payload, key)
    return ""


def render_indices(payload: dict, rect: Rect, font_path: str, options: dict | None = None) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    items = [key for key in ((options or {}).get("items") or DEFAULT_INDEX_ITEMS) if key in _INDEX_LABELS][:INDEX_MAX]
    if not items:
        items = list(DEFAULT_INDEX_ITEMS)
    english = is_en(payload)
    cards = [(_INDEX_LABELS[key][1 if english else 0], _index_value(key, payload) or DASH) for key in items]

    f_key = _font(sx, 22, font_path)
    f_val = _font(sx, 40, font_path)

    # 网格随卡片数自适应：1 张独占整行，其余两列；行数少时卡片更高
    cols = 1 if len(cards) == 1 else 2
    gap = int(16 * sx)
    # 网格整体收 2px：末列/末排边线坐标若等于分区宽高会越界被裁（框缺边）
    card_w = (rect.w - gap * (cols - 1) - 2) // cols
    rows = math.ceil(len(cards) / cols)
    card_h = (rect.h - gap * (rows - 1) - 2) // rows

    for i, (key, val) in enumerate(cards):
        r, c = divmod(i, cols)
        x0 = c * (card_w + gap)
        y0 = r * (card_h + gap)
        draw.rectangle((x0, y0, x0 + card_w, y0 + card_h), outline=style.RULE, width=1)
        draw.text((x0 + int(20 * sx), y0 + int(16 * sx)), key, fill=style.MID, font=f_key)
        # 长数值（如英文 AQI 等级）超出卡片内宽时逐级缩字，避免向左冲出卡片
        f_fit, size = f_val, 40
        while size > 24 and style.text_size(draw, val, f_fit)[0] > card_w - int(40 * sx):
            size -= 2
            f_fit = _font(sx, size, font_path)
        style.draw_text_right(draw, x0 + card_w - int(20 * sx), y0 + card_h - int(56 * sx), val, f_fit, style.INK)
    return img

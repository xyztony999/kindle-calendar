"""今日页：分区渲染 + 时钟字形。页眉/页脚见 common.py。"""

from __future__ import annotations

import math
from datetime import datetime

from PIL import Image, ImageDraw

from server.icons import draw_weather_icon
from server.render import style
from server.render.pages import common
from server.render.regions import ClockMetrics, Rect, clock_metrics, today_regions
from server.render.scene import render_scene

GLYPHS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ":"]


def _is_day(payload: dict) -> bool:
    now_min = payload["clock"]["minutes"]
    rise, set_ = payload["sun"].get("sunrise_minutes"), payload["sun"].get("sunset_minutes")
    if rise is None or set_ is None:
        return 6 * 60 <= now_min <= 18 * 60
    return rise <= now_min <= set_


def _font(payload_size: float, base: int, font_path: str):
    return style.get_font(max(15, round(base * payload_size)), font_path)


def render_header(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    return common.render_header(payload, rect, font_path, page="today")
    return img


def render_weather(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    cur = payload["weather"]["current"]
    today = payload["weather"]["daily"][0]

    f_temp = _font(sx, 118, font_path)
    f_desc = _font(sx, 36, font_path)
    f_info = _font(sx, 26, font_path)

    draw.text((2, 4), f"{cur['temperature']:.0f}°", fill=style.INK, font=f_temp)
    draw.text((8, 152), cur["description"], fill=style.INK, font=f_desc)
    draw.text((8, 198), f"今日 {today['temp_min']:.0f}° / {today['temp_max']:.0f}°", fill=style.MID, font=f_info)

    stats = [
        f"湿度 {cur['humidity']}%",
        f"风 {cur['wind_speed']:.0f} km/h",
        f"降水 {payload['weather'].get('precip_prob', 0)}%",
    ]
    for i, line in enumerate(stats):
        style.draw_text_right(draw, rect.w - 150 * sx, 34 + i * 44 * sx, line, f_info, style.MID)

    icon_size = 132 * sx
    draw_weather_icon(draw, cur["code"], int(rect.w - icon_size / 2 - 6), int(56 * sx), int(icon_size))
    return img


def render_sun(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    img = Image.new("L", (rect.w, rect.h), style.PAPER)
    draw = ImageDraw.Draw(img)
    sx = rect.w / 646

    f_label = _font(sx, 24, font_path)
    sun = payload["sun"]

    x0, x1 = 8, int(rect.w * 0.60)
    cx, rx, ry = (x0 + x1) // 2, (x1 - x0) // 2, int(rect.h * 0.42)
    cy = int(rect.h * 0.82)

    draw.arc((cx - rx, cy - ry, cx + rx, cy + ry), start=180, end=360, fill=style.MID, width=2)
    draw.line((x0 - 6, cy, x1 + 6, cy), fill=style.RULE, width=1)

    rise, set_ = sun.get("sunrise_minutes"), sun.get("sunset_minutes")
    now_min = payload["clock"]["minutes"]
    if rise is not None and set_ is not None and set_ > rise:
        t = min(1.0, max(0.0, (now_min - rise) / (set_ - rise)))
        theta = math.pi * (1 - t)
        px = cx + rx * math.cos(theta)
        py = cy - ry * math.sin(theta)
        r = 5
        draw.ellipse((px - r, py - r, px + r, py + r), fill=style.INK)

    draw.text((x0, 2), f"日出 {sun['sunrise']}", fill=style.MID, font=f_label)
    style.draw_text_right(draw, x1 + 8, 2, f"日落 {sun['sunset']}", f_label, style.MID)

    # 月相盘
    mcx, mcy, mr = int(rect.w - 52 * sx), int(rect.h * 0.46), int(34 * sx)
    draw.ellipse((mcx - mr, mcy - mr, mcx + mr, mcy + mr), outline=style.MID, width=2)
    illum = sun.get("illumination", 50)
    draw.pieslice(
        (mcx - mr + 2, mcy - mr + 2, mcx + mr - 2, mcy + mr - 2),
        start=-90,
        end=90 if sun.get("phase", 0.5) >= 0.5 else -90,
        fill=style.LIGHT,
    )
    style.draw_text_center(draw, mcx, int(rect.h * 0.82), f"{sun['name']} {illum}%", f_label, style.MID)
    return img


def render_quote(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    return common.render_quote(payload, rect, font_path)


def render_scene_region(payload: dict, rect: Rect, font_path: str) -> Image.Image:
    code = payload["weather"]["current"]["code"]
    return render_scene(
        code, _is_day(payload), payload["sun"].get("phase", 0.5), datetime.fromisoformat(payload["clock"]["iso"]), rect.w, rect.h
    )


def render_regions(payload: dict, width: int, height: int, font_path: str) -> dict[str, Image.Image]:
    """渲染今日页的五个内容分区（时钟由设备端字形拼装，不在其中）。"""
    regions = today_regions(width, height)

    out: dict[str, Image.Image] = {}
    for name, fn in (
        ("header", render_header),
        ("weather", render_weather),
        ("sun", render_sun),
        ("scene", render_scene_region),
        ("quote", render_quote),
    ):
        rect = regions[name]
        out[name] = fn(payload, rect, font_path)
    return out


def render_glyphs(metrics: ClockMetrics, font_path: str) -> dict[str, Image.Image]:
    """时钟字形集合：10 个数字 + 冒号，白底黑字，供设备端 A2 拼装。"""
    out: dict[str, Image.Image] = {}
    font = style.get_font(int(metrics.digit_h * 0.92), font_path)
    for glyph in GLYPHS:
        cell_w = metrics.colon_w if glyph == ":" else metrics.digit_w
        img = Image.new("L", (cell_w, metrics.digit_h), style.PAPER)
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), glyph, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (cell_w - tw) // 2 - bbox[0]
        y = (metrics.digit_h - th) // 2 - bbox[1]
        draw.text((x, y), glyph, fill=style.INK, font=font)
        out[glyph] = img
    return out


def compose(
    payload: dict,
    width: int,
    height: int,
    font_path: str,
    glyphs: dict[str, Image.Image] | None = None,
) -> Image.Image:
    """合成今日页整页（含当前时间时钟）。其余页的合成见 render.compose_page。"""
    canvas = Image.new("L", (width, height), style.PAPER)
    regions = today_regions(width, height)

    parts = render_regions(payload, width, height, font_path)
    for name, img in parts.items():
        rect = regions[name]
        canvas.paste(img, (rect.x, rect.y))

    if glyphs is None:
        metrics = clock_metrics(width, height)
        glyphs = render_glyphs(metrics, font_path)
    metrics = clock_metrics(width, height)
    x0 = (width - metrics.total_w()) // 2
    y0 = regions["clock"].y + (regions["clock"].h - metrics.digit_h) // 2
    hhmm = payload["clock"]["now"]
    sequence = [hhmm[0], hhmm[1], ":", hhmm[3], hhmm[4]]
    x = x0
    for glyph in sequence:
        cell_w = metrics.colon_w if glyph == ":" else metrics.digit_w
        canvas.paste(glyphs[glyph], (x, y0))
        x += cell_w + metrics.gap
    return canvas

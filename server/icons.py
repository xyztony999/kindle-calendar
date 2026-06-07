"""简单灰度天气图标（矢量绘制，适配墨水屏）。"""

from __future__ import annotations

import math

from PIL import ImageDraw


def _icon_kind(code: int) -> str:
    if code in (0, 1):
        return "sun"
    if code in (2, 3):
        return "cloud"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "cloud"


def draw_weather_icon(draw: ImageDraw.ImageDraw, code: int, cx: int, cy: int, size: int) -> None:
    kind = _icon_kind(code)
    if kind == "sun":
        _draw_sun(draw, cx, cy, size)
    elif kind == "cloud":
        _draw_cloud(draw, cx, cy, size)
    elif kind == "fog":
        _draw_fog(draw, cx, cy, size)
    elif kind == "rain":
        _draw_rain(draw, cx, cy, size)
    elif kind == "snow":
        _draw_snow(draw, cx, cy, size)
    elif kind == "storm":
        _draw_storm(draw, cx, cy, size)


def _draw_sun(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    r = size // 4
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=0, width=2)
    for i in range(8):
        angle = i * math.pi / 4
        x0 = cx + int((r + 3) * math.cos(angle))
        y0 = cy + int((r + 3) * math.sin(angle))
        x1 = cx + int((r + size // 6) * math.cos(angle))
        y1 = cy + int((r + size // 6) * math.sin(angle))
        draw.line((x0, y0, x1, y1), fill=0, width=2)


def _draw_cloud(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    w, h = size, size * 2 // 3
    x0, y0 = cx - w // 2, cy - h // 4
    draw.ellipse((x0, y0, x0 + w // 2, y0 + h // 2), fill=0)
    draw.ellipse((x0 + w // 4, y0 - h // 6, x0 + w * 3 // 4, y0 + h // 2), fill=0)
    draw.ellipse((x0 + w // 3, y0, x0 + w, y0 + h // 2), fill=0)


def _draw_fog(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    _draw_cloud(draw, cx, cy - size // 8, size * 3 // 4)
    w = size
    for i, dy in enumerate((size // 5, size // 2, size * 4 // 5)):
        lw = w - i * (w // 6)
        draw.line((cx - lw // 2, cy - size // 4 + dy, cx + lw // 2, cy - size // 4 + dy), fill=0, width=2)


def _draw_rain(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    _draw_cloud(draw, cx, cy - size // 6, size * 4 // 5)
    base_y = cy + size // 6
    for dx in (-size // 4, 0, size // 4):
        draw.line((cx + dx, base_y, cx + dx - size // 10, base_y + size // 3), fill=0, width=2)


def _draw_snow(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    _draw_cloud(draw, cx, cy - size // 6, size * 4 // 5)
    base_y = cy + size // 4
    for dx in (-size // 4, 0, size // 4):
        x, y = cx + dx, base_y
        d = size // 10
        draw.line((x - d, y, x + d, y), fill=0, width=2)
        draw.line((x, y - d, x, y + d), fill=0, width=2)


def _draw_storm(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    _draw_cloud(draw, cx, cy - size // 5, size)
    x, y = cx - size // 8, cy + size // 5
    points = [(x, y), (x + size // 6, y + size // 5), (x + size // 12, y + size // 5), (x + size // 4, y + size // 2)]
    draw.line(points, fill=0, width=2)

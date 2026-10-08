"""程序化场景图：山峦剪影 + 日/月 + 天气元素，Bayer 有序抖动为印刷质感二值图。

无外部图片依赖，离线可用；随机种子按日期+天气码确定，一天一景。
"""

from __future__ import annotations

import math
import random
from datetime import datetime

from PIL import Image, ImageDraw

from server.icons import _icon_kind
from server.render.style import INK, PAPER, ordered_dither

FAR_GRAY = 165  # 远山（抖动后为稀疏点）
NEAR_GRAY = 88  # 近山（抖动后为浓密点）
CLOUD_GRAY = 178


def _ridge(rand: random.Random, w: int, h: int, base_y: int, amp: int) -> list[tuple[int, int]]:
    pts: list[tuple[int, int]] = [(0, base_y + rand.randint(-amp, amp))]
    x = 0
    while x < w:
        x += rand.randint(max(8, w // 14), max(12, w // 7))
        pts.append((min(x, w), base_y + rand.randint(-amp, amp)))
    pts[-1] = (w, pts[-1][1])
    return pts


def _mountains(draw: ImageDraw.ImageDraw, rand: random.Random, w: int, h: int) -> None:
    far = _ridge(rand, w, h, int(h * 0.52), int(h * 0.16))
    draw.polygon(far + [(w, h), (0, h)], fill=FAR_GRAY)
    near = _ridge(rand, w, h, int(h * 0.74), int(h * 0.18))
    draw.polygon(near + [(w, h), (0, h)], fill=NEAR_GRAY)


def _sun(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=INK, width=3)
    for i in range(8):
        ang = i * math.pi / 4
        x0 = cx + int((r + 5) * math.cos(ang))
        y0 = cy + int((r + 5) * math.sin(ang))
        x1 = cx + int((r + 5 + r * 0.45) * math.cos(ang))
        y1 = cy + int((r + 5 + r * 0.45) * math.sin(ang))
        draw.line((x0, y0, x1, y1), fill=INK, width=2)


def _moon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, phase: float) -> None:
    """phase: 0 新月 0.5 满月。用错位圆 carve 出盈亏。"""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=INK)
    illum = (1 - math.cos(2 * math.pi * phase)) / 2  # 0..1
    shift = int(r * 1.8 * (1 - abs(2 * illum - 1)))
    dx = -shift if phase < 0.5 else shift
    draw.ellipse((cx - r + dx, cy - r, cx + r + dx, cy + r), fill=PAPER)


def _stars(draw: ImageDraw.ImageDraw, rand: random.Random, w: int, h: int, n: int) -> None:
    for _ in range(n):
        x = rand.randint(4, w - 4)
        y = rand.randint(4, int(h * 0.45))
        s = rand.choice((1, 1, 2))
        draw.rectangle((x, y, x + s, y + s), fill=INK)


def _clouds(draw: ImageDraw.ImageDraw, rand: random.Random, w: int, h: int, n: int) -> None:
    for _ in range(n):
        cx = rand.randint(int(w * 0.1), int(w * 0.9))
        cy = rand.randint(int(h * 0.08), int(h * 0.3))
        r = rand.randint(int(h * 0.1), int(h * 0.18))
        for dx, dy, rr in ((-r, 0, r), (0, -r // 2, int(r * 1.15)), (r, 0, int(r * 0.9))):
            draw.ellipse((cx + dx - rr, cy + dy - rr // 2, cx + dx + rr, cy + dy + rr // 2), fill=CLOUD_GRAY)


def render_scene(
    code: int,
    is_day: bool,
    moon_phase: float,
    now: datetime,
    w: int,
    h: int,
) -> Image.Image:
    rand = random.Random(f"{now:%Y%m%d}-{code}")
    kind = _icon_kind(code)

    img = Image.new("L", (w, h), PAPER)
    draw = ImageDraw.Draw(img)

    if is_day:
        _sun(draw, cx=int(w * 0.78), cy=int(h * 0.3), r=max(10, int(h * 0.14)))
    else:
        _moon(draw, cx=int(w * 0.78), cy=int(h * 0.26), r=max(8, int(h * 0.12)), phase=moon_phase)
        _stars(draw, rand, w, h, 7)

    if kind in ("cloud", "fog", "rain", "snow", "storm"):
        _clouds(draw, rand, w, h, 2)

    _mountains(draw, rand, w, h)

    if kind == "rain":
        for _ in range(26):
            x = rand.randint(6, w - 6)
            y = rand.randint(int(h * 0.2), int(h * 0.66))
            ln = rand.randint(int(h * 0.12), int(h * 0.2))
            draw.line((x, y, x - ln // 3, y + ln), fill=INK, width=2)
    elif kind == "snow":
        for _ in range(30):
            x = rand.randint(4, w - 4)
            y = rand.randint(int(h * 0.15), int(h * 0.7))
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=INK)
    elif kind == "fog":
        for i in range(3):
            y = int(h * (0.35 + 0.18 * i)) + rand.randint(-3, 3)
            draw.rectangle((0, y, w, y + max(4, h // 20)), fill=CLOUD_GRAY)
    elif kind == "storm":
        x = int(w * 0.35)
        y = int(h * 0.24)
        pts = [(x, y), (x - 14, y + int(h * 0.2)), (x + 2, y + int(h * 0.2)), (x - 10, y + int(h * 0.4))]
        draw.line(pts, fill=INK, width=3)
        for _ in range(20):
            rx = rand.randint(6, w - 6)
            ry = rand.randint(int(h * 0.3), int(h * 0.66))
            draw.line((rx, ry, rx - 4, ry + int(h * 0.14)), fill=INK, width=2)

    return ordered_dither(img)

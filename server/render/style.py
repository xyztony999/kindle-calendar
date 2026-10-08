"""印刷杂志风设计 token：调色板、衬线字体、有序抖动、排版助手。"""

from __future__ import annotations

import platform
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 四档灰阶（设计定稿：正文只用四档，减少局刷残影）
INK = 0x11  # 近黑（印刷感，非纯黑）
MID = 0x55
LIGHT = 0x99
PAPER = 0xFF
RULE = 0x77  # 细规则线

# Bayer 8×8 有序抖动矩阵（0..63）
BAYER8 = [
    [0, 32, 8, 40, 2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
]

_font_cache: dict[tuple[str, str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _candidates(kind: str) -> list[str]:
    """kind: 'serif' 优先衬线；找不到时回退黑体族。"""
    serif: list[str]
    sans: list[str]
    if platform.system() == "Windows":
        serif = [r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\msyh.ttc"]
        sans = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]
    elif platform.system() == "Darwin":
        serif = [
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
        ]
        sans = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc"]
    else:
        serif = [
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
        sans = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        ]
    return serif if kind == "serif" else sans


def get_font(size: int, font_path: str = "", kind: str = "serif") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (font_path or "", kind, size)
    cached = _font_cache.get(key)
    if cached is not None:
        return cached

    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    paths = [font_path] if font_path and Path(font_path).exists() else []
    for path in paths + _candidates(kind) + _candidates("sans"):
        if Path(path).exists():
            font = ImageFont.truetype(path, size)
            break
    else:
        font = ImageFont.load_default()

    _font_cache[key] = font
    return font


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: int = INK,
    tracking: int = 0,
) -> None:
    """带字距的文字绘制（tracking 为字符间附加像素，用于 kicker 小字）。"""
    x, y = xy
    if tracking <= 0:
        draw.text((x, y), text, fill=fill, font=font)
        return
    for ch in text:
        draw.text((x, y), ch, fill=fill, font=font)
        w, _ = text_size(draw, ch, font)
        x += w + tracking


def tracked_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, tracking: int = 0) -> int:
    w, _ = text_size(draw, text, font)
    return w + tracking * max(len(text) - 1, 0)


def hairline(draw: ImageDraw.ImageDraw, x0: int, y: int, x1: int, fill: int = RULE) -> None:
    draw.line((x0, y, x1, y), fill=fill, width=1)


def draw_text_right(
    draw: ImageDraw.ImageDraw,
    right: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    fill: int = INK,
    tracking: int = 0,
) -> None:
    w = tracked_width(draw, text, font, tracking)
    draw_text(draw, (right - w, y), text, font, fill, tracking)


def draw_text_center(
    draw: ImageDraw.ImageDraw,
    cx: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    fill: int = INK,
    tracking: int = 0,
) -> None:
    w = tracked_width(draw, text, font, tracking)
    draw_text(draw, (cx - w // 2, y), text, font, fill, tracking)


def ordered_dither(img: Image.Image) -> Image.Image:
    """灰度图 → Bayer 8×8 有序抖动二值图（保持 'L' 模式，值 0/255）。"""
    g = img if img.mode == "L" else img.convert("L")
    w, h = g.size
    src = g.load()
    out = Image.new("L", (w, h), PAPER)
    dst = out.load()
    for y in range(h):
        row = BAYER8[y & 7]
        for x in range(w):
            v = src[x, y] * 64 // 256
            dst[x, y] = PAPER if v > row[x & 7] else INK
    return out

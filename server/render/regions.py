"""页面分区几何：以 758×1024 为基准设计，按目标分辨率等比缩放。

分区为全宽横条，便于设备端按差异重绘与局刷。
五页共用页眉（44-122）与页脚一言（948-1000，共享资产）。
"""

from __future__ import annotations

from dataclasses import dataclass

BASE_W, BASE_H = 758, 1024

PAGES = ("today", "week", "month", "detail", "almanac")

# 各页内容分区（基准 y 区间）。pageblank 为整页白底 underlay（122-948），
# 先铺它再画内容分区——消除分区间缝隙里的上一页残留。
# 各页共用页眉（44-122）与页脚一言（948-1000，共享资产）。
_PAGE_BANDS: dict[str, dict[str, tuple[float, float]]] = {
    "today": {
        "header": (44, 122),
        "clock": (130, 372),
        "weather": (392, 636),
        "sun": (656, 788),
        "scene": (808, 932),
        "quote": (948, 1000),
        "pageblank": (122, 948),
    },
    "week": {
        "header": (44, 122),
        "list": (130, 620),
        "chart": (640, 930),
        "quote": (948, 1000),
        "pageblank": (122, 948),
    },
    "month": {
        "header": (44, 122),
        "title": (130, 190),
        "grid": (200, 930),
        "quote": (948, 1000),
        "pageblank": (122, 948),
    },
    "detail": {
        "header": (44, 122),
        "hourly": (130, 560),
        "indices": (580, 930),
        "quote": (948, 1000),
        "pageblank": (122, 948),
    },
    "almanac": {
        "header": (44, 122),
        "main": (130, 930),
        "quote": (948, 1000),
        "pageblank": (122, 948),
    },
}


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class ClockMetrics:
    x: int  # 时钟区域左上
    y: int
    digit_w: int
    digit_h: int
    colon_w: int
    gap: int

    def total_w(self) -> int:
        return 4 * self.digit_w + self.colon_w + 4 * self.gap


def page_regions(page: str, width: int, height: int) -> dict[str, Rect]:
    sx, sy = width / BASE_W, height / BASE_H
    margin = round(56 * sx)
    bands = _PAGE_BANDS[page]

    def band(y0: float, y1: float) -> Rect:
        top, bottom = round(y0 * sy), round(y1 * sy)
        return Rect(margin, top, width - 2 * margin, bottom - top)

    return {name: band(*ys) for name, ys in bands.items()}


def today_regions(width: int, height: int) -> dict[str, Rect]:
    return page_regions("today", width, height)


def clock_metrics(width: int, height: int) -> ClockMetrics:
    sx, sy = width / BASE_W, height / BASE_H
    regions = page_regions("today", width, height)
    clock = regions["clock"]
    return ClockMetrics(
        x=clock.x,
        y=clock.y,
        digit_w=round(118 * sx),
        digit_h=round(196 * sy),
        colon_w=round(58 * sx),
        gap=round(14 * sx),
    )


def metrics_in(rect: Rect) -> ClockMetrics:
    """把四位时钟放进给定矩形，返回的 x/y 已是字形左上角。"""
    gap = max(2, rect.w // 40)
    colon_w = max(8, rect.w // 12)
    digit_w = max(8, (rect.w - colon_w - 4 * gap) // 4)
    digit_h = min(rect.h, max(16, round(digit_w * 196 / 118)))
    total = 4 * digit_w + colon_w + 4 * gap
    return ClockMetrics(
        x=rect.x + max(0, (rect.w - total) // 2),
        y=rect.y + max(0, (rect.h - digit_h) // 2),
        digit_w=digit_w,
        digit_h=digit_h,
        colon_w=colon_w,
        gap=gap,
    )

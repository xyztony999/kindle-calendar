"""页面分区几何：以 758×1024 为基准设计，按目标分辨率等比缩放。

分区为全宽横条，便于设备端按差异重绘与局刷。
"""

from __future__ import annotations

from dataclasses import dataclass

BASE_W, BASE_H = 758, 1024


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


def today_regions(width: int, height: int) -> dict[str, Rect]:
    sx, sy = width / BASE_W, height / BASE_H
    margin = round(56 * sx)

    def band(y0: float, y1: float) -> Rect:
        top, bottom = round(y0 * sy), round(y1 * sy)
        return Rect(margin, top, width - 2 * margin, bottom - top)

    return {
        "header": band(44, 122),
        "clock": band(130, 372),
        "weather": band(392, 636),
        "sun": band(656, 788),
        "scene": band(808, 932),
        "quote": band(948, 1000),
    }


def clock_metrics(width: int, height: int) -> ClockMetrics:
    sx, sy = width / BASE_W, height / BASE_H
    regions = today_regions(width, height)
    clock = regions["clock"]
    return ClockMetrics(
        x=clock.x,
        y=clock.y,
        digit_w=round(118 * sx),
        digit_h=round(196 * sy),
        colon_w=round(58 * sx),
        gap=round(14 * sx),
    )

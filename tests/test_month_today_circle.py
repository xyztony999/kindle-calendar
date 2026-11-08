"""月历页今日圈注居中测试：圈心必须对准数字实际墨水包围盒（±2px）。"""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from server.data import build_payload
from server.render.pages import month
from server.render.regions import Rect
from server.weather import CurrentWeather, DailyForecast, HourlyPoint, WeatherData

RECT = Rect(0, 0, 646, 730)
COL_W = 646 // 7


def _payload(day: int) -> dict:
    tz = ZoneInfo("Asia/Shanghai")
    now = datetime(2026, 11, day, 16, 0, tzinfo=tz)
    weather = WeatherData(
        CurrentWeather(20, 50, 5, 0, "晴"),
        [DailyForecast(f"2026-11-{day:02d}", 24, 14, 0, "晴")],
        [HourlyPoint(f"2026-11-{day:02d}T16:00", 20, 0, 0)],
    )
    with patch("server.quotes.get_quote", return_value={"text": "测试一言", "from": "单测"}):
        return build_payload({"latitude": 39.9, "longitude": 116.4, "location_name": "北京"}, weather, now)


def _bbox_of(img, box, predicate) -> tuple[int, int, int, int] | None:
    px = img.load()
    x0, y0, x1, y1 = box
    xs, ys = [], []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if predicate(px[x, y]):
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


class TodayCircleCenterTest(unittest.TestCase):
    def test_circle_centered_on_digit_ink(self):
        # 今日=3（周二，非周末：有圈/无圈两次渲染中数字填充色一致，像素差即纯圈环）
        with_circle = month.render_grid(_payload(3), RECT, "")
        without_circle = month.render_grid(_payload(5), RECT, "")
        ca, cb = with_circle.load(), without_circle.load()

        cell = (94, 166, 182, 240)  # 11月3日格（row1 col1）数字区，避开行发丝线与农历角标
        digit = _bbox_of(without_circle, cell, lambda v: v < 128)
        self.assertIsNotNone(digit, "digit ink missing in cell")

        xs, ys = [], []
        for y in range(166, 275):
            for x in range(94, 182):
                if ca[x, y] != cb[x, y]:
                    xs.append(x)
                    ys.append(y)
        self.assertGreater(len(xs), 20, "circle ring pixels missing from diff")
        ring = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)

        ring_cx, ring_cy = (ring[0] + ring[2]) / 2, (ring[1] + ring[3]) / 2
        digit_cx, digit_cy = (digit[0] + digit[2]) / 2, (digit[1] + digit[3]) / 2
        self.assertLessEqual(abs(ring_cx - digit_cx), 2.0, f"horizontal offset {ring_cx - digit_cx:+.1f}px")
        self.assertLessEqual(abs(ring_cy - digit_cy), 2.0, f"vertical offset {ring_cy - digit_cy:+.1f}px")
        # 圈须整体套住数字
        self.assertLessEqual(ring[0] <= digit[0] and ring[1] <= digit[1] and ring[2] >= digit[2] and ring[3] >= digit[3], True)


if __name__ == "__main__":
    unittest.main()

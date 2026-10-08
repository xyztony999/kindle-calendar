"""渲染包：分区渲染、时钟字形、整页合成。"""

from server.render.pages.today import compose, render_glyphs, render_regions
from server.render.regions import clock_metrics, today_regions

__all__ = ["compose", "render_glyphs", "render_regions", "clock_metrics", "today_regions"]

"""指数卡目录：layout（选项 schema）与 detail（渲染）共用。

独立成无依赖模块：layout 依赖 render.regions，而 render 包初始化会加载页面渲染器，
渲染器若反向导入 layout 会形成循环导入。
"""

from __future__ import annotations

# 顺序即候选列表顺序：现有六项 / 现有数据补足 / 气象扩展 / 空气细分 / 生活建议
INDEX_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("humidity", "湿度", "Humidity"),
    ("wind", "风速", "Wind"),
    ("precip", "降水概率", "Rain"),
    ("sunrise", "日出", "Sunrise"),
    ("sunset", "日落", "Sunset"),
    ("aqi", "AQI", "AQI"),
    ("feels", "体感温度", "Feels like"),
    ("range", "今日高低温", "High / low"),
    ("moon", "月相", "Moon"),
    ("uv", "紫外线", "UV index"),
    ("pressure", "气压", "Pressure"),
    ("visibility", "能见度", "Visibility"),
    ("wind_dir", "风向", "Wind direction"),
    ("pm25", "PM2.5", "PM2.5"),
    ("pm10", "PM10", "PM10"),
    ("dress", "穿衣", "What to wear"),
    ("laundry", "晾晒", "Laundry"),
    ("exercise", "运动", "Exercise"),
    ("carwash", "洗车", "Car wash"),
    ("cold", "感冒", "Cold risk"),
    ("sunscreen", "防晒", "Sun protection"),
)
INDEX_KEYS = tuple(key for key, _zh, _en in INDEX_ITEMS)
DEFAULT_INDEX_ITEMS = ("humidity", "wind", "precip", "sunrise", "sunset", "aqi")
INDEX_MAX = 6

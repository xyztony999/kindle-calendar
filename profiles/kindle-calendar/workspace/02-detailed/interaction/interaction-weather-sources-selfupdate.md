# 交互：weather-sources-selfupdate

- 版本：v1.0（2026-10-26）

## 1. 体感温度

- 数据积木字段列表新增「体感温度」（数值，°）。
- 天气积木选中时外观面板新增开关「体感温度」（默认关，开启后出现在右侧 stats 行）。

## 2. 天气突变提醒

- 提醒出现在**页眉备注行**（星期行右侧），复用现有「节日与假期备注」开关：关掉该开关则提醒一并隐藏。
- 文案：`较昨日降 6°`、`降水 70%`（en：`Down 6°`、`Rain 70%`）；与节日/纪念日共享前两条截断。

## 3. 数据源健康卡（侧栏，设备卡下方）

```
┌ 数据源 ────────────────────┐
│ ● 天气    3 分钟前          │
│ ● AQI     3 分钟前          │
│ ● 一言    今天 08:00        │
│ ● ICS     2 小时前  ⚠ 失败  │
│   （失败行下灰字显示最近错误，悬停看全文）│
└────────────────────────────┘
```
- 徽标：正常（绿点）/ 失败（红）/ 未配置（灰，如 ICS 无订阅链接、一言非在线模式）；随设备卡每 30 秒轮询。

## 4. dash.sh 自更新

- 用户无感：设备每个拉取周期比对校验和，后台完成下载→校验→替换→重启；日志记录于设备端。
- `config.sh` 可设 `DASH_AUTOUPDATE=0` 关闭。
- 管理端不做更新 UI；部署文档说明「升级到带自更新的版本需最后一次手动拷贝 dash.sh」。

## 5. 文案（locale 新增）

zh：sources_h2 数据源 / source_weather 天气 / source_aqi AQI / source_quote 一言 / source_ics 日程 ICS / source_ok 正常 / source_fail 失败 / source_off 未启用 / source_never 从未刷新
en：Data sources / Weather / AQI / Quote / ICS schedule / OK / Failed / Not configured / Never refreshed
（页眉提醒与体感文案在渲染层/format 内实现；show_feels 标签在 layout.py schema。）

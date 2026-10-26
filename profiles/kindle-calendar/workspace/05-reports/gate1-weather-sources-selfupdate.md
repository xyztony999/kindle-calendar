# Gate 1 报告：weather-sources-selfupdate

- 日期：2026-10-26
- 启动模式：增量（基于 8277d50）
- 结论：**PASS**（用户按推荐执行：1A/2A/3A/4A）

## 决策

| 决策点 | 选择 |
|---|---|
| 自更新策略 | A：md5 对比+校验+原子替换+自动重启，config.sh 可关 |
| 提醒呈现 | A：页眉备注行（复用 show_notes） |
| 体感呈现 | A：数据积木字段 + 天气积木 stats 开关 |
| 顺序 | A：体感→提醒→健康页→自更新 |

## 关键勘察结论

- 镜像不含 kindle/（.dockerignore 排除），需新增 COPY。
- 天气 API 无 past_days/apparent；daily[0]=今天 是 today/week/fields 多处契约 → 昨日按日期校验后单独存 WeatherData.yesterday，不动 daily。
- 一言/AQI/ICS 失败对调用方不可见（静默回退/吞异常），需补模块级状态。
- 设备 busybox：md5sum 必有（sha256sum 不保证）；脚本不使用 $0，硬编码 DASH_DIR；v2.2 trap 清理在 exit 时生效。

## 风险

- 自更新引导：现役设备 dash.sh 无更新逻辑，升级到本版需最后一次手动 scp。
- past_days 若被 API 忽略 → yesterday=None，提醒静默跳过（按日期校验防御）。
- Open-Meteo apparent 字段缺失时为 None：字段显示 —，开关行隐藏。

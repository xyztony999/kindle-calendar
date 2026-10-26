# Gate 1 报告：schedule-presets-clock12

- 日期：2026-10-25
- 启动模式：增量（叠加未提交的 editor-manage）
- 结论：**PASS**（用户拍板 1A/2A/3B/4A）

## 决策

| 决策点 | 选择 |
|---|---|
| ICS URL 存储 | A：settings.json + 管理端配置卡 |
| ICS 解析依赖 | A：icalendar + recurring-ical-events |
| 12h 显示形态 | **B：完整版——去前导零 + AM/PM 小字**（设备端 draw_clock 重构为可变格循环；字形集扩 am/pm；metrics/env 扩后缀位） |
| 实施顺序 | A：时钟 → 快照 → 日程 |

## 关键勘察结论

- 时钟：`date +%H%M` 硬编码 5 格循环；busybox 环境须纯 shell 取模（`${h#0}` 防八进制）；`%l` 不可用。新 env 变量旧脚本静默忽略。可变 token 方案：token 数变化整只重画，同构时逐格差分。
- ICS：holidays.py 的 TTL+锁+降级骨架 + catalog.py 的 URL 校验为最佳模板；requirements 无 icalendar 需新增。v2-design.md 已预留 events payload 形态与 `server/ics.py`。
- settings 新键：SCHEMA_VERSION 保持 3，validate 对缺失容错（旧导入不降级）。

## 风险

- 12h 完整版动设备端循环结构与字形契约，必须 harness 覆盖 draw_clock 全分支；真机需用户拷贝新版 dash.sh。
- recurring-ical-events 对异常 RRULE 的健壮性：单条事件解析失败跳过不阻塞整体。
- editor-manage 未提交叠加开发：本轮验证需覆盖两轮全部回归。

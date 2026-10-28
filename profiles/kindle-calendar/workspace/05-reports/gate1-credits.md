# Gate 1 报告：credits（开源组件说明页）

- 日期：2026-10-29
- 启动模式：增量（master @ 2a62f3d）
- 结论：**PASS**（用户按推荐执行：A 仅落地页入口；手写字典）

## 决策

| 决策点 | 选择 |
|---|---|
| 是否单独一页 | 是（AGPL 署名义务 + 落地页已有 GPL 声明无明细） |
| 范围 | A：落地页页脚入口 + /credits；管理端入口不做 |
| 内容维护 | A：landing.py 手写中英字典 |

## 事实核查（许可证一手证据）

- **FBInk 实为 GPL-3.0+（此前 README 误标 MIT）**——本项目以独立二进制经命令行调用（非库链接），合规且需署名；README 一并更正。
- recurring-ical-events = LGPL-3.0+（pip import 动态使用可接受）；icalendar = BSD-2；Pillow = MIT-CMU；其余见 api-credits.md 表。
- hitokoto 语料 AGPL-3.0、holiday-cn MIT、Noto CJK OFL-1.1 均一手确认。

## 风险

- 上游许可未来变更：页面标注"以各上游项目最新声明为准"。

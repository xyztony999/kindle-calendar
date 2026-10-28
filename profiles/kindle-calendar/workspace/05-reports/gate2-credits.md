# Gate 2 报告：credits（开源组件说明页）

- 日期：2026-10-29
- 结论：**PASS（待用户验收）**——128 项单测全过、E2E PASS、/credits 双语渲染正常；未提交。

## 交付清单

- **`GET /credits`**：真 Jinja 页面（credits.html），复用落地页语言机制（`?lang=`/cookie/Accept-Language + 写回 cookie）、深浅色主题与品牌头；四组内容：Python 依赖（10 包各附许可证与用途）、数据与内容（Open-Meteo/hitokoto AGPL/holiday-cn）、设备端与字体（FBInk GPL-3.0+/Noto Serif CJK OFL/tapread 自研）、本项目 GPL-3.0 声明。
- **入口**：落地页页脚「开源组件/Open-source credits」链接；`/credits` 登记进首页接口目录（中英描述）。
- **事实更正**：FBInk 实为 **GPL-3.0-or-later**（此前 bin/README 误标 MIT）——独立二进制命令行调用合规，README 与 credits 页均已如实标注；recurring-ical-events 为 LGPL-3.0+、Pillow MIT-CMU、icalendar BSD-2（全部经 PyPI/上游 LICENSE 一手核实）。

## 验证

- 128 项单测 OK（新增 CreditsRouteTests 4 项：中文默认+署名断言、英文切换、cookie 记忆、JSON 目录登记）。
- E2E PASS；/credits 实测 200（10.4KB）双语渲染。
- 过程修复：Jinja `group.items` 解析为 dict 方法的 500（改 `group['items']`）。

## 部署注意

纯服务端/模板改动，push 后自动上线。

## 保留待办

- 管理端顶栏入口（本轮范围外，需要时再做）。

# Gate 2 报告：schedule-presets-clock12（个人日程 + 版面快照 + 时钟 12h）

- 日期：2026-10-26
- 结论：**PASS（待用户验收）**——108 项单测全过、两条 E2E 全绿、dash.sh harness 覆盖时钟三模式；未提交。

## 交付清单

### R1 时钟 12/24 小时制（完整版：去前导零 + AM/PM）
- 服务端：`clock.hour12` 选项（默认关=24h 零回归）；`metrics_in(rect, hour12)` 追加后缀位（suf_w≈0.30×digit_h、suf_h≈0.24×digit_h，整体仍居中）；字形集 12h 另生成 am/pm 小字（底对齐）；env 新增 `CLOCK_<页>_HOUR12/SUF_W/SUF_H`（+today legacy）；字形路由正则放宽 `am|pm`；预览 paste_page 同规则换算（单数字小时右移半格居中）。
- 设备端 dash.sh：`apply_clock` 读取新变量并入几何指纹（模式切换自动清 clock.last）；`draw_clock` 重构为可变 token 循环（位数/模式变化整只重画、同构按位差分、后缀仅 am↔pm 或整只重画时绘制）；`sync_glyphs` 按模式校验 11/13 个字形。busybox 安全取模（`${h#0}` 防八进制）。
- 兼容：旧 dash.sh 静默忽略新 env 变量；**12h 生效需用户拷贝新版 dash.sh 到 Kindle**。

### R2 版面快照
- settings `presets[]`（≤8，整包快照 pages+widget_defs+assets，缺失键容错）；管理端「页面与轮播」卡内：保存（prompt 命名）/应用（替换三块+标脏，先关弹窗）/覆盖/导出 JSON/删除。

### R3 个人日程
- `server/ics.py`：SSRF 加固拉取（https 前缀 + DNS 解析全公网 IP + TLS 直连已校验 IP/SNI 域名校验 + 禁重定向 + 2MB 上限 + 8s 超时）；`icalendar + recurring-ical-events` 解析（RRULE/时区/全天）；TTL 6h 缓存、全失败保旧数据、独立线程刷新（不阻塞请求路径）。
- 纪念日：settings `anniversaries[]`（none/yearly/lunar，农历 lunar-python 年度换算）；未来 7 天命中以全天事件并入 `payload.events`（source=anniv），今天命中同时并入页眉节日备注行；`payload.countdowns` = 365 天内最近 5 条。
- 新系统积木：**日程** schedule（≤6 行时间+标题/全天标记/省略号，`show_tomorrow` 选项，空态提示）、**倒计时** countdown（「距 ··· N 天」，days=0 高亮「今天是」）；两者自动获得 border 选项。
- 月历 `show_event_dots` 选项：命中日在日期右上角画点。
- 新数据积木字段：今日日程数/ 下一场日程/ 下一场时间（FIELD_IDS 25→28）。
- 管理端「日程」卡：ICS 订阅链接（≤3）+ 纪念日列表（none/yearly 即时显示倒计天数）。

## 验证

- 单测 108 项 OK（新增：test_ics 5 项——解析/RRULE/occurrences/合并/缓存降级/配置校验；draw_clock harness 2 项——24h 差分、12h 单/双数字+AM/PM+模式切换整只重画、坐标精确断言；glyph/字段/env 断言更新）。
- E2E 两条 PASS；服务端 smoke（hour12 配置校验/normalize、env 变量、旧配置缺键容错）通过。
- 过程中修复 4 处过期测试 + 2 处产品问题（settings ics 缺失键不容错会导致旧配置静默降级——严重级；12h 后缀每分钟冗余局刷）。另发现并修复上轮遗留的 fetch 确认 harness 损坏（v2.2 拆分时未更新）。

## 部署注意

1. 新增 Python 依赖（构建时自动安装）：icalendar、recurring-ical-events。
2. **Kindle 端需拷贝新版 dash.sh 才能显示 12h**；不拷贝则维持 24h，其余功能不受影响。
3. ICS 订阅链接在管理端「日程」卡配置；隐私：只存服务器 settings.json。

## 保留待办

- 真机验收：12h 时钟观感（单数字居中、AM/PM 小字）、月历事件点、日程/倒计时积木实际渲染。
- 并行会话的 sysopt-layout-fix（外观面板排版）叠加在本轮之上，提交时两轮一起。

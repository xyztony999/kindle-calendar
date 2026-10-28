---
pipeline:
  - module: credits
    title: "开源组件说明页 /credits（双语+主题，AGPL/GPL 署名，FBInk 许可更正）"
    stages:
      design:
        status: complete
        note: "2026-10-29 增量 Gate 1 PASS，用户按推荐执行（落地页入口+手写字典）。许可证一手核实：FBInk 实为 GPL-3.0+ 非 MIT（bin/README 误标已更正），recurring-ical-events LGPL-3.0+。"
      code:
        status: complete
        note: "2026-10-29 已实现并验证：/credits Jinja 页（双语/主题/品牌头）+ 落地页页脚入口 + 接口目录登记 + bin/README 更正。128 单测+E2E PASS（修复 Jinja group.items 方法陷阱 500）。Gate 2 PASS 待用户验收，未提交。报告 05-reports/gate2-credits.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-credits.md
      api:
        - 02-detailed/api/api-credits.md
      reports:
        - 05-reports/gate1-credits.md
        - 05-reports/gate2-credits.md
  - module: quote-library-refresh
    title: "语料库刷新机制（管理端手动按钮+7 天自动 TTL，data/ 持久化+热替换）"
    stages:
      design:
        status: complete
        note: "2026-10-27 增量 Gate 1 PASS，用户按推荐执行（7 天自动/行内按钮/失败健康行+toast/脚本薄封装）。"
      code:
        status: complete
        note: "2026-10-27 已实现并验证：refresh_library（加固拉取+过滤+原子写 data/+热替换+<100 拒写+内置忙守卫）；加载 data/ 优先内置兜底；自动 7 天 TTL 挂 ICS 线程；手动 POST quotes-refresh 后台线程+数据源卡按钮+toast；徽标 library 有库即正常；脚本薄封装。124 单测+E2E+并发冒烟+真实网络自动刷新跑通全过。验证抓出并修复 P0（Event 当锁致刷新必崩+双重加锁死锁）。Gate 2 PASS，随 2a62f3d 提交推送（与 quote-resilience、quote-library 同批）。报告 05-reports/gate2-quote-library-refresh.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-quote-library-refresh.md
      api:
        - 02-detailed/api/api-quote-library-refresh.md
      interaction:
        - 02-detailed/interaction/interaction-quote-library-refresh.md
      reports:
        - 05-reports/gate1-quote-library-refresh.md
        - 05-reports/gate2-quote-library-refresh.md
  - module: quote-library
    title: "一言语料库本地化（7,684 条内置+12 分类管理端筛选，新默认模式，AGPL 署名）"
    stages:
      design:
        status: complete
        note: "2026-10-27 增量。Gate 1 对比本地化 vs 自部署后端（后者运维成本与产品形态不匹配否决）；用户拍板 A+A2。官方 sentences-bundle 已按分类拆分，jsDelivr fastly 可达；协议 AGPL-3.0。"
      code:
        status: complete
        note: "2026-10-27 已实现并验证：quotes_library.json 内置（7,684 条/756KB）；模式 library(新默认)/online/custom，offline 迁移；library_types a-l 校验；library_quote 确定性选句+兜底；管理端三模式+12 分类复选（中英）；英文 library 不联网；update_quotes.py 加固重建；README 署名。120 单测+E2E PASS（顺带密闭化 test_system_options 真实联网）。Gate 2 PASS，随 2a62f3d 提交推送。报告 05-reports/gate2-quote-library.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-quote-library.md
      api:
        - 02-detailed/api/api-quote-library.md
      interaction:
        - 02-detailed/interaction/interaction-quote-library.md
      reports:
        - 05-reports/gate1-quote-library.md
        - 05-reports/gate2-quote-library.md
  - module: quote-resilience
    title: "一言在线获取韧性（CF 跨洋链路超时：拆分超时+重试+上次成功粘性缓存）"
    stages:
      design:
        status: complete
        note: "2026-10-26 增量。D0 服务器实测定位根因（请求合规官方文档；阿里云北京→Cloudflare 洛杉矶 POP 晚高峰 ~80% 丢包撞穿 8s 读超时，international 同 IP 换域无效）；Gate 1 PASS 用户按推荐执行（韧性包+英文同步）。"
      code:
        status: complete
        note: "2026-10-26 已实现并验证：超时 (5,12)+失败重试一次+粘性缓存 ≤7 天（中英两路）；修复 _days_old 带时区崩溃 bug；117 单测 + E2E PASS。Gate 2 PASS，随 2a62f3d 提交推送（后续 quote-library 上线后在线模式为可选项）。报告 05-reports/gate2-quote-resilience.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-quote-resilience.md
      reports:
        - 05-reports/gate1-quote-resilience.md
        - 05-reports/gate2-quote-resilience.md
  - module: weather-sources-selfupdate
    title: "体感温度、天气突变提醒（页眉）、数据源健康卡与 dash.sh 自更新"
    stages:
      design:
        status: complete
        note: "2026-10-26 增量 Gate 1 PASS，用户按推荐执行（自更新校验+自动重启/提醒走页眉/体感字段+开关/顺序体感→提醒→健康→自更新）。"
      code:
        status: complete
        note: "2026-10-26 四项实现并验证：体感（字段+show_feels）、突变提醒（past_days 昨日切分+页眉 notes）、健康页（quotes/aqi/ics 状态+/admin/api/sources+侧栏卡）、dash.sh 自更新（镜像内置+/api/v1/script+md5 校验原子替换重启，harness 四分支）。112 单测 + 2 E2E PASS。Gate 2 PASS，随 b0ba151 提交推送；设备需最后一次手动 scp 引导自更新。报告 05-reports/gate2-weather-sources-selfupdate.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-weather-sources-selfupdate.md
      api:
        - 02-detailed/api/api-weather-sources-selfupdate.md
      interaction:
        - 02-detailed/interaction/interaction-weather-sources-selfupdate.md
      reports:
        - 05-reports/gate1-weather-sources-selfupdate.md
        - 05-reports/gate2-weather-sources-selfupdate.md
  - module: sysopt-layout-fix
    title: "外观面板系统/文字选项排版修复（时钟 choice 单选钮重叠·点档位文字激活错误项·开关漂移）"
    stages:
      design:
        status: complete
        note: "2026-10-26 增量。D0 实测复现定根因（renderSystemOptions/renderTextOptions 复用样式卡 CSS）；Gate 1 PASS，用户确认方案 A（行式选项布局与样式卡解耦）。无架构/接口/文案变更，不单独出 api/interaction 文档。"
      code:
        status: complete
        note: "2026-10-26 已实现并验证：opt-list/opt-row/opt-pick 行式布局+改选焦点恢复+legend 切换；两条 E2E PASS（含时钟三档钮两两不重叠/点档位文字激活该档/控件 inside 断言）；数据样式卡与服务端零改动。Gate 2 PASS，随 8277d50 提交推送。报告 05-reports/gate2-sysopt-layout-fix.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-sysopt-layout-fix.md
      reports:
        - 05-reports/gate1-sysopt-layout-fix.md
        - 05-reports/gate2-sysopt-layout-fix.md
  - module: schedule-presets-clock12
    title: "个人日程（ICS+纪念日/倒计时+月历标记）、版面快照与时钟 12 小时制（AM/PM 完整版）"
    stages:
      design:
        status: complete
        note: "2026-10-25 增量 Gate 1 PASS，用户拍板 1A/2A/3B/4A；叠加未提交的 editor-manage 一轮开发。"
      code:
        status: complete
        note: "2026-10-26 三阶段实现并验证：时钟 12h 完整版（服务端 schema/metrics/字形/env/预览 + dash.sh 可变 token 循环，旧设备静默兼容）；版面快照 presets（整包快照+管理端应用/覆盖/导出）；个人日程（ics.py SSRF 加固 + icalendar/recurring-ical-events + 纪念日/倒计时/月历事件点/新字段/日程卡）。108 项单测 OK + 两条 E2E PASS + dash.sh harness 时钟三模式；过程中修 settings ics 缺键容错（防旧配置降级）与 12h 后缀冗余局刷，并修复上轮遗留 fetch harness 损坏。Gate 2 PASS，随 8277d50 提交推送；12h 需拷贝新版 dash.sh 到设备。报告 05-reports/gate2-schedule-presets-clock12.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-schedule-presets-clock12.md
      api:
        - 02-detailed/api/api-schedule-presets-clock12.md
      interaction:
        - 02-detailed/interaction/interaction-schedule-presets-clock12.md
      reports:
        - 05-reports/gate1-schedule-presets-clock12.md
        - 05-reports/gate2-schedule-presets-clock12.md
  - module: editor-manage
    title: "编辑器内管理抽屉与系统积木自定义扩展（选项包+周起始日+文字字号+通用边框+z序）"
    stages:
      design:
        status: complete
        note: "2026-10-24 增量 Gate 1 PASS，用户拍板 1A+2B；勘察发现 grid.show_lunar 死选项与月历偏移漏传 options 两个存量 bug 一并修复。"
      code:
        status: complete
        note: "2026-10-24 已实现并通过验证：100 项单测 OK、两条 E2E PASS（含抽屉全流程）。系统选项新增 show_notes/show_range/show_icon/quote size/week_start/border(除clock)/文字 size+align UI/z 序按钮；修复 grid.show_lunar 死选项与月历偏移漏传 options。Gate 2 PASS，随 8277d50 提交推送。报告 05-reports/gate2-editor-manage.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-editor-manage.md
      api:
        - 02-detailed/api/api-editor-manage.md
      interaction:
        - 02-detailed/interaction/interaction-editor-manage.md
      reports:
        - 05-reports/gate1-editor-manage.md
        - 05-reports/gate2-editor-manage.md
  - module: widget-manager
    title: "我的积木管理卡片、图片素材链路六项修复与版面编辑对齐吸附"
    stages:
      design:
        status: complete
        note: "2026-10-23 增量 Gate 1 PASS，用户确认按推荐执行（管理卡片+智能吸附+全量链路修复）。"
      code:
        status: complete
        note: "2026-10-23 已实现并通过验证：90 项单测 OK、两个 Playwright E2E PASS（顺带修复两脚本自 81aab26 起的选择器过期）。过程中修复存量 bug：layout.py STYLES 过期常量拒绝 horizontal/grid 定义；compose 不透传 OSS_*。Gate 2 PASS，用户 commit & push 确认（71337a1），CI/CD 自动部署。报告 05-reports/gate2-widget-manager.md"
    artifacts:
      prd:
        - 02-detailed/prd/prd-widget-manager.md
      api:
        - 02-detailed/api/api-widget-manager.md
      interaction:
        - 02-detailed/interaction/interaction-widget-manager.md
      reports:
        - 05-reports/gate1-widget-manager.md
        - 05-reports/gate2-widget-manager.md
  - module: adaptive-data-styles
    title: "按数据提供适用样式、画布实例外观与schema3兼容"
    stages:
      design:
        status: complete
        note: "2026-10-17 D0–D4与Gate1 PASS，用户已选按页面设置并回复确认四样式设计。"
      code:
        status: complete
        note: "2026-10-17 四样式/字段筛选/实例覆盖/schema3已实现，78项测试与两套浏览器回归通过，Gate2 PASS。用户commit & push确认本地结果并授权与前轮一起提交推送，前轮真机待办保留。"
    artifacts:
      prd:
        - 02-detailed/prd/prd-adaptive-data-styles.md
      api:
        - 02-detailed/api/api-adaptive-data-styles.md
      interaction:
        - 02-detailed/interaction/interaction-adaptive-data-styles.md
      reports:
        - 05-reports/gate1-adaptive-data-styles.md
        - 05-reports/gate2-adaptive-data-styles.md
  - module: admin-refinement
    title: "管理端八项体验反馈、设备确认400兼容与状态持久化"
    stages:
      design:
        status: complete
        note: "2026-10-16 增量D0–D4与Gate1 PASS，用户confirm确认。旧wget请求格式已模拟复现400。"
      code:
        status: complete
        note: "2026-10-16 八项体验与确认格式/持久化已实现；69项单测、编译、shell与浏览器回归通过。2026-10-17用户commit & push接受本地结果并授权提交推送，Gate2 WARN真机验收继续保留。"
    artifacts:
      prd:
        - 02-detailed/prd/prd-admin-refinement.md
      api:
        - 02-detailed/api/api-admin-refinement.md
      interaction:
        - 02-detailed/interaction/interaction-admin-refinement.md
      reports:
        - 05-reports/gate1-admin-refinement.md
        - 05-reports/gate2-admin-refinement.md
  - module: admin-feedback
    title: "管理端五条浏览器反馈：LogoLoom 标志、样式卡、预览语义、设备状态与退出按钮"
    stages:
      design:
        status: complete
        note: "2026-10-16 增量设计完成，Gate 1 PASS，用户 yes 确认。"
      code:
        status: complete
        note: "2026-10-16 五项反馈已实现；58项测试、编译、shell语法与中英/明暗/窄屏浏览器验证通过。Gate 2 WARN 用户已回复确认接受，本地交付确认完成，Kindle真机验收保留待办。未提交部署。"
    artifacts:
      prd:
        - 02-detailed/prd/prd-admin-feedback.md
      api:
        - 02-detailed/api/api-admin-feedback.md
      interaction:
        - 02-detailed/interaction/interaction-admin-feedback.md
      reports:
        - 05-reports/gate1-admin-feedback.md
        - 05-reports/gate2-admin-feedback.md
  - module: v2-pages
    title: "v2.1 页面集与显示治理（启动清屏 + 五页面集 + 双导航 + 三月预裁翻月）"
    stages:
      design:
        status: complete
        note: "D0-D4 + Gate 1 PASS（2026-10-09）；报告见 05-reports/gate1-v2-pages.md"
      code:
        status: complete
        note: "B1-B7 + 真机验收 + Gate 2 PASS（2026-10-10）：五页/env 契约/路由/dash.sh v2.1/tapread freestanding/滑动翻月/轮播圈清/防锁死；实现偏差见 api 文档附录；报告 05-reports/gate2-v2-pages.md"
    artifacts:
      architecture:
        - 00-architecture/business-arch.md (v1.0)
        - 00-architecture/application-arch.md (v1.0)
        - 00-architecture/function-list.md (v1.0)
      prd:
        - 02-detailed/prd/prd-v2-pages.md (v1.0)
      api:
        - 02-detailed/api/api-v2-pages.md (v1.0)
      interaction:
        - 02-detailed/interaction/interaction-v2-pages.md (v1.0)
      reports:
        - 05-reports/gate1-v2-pages.md
  - module: web-admin
    title: "Web 管理端（页面集与页序 / 每页轮播停留 / 一言来源 / 城市搜索设定 / 预览 / 设备状态 / 导入导出恢复默认，口令登录，云端优先下发）"
    stages:
      design:
        status: complete
        note: "D0 澄清（8 项决策锁定）→ D1 BA v1.2/AA v1.2/FL v1.1 级联 → D2 PRD → D3 API（单例配置聚合根、A-1~A-10、E-1~E-3）→ D4 PageSpec → Gate 1 PASS（2026-10-10）；报告见 05-reports/gate1-web-admin.md"
      code:
        status: complete
        note: "B1-B7 已实现（2026-10-10）。Gate 2 WARN：服务端单测/HTTP/浏览器已通过；真机页序、停留与下发状态待用户确认。报告 05-reports/gate2-web-admin.md"
    artifacts:
      architecture:
        - 00-architecture/business-arch.md (v1.2)
        - 00-architecture/application-arch.md (v1.2)
        - 00-architecture/function-list.md (v1.1)
      prd:
        - 02-detailed/prd/prd-web-admin.md (v1.0)
      api:
        - 02-detailed/api/api-web-admin.md (v1.0)
      interaction:
        - 02-detailed/interaction/interaction-web-admin.md (v1.0)
      conventions:
        - 01-solution/common-spec/enum-pool.md (v1.0, §1 web-admin + §2 v2-pages 回填)
      reports:
        - 05-reports/gate1-web-admin.md
        - 05-reports/gate2-web-admin.md
  - module: en-locale
    title: "双语画面与网页语言（天气台历.sh 中文 / WeatherCalendar.sh 英文；首页与管理端 Cookie 切换）"
    stages:
      design:
        status: complete
        note: "2026-10-11 增量 Gate 1 PASS，用户已确认后进入代码。方案丁 + 语言单按钮 + 系统深色 + 英文农历/干支。英文一言为 ZenQuotes 当日一句，失败或过宽用本地短句（API v1.3）。"
      code:
        status: complete
        note: "2026-10-11 增量已实现。Gate 2 WARN：单测 26 项、浏览器单按钮与系统深色、英文农历/黄历/页脚已通过；Kindle 真机未验证。报告 05-reports/gate2-en-locale.md。"
    artifacts:
      architecture:
        - 00-architecture/business-arch.md (v1.4)
        - 00-architecture/application-arch.md (v1.4)
        - 00-architecture/function-list.md (v1.3)
      prd:
        - 02-detailed/prd/prd-en-locale.md (v1.2)
      api:
        - 02-detailed/api/api-en-locale.md (v1.2)
      interaction:
        - 02-detailed/interaction/interaction-en-locale.md (v1.2)
      conventions:
        - 01-solution/common-spec/enum-pool.md (v1.1, §3 ui_lang)
      reports:
        - 05-reports/gate1-en-locale.md
        - 05-reports/gate2-en-locale.md
  - module: api-view
    title: "接口阅读页（首页上的数据接口在浏览器里显示阅读页，设备与脚本仍取原来的 JSON、env 和 PNG）"
    stages:
      design:
        status: complete
        note: "2026-10-11 冷启动。Gate 1 PASS，用户已确认四条范围。BA/AA/FL v1.5/v1.5/v1.4。"
      code:
        status: complete
        note: "2026-10-11 已实现。Gate 2 PASS，报告 05-reports/gate2-api-view.md。须用户确认后才算交付。未提交。"
    artifacts:
      architecture:
        - 00-architecture/business-arch.md (v1.5)
        - 00-architecture/application-arch.md (v1.5)
        - 00-architecture/function-list.md (v1.4)
      prd:
        - 02-detailed/prd/prd-api-view.md (v1.0)
      api:
        - 02-detailed/api/api-api-view.md (v1.0)
      interaction:
        - 02-detailed/interaction/interaction-api-view.md (v1.0)
      reports:
        - 05-reports/gate1-api-view.md
        - 05-reports/gate2-api-view.md
  - module: admin-back
    title: "管理端返回首页（页顶链接回网站首页，三种版面都可见）"
    stages:
      design:
        status: complete
        note: "2026-10-11 增量。Gate 1 PASS，用户已确认五条范围。"
      code:
        status: complete
        note: "2026-10-11 已实现。Gate 2 PASS，报告 05-reports/gate2-admin-back.md。须用户确认后才算交付。未提交。"
    artifacts:
      architecture:
        - 00-architecture/business-arch.md (v1.6)
        - 00-architecture/application-arch.md (v1.6)
        - 00-architecture/function-list.md (v1.5)
      prd:
        - 02-detailed/prd/prd-admin-back.md (v1.0)
      api:
        - 02-detailed/api/api-admin-back.md (v1.0)
      interaction:
        - 02-detailed/interaction/interaction-admin-back.md (v1.0)
      reports:
        - 05-reports/gate1-admin-back.md
        - 05-reports/gate2-admin-back.md
  - module: web-chrome
    title: "网页外观（登录卡与顶栏按钮、图片承载页、深色控件、深浅色切换）"
    stages:
      design:
        status: complete
        note: "2026-10-15 冷启动。D0–D4 完成。Gate 1 PASS，用户已确认六条。报告 05-reports/gate1-web-chrome.md"
      code:
        status: complete
        note: "2026-10-15 已实现。Gate 2 PASS，报告 05-reports/gate2-web-chrome.md。须用户确认后才算交付。未提交。"
    artifacts:
      architecture:
        - 00-architecture/business-arch.md (v1.7)
        - 00-architecture/application-arch.md (v1.7)
        - 00-architecture/function-list.md (v1.6)
      prd:
        - 02-detailed/prd/prd-web-chrome.md (v1.0)
      api:
        - 02-detailed/api/api-web-chrome.md (v1.0)
      interaction:
        - 02-detailed/interaction/interaction-web-chrome.md (v1.0)
      conventions:
        - 01-solution/common-spec/enum-pool.md (v1.2, §4 ui_theme)
      reports:
        - 05-reports/gate1-web-chrome.md
        - 05-reports/gate2-web-chrome.md
reference: []
modules:
  - name: onboarding
    title: "接入与知识库冷启动"
    stages:
      requirement: { status: complete, note: "profile 骨架 + README 溯源知识库（2026-09-27）" }
      design: { status: complete, note: "架构三文档已由 v2-pages 模块一并建立（2026-10-09）" }
---

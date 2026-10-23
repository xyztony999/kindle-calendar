---
pipeline:
  - module: widget-manager
    title: "我的积木管理卡片、图片素材链路六项修复与版面编辑对齐吸附"
    stages:
      design:
        status: complete
        note: "2026-10-23 增量 Gate 1 PASS，用户确认按推荐执行（管理卡片+智能吸附+全量链路修复）。"
      code:
        status: complete
        note: "2026-10-23 已实现并通过验证：90 项单测 OK、两个 Playwright E2E PASS（顺带修复两脚本自 81aab26 起的选择器过期）。过程中修复存量 bug：layout.py STYLES 过期常量拒绝 horizontal/grid 定义；compose 不透传 OSS_*。Gate 2 PASS 待用户验收，未提交。报告 05-reports/gate2-widget-manager.md"
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

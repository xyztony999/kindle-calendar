---
pipeline:
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
reference: []
modules:
  - name: onboarding
    title: "接入与知识库冷启动"
    stages:
      requirement: { status: complete, note: "profile 骨架 + README 溯源知识库（2026-09-27）" }
      design: { status: complete, note: "架构三文档已由 v2-pages 模块一并建立（2026-10-09）" }
---

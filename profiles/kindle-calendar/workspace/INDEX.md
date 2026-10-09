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
reference: []
modules:
  - name: onboarding
    title: "接入与知识库冷启动"
    stages:
      requirement: { status: complete, note: "profile 骨架 + README 溯源知识库（2026-09-27）" }
      design: { status: complete, note: "架构三文档已由 v2-pages 模块一并建立（2026-10-09）" }
---

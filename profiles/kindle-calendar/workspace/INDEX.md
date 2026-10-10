---
pipeline:
  - module: v2-pages
    title: "v2.1 页面集与显示治理（启动清屏 + 五页面集 + 双导航 + 任意月翻月）"
    stages:
      design:
        status: complete
        note: "D0-D4 + Gate 1 PASS（2026-10-09）；报告见 05-reports/gate1-v2-pages.md"
      code:
        status: complete
        note: "B1-B7 + 真机多轮验收 + Gate 2 PASS（2026-10-10）：五页/env 契约/路由/dash.sh v2.1/tapread freestanding/滑动翻月（任意月动态渲染）/轮播圈清/防锁死；报告 05-reports/gate2-v2-pages.md"
    artifacts:
      architecture:
        - 00-architecture/business-arch.md (v1.1)
        - 00-architecture/application-arch.md (v1.1)
        - 00-architecture/function-list.md (v1.1)
      prd:
        - 02-detailed/prd/prd-v2-pages.md (v1.0)
      api:
        - 02-detailed/api/api-v2-pages.md (v1.1)
      interaction:
        - 02-detailed/interaction/interaction-v2-pages.md (v1.0)
      reports:
        - 05-reports/gate1-v2-pages.md
        - 05-reports/gate2-v2-pages.md
  - module: v2-aqi
    title: "空气质量显示（今日页 AQI 卡替换月相盘 + 详情页 AQI 卡，月相移除）"
    stages:
      design:
        status: complete
        note: "D0-D4 + Gate 1 PASS（2026-10-10）；报告见 05-reports/gate1-v2-aqi.md；决策：彻底移除月相 / US AQI / -- 占位"
      code:
        status: complete
        note: "713d39d 部署（2026-10-10）：纯服务端实现（aqi.py+payload+sun/indices 渲染），实拉验证北京 188 中度，设备端零改动"
    artifacts:
      prd:
        - 02-detailed/prd/prd-v2-aqi.md (v1.0)
      api:
        - 02-detailed/api/api-v2-aqi.md (v1.0)
      interaction:
        - 02-detailed/interaction/interaction-v2-aqi.md (v1.0)
      reports:
        - 05-reports/gate1-v2-aqi.md
reference: []
modules:
  - name: onboarding
    title: "接入与知识库冷启动"
    stages:
      requirement: { status: complete, note: "profile 骨架 + README 溯源知识库（2026-09-27）" }
      design: { status: complete, note: "架构三文档已由 v2-pages 模块一并建立（2026-10-09）" }
---

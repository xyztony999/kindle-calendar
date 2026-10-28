# PRD：开源组件说明页（credits）

- 版本：v1.0（2026-10-29 Gate 1 确认，用户按推荐执行：A 仅落地页入口 + /credits；手写 landing.py 字典）
- 动机：落地页已声明 GPL-3.0 但无组件明细；内置一言语料为 AGPL-3.0（署名义务）、FBInk 二进制为 GPL-3.0+、FBInk 的 bin/README 此前误标 MIT 需更正。

## R1 页面

- R1.1 新路由 `GET /credits`：真 Jinja 页面（非静态文件），复用落地页语言机制（`?lang=`/kc_lang cookie/Accept-Language）、深浅色主题与品牌头；`?lang=` 写回 cookie 与落地页一致。
- R1.2 内容四组（手写 `landing.py` 中英字典，许可以 PyPI/上游 LICENSE 实测为准）：
  - Python 依赖：Flask(BSD-3)、Pillow(MIT-CMU)、PyYAML(MIT)、Requests(Apache-2.0)、tzdata(Apache-2.0)、oss2(MIT)、lunar-python(MIT)、icalendar(BSD-2)、recurring-ical-events(LGPL-3.0+)、gunicorn(MIT)，各附一句用途。
  - 数据与内容：Open-Meteo（天气与空气质量）、hitokoto.cn 开放句子库（AGPL-3.0，已内置筛选）、holiday-cn(MIT)。
  - 设备端与字体：FBInk(GPL-3.0+，独立二进制经命令行调用)、tapread(本项目自研)、Noto Serif CJK(OFL-1.1)。
  - 页脚：本项目 GPL-3.0 + GitHub 链接。
- R1.3 `/credits` 登记进首页接口目录（endpoints 字典 + 英文描述）。

## R2 入口与更正

- R2.1 落地页页脚加「开源组件/OPEN-SOURCE CREDITS」链接（copy.credits）；管理端入口本轮不做。
- R2.2 `kindle/bin/README.md` FBInk 许可更正 MIT → GPL-3.0+。

## 非目标

- 管理端顶栏入口；自动从 requirements 生成；许可证全文展示（只给名称与上游链接）。

## 交互要点（并入本 PRD，不单独出 interaction 文档）

- 页头：品牌（回首页）+ 主题切换 + 语言切换（与落地页同款）；主体分组卡片；页脚返回首页。

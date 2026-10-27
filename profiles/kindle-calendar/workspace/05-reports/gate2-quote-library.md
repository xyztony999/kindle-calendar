# Gate 2 报告：quote-library（一言语料库本地化 A+A2）

- 日期：2026-10-27
- 结论：**PASS（待用户验收）**——120 项单测全过、E2E PASS、中英文 library 模式实测零联网；未提交。

## 交付清单

- **内置语料库** `server/quotes_library.json`：官方 hitokoto-osc/sentences-bundle 筛选内置（4–28 字、去重、from≤24），7,684 条 / 756KB / 12 分类，含 license(AGPL-3.0)/source 元数据。
- **模式体系**：本地语料库（**新默认**）/ 在线一言（上轮韧性保留）/ 自定义文案；旧 `offline` 在 normalize 迁移为 library；`quote.library_types`（a–l 子集，默认诗词+文学，缺失补默认、空/非法报错）。
- **选句**：`library_quote(now, types)` 所选分类池内按年内第几天确定性轮换；池空回退 32 句兜底；英文页在 library 模式直接本地短句（与"不联网"语义一致）。
- **管理端**：一言卡三模式单选 + 12 分类复选（双语、默认勾诗词/文学、切模式隐藏保留选择）；clientErrors 空分类校验；健康卡"一言"在 library 显示未配置。
- **工具与署名**：`scripts/update_quotes.py`（复用 ics 的加固拉取：公网 IP 校验直连+SNI，fastly→cdn→raw 三源回退）；README 一言语料章节 + AGPL 署名；docs/quote-library.md 与 static 镜像标注已实现。
- **测试**：test_quotes +3（确定性/分类过滤/兜底/迁移校验）；既有桩适配 types 新参（web_admin/layout）；test_api_view 补 english_quote patch；**test_system_options 的 _payload 一直在真实联网被 socket 阻断法抓出并 patch**（全套件 quotes 相关联网归零）。

## 验证

- 120 项单测全 OK（含 socket 阻断下全过）；两条 E2E PASS；无头探测：三模式单选与 12 分类复选交互正确、切"在线"分类区隐藏。
- 冒烟：`['i','d']` 与 `['a','k']` 出不同句子；library 英文 `_fetch_zenquotes` 零调用。

## 部署注意

- 语料随镜像分发，push 后自动上线；无需设备/运维操作。
- 默认模式变为本地语料库——已保存过设置的服务器保持原模式（online 用户不受影响，可自行切换）。

## 保留待办

- docs/ 与 server/static/docs/ 双份文档靠手工同步（本次已同步，长期建议单一来源）。
- holidays.py 内置数据兜底的 2 次联网为既有行为，与一言无关。

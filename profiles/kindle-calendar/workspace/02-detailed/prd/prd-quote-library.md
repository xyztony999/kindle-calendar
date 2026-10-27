# PRD：一言语料库本地化（quote-library，方案 A+A2）

- 版本：v1.0（2026-10-27 Gate 1 确认，用户拍板 A+A2：本地语料库 + 管理端分类筛选）
- 背景：hitokoto 在线源经上轮韧性修复仍受阿里云→Cloudflare 跨洋链路制约；官方句子数据库完全公开（hitokoto-osc/sentences-bundle，AGPL-3.0），本地化后运行时零网络请求，彻底根治。

## R1 内置语料库

- `server/quotes_library.json`：官方句子包筛选内置（长度 4–28 字、去重、from≤24 字），含 license/source 元数据；当前 7,684 条 / 756KB，12 分类（a-l）。
- `quotes.library_quote(now, types)`：所选分类池内**按年内第几天确定性轮换**（同日同句、跨日推进）；池空回退内置 32 句。

## R2 模式体系

- 一言模式变为：**本地语料库（新默认）** / 在线一言（保留上轮韧性） / 自定义文案。
- 旧 `offline` 模式在 normalize 迁移为 `library`；32 句内置列表降级为最终兜底。
- settings `quote.library_types`：a-l 子集，默认 `["i","d"]`（保持现有选句品味）；空/非法校验报错，缺失容错补默认。

## R3 管理端

- 一言卡：模式单选三档；本地库模式下显示 12 分类复选（动画/漫画/游戏/文学/原创/网络/其他/影视/诗词/网易云/哲学/抖机灵），双语标签。
- 健康卡：本地库模式下"一言"显示**未配置**（enabled=False，无网络依赖即无失败）。

## R4 语料更新与署名

- `scripts/update_quotes.py`：加固下载（jsDelivr fastly 优先 + 源站回退；公网 IP 校验直连，无 requests.get）→ 同规则重建 quotes_library.json。手动执行。
- README 增加语料来源与 AGPL-3.0 署名说明；docs/quote-library.md 标注已实现。

## 非目标

- 在线模式行为变更（保持上轮韧性）；英文一言路径；语料定期自动同步（手动脚本即可）。

## 验收

- 同日同 types 选句确定；分类筛选生效；library 模式健康卡"未配置"；旧配置（offline/缺 library_types）导入迁移无错；单测+E2E 回归全绿。

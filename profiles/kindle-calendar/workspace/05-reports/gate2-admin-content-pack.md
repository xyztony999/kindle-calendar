# Gate 2：admin-content-pack 代码→交付门控

- 日期：2026-11-24
- 模块：管理端内容包轮 1（个人语录库上传 D-06-07 / 健康数值折线 D-05-07）
- 输入：prd/api/interaction v1.0 + Gate 1 PASS；断点续跑（design complete → code）
- 轨道：会话编排（本环境无 CreateWorkflow）

**总体判定：PASS（待用户验收确认；未 commit/push，用户自行提交）**

## 实现清单（对照 API 文档）

| 项 | 落点 | 说明 |
|---|---|---|
| §2 枚举扩展 | server/settings.py | QUOTE_MODES += personal（offline 兼容别名保留）；validate/normalize 通用链路天然放行 personal，custom 非空约束仅 mode=custom；单测验证 normalize 白名单不丢字段 |
| §3 上传端点 | server/admin.py + server/quotes.py | POST /admin/api/quotes-personal：require_write、multipart file、V1–V6 整份校验（validate_personal，details 带 index/field/code/message，顶层 index=null）、save_personal 单锁原子写 data/quotes_personal.json + 热替换；不改 settings、不切 mode |
| §4 取句 | server/quotes.py | personal_quote 按日轮换（tm_yday % len），空库 OFFLINE_QUOTES 兜底；english_quote personal 同库共用、空库 local_en_quote；health() += personal_count/personal_updated（上传 meta 优先，冷启动取文件 mtime）；enabled 语义不变 |
| §5 备份/恢复 | server/admin.py | backup 白名单 += quotes_personal.json（可选缺失跳过）；restore 先验后写（与上传同一 validate_personal），非法成员 400 BACKUP_INVALID 不破坏任何现有文件；成功原子写+热替换，restored_personal 入响应；gc_assets=False 不变 |
| §6 快照存值 | server/aqi.py / server/service.py / server/health_history.py | aqi._status += cn_value（失败拍 value/cn_value 清 None → 折线断点）；weather 健康条目 += value（℃ 原值）；record() 仅有限 int/float 非 bool 存 value/cn_value，旧文件无值兼容 |
| §6 历史换算 | server/service.py | sources_history() 按当前 settings.units 逐拍换算：aqi 迷你 payload 走 units.aqi_view（国标缺失回退美标）、weather 走 units.temp_number；cn_value 不外露；响应附 units{temp,aqi} 标签 |
| §7 前端 | server/templates/admin.html + server/locale.py | #quote-modes 第四项 personal（顺序 语料库/在线/自定义/个人库）；#personal-box 条件显隐（库信息/空态引导+规范链接/上传控件/inline 错误首条+共 M 处+details 逐条/整份替换说明）；上传成功 toast 区分 radio 是否已 personal，不 markDirty 不自动保存；.sources-lines 双 SVG 折线（7 天窗口、y 自适应 10% 边距、无值断线不插值、首尾 MM-DD 刻度、units 标签、role=img+aria-label、空态文案保留高度、replaceChildren 重建、30s 轮询）；健康卡 quote 徽标/库信息按 saved mode 区分 personal/library；备份文案与恢复 toast（restored_personal）；zh/en 词条同提交 |
| R1.9 文档 | docs/quote-library.md | 状态注记「个人库上传已实现」，/docs 路由单一来源（仅改 docs/） |

## 验证结果（Gate 2 前全过）

| 套件 | 结果 | 说明 |
|---|---|---|
| 全量单测 discover | 220/220 OK | 既有 195 + 新增 tests/test_admin_content_pack.py 25 项（枚举 normalize 链路 / V1–V6 逐条索引 / Unicode 字符非字节 / 轮换与热替换 / 空库与坏文件兜底 / 上传守卫 401/403/400 / 原文件不破坏 / 备份 round-trip / 非法成员不落盘 / 旧备份兼容 / record 存值过滤 / ℃→℉ 24→75 与美标→国标 42→57 / 国标缺失回退 / 无值拍断点 / 旧历史文件兼容） |
| HTTP 全端点回归 | 150/150 passed | data/ui-redesign/http_regression_content_pack.py（8899 端口，参考 bo2 手法）：公共端点+五页双语+月历六偏移+分区全量出图（默认/℉国标/恢复三遍）；personal 空库保存→上传解耦→取句中英比对→越界文件（101 条/33 字/17 字/换行/schema2/非 JSON/缺文件）逐条索引断言→备份 zip 成员→恢复 round-trip/非法成员/旧备份→sources/history 数值比对 24℃/75℉、42 美标/57 国标 + units 标签 + cn_value 不外露 |
| E2E 1（tests/ui_admin_refinement.cjs） | PASS | 新增：四态 radio + 面板显隐几何断言；mock 上传成功（toast/库信息刷新/toolbar 状态不变不标脏）；mock 上传失败（inline 首条+共 3 处+details li=3+#1 索引）；注入固定快照折线 path M 段数=[2,2] 断点断言 + 美标/℃ 标签 + 点阵四行回归 + 切 ℉/国标标签 + 全窗口无值空态；移动端面板 ≤390px |
| E2E 2（data/verify_admin_ui.cjs） | PASS | zh/en × light/dark 截图、设备状态、键盘选项、手动预览、移动端溢出、登出、零配置写入、零 JS 错误；新增四态 radio/面板显隐/折线两行断言 |

## 实现期勘察与偏差说明

- 端点实为 /admin/api/sources/history（PRD R2.3 笔误 sources-history，以 API 文档与既有路由为准）。
- aqi 失败拍原实现保留 stale value；本轮按 R2.4「源失败断线」语义改为失败清 value/cn_value（既有行为微调，单测覆盖）。
- 个人库路径随 SETTINGS_PATH（与 settings.json 同目录），测试天然隔离；验证服务器 AQI mock 改走真实 fetch_aqi 链路（us_aqi=42、pm2_5=40→IAQI57、pm10=50→IAQI50，故 cn=57），移除 get_quote stub 以暴露 personal 真实取句路径。
- 本地 harness 现代化（data/ gitignored，不入提交）：verify_admin_ui.cjs 停留页签制前长滚动布局与旧外观面板选择器（#def-hero/#def-editor/.style-grid），本轮适配 device 分区切换、#block-styles 行式选项键盘断言、系统积木 opt-list 容器；端口 8766→8899、chromium-1234→1248。
- E2E 断言写法修正：折叠 <details> 内 li 用 textContent（innerText 隐藏态为空）。
- 验证污染防护：HTTP 回归真实保存后删 verify-settings.json + quotes_personal.json 并重启再跑 E2E；data/health_history.json 验证前备份、验证后原样恢复；真实 data/settings.json 全程未触碰。

## 待跟进项

- 用户验收确认后自行 commit & push（本轮不提交）。
- 轮 2（多城市切换 cities+active）另行立项。
- 设备端零改动；settings_version 因枚举扩展一次性轮转（设备多拉一次 env，可忽略）。
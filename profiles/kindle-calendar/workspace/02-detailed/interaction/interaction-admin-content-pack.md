# 管理端内容包交互增量（admin-content-pack）

v1.0 / 2026-11-24，继承 interaction-admin-refinement 与 v2.4 侧栏定稿（docs/v2-design.md §12）。视觉零变更：暖纸 tokens、胶囊按钮、分区头语言全部沿用；本轮只加控件与图。

## 一言分区（#section=quote）

来源 radio（#quote-modes，input.name="quote-mode"）加第四项「个人库」（personal），顺序：语料库 / 在线 / 自定义 / 个人库。radio 文案走 T.quote_mode 词条映射（同 mon/sun 先例，值→词条）。

选中 personal 时显示个人库面板（条件显隐 wrap，同 library_types/custom 列表手法）：

- 库信息行：已上传显示「N 条 · 上传于 YYYY-MM-DD HH:mm」（数据来自 /admin/api/sources 的 quote 源 personal_count/personal_updated，30s 轮询既有节拍）；未上传显示空态引导「尚未上传个人语录库。按规范准备 JSON（1–100 条，文本≤32 字、出处≤16 字）后上传」+ 规范文档链接（/docs/quote-library.md，同既有语录库链接手法）。
- 上传控件：file input（accept=".json,application/json"）+「上传」次按钮（描边淡底，非主按钮——保存才是主按钮）。选择文件后按钮才可点；上传中禁用并文案「上传中…」。
- 上传成功：toast「已上传 N 条。选择『个人库』并保存后生效」（若当前 radio 已是 personal 则「已上传 N 条，保存后生效」）；库信息行立即刷新；**不自动 markDirty、不自动保存**（文件生效与配置生效解耦）。
- 上传失败：面板内 inline 错误区（红字，同校验错误手法）显示首条错误 + 「共 M 处问题」；details 可展开逐条（索引+字段+消息，来自 error.details）；原库信息不变。
- 重传即替换：无独立删除入口（非目标）；面板常驻一行小字说明「重新上传将整份替换现有个人库」。

radio 切走再切回：面板状态保持（文件信息来自服务端，不依赖前端暂存）。personal 的脏点只随 radio 选择变化（沿用 SECTION_KEYS quote 子树快照）；上传本身不标脏。

## 设备分区健康卡（#section=device）

四源状态卡与 .sources-history 点阵（.sh-row，14px 高 SVG）保留不变。点阵之上插入 .sources-lines 块：两条原生 SVG 折线行，布局同 .sh-row（52px 标签 + 图）：

- 行 1 标签「AQI」，行 2 标签「温度」（词条随语言）；图高 48px（点阵的 ~3 倍，折线需要纵向分辨率）。
- 数据：/admin/api/sources/history 响应 sources.aqi/sources.weather 的 value（已按当前 units 换算）；x=at（7 天窗口），y 轴自适应（min/max 留 10% 边距）；x 轴首尾日期刻度（MM-DD）。
- 无值拍（旧快照/源失败/未配置）断线：相邻有值点才连线，不插值、不补零；全窗口无值显示空态文案「近七日无数值记录」（灰字，图区保留高度防跳动）。
- 单位标签：行标签右侧小字显示当前口径（℃/℉、美标/国标，来自响应 units）；units 保存后随下次轮询整体重绘。
- 描边用 --ink 系 1.5px，无填充无渐变（墨水屏审美延续）；失败拍不画红点（点阵已表达成败，折线只表达数值）。
- 轮询节拍沿用健康卡 30s；SVG 重建用 replaceChildren（同 renderCanvas 清理手法）。

## 数据组（备份/恢复）

文案更新：备份说明「配置 + 官方语料库 + 个人语录库」；恢复成功 toast 增「个人库已恢复」（restored_personal=true 时）。交互流程不变（文字链入口、文件选择、确认）。恢复失败（含个人库成员非法）沿用 BACKUP_INVALID inline 错误。

## i18n 词条（zh/en 同提交）

T.quote_mode.personal=个人库/Personal；新增：quote_personal_info（{n} 条 · 上传于 {t}）、quote_personal_empty、quote_personal_upload、quote_personal_uploading、quote_personal_replace_note、quote_personal_done（已上传 {n} 条…）、quote_personal_done_saved、quote_personal_errcount（共 {m} 处问题）、health_line_aqi、health_line_temp、health_line_empty、health_unit_us/cn、backup_personal_restored。Jinja 侧 ui.* 同步（备份说明文案）。

## 移动端与无障碍

<768px：个人库面板自然换行（file input + 按钮竖排）；折线行 52px 标签列收窄为 40px（同点阵移动端手法）。radio/上传按钮焦点环沿用；错误区 aria-live=polite；SVG 折线 role="img" + aria-label 概述（「AQI 七日趋势，最高 X 最低 Y」）。

## E2E 断言点（ui 脚本同提交更新）

- radio 四项存在且 personal 文案命中词条；选 personal 面板可见、切 library 隐藏（几何断言）。
- 上传合规文件 → 200 + 库信息行条数更新 + radio 未自动保存（toolbar 状态文案不变）；上传 101 条文件 → inline 错误 + details 条数=越界条数。
- 健康折线：注入固定快照（含无值拍）→ SVG path 段数=有值连续段数（断点断言）；units 切 ℉/国标 → 折线 y 值换算断言（HTTP 层数值比对优先于像素）。
- 备份 zip 成员断言含 quotes_personal.json；恢复链路 restored_personal。
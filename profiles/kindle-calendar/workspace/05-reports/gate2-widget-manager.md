# Gate 2 报告：widget-manager（我的积木管理页 / 图片链路修复 / 编辑器对齐）

- 日期：2026-10-23
- 结论：**PASS（待用户验收）**——本地验证全绿，未提交；真机验收沿用项目惯例由用户确认。

## 交付清单

### 代码（未提交，工作区待用户 review）
| 文件 | 变更 |
|---|---|
| server/templates/admin.html | 主视图新增「我的积木」卡片（新建/编辑字段/删除/素材删除）；弹窗 def-editor 移除、放置列表简化 + 「管理我的积木」入口；吸附（候选线+参考线+Alt禁用+开关持久化）；缩放/落点吸附；方向键微调（Shift×10）；上传 OSS 门控；取消编辑素材删除确认 |
| server/locale.py | 中英各新增 16 条文案 |
| server/storage.py | 空文件报 `ASSET_EMPTY`；`get_object` 未配置 OSS 写 warning 日志 |
| server/admin.py | 上传接口空文件 400 `ASSET_EMPTY`；widget-catalog 返回 `storage.configured` |
| server/render/placed.py | 缺图画语言无关占位（灰框对角线）；透明 PNG 白底合成 |
| server/app.py | `MAX_CONTENT_LENGTH=4MB` + 413 JSON |
| server/layout.py | **存量 bug 修复**：`widget_defs`/模板中心样式校验从过期 `STYLES=(hero,rows)` 改为 `DATA_STYLES` 四种（保留 hero≤3/其余≤6 字段上限），删除 STYLES 常量 |
| docker-compose{,.acr,.image,.baota}.yml | 透传 `OSS_*` 与 `WIDGET_CENTER_URL`（此前 .env 配了也进不了容器） |
| DEPLOY.md | 新增「图片素材存储（OSS）」章节 + 2 条 FAQ |
| tests/test_layout.py | 新增 `test_asset_guards_and_catalog_storage_flag`（catalog storage 标志 / ASSET_EMPTY / 透明 PNG 白底 / 缺图占位） |
| tests/ui_admin_refinement.cjs, ui_data_styles.cjs | 适配新 UI（卡片新建、`.widget-row .w-add` 放置、上传门控、方向键微调、catalog storage mock）；顺带修复两脚本自 81aab26 起选择器过期的问题 |

### 验证结果
- `python -m unittest discover -s tests`：**90 项 OK**（含新增 1 项）
- `compileall`：通过；`grep STYLES` 残留：无
- E2E（Playwright + 隔离服务）：
  - `ui_admin_refinement.cjs` PASS（含：卡片新建+放置、方向键 1px 微调、卡片删除、OSS 未配置禁用且零请求、迟到上传不进草稿、中英/明暗/移动端）
  - `ui_data_styles.cjs` PASS（四样式 PNG 差异、旧版继承、两页隔离、恢复默认；grid+4字段预览不再 400）

### 实现过程中发现并修复的存量问题
1. `layout.py STYLES` 过期常量导致 horizontal/grid 数据积木定义无法通过校验（旧弹窗硬编码 rows 掩盖了问题）——E2E 暴露，已修复并回归。
2. docker-compose 系列不透传 OSS 变量——已修。
3. 两个 ui_*.cjs 自 81aab26 行式列表重设计后选择器过期——已随本次适配。

### 部署注意（用户操作）
1. 服务器 `.env` 补 `OSS_*`（见 DEPLOY.md 第 6 节），并同步新的 `docker-compose.acr.yml` 后 `up -d`，图片上传才可用。
2. compose 文件本身不随镜像更新，需把仓库新版 compose 同步到服务器（DEPLOY.md 已有此惯例提示）。

### 保留待办
- Kindle 真机验收（吸附后版面、缺图占位实际观感）。
- 模板中心若曾下发 horizontal/grid 数据模板，部署新版后即可被接受（此前被旧校验拒绝）。

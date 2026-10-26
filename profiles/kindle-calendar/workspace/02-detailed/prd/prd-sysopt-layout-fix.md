# PRD：外观面板系统/文字选项排版修复（sysopt-layout-fix）

| 属性 | 值 |
|------|-----|
| 模块 | sysopt-layout-fix |
| 版本 | v1.0 |
| 状态 | 待 Gate 1 确认 |
| 最后更新 | 2026-10-26 |
| 功能类型 | 缺陷修正（纯前端模板/样式）。无聚合根、无接口变更、无新文案 |
| 输入 | 2026-10-26 用户反馈：选择时钟积木时，外观选项排版有严重错误（附截图）。D0 对照 `server/templates/admin.html`、`server/layout.py` SYSTEM_OPTIONS，81aab26 引入的系统积木选项渲染复用了数据样式卡 CSS |

## 0. 需求澄清（D0 诊断）

### 0.1 复现与量化（隔离测试服务器 8766 + Playwright，2026-10-26）

| 场景 | 表现（量化） | 严重度 |
|------|--------------|--------|
| 时钟积木（`size` choice，3 档） | 3 个单选钮中心点**完全重合于 (845,267)**（`.style-option input` 绝对定位 top:10/right:10 叠在同一格右上角）；且整行包在一个 `<label>` 内，**点「小」的文字实际激活「大」**（实测 lg checked） | 阻断 |
| 天气积木（6 个 bool 开关） | 每格 132×23px，勾选框漂在格子右上角、离文字约 50–70px，视觉上控件与标签分离 | 严重 |
| 文字积木（对齐/字号 fieldset） | 每个单选钮 `inside:false` 溢出其标签盒，下沉裁切 | 严重 |
| 数据积木样式卡（该 CSS 的原设计用途） | 正常（钮藏卡片右上角是设计意图，`#block-style-*` 不动） | — |

### 0.2 根因

`renderSystemOptions`（81aab26 引入）与 `renderTextOptions`（editor-manage 未提交代码）把表单行式控件塞进数据样式卡的 `.style-option`/`#block-styles.style-grid`（两列卡片网格）体系：

1. `.style-option input { position:absolute; top:10px; right:10px }` 为「卡片右上角选钮」设计，choice 多钮全部叠到同一点；inline label 上则溢出盒外。
2. choice 整行（标签+全部档位）包进单个 `<label>`：HTML 语义上 label 只能关联第一个控件，点档位文字激活错误选项。
3. `span` 上设置 `for` 属性无效（HTML 不允许）。

### 0.3 类型与边界

| 维度 | 结论 |
|------|------|
| 匹配 | 部分匹配。外观面板、SYSTEM_OPTIONS schema、选项读写链路均已存在，坏的只是呈现层 |
| 类型 | 修正（bug fix）。无架构变更：BA/AA/FL 不动；D3 无接口变更（`/admin/api/widget-catalog` schema 与选项持久化字段不变）；D4 无交互契约变更（无新增文案与页面） |
| 影响面 | 仅 `server/templates/admin.html`：CSS 增补 + `renderSystemOptions`/`renderTextOptions`/`renderBlockAppearance` 局部重构。数据样式卡路径 DOM/CSS/id 不动（`#block-style-*` 有 E2E 依赖） |

## 1. 目标

选中系统积木（时钟/天气/页眉/日出/一言/月历/黄历）或文字积木时，外观面板呈现可用的表单行式选项；时钟场景必须可用且语义正确。

## 2. 方案（推荐 A）

**A（推荐）行式选项布局，与样式卡解耦**

- 新 CSS：`.opt-list`（`#block-styles` 单列容器变体）、`.opt-row`（flex/wrap 行，选项标签在左）、`.opt-pick`（内联 `<label>`：控件+文字，点文字即选中该档）。
- `renderSystemOptions`：bool → `<label class="opt-row">`（checkbox 在前+文字）；choice → `div.opt-row`（左标签 + 每档独立 `label.opt-pick` 包 radio+文字）。
- `renderTextOptions`：两个 fieldset 内的选项改用 `.opt-pick`。
- `#block-styles` 按渲染路径切换容器类：数据样式 → `style-grid`（原样）；系统/文字选项 → `opt-list`。
- 移除 `span[for]` 无效属性用法。

**B（备选）最小覆盖补丁**：仅给系统选项加 `.style-option.compact input { position:static }` 等覆盖规则。改动更小，但两种语义继续共用卡片类，点文字激活错误选项的问题需另行处理，后续每加选项都再打补丁。

**C 重构统一选项组件**：过度设计，否决。

## 3. 验证计划

- 单测：服务端零改动，跑全量（100 项）确认无回归。
- E2E（ui_admin_refinement.cjs 扩一段）：选中时钟 → 三档单选钮两两几何不重叠 + 点「小」文字后 `sys-opt-size-sm` checked；选中天气 → 各勾选框 `inside` 其 label 盒；文字积木 → 各单选钮 inside 其 label 盒。
- 回归：ui_data_styles.cjs 全量（数据样式卡不受影响）；修复前后截图对比入 `data/ui-bugfix/`。
- 中英双语、明暗主题下目检截图。

## 4. 不做

- 不改 SYSTEM_OPTIONS schema、校验、normalize、渲染链路（81aab26 已交付且正确）。
- 不改数据样式卡（`#block-style-*`）的 DOM/CSS/交互。
- 不新增 i18n 文案（复用现有标签与 choiceLabels 映射）。
- 不改 editor-manage 未提交改动的其他内容（Gate 2 待验收范围保持原样，本修复叠加其上）。

## 更新记录

| 版本 | 日期 | 更新说明 |
|------|------|---------|
| v1.0 | 2026-10-26 | D0 复现定根因；方案 A 设计；验证计划 |

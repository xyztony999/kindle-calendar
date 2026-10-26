# Gate 2 报告：sysopt-layout-fix（外观面板系统/文字选项排版修复）

- 日期：2026-10-26
- 结论：**PASS（待用户验收）**——两条 E2E 全绿（含新增三场景几何断言）；Python 单测 93/100，7 项失败全部归属用户并行未提交改动（见下），与本修复无关。未提交。

## 交付内容（仅 `server/templates/admin.html` + `tests/ui_admin_refinement.cjs`）

**方案 A 实现**：
- 新 CSS：`.opt-list`（单列容器）/`.opt-row`（flex 换行行）/`.opt-name`/`.opt-pick`（内联 label：控件+文字）；native 控件继承全局 `accent-color: var(--ink)`，明暗主题均正常。
- `renderSystemOptions` 重写：bool → `label.opt-row`（勾选框在前+文字）；choice → `div.opt-row`（选项名 + 每档独立 `label.opt-pick` 包 radio+文字，点文字即选该档）；改选后焦点恢复到该控件（键盘可达）。
- `renderTextOptions`：对齐/字号两组改用 `.opt-pick`；`#block-styles` 容器类按渲染路径切换（数据样式 `style-grid` 原样 ↔ 系统/文字 `opt-list`）；fieldset legend 随系统选项切换为「外观选项/Appearance options」（复用既有 i18n 键，无新文案）。
- 移除无效的 `span[for]` 属性用法与内联 padding hack。
- **红线遵守**：数据样式卡 `#block-style-*` 的 DOM/CSS/id 零改动；服务端零改动。

## 验证

| 项 | 结果 |
|---|---|
| E2E ui_admin_refinement.cjs | PASS（新增：时钟三档单选钮两两不重叠+全部在行盒内+点「小」激活 `sys-opt-size-sm`+焦点恢复；天气开关 inside 行盒；文字积木 6 钮 inside 标签盒+点「右」激活 `#block-align-right`；legend 断言） |
| E2E ui_data_styles.cjs（数据样式卡回归） | PASS |
| Python 单测 | 93/100 过；**7 项失败与本修复无关**，归属用户并行未提交工作 |
| 截图 | `data/ui-bugfix/`：clock-before/after、clock-after-dark、weather-before/after、text-before |

7 项失败归属证据：
- `test_system_options.test_block_options_normalization`：断言 `{'size':'lg'}` 实得 `{'size':'lg','hour12':False}`——`hour12` 为 layout.py 于 **14:21:48**（本会话进行中）新增的外部改动，测试尚未随其更新。
- `test_layout` ×2：`ics.urls` ICS_INVALID（almanac.py 未提交改动的既有状态）。
- `test_kindle_device` ×5：dash.sh 拉取确认顺序（PW2 后续工作既有状态）。
以上均不在本修复（admin.html 模板）的导入链上。

## 过程记录

- 会话中途检测到 `server/layout.py` 被外部修改（新增 clock `hour12` 选项）——本修复为 schema 驱动渲染，自动适配新选项，E2E 断言改为不硬编码选项数量。
- 首次 E2E 运行发现面板 4 控件（含 hour12）与设计时 3 控件不符，正是上述外部改动所致。

## 保留待办

- 用户 commit & push（可与 editor-manage 未提交工作合并提交）后 CI/CD 自动部署；浏览器端目检截图确认。

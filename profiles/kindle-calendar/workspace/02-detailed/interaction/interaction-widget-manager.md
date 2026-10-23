# 交互：widget-manager（我的积木管理卡片 / 图片链路 / 编辑器吸附）

- 版本：v1.0（2026-10-23）

## 1. 我的积木管理卡片（#card-widgets，主视图「页面与轮播」之后）

结构：

```
┌ 我的积木                      [+ 新建数据积木] ┐
│ （表单：默认收起；新建/编辑共用）              │
│   名称 [____]  字段复选（catalog.fields）      │
│   首字段提示 · [保存] [取消]                   │
│ ● 积木行：名称 | 字段摘要 | 用于 N 页 | ✎ | 🗑 │
│ 图片素材                                        │
│ ● 素材行：a1b2c3d4 | 图片素材 | 🗑            │
└────────────────────────────────────────────────┘
```

- 新建：点「+ 新建数据积木」展开空表单；保存成功收起表单、行出现在列表。字段 1–6 限制不满足时 toast 报错。
- 编辑：行内 ✎ 展开表单并预填；保存后字段变更自动重算受影响样式（无需用户操作）。
- 删除积木：确认弹窗沿用现有文案（含引用页数）；「编辑器内取消可撤销」的说明仅当弹窗打开期间适用。
- 删除素材：确认「删除图片素材 {id}？将从 {n} 个页面移除；保存后从云端存储一并清除」。
- 行复用现有 `.widget-row` 样式；管理卡片不承担放置职责。

## 2. 版面编辑弹窗调整

- 左栏「我的积木」：仍显示数据积木与素材行用于点击/拖放放置；移除行内 ✎/🗑；标题下增加「管理我的积木」链接按钮 → 完成编辑（保留草稿）并平滑滚动到管理卡片。
- 右栏：移除「新建数据积木」面板（#def-editor）；保留「当前积木外观」。
- 上传图片按钮：`catalog.storage.configured=false` 时禁用，title 提示「上传图片需要服务器配置阿里云 OSS」。
- 取消编辑（Esc/遮罩/取消按钮）：若本次会话上传过素材，先确认「取消将一并删除」；拒绝则留在编辑器。

## 3. 对齐吸附（画布工具栏）

- 工具栏新增「对齐吸附」开关（默认开，localStorage 记忆）；旁注说明：拖动时自动对齐边距与其他积木，Alt 临时关闭，方向键微调（Shift ×10）。
- 拖动：距离候选线 ≤8px 吸附并显示参考线（竖/横细线）；松手隐藏。
- 缩放：右/下边缘吸附同一组候选线。
- 键盘：选中积木后 ↑↓←→ 1px、Shift 10px；焦点在输入框时不劫持；微调后焦点保持在积木上。

## 4. 文案（locale 新增）

zh：widgets_h2 我的积木 / add_data_widget 新建数据积木 / cancel_widget 取消 / edit_widget 编辑 / used_pages 用于 {n} 个页面 / unused_widget 未使用 / widget_fields_invalid 名称必填，字段选 1–6 项 / max_defs 最多 12 个数据积木 / image_assets_h2 图片素材 / delete_asset 删除素材 / delete_asset_confirm … / manage_widgets 管理我的积木 / snap_align 对齐吸附 / snap_hint … / asset_discard_confirm …

en 对应：My Blocks / New Data Block / Cancel / Edit / Used on {n} page(s) / Unused / Name required; pick 1–6 fields / Up to 12 data blocks / Image Assets / Delete asset / … / Manage my blocks / Snap / … / …

（复用既有：my_blocks、new_data、widget_name、save_widget、first_field、image_asset、oss_missing、delete_widget(_confirm)、rename_widget、add_text、upload_image。）

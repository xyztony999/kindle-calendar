# API：widget-manager（我的积木管理页 / 图片链路修复 / 编辑器吸附）

- 版本：v1.0（2026-10-23）
- 原则：不新增积木 REST 资源；所有变更向后兼容。

## 1. 变更清单

### A-1 GET /admin/api/widget-catalog（修改）

响应 `data` 新增字段：

```json
"storage": {"type": "oss", "configured": false}
```

`configured=false` 时前端禁用上传图片入口并提示（文案 `oss_missing`）。

### A-2 POST /admin/api/assets（修改）

- 无 `file` 字段或文件名为空 → `400 ASSET_EMPTY「未收到图片文件」`（原为误报 `ASSET_TOO_LARGE`）。
- 其余行为不变（≤2MB、JPEG/PNG、写 OSS、`gc_assets=False` 立即落库）。

### A-3 错误码

| code | HTTP | 场景 | message |
|---|---|---|---|
| `ASSET_EMPTY` | 400 | multipart 无文件 / 字节为空 | 未收到图片文件 |
| `REQUEST_TOO_LARGE` | 413 | 请求体 > 4MB（全站 `MAX_CONTENT_LENGTH`） | 请求体过大 |
| `OSS_NOT_CONFIGURED` | 400 | 上传时未配置 OSS（不变） | 未配置阿里云 OSS，暂时不能上传图片 |

### A-4 渲染行为（非 HTTP）

- `render/placed.py paint_image(source=None)`：画语言无关缺图占位（灰框+对角线），替代纯白。
- `paint_image` 透明模式（RGBA/LA/PA/P+transparency）先白底合成再灰度。
- `storage.get_object`：未配置 OSS 时 `log.warning("OSS 未配置，无法读取素材 key=…")`。

### A-5 部署环境变量（docker-compose*.yml 透传）

```
OSS_ENDPOINT / OSS_BUCKET / OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET / OSS_PREFIX
WIDGET_CENTER_URL
```

模板见 `.env.example`；DEPLOY.md 新增 OSS 开通章节。

### A-6 校验修复（实现中发现）

`server/layout.py` 中 `widget_defs[*].style` 与模板中心条目样式校验原先使用过期常量 `STYLES=("hero","rows")`，导致 horizontal/grid 数据积木定义无法通过校验（保存/预览 400）。已改为 `DATA_STYLES` 四种外观，字段数量上限不变（hero≤3，其余≤6）。`STYLES` 常量已删除。

## 2. 不变项

- `settings/save` 仍是积木 CRUD 与素材 GC（`drop_unreferenced_assets` + OSS delete）唯一落库路径。
- `layout-preview` 草稿预览契约不变。
- 设备端 env/分区 PNG 契约不变。

# API：quote-library-refresh

- 版本：v1.0（2026-10-27）

## 新端点

### POST /admin/api/quotes-refresh（require_write）
拉起后台 daemon 线程执行 `quotes.refresh_library(force=True)`，立即返回：

```json
{"ok": true, "data": {"started": true}}                    // 已启动
{"ok": true, "data": {"started": false, "running": true}}  // 已在刷新中（防重入）
```

结果经 `GET /admin/api/sources` 的 quote 条目反映（30s 轮询）。

## health() 扩展（quotes._status）

新增字段：`{"library_updated": "ISO|null", "library_count": int, "refreshing": bool}`；
`error` 语义扩展：语料刷新失败写入此处（在线一言失败仍写入同一 error，以最近一次为准）。

## 文件契约

- `data/quotes_library.json`：与内置同构（license/source/updated/types/sentences）；刷新成功后存在，**优先于**镜像内置 `server/quotes_library.json`。
- `data/quotes_meta.json`：`{"updated","source","count","last_error","fetched_at"}`（原子写，损坏忽略）。

## env/其他

- `QUOTES_LIBRARY_TTL_S`（可选环境变量覆盖，默认 7*86400）。
- `scripts/update_quotes.py` → 薄封装 `quotes.refresh_library(force=True)`。

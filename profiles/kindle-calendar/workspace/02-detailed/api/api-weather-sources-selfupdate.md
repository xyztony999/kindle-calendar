# API：weather-sources-selfupdate

- 版本：v1.0（2026-10-26）

## 新端点

### GET /api/v1/script
下发镜像内 `kindle/dash.sh` 原文（text/plain）。响应头 `ETag`/`X-Script-Md5` = md5 hex；`Cache-Control: no-store`。文件缺失 → 404 文本。

### GET /admin/api/sources（会话）
```json
{"ok": true, "data": {"sources": [
  {"id": "weather|aqi|quote|ics", "ok": bool, "at": "ISO 时间|null", "error": "str"}
]}}
```
内存态（重启清零）；名称文案在前端按 id 取 locale。

## env 新增
```
DASH_MD5="<md5 of dash.sh>"
DASH_SCRIPT_URL="<base>/api/v1/script"
```

## payload 变更
- `weather.current.apparent: number|null`
- `weather_alerts: [{"kind":"cool","drop":number},{"kind":"rain","prob":number}]`（可能为空数组）

## SYSTEM_OPTIONS 变更
- weather 增 `show_feels`（bool，默认 False）

## FIELD_DEFS 变更
- 增 `weather.apparent`（number）→ FIELD_IDS=29

## settings 无变更；dash.sh 契约
- 新函数 `self_update()`：config 变量 `DASH_AUTOUPDATE`（默认 1）；md5 比对→下载→校验→备份 dash.sh.old→原子替换→`nohup` 重启 + `exit 0`（trap 清理生效）；写 `$STATE_DIR/updated.flag` 与 `$DASH_DIR/update.log`。

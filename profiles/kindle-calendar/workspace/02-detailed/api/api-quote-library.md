# API：quote-library

- 版本：v1.0（2026-10-27）
- settings 变更（schema 3 不变，缺失容错）：

```json
"quote": {
  "mode": "library | online | custom",   // 默认 library；旧 offline 迁移为 library
  "custom": [...],
  "library_types": ["i", "d"]            // a-l 子集，默认诗词+文学
}
```

- 校验：mode ∈ (online, library, custom, offline*)（*仅兼容旧数据，normalize 迁移）；library_types 非空且 ⊆ abcdefghijkl，否则 `QUOTE_LIBRARY_INVALID`。
- payload/渲染/设备端契约：零变化（get_quote 返回结构不变）。
- 健康源：quotes.health().enabled 仅在 online 为 True。
- 内置文件 `server/quotes_library.json` 随镜像分发；`scripts/update_quotes.py` 手动重建。

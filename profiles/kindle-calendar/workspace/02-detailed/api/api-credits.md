# API：credits

- 版本：v1.0（2026-10-29）

## 新端点

### GET /credits
HTML 页面（组件致谢）。语言解析与 `/` 一致：`?lang=` > `kc_lang` cookie > Accept-Language > zh；命中 `?lang=` 时写回 cookie。模板 `credits.html`，文案 `landing.credits_copy(lang)`。

## 变更

- `index()` 的 endpoints 字典新增 `"/credits": "开源组件说明 / Open-source credits"`；`landing._EN_ENDPOINTS` 同步英文描述。
- 无 settings/设备端契约变化。

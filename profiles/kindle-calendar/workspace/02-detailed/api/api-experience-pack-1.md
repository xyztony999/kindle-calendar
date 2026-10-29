# API：experience-pack-1

- 版本：v1.0（2026-10-29）

## settings 变更（schema 3 不变，缺失容错）

```json
"rotation": {"enabled": true, "suppress_s": 120, "fetch_interval_s": null},   // null|int(300-86400)
"ics": {"urls": [{"url": "https://…", "enabled": true}]}                       // 旧 str 自动迁移
```

validate：fetch_interval_s 缺失/None 通过（不下发语义）；int 时域外报错。ics 项 str 视为 enabled:true，dict 校验 url（https/≤500）+ enabled(bool)。
normalize：rotation 三键重建（缺失补 null）；ics 统一产出对象数组。

## 块结构变更

- 新系统积木 `wallpaper`（DESIGN 758×980）；options：`mode` choice(fixed/daily, 默认 daily) + 自动注入 border。
- wallpaper 块级字段 `asset`（fixed 模式必填且须存在于 assets；daily 忽略）；normalize 白名单保留。

## payload 变更

- 新增 `anniv_today: [name,…]`（今天命中的纪念日名；参与 data_fingerprint）。

## env 变更

- rotation.fetch_interval_s 有值时下发 `FETCH_INTERVAL=<n>`；缺省不下发。旧版 dash.sh 静默忽略。

## 渲染行为

- render_placed 新增 wallpaper 分支：fixed→paint_image(images[asset])；daily→按 `int(iso.replace("-","")) % len(sorted(ids))` 轮换；空/缺图→缺图占位。
- anniv_today 非空时 pageblank 画整页细双线框（PAPER 底不变，INK/MID 细线）。

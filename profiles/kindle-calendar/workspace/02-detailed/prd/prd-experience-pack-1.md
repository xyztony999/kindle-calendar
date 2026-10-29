# PRD：体验包一轮（experience-pack-1：每日一图 / 生日特别版式 / 拉取间隔可调 / ICS 源启停）

- 版本：v1.0（2026-10-29 Gate 1 确认，用户按推荐执行：分两轮 / wallpaper 双模式 / 备份不嵌素材）
- 七项打包之轮 1；轮 2（备份/健康折线/docs 单一来源）另行立项。

## R1 每日一图（wallpaper 系统积木）

- R1.1 新系统积木 `wallpaper`，设计尺寸 758×980（全屏，避开顶部状态栏）；任意页可放置，放底层 z 即整页壁纸。
- R1.2 外观选项 `mode`：`daily`（默认，按日期确定性轮换取图）/ `fixed`（钉住指定素材，块级 `asset` 字段指定）。
- R1.3 不走 paint_system（需素材字典），render_placed 单独分发，复用 paint_image（灰度/抖动/居中）；素材字典为空或 fixed 未选素材时画缺图占位。
- R1.4 管理端：调色板自动出现；选中后外观面板显示模式单选 + fixed 时素材单选列表。
- R1.5 校验：fixed 模式 asset 必须存在于素材列表；normalize 保留 asset。

## R2 生日/纪念日当天特别版式

- R2.1 payload 新增 `anniv_today`（今天命中的纪念日名列表）。
- R2.2 命中时 pageblank 层画整页细装饰双线框（页眉 notes 行已自动显示纪念日名，沿用）；不反色（与设备端 INVERT 手势冲突）；随 data_fingerprint 自动跨天失效。

## R3 拉取间隔可调

- R3.1 `rotation.fetch_interval_s`（int，300–86400，缺省/空=不下发=设备 config.sh 的 INTERVAL 兜底）。
- R3.2 env 新增 `FETCH_INTERVAL`（有值才下发）；dash.sh 在 source env 后消费（数字夹紧校验），旧版脚本静默忽略。
- R3.3 管理端「页面与轮播」卡 suppress 旁加输入框；留空=用设备本地配置。

## R4 ICS 源启停

- R4.1 `ics.urls` 升级为 `[{url, enabled}]`；旧字符串数组导入自动迁移（enabled=true），不 bump schema。
- R4.2 消费侧只拉 enabled 的源；全部禁用=未配置语义（健康卡显示未配置）。
- R4.3 管理端每行加启停开关。

## 非目标

- 页眉徽标（notes 行已显示纪念日名）；壁纸自动置底（用户用现有 z 序按钮控制）；下拉间隔可调看板。

## 验收

- wallpaper daily 跨天换图、fixed 钉住；空素材占位；校验拒绝不存在的 asset。
- anniv_today 命中日装饰框出现、次日消失（缓存指纹变化）。
- FETCH_INTERVAL 下发/消费/兼容三向正确；管理端留空不下发。
- ICS 禁用源不拉取、旧配置迁移无损。

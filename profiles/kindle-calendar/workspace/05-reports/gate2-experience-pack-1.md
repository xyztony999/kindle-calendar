# Gate 2 报告：experience-pack-1 轮 1（每日一图 / 生日版式 / 拉取间隔 / ICS 启停）

- 日期：2026-10-29
- 结论：**PASS（待用户验收）**——131 项单测全过、E2E PASS、像素级冒烟确认壁纸真正渲染；未提交。

## 交付清单

### R1 每日一图（wallpaper 积木）
- SYSTEM_WIDGETS/DESIGN(758×980)/SYSTEM_LABELS/SYSTEM_OPTIONS(mode: daily 默认/fixed) 注册；border 自动注入。
- **render_placed 专用分支**（DESIGN 泛化分支排除 wallpaper——素材字典只在 render_placed 可见）：fixed→指定素材；daily→`int(iso数字) % len(sorted(ids))` 确定性轮换；空素材→缺图占位。
- 校验：fixed 模式 asset 必须存在于素材列表；normalize 保留 asset。
- 管理端：调色板自动出现；外观面板模式单选（切 daily↔fixed 即时刷新）+ fixed 时素材单选（无素材提示 OSS 未配置）。
- 使用：放置后拉满屏（0,44,758,980），用层级按钮置底；分区 env 泛化下发，设备端零改动。

### R2 生日/纪念日特别版式
- payload 新增 `anniv_today`（今天命中纪念日名列表，参与 data_fingerprint 跨天自动失效）；命中时 pageblank 层画整页细双线框；页眉 notes 行沿用（已显示纪念日名）。

### R3 拉取间隔可调
- `rotation.fetch_interval_s`（300–86400，缺省 null=不下发）；env `FETCH_INTERVAL` 有值才下发；dash.sh source env 后消费（数字+域校验才采纳，否则保持 config.sh 值）——旧版脚本静默忽略；管理端「页面与轮播」卡新输入框（留空=设备默认）。

### R4 ICS 源启停
- `ics.urls` 升级 `[{url, enabled}]`，str 自动迁移不 bump schema；消费侧过滤 enabled；管理端每行启停 checkbox（禁用行置灰）；全部禁用=未配置语义。

## 验证

- 131 项单测 OK（新增 wallpaper 校验/normalize、fetch_interval 往返、anniv_today payload；test_ics 断言更新为对象数组）。
- E2E 两条 PASS + 临时脚本针对性冒烟（fetch-interval 900/空/200 三态、ics checkbox payload、wallpaper 放置与面板交互）全过。
- 像素冒烟：daily 两天选中不同素材、输出非纯白且不同（修复后）。
- **验证抓出并修复严重 bug**：wallpaper 进 DESIGN 后 paint_system 分支优先命中 → 渲染恒为纯白（专用分支成死代码）——DESIGN 分支排除 wallpaper 修复；顺带修 mode 切换不即时刷新素材区的 UX。

## 部署注意

- 旧版 dash.sh 忽略 FETCH_INTERVAL（拉取间隔不生效），拷贝新版脚本后生效；其余三项纯服务端。
- wallpaper 生效需重新保存设置（分区 env 下发）。

## 保留待办

- 真机：壁纸观感（抖动后全屏图片）、生日装饰框、拉取间隔实际节拍。

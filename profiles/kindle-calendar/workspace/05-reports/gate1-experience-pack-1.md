# Gate 1 报告：experience-pack-1（体验包一轮）

- 日期：2026-10-29
- 启动模式：增量（master @ c0c4995）；七项打包第一轮（轮 2：备份/健康折线/docs 单一来源另行立项）
- 结论：**PASS**（用户按推荐执行：分两轮 / wallpaper 双模式 / 备份不嵌素材）

## 决策

| 决策点 | 选择 |
|---|---|
| 交付节奏 | A 分两轮 |
| 每日一图 | wallpaper 系统积木 + fixed/daily 双模式 |
| 备份范围（轮 2） | 不嵌素材二进制（OSS key 跨实例复用） |

## 关键勘察结论

- 每日一图否决"特殊页面类型"路线：设备端对自定义页零特殊处理，积木层实现零设备改动且五页可放；wallpaper 需 render_placed 单独分发（paint_system 无 images 参数）。
- 生日版式否决整页反色：与设备端 INVERT 手势冲突且 style 常量无主题开关；pageblank 装饰框 + 页眉 notes（已有）双落点。
- 拉取间隔归属 rotation 子键（normalize 封闭结构顶层键成本高）；设备端 env 优先、config.sh 兜底，旧脚本静默兼容。
- ICS 启停升级 [{url,enabled}] 不 bump schema（normalize 容错迁移，代价仅设备多拉一次 env）。
- docs 单一来源（轮 2）：Flask 路由 + Dockerfile COPY docs/，否决 symlink（Windows/构建双坑）。

## 风险

- wallpaper 与 pageblank 的绘制顺序：壁纸需用户置底 z（现有层级按钮支持）；报告注明。
- FETCH_INTERVAL 消费点在 fetch_consume source 之后（FETCH_RETRY 赋值前），需精确插位。

# 设计决策（源自 README）

| 决策 | 结论 | 理由 |
|------|------|------|
| D-1 架构 | 云端渲染 + Kindle 拉取 | 无 PC 常开；Kindle 仅做显示 |
| D-2 局刷策略 | 时钟本地字形 + 分区 ETAG | A2 零网络每分钟可行；分区仅变化才拉 |
| D-3 残影治理 | 每日 03:00 全刷 | eink 维护 |
| D-4 服务框架 | Flask v2（Python）+ Pillow 渲染 PNG | 轻量、容器友好 |
| D-5 部署矩阵 | Render 免费版 / Docker（通用/VPS/宝塔/ACR） | 免费休眠可接受；自托管多路径 |
| D-6 配置 | 环境变量 + config.yaml | Render/宝塔双形态兼容 |

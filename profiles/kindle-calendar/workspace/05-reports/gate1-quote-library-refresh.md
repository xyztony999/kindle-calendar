# Gate 1 报告：quote-library-refresh

- 日期：2026-10-27
- 启动模式：增量（叠加未提交的 quote-resilience、quote-library）
- 结论：**PASS**（用户按推荐执行：7 天自动 / 行内按钮 / 失败健康行+toast / 脚本薄封装）

## 关键设计依据（勘察）

- 热替换安全：`library_quote` 每次重取全局引用，`_library_sentences` 锁内替换即生效；library 模式不经过 `_day_cache`。
- 持久化选 data/ volume（先例：device-status.json；镜像层写会升级即丢且与内置冲突）；元数据独立 `data/quotes_meta.json`（normalize 剥未知键，进 settings 不值得；模板 HeartbeatLog）。
- 自动刷新挂 `_refresh_ics` 线程尾部（请求触发+TTL 判定，与既有周期语义一致，无独立定时器）。
- 手动刷新异步化：12 文件串行最坏数十秒，POST 即返 ack，前端 disabled+轮询。
- `_fetch_ics` 2MB 限长不构成障碍（单分类文件约 300-400KB）。

## 风险

- data/ 库与镜像内置可能版本漂移——meta 文件记录来源与 updated 供辨识；"恢复内置"不在本轮（删 data/ 文件即可）。
- health().error 为在线一言与语料刷新共用（最近一次为准），前端文案区分靠上下文。

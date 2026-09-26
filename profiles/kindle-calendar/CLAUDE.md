# Kindle 台历知识注入

把闲置 Kindle 变成低功耗常亮的电子天气台历：**服务部署云端**（Render/Docker），Kindle 越狱后经 WiFi
自行拉取 PNG，无需 PC 常开。

分工：云端 Flask v2 渲染（/api/v1/dashboard：天气/农历/节气/月相/一言/节假日；/r/today/*.png 分区灰度图，
ETAG 变化才需重拉；/dashboard.png v1 整图兼容）；Kindle 端 dash.sh v2 主循环（时钟本地字形拼装每分钟 A2 局刷
零网络；分区图 GC16 局刷；凌晨 03:00 全刷清残影；无 fbink 回退 eips 整图）。

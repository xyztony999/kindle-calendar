# 交互：quote-library-refresh

- 版本：v1.0（2026-10-27）

## 数据源卡「一言」行

```
● 一言  [正常]  3 小时前 · 7,684 条   [刷新语料库]
  （刷新中：按钮文字变「刷新中…」并禁用；健康行显示"刷新中"状态）
  （失败：行下灰字错误摘要 + toast「语料库刷新失败」）
```

- 点击→按钮立即禁用防重入→后台执行（不等）→30s 轮询或手动刷新健康卡看结果；成功 toast「语料库已更新（N 条）」。
- 语料更新时间用 relTime（刚刚/n 天前）。

## 文案（locale 新增）

zh：refresh_library 刷新语料库 / refresh_library_busy 刷新中… / library_refresh_ok 语料库已更新（{n} 条）/ library_refresh_fail 语料库刷新失败 / library_refreshing 语料刷新中
en：Refresh library / Refreshing… / Library updated ({n} entries) / Library refresh failed / Refreshing library

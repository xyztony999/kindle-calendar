# API / 契约设计：v2-aqi（空气质量显示）

| 属性 | 值 |
|------|-----|
| 模块 | v2-aqi |
| 版本 | v1.0 |
| 状态 | 待评审 |
| 最后更新 | 2026-10-10 |
| 输入 | prd-v2-aqi.md v1.0 |
| 技术规约 | 无激活技术栈；沿用 v2-pages 契约规约（api-v2-pages.md §3.1） |

## 1. 模块设计概述

### 1.1 业务背景及目标

为 AQI 显示定义数据契约：新增空气质量数据源接入、payload 扩展；渲染变化发生在**现有分区内**（今日页 sun 分区右半、详情页 indices 卡），env/分区路由契约零变化。

### 1.2 边界说明

| 边界 | 说明 |
|------|------|
| 做 | AQI 数据拉取与降级、payload `aqi` 节、sun/indices 分区渲染内容更新、US→中文等级映射 |
| 不做 | 设备端任何改动（env/手势/刷新逻辑零变化）、中国 AQI 计算、月相数据删除（场景图仍用） |

### 1.3 设计决策

| # | 决策 | 理由 |
|---|------|------|
| AD-0 | 管理模式：不适用（只读展示契约） | 同 v2-pages |
| AD-1 | AQI 画进现有 sun/indices 分区，**不新增分区** | env 契约零变化，设备端零更新 |
| AD-2 | US AQI 直接取 `current.us_aqi`，等级映射在服务端完成（payload 携带现值+中文等级） | 零计算决策的落地；渲染层不做等级判断 |
| AD-3 | 失败降级为 payload `aqi: null`，渲染层输出 `--` 占位 | 显式 null 优于缺字段 |
| AD-4 | 等级刻度条六段等宽灰阶（INK/MID/LIGHT 交替 + 当前段实心） | 四档灰阶约束内最大化可读性 |

### 1.4 领域对象总览

| 对象 | 分类 | 说明 |
|------|------|------|
| AirQuality | 值对象（新增） | us_aqi(int)、level_zh(str)、fetched_at；不可变 |
| （其余） | — | 沿用 v2-pages 领域模型（PageAssetSet 聚合根等），不重复 |

无子流程、无关联领域对象。过程数据：无新增。

### 1.5 上下文映射

| 对方 | 关系 |
|------|------|
| Open-Meteo Air Quality | 外部系统，ACL：域名白名单 + https + 禁重定向 + 独立 try/except |
| 页面渲染/缓存协商 | 下游：消费 payload.aqi |

## 2. 跨聚合根设计

不适用（单聚合根）。

## 3. 应用/基础设施层设计

### 3.1 接口规范

沿用 v2-pages §3.1（GET-only、像素坐标、env 可 source）。新增数据源规约：

| 项 | 规约 |
|----|------|
| URL | `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=…&longitude=…&current=us_aqi&timezone=…` |
| 白名单 | `air-quality-api.open-meteo.com`，https-only，allow_redirects=False |
| 超时 | 10s；失败 aqi=null（独立于天气拉取的 try/except） |

### 3.2 依赖与约束

- 依赖天气拉取调度（同周期触发，不独立定时）；
- 约束：AQI 失败不影响 payload 其余节点。

### 3.3 权限模型

不适用（只读公开数据）。

### 3.4 公共规范

| 枚举 | 取值 |
|------|------|
| aqi.level_zh | 优 / 良 / 轻度敏感 / 中度 / 重度 / 严重 / 暂无（失败） |
| aqi.us_aqi | int 0-500 或 null |

## 4. 聚合根详细设计（页面资产集·增量）

### 4.1 领域模型增量

payload 扩展（`/api/v1/dashboard.json` 新增节点）：

```jsonc
{
  "aqi": {                       // 拉取失败时整体为 null
    "us_aqi": 45,                // int | null
    "level_zh": "良",            // BR-1 映射 | "暂无"
    "fetched_at": "2026-10-10T14:00:00+08:00"
  }
}
```

- 不变量 INV-A1：`aqi != null` 时 `us_aqi ∈ [0, 500]` 且 `level_zh` 按 BR-1 映射；
- 不变量 INV-A2：`aqi == null` 时今日页 sun 分区含 `AQI --`、indices 第 6 卡为 `暂无数据`（指纹随内容变化，ETAG 正常轮转）；
- INV-A3：`sun` 节点保留 `phase/illumination/name`（场景图依赖），渲染层不再消费于今日/详情页。

### 4.2 状态模型

不适用（无状态机；数据随拉取周期刷新）。

### 4.3 接口设计

| # | 端点/契约 | 变更 |
|---|----------|------|
| I-1 | `GET /api/v1/dashboard.json` | 扩展：新增 `aqi` 节（§4.1） |
| I-2 | `GET /r/today/sun.png` | 渲染变化：右半由月相盘改 AQI 卡（ETAG 随内容轮转） |
| I-3 | `GET /r/detail/indices.png` | 渲染变化：第 6 卡月相→AQI |
| I-4 | `GET /api/v1/dashboard.env` 及其余分区路由 | **零变化**（NFR-3） |

校验规则：us_aqi 非数值/越界（<0 或 >500）一律按拉取失败处理（aqi=null）。

### 4.4 领域事件与集成

无。

## 5. 模块清单汇总

| 项 | 内容 |
|----|------|
| 出站调用 | Open-Meteo Air Quality（新，白名单） |
| 变更端点 | dashboard.json（+aqi）、sun.png/indices.png（渲染内容） |
| 设备端变更 | 无 |

## 6. 更新记录

| 版本 | 日期 | 更新说明 |
|------|------|---------|
| v1.0 | 2026-10-10 | initial：AQI 数据源契约、payload 扩展、分区渲染增量、INV-A1~A3 |

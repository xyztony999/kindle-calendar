# 契约：block-options-2（积木自定义二期）

- 版本：v1.0（Gate 1 草案，2026-11-08）
- 需求：`02-detailed/prd/prd-block-options-2.md`
- 设备端零改动：全部为服务端出图变化，新 payload 键自动参与 data_fingerprint → ETAG 轮转（AD-1）。

## 1. settings 新顶层键 `units`（轮 1）

```json
"units": {"temp": "c", "wind": "kmh", "aqi": "us"}
```

| 键 | 取值 | 默认 |
|---|---|---|
| temp | `c` / `f` | c |
| wind | `kmh` / `ms` / `bft` | kmh |
| aqi | `us` / `cn` | us |

- validate：键缺失合法（旧配置）；存在但取值非法 → `UNITS_INVALID`（field=`units.<key>`）。
- normalize：`data.get("units") or {}` 后逐键 `.get(k, 默认)`，非法回退默认，恒输出完整三键。
- 管理端：城市分区「显示单位」组；`SECTION_KEYS.env = ["location", "units"]`。
- payload：`build_payload` 附 `payload["units"]`（同三键）。/weather 与 dashboard.json 的数值字段保持 ℃/km/h/美标原值（数据契约不变）。

## 2. 格式化层 `server/units.py`（轮 1）

| 函数 | 说明 |
|---|---|
| `fmt_temp(c, payload)` | ℉=℃×9/5+32；**四舍五入（half-up）后取 int**，根治 "-0"；返回 `"23°"` |
| `fmt_temp_delta(dc, payload)` | 温差只 ×9/5（降温提醒用） |
| `fmt_wind(kmh, payload)` | `5 km/h` / `1.4 m/s`（一位小数）/ `3级`（英文 `Force 3`） |
| `beaufort(kmh)` | 蒲福风级 0–12，阈值 km/h：1,6,12,20,29,39,50,62,75,89,103,118 |
| `aqi_view(payload)` | 按 units.aqi 返回 `(value, level_text)`；国标数据缺失时回退美标 |

替换点（10 处温度 + 3 处风速 + 3 处 AQI）：today.render_weather、week.render_list/render_chart、detail.render_hourly/render_indices、common 降温提醒、fields._temp 与风速/AQI 字段、today.render_sun 的 AQI 卡。

## 3. 中国 AQI（HJ 633-2012，轮 1）

- aqi.py 请求 `current=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide`（同一请求加字段，沿用加固模板）。
- 实时口径：SO2/NO2/CO/O3 用 1 小时限值表；PM2.5/PM10 用小时浓度套 24 小时限值表（与国家实时发布平台一致）；CO 由 µg/m³ ÷1000 换 mg/m³。
- IAQI 分段线性插值后**向上取整**，AQI=各 IAQI 最大值；超最高限值记 500。SO2 1h>800 时改用 24h 表。

| IAQI | 0 | 50 | 100 | 150 | 200 | 300 | 400 | 500 |
|---|---|---|---|---|---|---|---|---|
| SO2 1h | 0 | 150 | 500 | 650 | 800 | — | — | — |
| SO2 24h | 0 | 50 | 150 | 475 | 800 | 1600 | 2100 | 2620 |
| NO2 1h | 0 | 100 | 200 | 700 | 1200 | 2340 | 3090 | 3840 |
| CO 1h (mg/m³) | 0 | 5 | 10 | 35 | 60 | 90 | 120 | 150 |
| O3 1h | 0 | 160 | 200 | 300 | 400 | 800 | 1000 | 1200 |
| PM10 24h | 0 | 50 | 150 | 250 | 350 | 420 | 500 | 600 |
| PM2.5 24h | 0 | 35 | 75 | 115 | 150 | 250 | 350 | 500 |

等级：0–50 优、51–100 良、101–150 轻度污染、151–200 中度污染、201–300 重度污染、>300 严重污染（英文短写 Excellent / Good / Light / Moderate / Heavy / Severe，与美标英文同等长度，避免冲出卡片）。

- payload.aqi 增量：`cn_aqi, cn_level, pm2_5, pm10`（污染物缺失则 cn_* 为 None）。健康历史仍记 us_aqi。

## 4. 新选项类型（轮 1：text；轮 2：list）

| kind | 存储 | 校验 |
|---|---|---|
| `text` | 字符串 | 长度 ≤ max_len；`{X}` 占位符须在白名单 |
| `list` | 有序数组 | 元素唯一且属于目录；1 ≤ 长度 ≤ max |

catalog（`system_options_catalog`）每项新增：`choice_labels`（取值→当前语言文案，服务端表）；text 项带 `max_len/placeholders/visible_when`；list 项带 `items:[{key,label}]` 与 `max`。前端按 kind 渲染，`visible_when={"date_format":"custom"}` 控制模板框显隐。

## 5. 系统积木新选项

取值一律字符串（数字档位也用字符串，保持 choice 同构）；首项为默认=现状。

| 积木 | 键 | kind | 取值 | 轮 |
|---|---|---|---|---|
| header | date_format | choice | cn / md / ymd / dot / custom | 1 |
| header | date_template | text | ≤24 字（按模板写法计），占位 `{Y}{M}{MM}{D}{DD}{CM}{CD}{W}` | 1 |
| grid | today_mark | choice | circle / fill / box | 1 |
| hourly | chart | choice | bar / line / area | 2 |
| hourly | span | choice | 24 / 12 | 2 |
| hourly | precip | choice | dots / bars / off | 2 |
| hourly | labels | choice | ends / extremes / every3 | 2 |
| hourly | ticks | choice | 6 / 3 | 2 |
| indices | items | list | 目录 21 项，max 6 | 2 |
| list | days / show_precip / show_icon | choice / bool / bool | 7·5 / false / true | 2 |
| chart | days | choice | 7 / 5 | 2 |

- 页眉模板渲染：英文页 `{CM}{CD}` 回退阿拉伯数字、`{W}` 为英文缩写；`custom` 且模板为空或非法 → 按 cn。日期文字超出页眉左侧可用宽（页签起点 −12px）时字号逐级缩小，下限 20px；下限仍放不下则截断加「…」。
- 模板校验：未知占位符与**未闭合花括号**（如「周{W」）都报错；前端不设 maxLength（避免静默截断），超长即报错。
- 今日标记 fill：墨色实心圆＋PAPER 色数字（数字先画圆后重绘）；box：圆角 4px 方框，同半径包围盒。

## 6. 天气数据扩展（轮 2）

- current 增：`uv_index, pressure_msl, visibility, wind_direction_10m`
- daily 增：`precipitation_probability_max, uv_index_max`
- dataclass 新字段全部 `= None` 默认（旧缓存/测试夹具兼容）；payload：`weather.current.{uv, pressure, visibility_km, wind_dir}`、`weather.daily[i].{precip_prob, uv_max}`。
- 风向：8 方位（北/东北/东/东南/南/西南/西/西北 + 「风」；英文 N/NE/…）；能见度 ≥10km 取整、<10km 一位小数。

## 7. 生活建议规则（轮 2）

输入：体感温度 T（缺则实温，℃）、今日降水概率 P、湿度 H、今日最大紫外线 U、AQI（按当前标准）、风速 W(km/h)、日温差 S=max−min、明日降水概率 P1。自上而下首个命中即结果。

| 项 | 规则 → 结果 |
|---|---|
| 穿衣 | T≥28 短袖；≥23 薄长袖；≥18 长袖衬衫；≥12 薄外套；≥5 厚外套；≥−5 棉衣；否则 羽绒服 |
| 晾晒 | P≥50 或当前降水天气码 → 不宜；P≥30 或 H≥85 → 较不宜；U≥3 且 H<70 且 P<20 → 适宜；否则 较适宜 |
| 运动 | AQI>150 或 P≥60 或 T≥35 或 T≤−10 → 不宜；AQI>100 或 P≥30 或 T≥30 或 T≤0 或 W≥39 → 较不宜；10≤T≤26 且 AQI≤50 且 P<20 → 适宜；否则 较适宜 |
| 洗车 | P≥30 或 P1≥50 → 不宜；AQI>150 或 W≥39 → 较不宜；否则 适宜 |
| 感冒 | S≥10 或 T≤5 或 有降温提醒 → 易发；S≥7 或 T≤10 或 H≤30 → 较易发；否则 少发 |
| 防晒 | U≥11 极强；≥8 很强；≥6 强；≥3 中等；否则 弱 |

英文：Shorts / Light layers / Long sleeves / Light jacket / Warm jacket / Padded coat / Down jacket；Not advised / Less suitable / Suitable / Fairly suitable；Likely / Possible / Unlikely；Extreme / Very high / High / Moderate / Low。数据缺失（如 U 为 None）时该项显示「—」。

## 8. 指数卡目录与数据积木字段（轮 2）

指数目录键（顺序即候选列表顺序）：`humidity wind precip sunrise sunset aqi feels range moon uv pressure visibility wind_dir pm25 pm10 dress laundry exercise carwash cold sunscreen`；默认 `[humidity, wind, precip, sunrise, sunset, aqi]`。

数据积木 FIELD_IDS 新增 12 个（29→41）：`weather.uv weather.pressure weather.visibility weather.wind_dir air.pm25 air.pm10 life.dress life.laundry life.exercise life.carwash life.cold life.sunscreen`。字段目录增加 `group` 属性（weather/date/lunar/sun_moon/air/quote/events/life，轮 1 先为现有 29 个字段标注），前端按组渲染。

## 9. 兼容与风险

- 旧配置无 `units`、旧积木无新 options → 渲染与现状一致；新 option 值必须过 `_normalize_block` 链路（历史教训：未进白名单会被静默剥离）。
- 四舍五入口径由 half-even 改 half-up：x.5 的温度可能比旧版高 1°，单测固定口径。
- Open-Meteo 新字段缺失（API 异常）→ 对应卡/字段显示「—」，不阻断整页渲染。

## 10. 轮 1 实现偏差（2026-11-08）

| 契约草案 | 实际实现 | 原因 |
|---|---|---|
| 模板 ≤16 字 | ≤24 字 | 占位符本身占 3–4 字，「{Y}年{M}月{D}日 周{W}」就有 17 字；验证时发现输入框 maxLength 静默截掉结尾「}」，残缺的「{W」被当文字渲染 |
| 只校验未知占位符 | 未闭合花括号也报错；去掉 maxLength | 同上，杜绝「看着保存成功、出图却是乱码」 |
| 缩字下限 20px | 下限仍放不下时截断加「…」 | 极端模板在 20px 仍宽 320px，会压到页签 |
| 国标英文全称 | 英文短写 | 「107 Moderately polluted」在 40px 下宽 460px，冲出指数卡 |
| — | 指数卡数值超宽时缩字（40→24px） | 顺带修复既有溢出：美标英文「Very Unhealthy」本来就会冲出卡片 |
| — | aqi.py 补 `log` 定义 | 既有 bug（b0ba151）：AQI 拉取失败时 except 分支 NameError，周期刷新里连同刚拉到的天气一起丢弃 |
| reading.py 一并修 -0° | 不改 | 阅读页用 `:g` 原样显示带小数的原始值（数据接口视图），不存在取整成 -0 的问题 |
| — | FIELD_DEFS 调整为按组连续 | 宜/忌并入农历组、日程移到地点之前；分组展示后 DOM 顺序 = 目录顺序，「首项」语义不变 |
| — | 单选文案改由服务端下发 `choice_labels` | 顺带修复每日一图模式选项一直显示原始值「daily / fixed」 |

## 11. 轮 2 实现偏差（2026-11-09）

| 契约草案 | 实际实现 | 原因 |
|---|---|---|
| 指数目录定义在 layout | 拆为无依赖模块 `server/indices.py`，layout 与 detail 共用 | render 包初始化即加载页面渲染器，渲染器反向导入 layout 会循环导入 |
| 紫外线取实况 | 卡片/字段/防晒建议统一取**当日最大值**，缺失回退实况 | 实况夜间恒为 0，台历早上看没有参考意义 |
| 生活建议降水 P | 当日最大降水概率，缺失回退未来 6 小时最大值 | 晾晒/洗车/运动看的是整天 |
| 仅修首个刻度标签裁切 | 逐时全部边缘文字（刻度/温度/百分比）钳制在分区内 | 默认出图对比旧版只差 3 处，全是边缘裁切：首刻度「22时」、首温度「-1°」、末小时「60%」 |
| — | 同一小时既有温度标注又有降水时，自下而上叠放「点 → 温度 → 圆点 → 百分比」；折线/面积图标注加纸色衬底 | 验证中发现「每 3 小时标注」下百分比与温度互压、折线穿字；旧版在首尾标注小时也有同类压字 |
| — | **一周曲线低温标注压到日期刻度时改放到点上方** | 既有 bug：首/末/今日的低温恰为一周最低时，「-3°」必压在日期「8」上（022830e 版本即存在） |
| 一周列表降水概率位置未定 | 与高低温同行、在其左侧，前缀几何绘制的小水滴 | 7 天行高仅 70px 放不下第二行；e-ink 字体不保证有 ☂ 等符号 |
| — | 一周列表天气图标尺寸以 7 天行高为上限 | 5 天行更高，图标随之放大会压住天气描述 |

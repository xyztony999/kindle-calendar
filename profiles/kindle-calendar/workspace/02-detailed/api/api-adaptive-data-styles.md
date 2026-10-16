# 数据积木外观接口增量

v1.0 / 2026-10-17，继承api-admin-refinement与现有自由画布契约。

## 配置版本与数据结构

SCHEMA_VERSION=3，ACCEPTED_SCHEMAS=(1,2,3)。load/import统一用该枚举；旧1/2迁移为3且不写block默认覆盖。content_version沿用现有完整配置计算；升级后的版本以服务端返回为准，不承诺hash保持相同。旧配置的画面与坐标保持。

widget_defs保留{id,name,fields,style}：新建style固定rows作默认，fields数量1–6；现有hero/rows定义沿用旧数量校验，不新增类型拒绝。中心已审核data定义仍沿用既有默认hero/rows契约与审核检查，不因本地外观设置绕过审核。

custom布局实例增加可选style，允许hero/rows/horizontal/grid；其他widget不接受此属性。有效样式为block.style优先，否则definition.style，缺省rows。normalize保留合法style，保存、预览、导入导出、缓存版本均覆盖。渲染复制定义合并覆盖，不修改共享definitions对象。

显式style要按所引用的本地/已审核中心定义字段校验；不存在或未审核仍报WIDGET_DEF_INVALID，不适用style报LAYOUT_INVALID，details.field定位到pages[i].layout[j].style并提供原因。无显式覆盖的旧hero即使含长文也可继承，不强制重排。已有默认style的字段上限约束保留。

## 字段能力元信息

GET /admin/api/widget-catalog 的fields每项增加kind，仍保留id/label。类别：number、time、date、short_text、text，均为稳定code+label（见enum-pool）。

- number：weather.temperature/humidity/wind_speed/precip_prob/temp_min/temp_max、sun.illumination、aqi.value。
- time：sun.sunrise、sun.sunset。
- date：date.month_day。
- short_text：weather.description、date.weekday、date.solar_term、sun.moon、aqi.level。
- text：date.lunar、date.ganzhi、date.festivals、date.holiday、quote.text、quote.from、almanac.yi、almanac.ji、location.name。

新增data_styles目录，每项{id,label,description,min_fields,max_fields,allowed_kinds,first_kinds}。rows的allowed_kinds含所有类别；hero为紧凑类别、首项number/time/date；horizontal和grid为紧凑类别，首项不额外限制。目录只提供可计算规则与文案，不动态执行表达式。共享后端helper返回适用列表与recommended供校验/测试；前端按同一目录规则计算，不复制字段名单，不从当天字符串推测类型。

推荐顺序：单项number/time/date→hero；2–3项且全部紧凑→horizontal；4–6项且全部紧凑→grid；其余→rows。新放置block写入推荐style；历史block不自动写覆盖。kind未知按text处理，接口只接受字段白名单。

## 预览与渲染

沿用POST /admin/api/layout-preview，layout包含实例style，widget_defs包含定义。候选选择后使用真实payload与正式paint_custom渲染，不使用固定24°伪造结果，不新增预览端点。新渲染策略在矩形内fit/wrap并按高度预算末行省略；缺失值—保持候选稳定。

## 验证

字段分类白名单覆盖25项；各样式数量/类型边界，未知style/错误widget属性/未审核中心引用拒绝；继承旧hero长文允许；同定义双实例不同style无串改；schema1/2迁移、schema3导入导出；save→preview→export→import完整链；布局版本和ETag随style变化。实际Pillow渲染验证中文/英文/空值/长字串/最小矩形；浏览器验证创建无样式、画布选择适用候选、即时预览、键盘、取消和已有草稿保留。

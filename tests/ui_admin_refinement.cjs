// Run against an isolated Flask test server with mocked weather/storage.
// Set PLAYWRIGHT_MODULE and UI_TEST_BROWSER if Playwright is outside node_modules.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.UI_TEST_BASE || 'http://127.0.0.1:8766';
const output = process.env.UI_TEST_OUTPUT || path.join(__dirname, '../data/ui-refinement');
fs.mkdirSync(output, {recursive:true});

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.UI_TEST_BROWSER ? {executablePath:process.env.UI_TEST_BROWSER} : {})});
  const page = await browser.newPage({viewport:{width:1059,height:964}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('dialog', dialog => dialog.accept());
  let savedPayload;
  await page.route('**/admin/api/settings/save', async route => {
    savedPayload = route.request().postDataJSON();
    await route.fulfill({json:{ok:true,data:{settings:savedPayload,settings_version:'ui-test',location_changed:false}}});
  });
  async function save() {
    const response = page.waitForResponse(r => r.url().endsWith('/settings/save'));
    await page.locator('#save-btn').click();
    await response;
    await page.locator('#save-btn:enabled').waitFor();
    return structuredClone(savedPayload);
  }
  async function edit(index = 0) {
    await page.locator('#page-list button').filter({hasText:/编辑版面|Edit layout/}).nth(index).click();
    await page.locator('#canvas-modal').waitFor({state:'visible'});
    await page.locator('#stage').waitFor({state:'visible'});
  }
  // 数据积木在主视图「我的积木」卡片新建/编辑，弹窗内只负责放置。
  async function create(name) {
    await page.locator('#widget-add').click();
    await page.locator('#widget-name').fill(name);
    await page.locator('#widget-fields input').first().check();
    await page.locator('#widget-save').click();
    await page.locator('#widget-form').waitFor({state:'hidden'});
    await page.locator('#widget-list .widget-row .w-name').filter({hasText:name}).first().waitFor();
  }
  async function placeFirst() {
    await page.locator('#palette-mine .widget-row .w-add').first().click();
  }
  async function tab(name) {
    await page.locator(`#side-nav .side-item[data-section=${name}]`).click();
  }
  await page.goto(base + '/admin?lang=zh');
  await page.locator('#password').fill(process.env.UI_TEST_PASSWORD || 'local-ui-verification');
  await page.locator('#login-btn').click();
  await page.locator('#view-settings').waitFor({state:'visible'});
  const pageCount = await page.locator('#page-list .page-row').count();
  assert.equal(await page.locator('#card-pages .section-head #add-page').count(), 1);
  assert.equal(await page.locator('.main-bar #save-btn').count(), 1);
  // 侧栏制：分区总览常驻 + 分区级脏点 + hash 路由 + 城市/一言拆平
  assert.equal(await page.locator('#side-nav .side-item[data-section]').count(), 6);
  assert.equal(await page.locator('[data-dirty-dot="pages"]').isVisible(), false);
  const dwellProbe = page.locator('#page-list .page-row input[type=number]').first();
  const dwellBase = await dwellProbe.inputValue();
  await dwellProbe.fill(String(Number(dwellBase) + 1));
  assert.equal(await page.locator('[data-dirty-dot="pages"]').isVisible(), true);
  assert.match(await page.locator('#toolbar-status').innerText(), /1\s*处未保存|1\s*sections unsaved/);
  await dwellProbe.fill(dwellBase);
  assert.equal(await page.locator('[data-dirty-dot="pages"]').isVisible(), false);
  await tab('schedule');
  assert.equal(page.url().includes('#section=schedule'), true);
  assert.match(await page.locator('#main-title').innerText(), /日程与倒计时|Schedule/);
  await tab('quote');
  assert.equal(await page.locator('#card-quote').isVisible(), true);
  assert.equal(await page.locator('#card-location').isVisible(), false);
  // admin-content-pack：来源四态 radio（语料库/在线/自定义/个人库）+ 个人库面板条件显隐
  assert.equal(await page.locator('#quote-modes input[name="quote-mode"]').count(), 4);
  assert.match(await page.locator('#quote-modes label').last().innerText(), /个人库|Personal/);
  assert.equal(await page.locator('#personal-box').isVisible(), false);
  await page.locator('#quote-modes input[value="personal"]').check();
  assert.equal(await page.locator('#personal-box').isVisible(), true);
  assert.equal(await page.locator('#quote-types').isVisible(), false);
  assert.equal(await page.locator('#custom-box').isVisible(), false);
  assert.match(await page.locator('#personal-info').innerText(), /尚未上传|No personal quote library/);
  assert.equal(await page.locator('#personal-upload').isDisabled(), true);
  await page.locator('#quote-modes input[value="library"]').check();
  assert.equal(await page.locator('#personal-box').isVisible(), false);
  // 数据积木字段按类分组展示（组名 + 组内多列）
  await tab('blocks');
  await page.locator('#widget-add').click();
  assert.ok(await page.locator('#widget-fields .field-group').count() >= 7, 'fields should be grouped');
  assert.match(await page.locator('#widget-fields .field-group-name').first().innerText(), /天气|Weather/);
  assert.equal(await page.locator('#widget-fields input').first().getAttribute('value'), 'weather.temperature');
  await page.locator('#widget-cancel').click();
  await tab('pages');
  assert.equal(await page.locator('#geo-btn').count(), 0);
  await page.locator('#add-page').click();
  await page.locator('#editor-page-name').fill('Discarded page');
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#page-list .page-row').count(), pageCount);
  assert.equal(await page.locator('#dirty-flag').isVisible(), false);
  assert.equal(await page.locator('#add-page').evaluate(el => el === document.activeElement), true);

  const dwell = page.locator('#page-list .page-row input[type=number]').first();
  await dwell.fill('65');
  await edit();
  const blockCount = await page.locator('#stage .block').count();
  assert.equal(await page.locator('#snap-toggle').isChecked(), true);
  await page.locator('#stage .block-remove').last().click();
  await page.locator('#cancel-editor').click();
  assert.equal(await dwell.inputValue(), '65');
  assert.equal(await page.locator('#page-list .page-row button').first().evaluate(el => el === document.activeElement), true);
  assert.equal(await page.locator('#dirty-flag').isVisible(), true);
  await edit();
  assert.equal(await page.locator('#stage .block').count(), blockCount);
  assert.equal(await page.locator('#palette-mine .widget-row').count(), 0);
  assert.equal(await page.locator('#def-editor').count(), 0);
  await page.locator('#close-editor').click();
  await tab('blocks');
  await create('Shared test');
  await tab('pages');
  await edit();
  await placeFirst();
  await page.locator('#close-editor').click();
  await edit(1);
  await placeFirst();
  await page.locator('#close-editor').click();
  let payload = await save();
  const defId = payload.widget_defs[0].id;
  assert.equal(payload.pages.filter(p => p.layout.some(b => b.def === defId)).length, 2);

  // 方向键微调：选中已放置积木后 ArrowRight 移动 1px。
  await edit();
  await page.locator('#stage .block').filter({hasText:'Shared test'}).last().click();
  await page.keyboard.press('ArrowRight');
  await page.locator('#close-editor').click();
  payload = await save();
  const moved = payload.pages.flatMap(p => p.layout).find(b => b.def === defId);
  assert.equal(moved.x, 57);

  // 卡片删除数据积木（确认框由 dialog 处理器接受），保存后从所有页面移除。
  await tab('blocks');
  await page.locator('#widget-list .widget-row .w-act.danger').first().click();
  payload = await save();
  assert.equal(payload.widget_defs.length, 0);
  assert.equal(payload.pages.some(p => p.layout.some(b => b.def === defId)), false);

  // 编辑器内抽屉：不关闭弹窗完成新建、放置与层级调整。
  await tab('pages');
  await edit();
  await page.locator('#palette-mine button.btn', {hasText:/管理我的积木|Manage my blocks/}).click();
  await page.locator('#widget-drawer:not([hidden])').waitFor();
  await page.locator('#wm-add').click();
  await page.locator('#wm-name').fill('Drawer block');
  await page.locator('#wm-fields input').first().check();
  await page.locator('#wm-save').click();
  await page.locator('#wm-list .widget-row .w-name').filter({hasText:'Drawer block'}).waitFor();
  await page.locator('#palette-mine .widget-row .w-name').filter({hasText:'Drawer block'}).waitFor();
  await page.locator('#wm-list .widget-row .w-place').first().click();
  await page.locator('#stage .block').filter({hasText:'Drawer block'}).waitFor();
  await page.locator('#stage .block').filter({hasText:'Drawer block'}).click();
  await page.locator('#layer-down:enabled').click();
  await page.locator('#layer-up:enabled').click();
  await page.locator('#wm-back').click();
  await page.locator('#close-editor').click();
  payload = await save();
  assert.equal(payload.widget_defs.some(d => d.name === 'Drawer block'), true);
  assert.equal(payload.pages.some(p => p.layout.some(b => b.def === payload.widget_defs[0].id)), true);

  // 未配置 OSS：上传按钮禁用，选文件后不应发出上传请求。
  let uploadHit = false;
  let finishUpload;
  const uploadGate = new Promise(resolve => { finishUpload = resolve; });
  await tab('pages');
  await page.route('**/admin/api/assets', async route => {
    uploadHit = true;
    await uploadGate;
    await route.fulfill({json:{ok:true,data:{asset:{id:'a12345678',key:'test.png'}}}});
  });
  await edit();
  assert.equal(await page.locator('#palette-mine button.btn', {hasText:/上传图片|Upload image/}).first().isDisabled(), true);
  await page.locator('#image-file').setInputFiles({name:'test.png',mimeType:'image/png',buffer:Buffer.from('mock image')});
  await page.waitForTimeout(300);
  assert.equal(uploadHit, false);
  await page.locator('#cancel-editor').click();

  // 配置 OSS 后：迟到的上传响应不得进入已取消的编辑草稿。
  await page.route('**/admin/api/widget-catalog', async route => {
    const response = await route.fetch();
    const body = await response.json();
    body.data.storage = {type:'oss', configured:true};
    await route.fulfill({json:body});
  });
  await page.reload();
  await page.locator('#view-settings').waitFor({state:'visible'});
  await edit();
  const uploadRequest = page.waitForRequest('**/admin/api/assets');
  await page.locator('#image-file').setInputFiles({name:'test.png',mimeType:'image/png',buffer:Buffer.from('mock image')});
  await uploadRequest;
  await page.locator('#cancel-editor').click();
  const uploadResponse = page.waitForResponse('**/admin/api/assets');
  finishUpload();
  await uploadResponse;
  payload = await save();
  assert.equal(payload.assets.some(a => a.id === 'a12345678'), false);

  // Simulate a slower old query, then choose the new query with the keyboard.
  const geoQueries = [];
  await page.route('**/admin/api/geocode?*', async route => {
    const q = new URL(route.request().url()).searchParams.get('q');
    geoQueries.push(q);
    if (q === 'old') await new Promise(resolve => setTimeout(resolve, 700));
    await route.fulfill({json:{ok:true,data:{candidates:[{name:q,admin1:'Test',country:'CN',latitude:30,longitude:120,timezone:'Asia/Shanghai'}]}}}).catch(() => {});
  });
  await tab('env');
  const geo = page.locator('#geo-q');
  await geo.fill('old');
  await page.waitForRequest('**/admin/api/geocode?q=old');
  await geo.fill('杭州');
  await page.locator('#geo-list button').filter({hasText:'杭州'}).waitFor();
  await page.waitForTimeout(750);
  assert.match(await page.locator('#geo-list').innerText(), /杭州/);
  assert.doesNotMatch(await page.locator('#geo-list').innerText(), /old/);
  await geo.press('ArrowDown');
  await geo.press('Enter');
  assert.equal(await page.locator('#loc-name').inputValue(), '杭州');
  assert.equal(await geo.getAttribute('aria-expanded'), 'false');
  const beforeComposition = geoQueries.length;
  await geo.dispatchEvent('compositionstart');
  await geo.fill('北京');
  await page.waitForTimeout(500);
  assert.equal(geoQueries.length, beforeComposition);
  await geo.dispatchEvent('compositionend');
  await page.locator('#geo-list button').filter({hasText:'北京'}).waitFor();
  await geo.press('Escape');
  assert.equal(await geo.getAttribute('aria-expanded'), 'false');
  assert.equal((await geo.boundingBox()).height, 42);

  // 显示单位：城市分区内切 ℉ / 风力等级 / 国标，保存载荷带 units
  await page.locator('#units-box input[data-unit=temp][value=f]').check();
  await page.locator('#units-box input[data-unit=wind][value=bft]').check();
  await page.locator('#units-box input[data-unit=aqi][value=cn]').check();
  assert.equal(await page.locator('[data-dirty-dot="env"]').isVisible(), true);
  payload = await save();
  assert.deepEqual(payload.units, {temp:'f', wind:'bft', aqi:'cn'});

  // admin-content-pack：个人库上传（路由 mock，不写服务端）——成功 toast/库信息刷新/不自动保存；失败 inline 逐条 details
  await tab('quote');
  await page.locator('#quote-modes input[value="personal"]').check();
  await page.route('**/admin/api/quotes-personal', route => route.fulfill({json:{ok:true,data:{count:3,uploaded_at:'2026-11-24T04:00:00+00:00'}}}));
  await page.route('**/admin/api/sources', async route => {
    const response = await route.fetch();
    const body = await response.json();
    const quote = (body.data.sources || []).find(s => s.id === 'quote');
    if (quote) { quote.personal_count = 3; quote.personal_updated = '2026-11-24T04:00:00+00:00'; }
    await route.fulfill({json:body});
  });
  const statusBeforeUpload = await page.locator('#toolbar-status').innerText();
  await page.locator('#personal-file').setInputFiles({name:'personal.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({schema_version:1,quotes:[{text:'此心安处是吾乡。',from:'苏轼《定风波》'}]}))});
  assert.equal(await page.locator('#personal-upload').isEnabled(), true);
  const uploadOk = page.waitForResponse(r => r.url().endsWith('/admin/api/quotes-personal') && r.status() === 200);
  await page.locator('#personal-upload').click();
  await uploadOk;
  await page.locator('#personal-info').filter({hasText:/3\s*条|3 entries/}).waitFor();
  assert.match(await page.locator('#toast').innerText(), /已上传 3 条|3 entries uploaded/);
  assert.equal(await page.locator('#toolbar-status').innerText(), statusBeforeUpload); // 上传不标脏、不自动保存
  await page.unroute('**/admin/api/quotes-personal');
  await page.route('**/admin/api/quotes-personal', route => route.fulfill({status:400,json:{ok:false,error:{code:'QUOTES_PERSONAL_INVALID',message:'个人语录库校验失败',details:[
    {index:1,field:'text',code:'QUOTES_PERSONAL_INVALID',message:'文案须为 1–32 字且不含换行'},
    {index:2,field:'from',code:'QUOTES_PERSONAL_INVALID',message:'出处最多 16 字且不含换行'},
    {index:null,field:'quotes',code:'QUOTES_PERSONAL_INVALID',message:'语录须为 1–100 条的数组'}]}}}));
  await page.locator('#personal-file').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{"schema_version":1,"quotes":[]}')});
  const uploadBad = page.waitForResponse(r => r.url().endsWith('/admin/api/quotes-personal') && r.status() === 400);
  await page.locator('#personal-upload').click();
  await uploadBad;
  assert.equal(await page.locator('#personal-error').isVisible(), true);
  assert.match(await page.locator('#personal-error').innerText(), /共 3 处问题|3 problems in total/);
  assert.equal(await page.locator('#personal-error details li').count(), 3);
  assert.match(await page.locator('#personal-error details li').first().textContent(), /#1/); // details 折叠态 innerText 为空，用 textContent
  assert.match(await page.locator('#personal-info').innerText(), /3\s*条|3 entries/); // 失败原库信息不变
  await page.locator('#quote-modes input[value="library"]').check();
  await page.unroute('**/admin/api/quotes-personal');
  await page.unroute('**/admin/api/sources');

  // admin-content-pack：健康数值折线——注入固定快照（含无值拍），断言 path 段数=有值连续段数 + units 标签 + 空态
  const at = (h) => new Date(Date.now() - h * 3600 * 1000).toISOString();
  const historyPayload = {ok:true,data:{sources:{
    aqi:[{at:at(6),ok:true,error:'',value:40},{at:at(5),ok:true,error:'',value:50},{at:at(4),ok:false,error:'x'},{at:at(3),ok:true,error:'',value:60},{at:at(2),ok:true,error:'',value:70}],
    weather:[{at:at(6),ok:true,error:'',value:20},{at:at(5),ok:false,error:'x'},{at:at(4),ok:true,error:'',value:24}],
    quote:[{at:at(6),ok:true,error:''}],ics:[]},units:{temp:'c',aqi:'us'}}};
  await page.route('**/admin/api/sources/history', route => route.fulfill({json:historyPayload}));
  await page.reload();
  await page.locator('#view-settings').waitFor({state:'visible'});
  await tab('device');
  await page.locator('.sources-lines .sl-row').first().waitFor();
  assert.equal(await page.locator('.sources-lines .sl-row').count(), 2);
  const segments = await page.evaluate(() => [...document.querySelectorAll('.sources-lines path')].map(p => (p.getAttribute('d').match(/M/g) || []).length));
  assert.deepEqual(segments, [2, 2]); // 无值拍断线：aqi [40,50]|[60,70]，weather [20]|[24]
  assert.match(await page.locator('.sources-lines .sl-row').first().innerText(), /美标|US/);
  assert.match(await page.locator('.sources-lines .sl-row').nth(1).innerText(), /℃/);
  assert.equal(await page.locator('.sources-history .sh-row').count(), 4); // 点阵回归不变
  assert.equal(await page.locator('.sources-lines svg').first().getAttribute('role'), 'img');
  historyPayload.data.units = {temp:'f',aqi:'cn'};
  historyPayload.data.sources.aqi = [{at:at(6),ok:true,error:''}];
  historyPayload.data.sources.weather = [];
  await page.reload();
  await page.locator('#view-settings').waitFor({state:'visible'});
  await tab('device');
  await page.locator('.sources-lines .sl-row').first().waitFor();
  assert.match(await page.locator('.sources-lines .sl-row').first().innerText(), /国标|CN/);
  assert.match(await page.locator('.sources-lines .sl-row').nth(1).innerText(), /℉/);
  assert.match(await page.locator('.sources-lines').innerText(), /近七日无数值记录|No values in the last 7 days/);
  assert.equal(await page.locator('.sources-lines path').count(), 0);
  await page.unroute('**/admin/api/sources/history');

  // sysopt-layout-fix：系统/文字选项行式布局——单选钮不重叠、点档位文字激活该档、控件在标签盒内
  await tab('pages');
  await edit();
  await page.locator('#stage .block').filter({hasText: /时钟|Clock/}).first().click();
  await page.locator('#appearance-controls:not([hidden])').waitFor();
  assert.match(await page.locator('#block-styles-legend').innerText(), /外观选项|Appearance options/);
  const clockRows = await page.evaluate(() => [...document.querySelectorAll('#block-styles .opt-row')].map((row) => {
    const rowR = row.getBoundingClientRect();
    const inputs = [...row.querySelectorAll('input')].map((input) => {
      const r = input.getBoundingClientRect();
      return {id: input.id, type: input.type, cx: r.x + r.width / 2, cy: r.y + r.height / 2,
        inside: r.x >= rowR.x - 0.5 && r.y >= rowR.y - 0.5 && r.x + r.width <= rowR.x + rowR.width + 0.5 && r.y + r.height <= rowR.y + rowR.height + 0.5};
    });
    return {text: row.textContent.replace(/\s+/g, ''), inputs};
  }));
  const sizeRow = clockRows.find((row) => row.inputs[0] && row.inputs[0].type === 'radio' && row.inputs.length >= 3);
  assert.ok(sizeRow, 'clock size choice row missing');
  assert.equal(sizeRow.inputs.length, 3, 'clock size should have 3 tiers');
  assert.equal(new Set(sizeRow.inputs.map((i) => i.cx + ',' + i.cy)).size, sizeRow.inputs.length, 'clock size radios overlap');
  assert.ok(clockRows.length >= 2, 'clock should also expose toggles (hour12)');
  assert.ok(clockRows.every((row) => row.inputs.every((i) => i.inside)), 'clock input outside its row');
  await page.locator('#block-styles .opt-pick').filter({hasText: '小'}).first().click();
  assert.equal(await page.locator('#sys-opt-size-sm').isChecked(), true, 'clicking 小 label must pick sm');
  assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.id), 'sys-opt-size-sm');
  await page.screenshot({path: path.join(output, 'sysopt-clock.png')});

  await page.locator('#stage .block').filter({hasText: /天气|Weather/}).first().click();
  await page.locator('#block-styles .opt-row input[type="checkbox"]').first().waitFor();
  const boolInputs = await page.evaluate(() => [...document.querySelectorAll('#block-styles .opt-row')].map((row) => {
    const rowR = row.getBoundingClientRect();
    const input = row.querySelector('input');
    const r = input.getBoundingClientRect();
    return {id: input.id, inside: r.x >= rowR.x && r.y >= rowR.y && r.x + r.width <= rowR.x + rowR.width && r.y + r.height <= rowR.y + rowR.height};
  }));
  assert.ok(boolInputs.length >= 5, 'weather should expose several toggles');
  assert.ok(boolInputs.every((i) => i.inside), 'weather checkbox outside its row');
  await page.screenshot({path: path.join(output, 'sysopt-weather.png')});

  // block-options-2：外观开关必须逐行排列（a1937d4 丢失 opt-* 样式后挤成一段，旧断言没拦住）
  await page.locator('#stage .block').filter({hasText: /页眉|Header/}).first().click();
  await page.locator('#sys-opt-show_tabs').waitFor();
  const toggleTops = await page.evaluate(() => [...document.querySelectorAll('#block-styles label.opt-row')].map((row) => row.getBoundingClientRect().top));
  assert.ok(toggleTops.length >= 4, 'header should expose at least 4 toggles');
  assert.ok(toggleTops.every((top, i) => i === 0 || top > toggleTops[i - 1] + 8), 'each toggle must sit on its own line');
  // 日期格式：选「自定义」才出现模板框；非法占位符就地报错，合法后提交
  assert.equal(await page.locator('#sys-opt-date_template').count(), 0, 'template input hidden until custom');
  await page.locator('#sys-opt-date_format-custom').check();
  const template = page.locator('#sys-opt-date_template');
  await template.waitFor();
  await template.fill('{M}月{X}');
  assert.equal(await page.locator('#block-styles .opt-error').isVisible(), true, 'bad placeholder must be flagged');
  await template.fill('{M}月{D}日 周{W}');
  assert.equal(await page.locator('#block-styles .opt-error').isVisible(), false);
  await template.press('Enter');
  await page.locator('#sys-opt-date_template').waitFor();
  assert.equal(await page.locator('#sys-opt-date_template').inputValue(), '{M}月{D}日 周{W}');
  await page.screenshot({path: path.join(output, 'sysopt-header.png')});

  await page.locator('#palette-mine .btn').filter({hasText: /文字|Text/}).click();
  const textBlock = page.locator('#stage .block').filter({hasText: /这一页上的文字|Text on this page/}).last();
  await textBlock.click();
  await page.locator('#block-styles fieldset .opt-pick input').first().waitFor();
  const textInputs = await page.evaluate(() => [...document.querySelectorAll('#block-styles .opt-pick')].map((pick) => {
    const pickR = pick.getBoundingClientRect();
    const input = pick.querySelector('input');
    const r = input.getBoundingClientRect();
    return {id: input.id, inside: r.x >= pickR.x && r.y >= pickR.y && r.x + r.width <= pickR.x + pickR.width && r.y + r.height <= pickR.y + pickR.height};
  }));
  assert.equal(textInputs.length, 6);
  assert.ok(textInputs.every((i) => i.inside), 'text option radio outside its label');
  await page.locator('#block-styles .opt-pick').filter({hasText: '右'}).first().click();
  assert.equal(await page.locator('#block-align-right').isChecked(), true);
  await page.screenshot({path: path.join(output, 'sysopt-text.png')});
  await page.locator('#cancel-editor').click();

  // block-options-2 轮 2：指数卡有序多选（勾选 + ↑↓）与逐时图形
  await edit(3);
  await page.locator('#stage .block').filter({hasText: /指数|Indices/}).first().click();
  await page.locator('#sys-opt-items-humidity').waitFor();
  assert.equal(await page.locator('#block-styles .opt-chosen li').count(), 6);
  assert.equal(await page.locator('#sys-opt-items-uv').isDisabled(), true, 'candidates locked while 6 cards are chosen');
  await page.locator('#sys-opt-items-humidity').uncheck();
  await page.locator('#sys-opt-items-uv').check();
  await page.locator('#sys-opt-items-uv-up').click();
  const chosenOrder = await page.locator('#block-styles .opt-chosen li span').allInnerTexts();
  assert.deepEqual(chosenOrder.slice(-2), ['紫外线', 'AQI']);
  assert.equal(await page.locator('#sys-opt-items-uv-up').evaluate((el) => el === document.activeElement), true, 'focus follows the moved card');
  await page.screenshot({path: path.join(output, 'sysopt-indices.png')});
  await page.locator('#stage .block').filter({hasText: /逐时|Hourly/}).first().click();
  await page.locator('#block-styles .opt-pick').filter({hasText: '折线'}).click();
  assert.equal(await page.locator('#sys-opt-chart-line').isChecked(), true);
  await page.locator('#close-editor').click();
  payload = await save();
  const detailLayout = payload.pages.find((p) => p.page_id === 'detail').layout;
  assert.deepEqual(detailLayout.find((b) => b.widget === 'indices').options.items, ['wind', 'precip', 'sunrise', 'sunset', 'uv', 'aqi']);
  assert.equal(detailLayout.find((b) => b.widget === 'hourly').options.chart, 'line');

  for (const lang of ['zh','en']) {
    await page.goto(base + '/admin?lang=' + lang);
    await page.locator('#view-settings').waitFor({state:'visible'});
    for (const colorScheme of ['light','dark']) {
      await page.emulateMedia({colorScheme});
      await page.screenshot({path:path.join(output,`settings-${lang}-${colorScheme}.png`)});
      await edit();
      await page.locator('#draft-img:not([hidden])').waitFor();
      await page.locator('#close-editor').click();
      await tab('blocks');
      await create('Style preview');
      await tab('pages');
      await edit();
      await placeFirst();
      await page.locator('#block-style-hero').focus();
      await page.keyboard.press('ArrowRight');
      assert.equal(await page.locator('#block-style-rows').isChecked(), true);
      await page.screenshot({path:path.join(output,`editor-${lang}-${colorScheme}.png`)});
      await page.locator('#cancel-editor').click();
    }
  }
  await page.setViewportSize({width:390,height:568});
  // 侧栏折叠为横滑条：吸顶 + 主区标题栏叠在其下；数据操作收进「更多」。
  await tab('pages');
  assert.equal(await page.evaluate(() => document.documentElement.scrollHeight > innerHeight), true, 'pages section should overflow on small screens');
  await page.locator('#side-more summary').click();
  assert.equal(await page.locator('.side-ops #export-link').isVisible(), true, 'data ops open behind More on mobile');
  await page.locator('#side-more summary').click();
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  const strip = await page.locator('#side-nav').boundingBox();
  assert.ok(strip.y >= 0 && strip.y < 16, 'side strip must stick to top');
  const mainBar = await page.locator('.main-bar').boundingBox();
  assert.ok(mainBar.y >= 40 && mainBar.y < 90, 'main bar must stack under the strip');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await page.setViewportSize({width:390,height:844});
  await tab('pages');
  await edit();
  await page.locator('#close-editor').click();
  await tab('blocks');
  await create('Mobile preview');
  await tab('pages');
  await edit();
  await placeFirst();
  await page.locator('#block-appearance').scrollIntoViewIfNeeded();
  const styleBox = await page.locator('#block-styles').boundingBox();
  assert.ok(styleBox.x >= 0 && styleBox.x + styleBox.width <= 390);
  await page.screenshot({path:path.join(output,'editor-mobile.png')});
  await page.locator('#cancel-editor').click();
  // admin-content-pack：移动端个人库面板不溢出（file input + 按钮竖排）
  await tab('quote');
  await page.locator('#quote-modes input[value="personal"]').check();
  const personalBox = await page.locator('#personal-box').boundingBox();
  assert.ok(personalBox.x >= 0 && personalBox.x + personalBox.width <= 390, 'personal panel must fit 390px');
  await page.screenshot({path:path.join(output,'personal-mobile.png')});
  await page.locator('#quote-modes input[value="library"]').check();
  assert.deepEqual(errors, []);
  console.log('PASS: cancel/new page/prior draft/card create+place/arrow nudge/card deletion/oss gating/late upload/search race/IME/keyboard/zh-en/themes/mobile/sticky actions');
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });

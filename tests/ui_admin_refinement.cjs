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
  await page.goto(base + '/admin?lang=zh');
  await page.locator('#password').fill(process.env.UI_TEST_PASSWORD || 'local-ui-verification');
  await page.locator('#login-btn').click();
  await page.locator('#view-settings').waitFor({state:'visible'});
  const pageCount = await page.locator('#page-list .page-row').count();
  assert.equal(await page.locator('#card-pages .section-head #add-page').count(), 1);
  assert.equal(await page.locator('.settings-toolbar #save-btn').count(), 1);
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
  await create('Shared test');
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
  await page.locator('#widget-list .widget-row .w-act.danger').first().click();
  payload = await save();
  assert.equal(payload.widget_defs.length, 0);
  assert.equal(payload.pages.some(p => p.layout.some(b => b.def === defId)), false);

  // 编辑器内抽屉：不关闭弹窗完成新建、放置与层级调整。
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

  // sysopt-layout-fix：系统/文字选项行式布局——单选钮不重叠、点档位文字激活该档、控件在标签盒内
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

  for (const lang of ['zh','en']) {
    await page.goto(base + '/admin?lang=' + lang);
    await page.locator('#view-settings').waitFor({state:'visible'});
    for (const colorScheme of ['light','dark']) {
      await page.emulateMedia({colorScheme});
      await page.screenshot({path:path.join(output,`settings-${lang}-${colorScheme}.png`)});
      await edit();
      await page.locator('#draft-img:not([hidden])').waitFor();
      await page.locator('#close-editor').click();
      await create('Style preview');
      await edit();
      await placeFirst();
      await page.locator('#block-style-hero').focus();
      await page.keyboard.press('ArrowRight');
      assert.equal(await page.locator('#block-style-rows').isChecked(), true);
      await page.screenshot({path:path.join(output,`editor-${lang}-${colorScheme}.png`)});
      await page.locator('#cancel-editor').click();
    }
  }
  await page.setViewportSize({width:390,height:844});
  await page.locator('#card-quote').scrollIntoViewIfNeeded();
  const toolbar = await page.locator('.settings-toolbar').boundingBox();
  assert.ok(toolbar.y >= 0 && toolbar.y < 16);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await edit();
  await page.locator('#close-editor').click();
  await create('Mobile preview');
  await edit();
  await placeFirst();
  await page.locator('#block-appearance').scrollIntoViewIfNeeded();
  const styleBox = await page.locator('#block-styles').boundingBox();
  assert.ok(styleBox.x >= 0 && styleBox.x + styleBox.width <= 390);
  await page.screenshot({path:path.join(output,'editor-mobile.png')});
  await page.locator('#cancel-editor').click();
  assert.deepEqual(errors, []);
  console.log('PASS: cancel/new page/prior draft/card create+place/arrow nudge/card deletion/oss gating/late upload/search race/IME/keyboard/zh-en/themes/mobile/sticky actions');
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });

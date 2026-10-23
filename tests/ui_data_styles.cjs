// Use the isolated server described in ui_admin_refinement.cjs; settings writes are mocked.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.UI_TEST_BASE || 'http://127.0.0.1:8766';
const output = process.env.UI_TEST_OUTPUT || path.join(__dirname,'../data/ui-data-styles');
fs.mkdirSync(output,{recursive:true});
(async () => {
  const browser = await chromium.launch({headless:true,...(process.env.UI_TEST_BROWSER ? {executablePath:process.env.UI_TEST_BROWSER} : {})});
  const page = await browser.newPage({viewport:{width:1059,height:964}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(base + '/admin?lang=zh');
  await page.locator('#password').fill(process.env.UI_TEST_PASSWORD || 'local-ui-verification');
  await page.locator('#login-btn').click();
  await page.locator('#view-settings').waitFor({state:'visible'});
  const wire = await (await page.request.get(base + '/admin/api/settings')).json();
  const seed = wire.data.settings;
  seed.widget_defs = [
    {id:'w11111111',name:'Metrics',style:'rows',fields:['weather.temperature','weather.humidity']},
    {id:'w22222222',name:'Old quote',style:'hero',fields:['quote.text']}
  ];
  function block(id,def) { return {id,def,widget:'custom',x:56,y:800,w:300,h:160,z:20}; }
  seed.pages[0].layout.push(block('b11111111','w11111111'),{...block('b22222222','w22222222'),x:400});
  seed.pages[1].layout.push(block('b33333333','w11111111'));
  await page.route('**/admin/api/settings', route => route.fulfill({json:wire}));
  let savedPayload;
  await page.route('**/admin/api/settings/save', route => {
    savedPayload = route.request().postDataJSON();
    return route.fulfill({json:{ok:true,data:{settings:savedPayload,settings_version:'style-ui-test',location_changed:false}}});
  });
  async function save() {
    const response = page.waitForResponse('**/settings/save');
    await page.locator('#save-btn').click(); await response;
    await page.locator('#save-btn:enabled').waitFor();
    return structuredClone(savedPayload);
  }
  async function edit(index=0) {
    await page.locator('#page-list button').filter({hasText:/编辑版面|Edit layout/}).nth(index).click();
    await page.locator('#canvas-modal').waitFor({state:'visible'});
    await page.locator('#stage').waitFor({state:'visible'});
  }
  async function select(id) {
    const el = page.locator(`#stage .block[data-block-id="${id}"]`);
    await el.focus(); await el.press('Enter');
    await page.locator('#appearance-controls').waitFor({state:'visible'});
  }
  async function preview(id,style) {
    const response = page.waitForResponse(r => r.url().endsWith('/layout-preview') && r.status()===200
      && r.request().postDataJSON().layout.some(b => b.id===id && b.style===style));
    await page.locator('#draft-preview:enabled').click();
    const image = await response;
    assert.match(image.headers()['content-type'], /image\/png/);
    // Read through the API client: some Chromium builds discard completed fetch
    // bodies after the page creates a blob URL, before CDP can retrieve them.
    const rendered = await page.request.post(base+'/admin/api/layout-preview', {
      headers:{'X-Requested-With':'kindle-admin'},data:image.request().postDataJSON()
    });
    assert.equal(rendered.status(),200);
    const png = await rendered.body();
    assert.ok(png.length > 8);
    return png;
  }
  await page.reload();
  await page.locator('#view-settings').waitFor({state:'visible'});
  await edit();
  assert.equal(await page.locator('#def-editor').count(),0);
  assert.equal(await page.locator('#appearance-controls').isVisible(),false);
  await select('b11111111');
  assert.equal(await page.locator('#block-styles input').count(),4);
  assert.match(await page.locator('#appearance-current').innerText(),/原有样式/);
  const pngs = [];
  for (const style of ['hero','horizontal','grid','rows']) {
    await page.locator('#block-style-'+style).check();
    const png = await preview('b11111111',style);
    fs.writeFileSync(path.join(output,'render-'+style+'.png'),png);
    pngs.push(png);
  }
  assert.equal(new Set(pngs.map(buf => buf.toString('base64'))).size,4);
  await select('b22222222');
  assert.deepEqual(await page.locator('#block-styles input').evaluateAll(inputs=>inputs.map(el=>el.value)),['rows']);
  assert.match(await page.locator('#appearance-reason').innerText(),/旧版外观/);
  assert.equal(await page.locator('#block-style-rows').isChecked(),false);
  await page.locator('#block-style-rows').check();
  await page.locator('#cancel-editor').click();
  assert.equal(await page.locator('#dirty-flag').isVisible(),false);
  await edit(); await select('b11111111');
  await page.locator('#block-style-horizontal').check();
  await page.locator('#close-editor').click();
  await edit(1); await select('b33333333');
  await page.locator('#block-style-grid').check();
  await page.locator('#close-editor').click();
  let payload = await save();
  assert.equal(payload.pages[0].layout.find(b=>b.id==='b11111111').style,'horizontal');
  assert.equal(payload.pages[1].layout.find(b=>b.id==='b33333333').style,'grid');
  assert.equal(payload.widget_defs[0].style,'rows');
  assert.equal(Object.hasOwn(payload.pages[0].layout.find(b=>b.id==='b22222222'),'style'),false);
  await edit(1); await select('b33333333');
  await page.locator('#block-style-hero').check();
  await page.locator('#cancel-editor').click();
  await edit(1); await select('b33333333');
  assert.equal(await page.locator('#block-style-grid').isChecked(),true);
  await page.locator('#reset-block-style').click();
  assert.equal(await page.locator('#block-style-rows').isChecked(),true);
  await page.locator('#close-editor').click();
  payload = await save();
  assert.equal(Object.hasOwn(payload.pages[1].layout.find(b=>b.id==='b33333333'),'style'),false);
  assert.equal(payload.pages[0].layout.find(b=>b.id==='b11111111').style,'horizontal');

  // Four compact fields get only list/grid choices and default to grid.
  await page.locator('#widget-add').click();
  await page.locator('#widget-name').fill('Four metrics');
  for(const id of ['weather.temperature','weather.description','weather.humidity','weather.wind_speed'])
    await page.locator(`#widget-fields input[value="${id}"]`).check();
  await page.locator('#widget-save').click();
  await page.locator('#widget-form').waitFor({state:'hidden'});
  await page.locator('#widget-list .widget-row .w-name').filter({hasText:'Four metrics'}).waitFor();
  await edit();
  await page.locator('#palette-mine .widget-row .w-add').filter({hasText:'Four metrics'}).click();
  assert.deepEqual(await page.locator('#block-styles input').evaluateAll(inputs=>inputs.map(el=>el.value)),['rows','grid']);
  assert.equal(await page.locator('#block-style-grid').isChecked(),true);
  assert.match(await page.locator('#appearance-note').innerText(),/仅当前页面/);
  await page.locator('#draft-preview:enabled').click();
  await page.locator('#draft-img:not([hidden])').waitFor();
  for(const colorScheme of ['light','dark']) {
    await page.emulateMedia({colorScheme});
    await page.screenshot({path:path.join(output,'canvas-zh-'+colorScheme+'.png')});
  }
  await page.setViewportSize({width:390,height:844});
  await page.locator('#block-appearance').scrollIntoViewIfNeeded();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  const box = await page.locator('#block-styles').boundingBox();
  assert.ok(box.x>=0 && box.x+box.width<=390);
  await page.screenshot({path:path.join(output,'canvas-mobile.png')});
  await page.locator('#cancel-editor').click();
  await page.setViewportSize({width:1059,height:964});
  await page.goto(base+'/admin?lang=en'); await edit(); await select('b11111111');
  assert.equal(await page.locator('#block-styles input').count(),4);
  assert.match(await page.locator('#appearance-note').innerText(),/Only this block/);
  await page.screenshot({path:path.join(output,'canvas-en.png')});
  assert.deepEqual(errors,[]);
  console.log('PASS: field-filtered styles, real PNG differences, legacy inheritance, two-page isolation, cancellation, restore default, recommendation, keyboard, zh/en/themes/mobile');
  await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});

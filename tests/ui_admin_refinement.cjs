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
    await page.locator('#def-fields input').first().waitFor();
  }
  async function create(name) {
    await page.locator('#def-name').fill(name);
    await page.locator('#def-fields input').first().check();
    await page.locator('#def-save').click();
    await page.locator('#palette-mine .widget-item > button').filter({hasText:name}).waitFor();
  }
  async function removeDefinition() {
    await page.locator('#palette-mine .widget-menu summary').click();
    await page.locator('.widget-delete').click();
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
  await page.locator('#stage .block-remove').last().click();
  await create('Cancel this block');
  await page.locator('#cancel-editor').click();
  assert.equal(await dwell.inputValue(), '65');
  assert.equal(await page.locator('#page-list .page-row button').first().evaluate(el => el === document.activeElement), true);
  assert.equal(await page.locator('#dirty-flag').isVisible(), true);
  await edit();
  assert.equal(await page.locator('#stage .block').count(), blockCount);
  assert.equal(await page.locator('#palette-mine .widget-item').count(), 0);
  assert.equal(await page.locator('#def-list').count(), 0);
  await create('Shared test');
  await page.locator('#palette-mine .widget-item > button').click();
  await page.locator('#close-editor').click();
  await edit(1);
  await page.locator('#palette-mine .widget-item > button').click();
  await page.locator('#close-editor').click();
  let payload = await save();
  const defId = payload.widget_defs[0].id;
  assert.equal(payload.pages.filter(p => p.layout.some(b => b.def === defId)).length, 2);
  await edit(1);
  await removeDefinition();
  await page.locator('#cancel-editor').click();
  payload = await save();
  assert.equal(payload.pages.filter(p => p.layout.some(b => b.def === defId)).length, 2);
  await edit(1);
  await removeDefinition();
  await page.locator('#close-editor').click();
  payload = await save();
  assert.equal(payload.widget_defs.length, 0);
  assert.equal(payload.pages.some(p => p.layout.some(b => b.def === defId)), false);

  // A late upload response must not recreate a cancelled draft or add an asset.
  let finishUpload;
  const uploadGate = new Promise(resolve => { finishUpload = resolve; });
  await page.route('**/admin/api/assets', async route => {
    await uploadGate;
    await route.fulfill({json:{ok:true,data:{asset:{id:'a12345678',key:'test.png'}}}});
  });
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

  for (const lang of ['zh','en']) {
    await page.goto(base + '/admin?lang=' + lang);
    await page.locator('#view-settings').waitFor({state:'visible'});
    for (const colorScheme of ['light','dark']) {
      await page.emulateMedia({colorScheme});
      await page.screenshot({path:path.join(output,`settings-${lang}-${colorScheme}.png`)});
      await edit();
      await page.locator('#draft-img:not([hidden])').waitFor();
      await create('Style preview');
      await page.locator('#palette-mine .widget-item > button').click();
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
  await create('Mobile preview');
  await page.locator('#palette-mine .widget-item > button').click();
  await page.locator('#def-editor').scrollIntoViewIfNeeded();
  const styleBox = await page.locator('#block-styles').boundingBox();
  assert.ok(styleBox.x >= 0 && styleBox.x + styleBox.width <= 390);
  await page.screenshot({path:path.join(output,'editor-mobile.png')});
  await page.locator('#cancel-editor').click();
  assert.deepEqual(errors, []);
  console.log('PASS: cancel/new page/prior draft/cross-page deletion/late upload/search race/IME/keyboard/zh-en/themes/mobile/sticky actions');
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });

// Run against a local preview with Playwright installed outside the production app.
const {webkit} = require('playwright');
const assert = require('node:assert/strict');
const base = process.env.SHELF_TEST_URL || 'http://127.0.0.1:18787';
assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(new URL(base).hostname));
(async () => {
  const browser = await webkit.launch({headless: true});
  try {
    for (const [width, scale] of [[1280, 1], [390, 3]]) {
      const context = await browser.newContext({viewport: {width, height: 844}, deviceScaleFactor: scale, isMobile: width < 500, hasTouch: width < 500});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      let state = {is_playing: false};
      const controls = [];
      await page.route('**/playback', async route => {
        if (route.request().method() === 'POST') {
          const body = new URLSearchParams(route.request().postData());
          controls.push(body.get('action'));
          state = {...state, is_playing: body.get('action') === 'resume'};
        }
        await route.fulfill({json: state});
      });
      await page.route(base + '/?sort=custom', async route => {
        const response = await route.fetch();
        await route.fulfill({response, body: (await response.text()).replace('data-preview="true"', 'data-preview="false"')});
      });
      await page.goto(base + '/?sort=custom');
      await page.waitForSelector('.is-selected');
      await page.waitForFunction(() => [...document.querySelectorAll('.album-artwork img')].every(i => i.complete && i.naturalWidth > 0));
      const shelf = await page.locator('.album-artwork img').evaluateAll(images => images.map(i => ({src: i.currentSrc, width: Number(i.srcset.split(',').map(c => c.trim().split(/\s+/)).find(c => new URL(c[0], location.href).href === i.currentSrc)?.[1]?.replace('w', '')) || i.naturalWidth})));
      assert.ok(shelf.length > 50);
      assert.ok(shelf.every(i => i.width <= 320), 'shelf must not download full covers');
      const before = await page.evaluate(() => ({width: document.documentElement.scrollWidth, viewport: innerWidth, shelfBottom: document.querySelector('.crate-shell').getBoundingClientRect().bottom}));
      assert.equal(before.width, before.viewport);
      if (width < 500) assert.ok(before.shelfBottom <= 844);
      await page.locator('[data-record-id="1984"] .album-artwork').click();
      await page.waitForFunction(() => {const i=document.querySelector('.sleeve-front img');return i?.complete && i.naturalWidth>0;});
      const coverURL = await page.locator('.sleeve-front img').evaluate(i=>i.currentSrc);
      assert.ok(!coverURL.includes('%20'), 'cover width descriptors must not be encoded into URLs');
      await page.locator('.turn-sleeve').click();
      await page.waitForFunction(() => {const i=document.querySelector('.sleeve-back img');return i?.complete && i.naturalWidth>0;});
      await page.locator('.enlarge-sleeve').click();
      await page.waitForFunction(() => {const i=document.querySelector('.dialog-artwork img');return i?.complete && i.naturalWidth>0;});
      await page.locator('.dialog-close').click();
      await page.locator('.turn-sleeve').click();
      const key = await page.locator('.is-selected').getAttribute('data-disc-key');
      state = {is_playing: true, context_uri: key};
      await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      await page.waitForFunction(() => document.querySelector('.selected-play').textContent === 'Pause');
      await page.locator('.selected-play').click();
      await page.waitForFunction(() => document.querySelector('.selected-play').textContent === 'Resume');
      assert.equal(await page.locator('.record-disc').evaluate(e => e.classList.contains('is-spinning')), false);
      await page.locator('.selected-play').click();
      await page.waitForFunction(() => document.querySelector('.selected-play').textContent === 'Pause');
      assert.deepEqual(controls, ['pause', 'resume']);
      await page.waitForFunction(() => [...document.querySelectorAll('.disc-choice img, .now-playing img')].every(i => i.complete && i.naturalWidth > 0));
      const icons = await page.locator('.disc-choice img, .now-playing img').evaluateAll(images => images.map(i => Number(i.srcset.split(',').map(c => c.trim().split(/\s+/)).find(c => new URL(c[0], location.href).href === i.currentSrc)?.[1]?.replace('w', '')) || i.naturalWidth));
      assert.ok(icons.every(w => w <= (scale === 1 ? 64 : 160)));
      const bytes = await page.evaluate(() => performance.getEntriesByType('resource').filter(r => document.querySelectorAll('.album-artwork img').length && [...document.querySelectorAll('.album-artwork img')].some(i => i.currentSrc === r.name)).reduce((sum, r) => sum + r.encodedBodySize, 0));
      for (const selector of ['.selected-title-text', '.selected-copy']) {
        await page.evaluate(() => getSelection().removeAllRanges());
        const target = page.locator(selector);
        assert.equal(await target.evaluate(e => getComputedStyle(e).webkitUserSelect), 'none');
        const r = await target.boundingBox();
        await page.mouse.move(r.x + 2, r.y + r.height / 2);
        await page.mouse.down();
        await page.mouse.move(r.x + Math.min(r.width - 2, 140), r.y + r.height / 2, {steps: 20});
        await page.mouse.up();
        assert.equal(await page.evaluate(() => getSelection().toString()), '', 'shelf gestures must not select text');
      }
      assert.equal(await page.locator('.album-artwork img').first().evaluate(e => getComputedStyle(e).webkitUserDrag), 'none');
      const search = page.locator('#record-search');
      await search.fill('editable search');
      assert.equal(await search.evaluate(e => getComputedStyle(e).webkitUserSelect), 'text');
      await search.press('ControlOrMeta+A');
      assert.equal(await search.evaluate(e => e.selectionEnd - e.selectionStart), 'editable search'.length, 'search text must remain selectable');
      await search.fill('');
      assert.deepEqual(errors, []);
      console.log(JSON.stringify({viewport: width, pixelRatio: scale, shelfCovers: shelf.length, shelfImageBytes: bytes, maximumShelfImageWidth: Math.max(...shelf.map(i => i.width)), playback: controls, iconWidths: icons}));
      await context.close();
    }
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});

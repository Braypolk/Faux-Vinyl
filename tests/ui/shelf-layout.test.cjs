// Opt-in real layout check: SHELF_TEST_BROWSER=/path/to/chrome-headless-shell.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {JSDOM} = require('jsdom');

test('sleeve, controls and shelf stay fixed across albums with and without discs', {skip: !process.env.SHELF_TEST_BROWSER}, async t => {
  const base = process.env.SHELF_TEST_URL || 'http://127.0.0.1:18787';
  assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(new URL(base).hostname));
  const response = await fetch(base + '/?sort=custom');
  assert.equal(response.status, 200);
  const dom = new JSDOM(await response.text());
  const document = dom.window.document;
  t.after(() => dom.window.close());
  const root = path.join(__dirname, '../../server');
  document.head.replaceChildren();
  document.querySelectorAll('script').forEach(node => node.remove());
  const style = document.createElement('style');
  style.textContent = ['style.css', 'shelf.css', 'discs.css'].map(name => fs.readFileSync(path.join(root, 'static', name), 'utf8')).join('\n') + '\n*,*::before,*::after{animation:none!important;transition:none!important}';
  document.head.append(style);
  // Keep this geometry check independent of artwork downloads and Spotify.
  const pixel = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
  document.querySelector('[data-record-browser]').dataset.preview = 'true';
  // The optional Billie record need not be present in a fresh collection.
  const glowKey = 'spotify:album:0S0KGZnfBGSIssfF54WSJh';
  if (!document.querySelector('[data-disc-key="' + glowKey + '"]')) {
    const card = document.querySelector('[data-record-id]').cloneNode(true);
    card.dataset.recordId = 'glow-layout-fixture';
    card.dataset.discKey = glowKey;
    card.dataset.title = 'WHEN WE ALL FALL ASLEEP, WHERE DO WE GO?';
    const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../fixtures/collection/catalogue.json'), 'utf8')).items[glowKey];
    card.dataset.discOptions = JSON.stringify(fixture.discs);
    card.dataset.glow = JSON.stringify(fixture.glow);
    document.querySelector('.collection').append(card);
  }
  document.querySelectorAll('img').forEach(image => {image.src = pixel;});
  document.querySelectorAll('[data-record-id]').forEach(card => {
    card.dataset.front = card.dataset.back = '';
    const options = JSON.parse(card.dataset.discOptions || 'null');
    if (options) card.dataset.discOptions = JSON.stringify(options.map(option => ({...option, image: pixel})));
  });
  const script = document.createElement('script');
  script.textContent = `
    const motionListeners = [];
    const titleMotion = {matches: false, addEventListener: (type, listener) => motionListeners.push(listener)};
    const nativeMatchMedia = window.matchMedia.bind(window);
    window.matchMedia = query => query === '(prefers-reduced-motion: reduce)' ? titleMotion : nativeMatchMedia(query);
  ` + ['app.js', 'playback.js', 'shelf.js', 'discs.js'].map(name => fs.readFileSync(path.join(root, 'static', name), 'utf8')).join('\n') + `
    const cardsForLayout = [...document.querySelectorAll('[data-record-id]')];
    const samples = [
      cardsForLayout.reduce((best, card) => (JSON.parse(card.dataset.discOptions || 'null')?.length || 0) > (JSON.parse(best.dataset.discOptions || 'null')?.length || 0) ? card : best),
      cardsForLayout.find(card => !JSON.parse(card.dataset.discOptions || 'null')?.length),
      cardsForLayout.find(card => JSON.parse(card.dataset.discOptions || 'null')?.length === 1)
    ];
    const selectors = ['.record-player', '.sleeve', '.sleeve-tools', '.selected-title', '.selected-actions', '.shelf-toolbar', '.crate-shell'];
    const results = [];
    for (const card of [...samples, ...samples.toReversed()]) {
      if (!card) throw new Error('Missing disc/variant/no-disc fixture');
      card.querySelector('.album-artwork').click();
      const rects = Object.fromEntries(selectors.map(selector => {
        const r = document.querySelector(selector).getBoundingClientRect();
        return [selector, [r.x, r.y, r.width, r.height]];
      }));
      results.push({title: card.dataset.title, rects});
    }
    const header = document.querySelector('header');
    const headerBefore = header.getBoundingClientRect().toJSON();
    samples[0].querySelector('.album-artwork').click();
    document.querySelector('.selected-play').click();
    const shortcut = document.querySelector('.now-playing');
    const playingHeader = {
      hidden: shortcut.hidden,
      before: headerBefore,
      after: header.getBoundingClientRect().toJSON(),
      disc: shortcut.getBoundingClientRect().toJSON(),
      others: ['.brand', 'header nav'].map(selector => document.querySelector(selector).getBoundingClientRect().toJSON())
    };
    const egg = cardsForLayout.find(card => card.dataset.discKey === 'spotify:album:0S0KGZnfBGSIssfF54WSJh');
    egg.querySelector('.album-artwork').click();
    const measureGlow = () => Object.fromEntries([...selectors, '.disc-choices'].map(selector => {
      const r = document.querySelector(selector).getBoundingClientRect();
      return [selector, [r.x, r.y, r.width, r.height]];
    }));
    const glowBefore = measureGlow();
    for (let i = 0; i < 5; i++) document.querySelector('[data-disc-id="30664206604"]').click();
    const glow = {
      before: glowBefore,
      after: measureGlow(),
      pageWidth: document.documentElement.scrollWidth,
      viewportWidth: innerWidth,
      active: document.documentElement.classList.contains('glow-mode'),
      paper: getComputedStyle(document.documentElement).getPropertyValue('--paper'),
      ink: getComputedStyle(document.body).color,
      input: getComputedStyle(document.querySelector('.shelf-filter input')).backgroundColor,
      filter: getComputedStyle(document.querySelector('.record-disc')).filter,
      aura: getComputedStyle(document.querySelector('.record-disc'), '::before').content
    };
    const vinyl = document.querySelector('[data-disc-id="30672682790"]');
    vinyl.click();
    const vinylBefore = measureGlow();
    for (let i = 0; i < 4; i++) vinyl.click();
    const glowVinyl = {
      active: document.documentElement.classList.contains('glow-mode'),
      pageWidth: document.documentElement.scrollWidth,
      viewportWidth: innerWidth,
      before: vinylBefore,
      after: measureGlow(),
      filter: getComputedStyle(document.querySelector('.record-disc-image')).filter,
      thumbFilter: getComputedStyle(vinyl.querySelector('img')).filter,
      clip: getComputedStyle(document.querySelector('.record-disc-image')).clipPath
    };
    const heading = document.querySelector('.selected-title');
    const track = document.querySelector('.selected-title-track');
    const text = document.querySelector('.selected-title-text');
    const repeat = document.querySelector('.selected-title-repeat');
    const marquee = track.getAnimations()[0];
    if (!marquee) throw new Error('Long title did not start scrolling');
    marquee.pause();
    const duration = marquee.effect.getTiming().duration;
    const at = fraction => {
      marquee.currentTime = duration * fraction;
      return text.getBoundingClientRect().left;
    };
    const forward = [at(.25), at(.75), at(1.25), at(1.75)];
    marquee.currentTime = duration - 1;
    const beforeLoop = repeat.getBoundingClientRect().left;
    marquee.currentTime = duration + 1;
    const afterLoop = text.getBoundingClientRect().left;
    const titleScroll = {forward, beforeLoop, afterLoop, duplicateHiddenFromAT: repeat.getAttribute('aria-hidden'), duplicateText: repeat.textContent === text.textContent};
    heading.focus();
    titleScroll.manualDetails = {animations: track.getAnimations().length, repeatHidden: repeat.hidden, overflow: getComputedStyle(heading).overflowX, focused: document.activeElement === heading, tabIndex: heading.tabIndex};
    titleScroll.manual = !titleScroll.manualDetails.animations && titleScroll.manualDetails.repeatHidden && titleScroll.manualDetails.overflow === 'auto';
    heading.blur();
    titleMotion.matches = true;
    motionListeners.forEach(listener => listener());
    titleScroll.reducedMotion = !track.getAnimations().length && repeat.hidden && heading.tabIndex === 0;
    cardsForLayout.reduce((a, b) => a.dataset.title.length < b.dataset.title.length ? a : b).querySelector('.album-artwork').click();
    titleMotion.matches = false;
    motionListeners.forEach(listener => listener());
    titleScroll.shortTitle = !track.getAnimations().length && repeat.hidden && !heading.hasAttribute('tabindex');
    const result = document.createElement('pre');
    result.id = 'layout-results'; result.textContent = JSON.stringify({results, playingHeader, glow, glowVinyl, titleScroll}); document.body.append(result);
  `;
  document.body.append(script);
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'fauxvinyl-layout-'));
  t.after(() => fs.rmSync(temp, {recursive: true, force: true}));
  const file = path.join(temp, 'shelf.html');
  fs.writeFileSync(file, dom.serialize());
  for (const width of [1440, 1024, 768, 390, 320]) {
    const run = spawnSync(process.env.SHELF_TEST_BROWSER, ['--headless', '--no-sandbox', '--disable-gpu', '--no-proxy-server', '--dump-dom', '--window-size=' + width + ',1000', 'file://' + file], {encoding: 'utf8', timeout: 20000, maxBuffer: 2 * 1024 * 1024});
    assert.equal(run.status, 0, run.stderr);
    const output = new JSDOM(run.stdout);
    const result = output.window.document.querySelector('#layout-results');
    assert.ok(result, 'Browser did not produce layout measurements: ' + run.stderr);
    const {results: samples, playingHeader, glow, glowVinyl, titleScroll} = JSON.parse(result.textContent);
    output.window.close();
    for (const sample of samples.slice(1)) {
      for (const [selector, values] of Object.entries(sample.rects)) {
        values.forEach((value, i) => assert.ok(Math.abs(value - samples[0].rects[selector][i]) < 1, width + 'px: ' + selector + ' moved/resized on ' + sample.title + ': ' + JSON.stringify(sample.rects[selector]) + ' vs ' + JSON.stringify(samples[0].rects[selector])));
      }
    }
    const shelf = samples[0].rects['.crate-shell'];
    const toolbar = samples[0].rects['.shelf-toolbar'];
    assert.ok(toolbar[1] >= shelf[1] + shelf[3], width + 'px: search and browsing controls must sit below the shelf');
    assert.equal(playingHeader.hidden, false);
    assert.equal(playingHeader.before.height, playingHeader.after.height, 'starting playback must not resize the header');
    const {disc, after: header, others} = playingHeader;
    assert.ok(Math.abs(disc.x + disc.width / 2 - (header.x + header.width / 2)) < 1, width + 'px: playing disc must be centered');
    for (const other of others) {
      assert.ok(disc.right <= other.left || disc.left >= other.right || disc.bottom <= other.top || disc.top >= other.bottom, width + 'px: playing disc overlaps a header control');
    }
    assert.equal(glow.active, true);
    assert.equal(glow.pageWidth, glow.viewportWidth, width + 'px: CD glow must not widen the page');
    assert.equal(glow.paper, '#0b110e');
    assert.equal(glow.ink, 'rgb(227, 239, 229)');
    assert.equal(glow.input, 'rgb(21, 32, 25)');
    assert.match(glow.filter, /drop-shadow/);
    assert.equal(glow.aura, '""');
    for (const [selector, values] of Object.entries(glow.after)) {
      values.forEach((value, i) => assert.ok(Math.abs(value - glow.before[selector][i]) < 1, width + 'px: glow reveal moved/resized ' + selector));
    }
    assert.equal(glowVinyl.active, true);
    assert.equal(glowVinyl.pageWidth, glowVinyl.viewportWidth, width + 'px: vinyl glow must not widen the page');
    assert.match(glowVinyl.filter, /hue-rotate/);
    assert.match(glowVinyl.thumbFilter, /hue-rotate/);
    assert.match(glowVinyl.clip, /circle/);
    for (const [selector, values] of Object.entries(glowVinyl.after)) {
      values.forEach((value, i) => assert.ok(Math.abs(value - glowVinyl.before[selector][i]) < 1, width + 'px: glow vinyl reveal moved/resized ' + selector));
    }
    assert.ok(titleScroll.forward[1] < titleScroll.forward[0], width + 'px: title must move forward in its first loop');
    assert.ok(titleScroll.forward[3] < titleScroll.forward[2], width + 'px: title must keep moving forward in its second loop');
    assert.ok(Math.abs(titleScroll.beforeLoop - titleScroll.afterLoop) < 1, width + 'px: repeated title must meet the original seamlessly');
    assert.equal(titleScroll.duplicateHiddenFromAT, 'true');
    assert.equal(titleScroll.duplicateText, true);
    assert.equal(titleScroll.manual, true, width + 'px: ' + JSON.stringify(titleScroll.manualDetails));
    assert.equal(titleScroll.reducedMotion, true);
    assert.equal(titleScroll.shortTitle, true);
    t.diagnostic(width + 'px: stable shelf, both glow reveals and seamless forward title scrolling');
  }
});

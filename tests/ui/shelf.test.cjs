// DOM interaction checks against the HTML from a running local Go preview.
// Install jsdom as a temporary development dependency; no browser or Spotify is used.
const {test, before} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const serverRoot = path.join(__dirname, '../../server');
let html, liveScript;
before(async () => {
  const base = process.env.SHELF_TEST_URL || 'http://127.0.0.1:18787';
  const url = new URL(base);
  assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname), 'Use a local preview for UI tests');
  const response = await fetch(base + '/?sort=custom');
  assert.equal(response.status, 200);
  html = await response.text();
  const liveResponse = await fetch(base + '/__dev__/live.js');
  assert.equal(liveResponse.status, 200);
  liveScript = await liveResponse.text();
});
const script = fs.readFileSync(path.join(serverRoot, 'static/shelf.js'), 'utf8');
const response = (data, status = 200) => ({ok: status < 400, status, headers: {get: () => 'application/json'}, json: async () => data});
const deferred = () => {let resolve; const promise = new Promise(r => {resolve = r;}); return {promise, resolve};};
async function settle() {for (let i = 0; i < 5; i++) await new Promise(setImmediate);}
function setup(t, fetcher = () => {throw Error('Unexpected request');}, decorate = () => {}) {
  const dom = new JSDOM(html, {url: 'http://127.0.0.1:18787/?sort=custom', runScripts: 'outside-only', pretendToBeVisual: true});
  t.after(() => dom.window.close());
  const w = dom.window;
  w.matchMedia = () => ({matches: true, addEventListener() {}});
  w.ResizeObserver = class {observe() {}};
  w.HTMLImageElement.prototype.decode = () => Promise.resolve();
  w.fetch = fetcher;
  w.HTMLElement.prototype.animate = () => ({cancel() {}, pause() {}, play() {}});
  w.HTMLElement.prototype.scrollIntoView = function(options) {this.scrollOptions = options;};
  const captured = new Set();
  w.Element.prototype.setPointerCapture = id => captured.add(id);
  w.Element.prototype.hasPointerCapture = id => captured.has(id);
  w.Element.prototype.releasePointerCapture = id => captured.delete(id);
  w.document.querySelector('[data-record-browser]').dataset.preview = 'false';
  const timers = fakeTimers(w);
  decorate(w.document, w);
  w.eval(fs.readFileSync(path.join(serverRoot, 'static/app.js'), 'utf8'));
  w.eval(fs.readFileSync(path.join(serverRoot, 'static/playback.js'), 'utf8'));
  w.eval(script);
  const $ = selector => w.document.querySelector(selector);
  const cards = () => [...w.document.querySelectorAll('[data-record-id]')];
  const ids = () => cards().map(c => c.dataset.recordId);
  return {w, $, cards, ids, timers};
}
test('local preview plays, pauses, resumes and browses without playback requests', async t => {
  let calls = 0;
  const ui = setup(t, () => {calls++; throw Error('Test playback must stay in the UI');}, (document, w) => {
    document.querySelector('[data-record-browser]').dataset.preview = 'true';
  });
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  const withDiscs = ui.cards().filter(card => JSON.parse(card.dataset.discOptions || 'null')?.length);
  const [first, second] = withDiscs;
  first.querySelector('a').click();
  assert.equal(ui.$('.test-mode-toggle'), null);
  ui.$('.selected-play').click();
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(first.classList.contains('is-playing'), true);
  assert.equal(ui.$('.record-disc').classList.contains('is-spinning'), true);
  assert.equal(ui.$('.playback-feedback').hidden, true);
  ui.$('.selected-play').click();
  assert.equal(ui.$('.selected-play').textContent, 'Resume');
  assert.equal(ui.$('.playback-feedback').hidden, true);
  assert.equal(first.classList.contains('is-playing'), false);
  assert.equal(ui.$('.record-disc').classList.contains('is-spinning'), false);
  ui.$('.selected-play').click();
  second.querySelector('a').click();
  assert.equal(ui.$('.selected-play').textContent, 'Play');
  assert.equal(ui.$('.record-disc').classList.contains('is-spinning'), false);
  first.querySelector('a').click();
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(ui.$('.record-disc').classList.contains('is-spinning'), true);
  second.querySelector('a').click(); ui.$('.selected-play').click();
  assert.equal(first.classList.contains('is-playing'), false);
  assert.equal(second.classList.contains('is-playing'), true);
  const noDisc = ui.cards().find(card => !JSON.parse(card.dataset.discOptions || 'null')?.length);
  noDisc.querySelector('a').click(); ui.$('.selected-play').click();
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(ui.$('.record-disc').hidden, true);
  assert.equal(noDisc.classList.contains('is-playing'), true);
  await settle();
  assert.equal(calls, 0);
});
test('production playback ignores old test preferences and has no test-mode control', async t => {
  const calls = [];
  const ui = setup(t, async (url, options) => {
    calls.push(url);
    return response(options.method ? {device: 'TV'} : {csrf: 'csrf', action_token: 'action'});
  }, (document, w) => {
    w.sessionStorage.setItem('fauxvinyl-test-mode', 'true');
    w.history.replaceState(null, '', '/?test=1');
  });
  assert.equal(ui.$('.test-mode-toggle'), null);
  assert.equal(ui.$('[data-record-browser]').dataset.testMode, undefined);
  ui.$('.selected-play').click(); await settle();
  assert.equal(calls.length, 2);
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(ui.$('.playback-feedback').hidden, true);
});
const glowAlbumKey = 'spotify:album:0S0KGZnfBGSIssfF54WSJh';
const normalCDID = '30664206604';
const glowCDID = '30439409589';
const glowVinylID = 'billie-glow-vinyl';
function setupGlow(t, savedPreference) {
  let requests = 0;
  const ui = setup(t, () => {requests++; throw Error('Glow mode must stay in the UI');}, (document, w) => {
    document.querySelector('[data-record-browser]').dataset.preview = 'true';
    // Fresh databases need not contain the optional Billie album. Keep these
    // interaction checks independent of the developer's saved collection.
    if (!document.querySelector('[data-disc-key="' + glowAlbumKey + '"]')) {
      const card = document.querySelector('[data-record-id]').cloneNode(true);
      card.dataset.recordId = 'glow-test-fixture';
      card.dataset.discKey = glowAlbumKey;
      card.dataset.title = 'WHEN WE ALL FALL ASLEEP, WHERE DO WE GO?';
      const catalogue = JSON.parse(fs.readFileSync(path.join(__dirname, '../fixtures/collection/catalogue.json'), 'utf8'));
      card.dataset.discOptions = JSON.stringify(catalogue.items[glowAlbumKey].discs);
      card.dataset.glow = JSON.stringify(catalogue.items[glowAlbumKey].glow);
      document.querySelector('.collection').append(card);
    }
    if (savedPreference) w.localStorage.setItem('fauxvinyl-disc-preferences-v1', JSON.stringify({albums: {[glowAlbumKey]: savedPreference}, kind: savedPreference === glowVinylID ? 'vinyl' : 'cd'}));
  });
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  const card = ui.cards().find(card => card.dataset.discKey === glowAlbumKey);
  assert.ok(card, 'Billie album fixture is present');
  const options = JSON.parse(card.dataset.discOptions);
  card.querySelector('a').click();
  return {...ui, card, options, cd: () => ui.$('[data-disc-id="' + normalCDID + '"]'), glowing: () => ui.w.document.documentElement.classList.contains('glow-mode'), requests: () => requests};
}
test('five CD presses reveal the hidden glow edition, darken the room and keep test playback running', async t => {
  const ui = setupGlow(t);
  const secret = ui.options.find(option => option.id === glowCDID);
  assert.equal(ui.$('[data-disc-id="' + glowCDID + '"]'), null, 'secret edition has no direct choice');
  assert.equal(ui.$('.disc-choices').children.length, 2);
  ui.$('.selected-play').click();
  for (let count = 1; count <= 4; count++) {
    ui.cd().click();
    assert.equal(ui.glowing(), false, 'must remain hidden after ' + count + ' presses');
    assert.equal(ui.cd().textContent, ui.options.find(o => o.id === normalCDID).label);
  }
  ui.cd().click();
  assert.equal(ui.glowing(), true);
  assert.equal(ui.$('.record-disc').classList.contains('is-glowing'), true);
  assert.equal(ui.$('.record-disc-image').getAttribute('src'), secret.image);
  assert.equal(ui.cd().textContent, 'CD 2');
  assert.equal(ui.cd().getAttribute('aria-pressed'), 'true');
  assert.equal(ui.$('.sr-only[role="status"]').textContent, 'CD 2 unlocked. Glow-in-the-dark mode.');
  assert.equal(ui.$('.now-playing').classList.contains('is-glowing'), true);
  assert.equal(ui.$('.now-playing-art img').getAttribute('src'), secret.image);
  assert.equal(ui.$('.record-disc').classList.contains('is-spinning'), true);
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  const image = ui.$('.record-disc-image');
  ui.$('.selected-play').click(); // An unrelated action after unlocking must not relock it.
  ui.cd().click();
  assert.equal(ui.glowing(), true);
  assert.equal(ui.$('.record-disc-image'), image, 'repeated presses reuse the glow artwork');
  const saved = JSON.parse(ui.w.localStorage.getItem('fauxvinyl-disc-preferences-v1'));
  assert.equal(saved.albums[glowAlbumKey], normalCDID, 'the secret is not persisted as a normal preference');
  await settle();
  assert.equal(ui.requests(), 0);
});
test('the CD sequence resets on another action or album, and Vinyl exits glow mode', t => {
  const ui = setupGlow(t);
  for (let i = 0; i < 4; i++) ui.cd().click();
  ui.$('.selected-play').click();
  ui.cd().click();
  assert.equal(ui.glowing(), false, 'another action breaks the sequence');
  for (let i = 0; i < 3; i++) ui.cd().click();
  const other = ui.cards().find(card => card !== ui.card);
  other.querySelector('a').click();
  ui.card.querySelector('a').click();
  ui.cd().click();
  assert.equal(ui.glowing(), false, 'leaving the album resets the sequence');
  for (let i = 0; i < 4; i++) ui.cd().click();
  assert.equal(ui.glowing(), true);
  const vinyl = ui.options.find(option => option.kind === 'vinyl');
  ui.$('[data-disc-id="' + vinyl.id + '"]').click();
  assert.equal(ui.glowing(), false);
  assert.equal(ui.$('.record-disc').classList.contains('is-glowing'), false);
  assert.equal(ui.$('.now-playing').classList.contains('is-glowing'), false);
  assert.equal(ui.cd().textContent, 'CD 1');
  for (let i = 0; i < 5; i++) ui.cd().click();
  assert.equal(ui.glowing(), true);
  other.querySelector('a').click();
  assert.equal(ui.glowing(), true, 'browsing keeps the room dark');
  ui.card.querySelector('a').click();
  assert.equal(ui.glowing(), true, 'returning to the album keeps CD 2 revealed');
  assert.equal(ui.$('.record-disc-image').getAttribute('src'), ui.options.find(o => o.id === glowCDID).image);
  other.querySelector('a').click();
  ui.$('.selected-play').click();
  assert.equal(ui.glowing(), false, 'playing another record restores the normal theme');
  ui.card.querySelector('a').click();
  assert.equal(ui.$('.record-disc-image').getAttribute('src'), ui.options.find(o => o.id === normalCDID).image);
});
test('glow mode survives browsing, pause and resume, until a disc choice changes', t => {
  const ui = setupGlow(t);
  ui.$('.selected-play').click();
  for (let i = 0; i < 5; i++) ui.cd().click();
  const secretImage = ui.$('.record-disc-image');
  ui.$('.selected-play').click();
  assert.equal(ui.glowing(), true, 'pausing does not end glow mode');
  ui.$('.selected-play').click();
  assert.equal(ui.glowing(), true, 'resuming does not end glow mode');
  const other = ui.cards().find(card => card !== ui.card && JSON.parse(card.dataset.discOptions || 'null')?.length > 1);
  other.querySelector('a').click();
  assert.equal(ui.glowing(), true);
  assert.equal(ui.$('.record-disc').classList.contains('is-glowing'), false, 'another album does not gain the glow artwork');
  assert.equal(ui.$('.now-playing').classList.contains('is-glowing'), true);
  ui.$('.now-playing').click();
  assert.equal(ui.glowing(), true);
  assert.equal(ui.$('.record-disc-image'), secretImage, 'returning reuses the unlocked artwork');
  other.querySelector('a').click();
  const alternatives = [...ui.w.document.querySelectorAll('.disc-choice')];
  alternatives.find(button => button.getAttribute('aria-pressed') !== 'true').click();
  assert.equal(ui.glowing(), false, 'changing another album’s disc choice also exits glow mode');
});
test('a successful normal playback action on another record exits glow mode', t => {
  const ui = setupGlow(t);
  for (let i = 0; i < 5; i++) ui.cd().click();
  const other = ui.cards().find(card => card !== ui.card);
  other.querySelector('a').click();
  other.querySelector('a').click();
  ui.$('.selected-play').click();
  assert.equal(ui.glowing(), false);
});
test('a previously saved CD 2 choice cannot bypass the secret sequence', t => {
  const ui = setupGlow(t, glowCDID);
  assert.equal(ui.glowing(), false);
  assert.equal(ui.$('[data-disc-id="' + glowCDID + '"]'), null);
  assert.equal(ui.$('.record-disc-image').getAttribute('src'), ui.options.find(o => o.id === normalCDID).image);
  for (let i = 0; i < 4; i++) ui.cd().click();
  assert.equal(ui.glowing(), false);
  ui.cd().click();
  assert.equal(ui.glowing(), true);
});
test('five Vinyl presses reveal the glow pressing and keep its artwork while browsing', t => {
  const ui = setupGlow(t);
  const normal = ui.options.find(o => o.kind === 'vinyl' && o.id !== glowVinylID);
  const secret = ui.options.find(o => o.id === glowVinylID);
  assert.ok(secret, 'real glow-vinyl artwork is in the catalogue');
  const vinyl = ui.$('[data-disc-id="' + normal.id + '"]');
  assert.equal(ui.$('[data-disc-id="' + glowVinylID + '"]'), null, 'glow pressing has no direct choice');
  assert.equal(ui.$('.disc-choices').children.length, 2);
  ui.$('.selected-play').click();
  for (let i = 1; i <= 4; i++) {
    vinyl.querySelector('img').click();
    assert.equal(ui.glowing(), false, 'Vinyl remains ordinary after ' + i + ' presses');
  }
  vinyl.querySelector('img').click();
  assert.equal(ui.glowing(), true);
  assert.equal(ui.$('.record-disc-image').getAttribute('src'), secret.image);
  assert.equal(ui.$('.record-disc').classList.contains('is-glow-vinyl'), true);
  assert.equal(ui.$('.now-playing').classList.contains('is-glow-vinyl'), true);
  assert.equal(ui.$('.now-playing-art img').getAttribute('src'), secret.image);
  assert.equal(vinyl.textContent, secret.label);
  assert.equal(vinyl.getAttribute('aria-pressed'), 'true');
  assert.equal(ui.$('.glow-word').textContent, 'go', 'thumbnail presses keep the reveal bubble after artwork swaps');
  const image = ui.$('.record-disc-image');
  const thumb = vinyl.querySelector('img');
  const other = ui.cards().find(card => card !== ui.card);
  other.querySelector('a').click();
  assert.equal(ui.glowing(), true);
  assert.equal(ui.$('.record-disc').classList.contains('is-glow-vinyl'), false);
  ui.$('.now-playing').click();
  assert.equal(ui.$('.record-disc-image'), image);
  assert.equal(vinyl.querySelector('img'), thumb);
  assert.equal(ui.$('.record-disc').classList.contains('is-glow-vinyl'), true);
  const saved = JSON.parse(ui.w.localStorage.getItem('fauxvinyl-disc-preferences-v1'));
  assert.equal(saved.albums[glowAlbumKey], normal.id);
  assert.equal(saved.kind, 'vinyl');
  ui.cd().click();
  assert.equal(ui.glowing(), false, 'switching to CD exits glow mode');
  assert.equal(ui.$('.now-playing').classList.contains('is-glow-vinyl'), false);
  for (let i = 0; i < 4; i++) ui.cd().click();
  assert.equal(ui.glowing(), true);
  assert.equal(ui.$('.record-disc-image').getAttribute('src'), ui.options.find(o => o.id === glowCDID).image);
  assert.equal(ui.$('.record-disc').classList.contains('is-glow-vinyl'), false, 'CD retains its own artwork and treatment');
  vinyl.click();
  assert.equal(ui.glowing(), false, 'switching back to Vinyl exits CD glow mode');
  for (let i = 0; i < 4; i++) vinyl.click();
  assert.equal(ui.$('.record-disc-image'), image, 'unlocking the same pressing again reuses its image');
  assert.equal(vinyl.querySelector('img'), thumb, 'glow thumbnails are cached too');
  other.querySelector('a').click();
  ui.$('.selected-play').click();
  assert.equal(ui.glowing(), false, 'playing another record exits vinyl glow mode');
});
test('CD and Vinyl presses cannot be combined into one reveal sequence', t => {
  const ui = setupGlow(t);
  const vinyl = ui.$('[data-disc-id="30672682790"]');
  for (let i = 0; i < 4; i++) ui.cd().click();
  vinyl.click();
  ui.cd().click();
  assert.equal(ui.glowing(), false);
  for (let i = 0; i < 3; i++) ui.cd().click();
  assert.equal(ui.glowing(), false);
  ui.cd().click();
  assert.equal(ui.glowing(), true);
});
test('a saved glow-vinyl preference cannot bypass the hidden reveal', t => {
  const ui = setupGlow(t, glowVinylID);
  assert.equal(ui.glowing(), false);
  assert.equal(ui.$('[data-disc-id="' + glowVinylID + '"]'), null);
  assert.notEqual(ui.$('.disc-choice[aria-pressed="true"]').dataset.discId, glowVinylID);
});
test('top playing disc keeps its artwork while browsing and returns to a filtered-out playing record', async t => {
  let requests = 0;
  const ui = setup(t, () => {requests++; throw Error('No playback request expected');}, (document, w) => {
    document.querySelector('[data-record-browser]').dataset.preview = 'true';
  });
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  const shortcut = ui.$('.now-playing');
  assert.equal(shortcut.hidden, true);
  const record = ui.cards().find(card => JSON.parse(card.dataset.discOptions || 'null')?.length > 1);
  record.querySelector('a').click();
  ui.$('.selected-play').click();
  assert.equal(shortcut.hidden, false);
  assert.equal(shortcut.classList.contains('is-spinning'), true);
  assert.ok(shortcut.getAttribute('aria-label').includes(record.dataset.title));
  assert.equal(shortcut.querySelector('img').getAttribute('src'), ui.$('.record-disc-image').getAttribute('src'));
  ui.$('.disc-choices').lastElementChild.click();
  const image = shortcut.querySelector('img');
  assert.equal(image.getAttribute('src'), ui.$('.record-disc-image').getAttribute('src'));
  ui.cards().find(card => card !== record).querySelector('a').click();
  assert.equal(shortcut.querySelector('img'), image, 'browsing must retain the playing album artwork');
  ui.$('#record-search').value = 'no-record-matches-this-search';
  ui.$('#record-search').dispatchEvent(new ui.w.Event('input'));
  assert.equal(record.hidden, true);
  shortcut.click();
  assert.equal(ui.$('#record-search').value, '');
  assert.equal(record.hidden, false);
  assert.equal(record.classList.contains('is-selected'), true);
  assert.equal(ui.w.document.activeElement, record.querySelector('a'));
  assert.equal(ui.$('.record-player').scrollOptions, undefined, 'returning to the playing record must not scroll the page');
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  ui.$('.selected-play').click();
  assert.equal(shortcut.hidden, true);
  ui.$('.selected-play').click();
  assert.equal(shortcut.hidden, false);
  shortcut.querySelector('img').dispatchEvent(new ui.w.Event('error'));
  assert.ok(shortcut.querySelector('.now-playing-fallback'));
  ui.cards().find(card => card !== record).querySelector('a').click();
  assert.ok(shortcut.querySelector('.now-playing-fallback'), 'failed artwork keeps the fallback while browsing');
  shortcut.click();
  ui.$('.selected-play').click();
  assert.equal(shortcut.hidden, true);
  await settle();
  assert.equal(requests, 0);
});
test('top playing disc works even when no record has disc artwork', t => {
  const ui = setup(t, undefined, (document, w) => {
    document.querySelector('[data-record-browser]').dataset.preview = 'true';
    document.querySelectorAll('[data-record-id]').forEach(card => {card.dataset.discOptions = 'null';});
  });
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  const first = ui.cards()[0];
  ui.$('.selected-play').click();
  assert.equal(ui.$('.now-playing').hidden, false);
  assert.ok(ui.$('.now-playing-fallback'));
  ui.cards()[1].querySelector('a').click();
  ui.$('.now-playing').click();
  assert.equal(first.classList.contains('is-selected'), true);
});
test('top playing disc follows live playback state, pause and unrelated playback', async t => {
  let state = {is_playing: false};
  const ui = setup(t, async () => response(state), document => {document.querySelector('[data-record-browser]').dataset.preview = 'false';});
  const record = ui.cards()[0];
  state = {is_playing: true, context_uri: record.dataset.discKey};
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  await ui.timers.run(0);
  await settle();
  assert.equal(ui.$('.now-playing').hidden, false);
  assert.ok(ui.$('.now-playing').getAttribute('aria-label').includes(record.dataset.title));
  ui.cards()[1].querySelector('a').click();
  ui.$('.now-playing').click();
  assert.equal(record.classList.contains('is-selected'), true);
  state = {is_playing: false};
  ui.w.document.dispatchEvent(new ui.w.Event('visibilitychange'));
  await ui.timers.run(0); await settle();
  assert.equal(ui.$('.now-playing').hidden, true);
  state = {is_playing: true, context_uri: 'spotify:album:unrelated'};
  ui.w.document.dispatchEvent(new ui.w.Event('visibilitychange'));
  await ui.timers.run(0); await settle();
  assert.equal(ui.$('.now-playing').hidden, true);
});
test('revisiting sleeves reuses loaded and in-flight images without assigning their URLs again', async t => {
  const sources = [];
  const ui = setup(t, undefined, (document, w) => {
    const src = Object.getOwnPropertyDescriptor(w.HTMLImageElement.prototype, 'src');
    Object.defineProperty(w.HTMLImageElement.prototype, 'src', {...src, set(value) {sources.push(value); src.set.call(this, value);}});
    [...document.querySelectorAll('[data-record-id]')].slice(0, 2).forEach((card, i) => {
      card.dataset.front = '/test/front-' + i + '.webp';
      card.dataset.back = '/test/back-' + i + '.webp';
    });
  });
  const [first, second] = ui.cards();
  const front = ui.$('.sleeve-front img'), back = ui.$('.sleeve-back img');
  second.querySelector('a').click();
  first.querySelector('a').click();
  assert.equal(ui.$('.sleeve-front img'), front, 'an in-flight cover must be reused');
  assert.equal(ui.$('.sleeve-back img'), back);
  front.dispatchEvent(new ui.w.Event('load')); back.dispatchEvent(new ui.w.Event('load')); await settle();
  second.querySelector('a').click(); first.querySelector('a').click();
  assert.equal(ui.$('.sleeve-front img'), front);
  assert.equal(ui.$('.sleeve-loading'), null, 'cached covers must not show a new loading state');
  assert.equal(sources.length, 4, 'each front/back URL is assigned only on its first visit');
  ui.$('.turn-sleeve').click();
  assert.equal(ui.$('.sleeve-back img'), back);
});
test('late cover events leave the current album intact and failed images can be retried', async t => {
  const ui = setup(t, undefined, document => {
    [...document.querySelectorAll('[data-record-id]')].slice(0, 2).forEach((card, i) => {
      card.dataset.front = '/test/front-' + i + '.webp';
      card.dataset.back = '/test/back-' + i + '.webp';
    });
  });
  const [first, second] = ui.cards().filter(card => card.dataset.front && card.dataset.back);
  first.querySelector('a').click();
  const oldFront = ui.$('.sleeve-front img');
  second.querySelector('a').click();
  const newFront = ui.$('.sleeve-front img');
  oldFront.dispatchEvent(new ui.w.Event('error'));
  assert.equal(ui.$('.sleeve-front img'), newFront);
  newFront.dispatchEvent(new ui.w.Event('error'));
  assert.equal(ui.$('.sleeve-front img'), null);
  first.querySelector('a').click(); second.querySelector('a').click();
  assert.ok(ui.$('.sleeve-front img'));
  assert.notEqual(ui.$('.sleeve-front img'), newFront, 'errors must not be cached forever');
});
test('enlarged artwork reuses images when flipping and reopening the viewer', async t => {
  const ui = setup(t);
  ui.w.HTMLDialogElement.prototype.showModal = function() {this.open = true;};
  ui.w.HTMLDialogElement.prototype.close = function() {this.open = false;};
  const card = ui.cards().find(card => card.dataset.front && card.dataset.back);
  card.querySelector('a').click();
  ui.$('.enlarge-sleeve').click();
  const front = ui.$('.dialog-artwork img');
  front.dispatchEvent(new ui.w.Event('load')); await settle();
  ui.$('.dialog-turn').click();
  const back = ui.$('.dialog-artwork img');
  back.dispatchEvent(new ui.w.Event('load')); await settle();
  ui.$('.dialog-turn').click();
  assert.equal(ui.$('.dialog-artwork img'), front);
  ui.$('.dialog-close').click(); ui.$('.enlarge-sleeve').click();
  assert.equal(ui.$('.dialog-artwork img'), front);
  assert.equal(ui.$('.dialog-artwork .sleeve-loading'), null);
});
test('revisiting disc artwork reuses full images and choice thumbnails', t => {
  const sources = [];
  const ui = setup(t, undefined, (document, w) => {
    const src = Object.getOwnPropertyDescriptor(w.HTMLImageElement.prototype, 'src');
    Object.defineProperty(w.HTMLImageElement.prototype, 'src', {...src, set(value) {if (value.startsWith('/test/disc')) sources.push(value); src.set.call(this, value);}});
    document.querySelector('[data-record-browser]').dataset.preview = 'true';
    [...document.querySelectorAll('[data-record-id]')].slice(0, 2).forEach((card, i) => {
      card.dataset.discKey = 'test-album-' + i;
      card.dataset.discOptions = JSON.stringify([0, 1].map(j => ({id: i + '-' + j, kind: 'vinyl', label: 'Disc ' + j, image: '/test/disc-' + i + '-' + j + '.webp'})));
    });
  });
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  const [first, second] = ui.cards();
  const disc = ui.$('.record-disc-image'), choice = ui.$('.disc-choice');
  disc.dispatchEvent(new ui.w.Event('load'));
  const choices = [...ui.$('.disc-choices').children];
  choices[1].click(); choices[0].click();
  assert.equal(ui.$('.record-disc-image'), disc, 'variant switching should reuse the image');
  second.querySelector('a').click();
  const assignments = sources.length;
  first.querySelector('a').click(); second.querySelector('a').click(); first.querySelector('a').click();
  assert.equal(ui.$('.record-disc-image'), disc);
  assert.equal(ui.$('.disc-choice'), choice);
  assert.equal(ui.$('.record-disc').classList.contains('is-loading'), false);
  assert.equal(sources.length, assignments, 'returning to an album must not reset disc or thumbnail URLs');
  choices[1].click();
  const failed = ui.$('.record-disc-image');
  choices[0].click();
  failed.dispatchEvent(new ui.w.Event('error'));
  assert.equal(ui.$('.record-disc').hidden, false, 'a late error must not hide the selected disc');
  choices[1].click();
  const retry = ui.$('.record-disc-image');
  assert.notEqual(retry, failed, 'a failed disc should be retried on its next visit');
  retry.dispatchEvent(new ui.w.Event('error'));
  assert.equal(ui.$('.record-disc').hidden, true);
  choices[0].click();
  assert.equal(ui.$('.record-disc-image'), disc);
  assert.equal(ui.$('.record-disc').hidden, false);
});
test('search matches artists, songs, album names and mixed terms without network requests', t => {
  const ui = setup(t, undefined, document => {
    const cards = [...document.querySelectorAll('[data-record-id]')];
    cards[0].dataset.search = 'HIT ME HARD AND SOFT Billie Eilish BIRDS OF A FEATHER BLUE';
    cards[1].dataset.search = 'Happier Than Ever Billie Eilish Getting Older';
    cards[2].dataset.search = 'Renaissance Beyoncé DON’T HURT YOURSELF';
  });
  const [first, second, third] = ui.cards();
  const search = value => {ui.$('#record-search').value = value; ui.$('#record-search').dispatchEvent(new ui.w.Event('input')); return ui.cards().filter(c => !c.hidden);};
  assert.ok(search('billie eilish').includes(first));
  assert.ok(search('billie eilish').includes(second));
  assert.ok(search('birds of a feather').includes(first));
  assert.ok(!search('birds of a feather').includes(second));
  assert.ok(search('hit me hard').includes(first));
  assert.ok(search('BILLIE birds').includes(first));
  assert.ok(search('beyonce dont hurt').includes(third));
  assert.equal(search('there-is-no-such-artist-xyzz').length, 0);
  assert.equal(ui.$('.record-player').hidden, true);
  assert.equal(search('   ').length, ui.cards().length);
});
test('search from URL and sorting preserve the artist/song query', t => {
  const ui = setup(t, undefined, document => {
    document.querySelectorAll('[data-record-id]').forEach(card => {card.dataset.search = card.dataset.title;});
    const first = document.querySelector('[data-record-id]');
    first.dataset.search = 'Album Billie Eilish BIRDS OF A FEATHER';
    document.querySelector('#record-search').value = 'Billie birds';
  });
  assert.equal(ui.cards().filter(c => !c.hidden).length, 1);
  ui.$('#shelf-sort').form.addEventListener('submit', e => e.preventDefault());
  ui.$('#shelf-sort').dispatchEvent(new ui.w.Event('change'));
  assert.equal(ui.$('#shelf-sort').form.elements.q.value, 'Billie birds');
});
test('NFC opens the scanned album, overrides simulated mode and starts it once on the shelf', async t => {
  const calls = [];
  let target;
  const ui = setup(t, async (url, options) => {
    calls.push({url, options});
    return response(options.method ? {device: 'TV'} : {csrf: 'fresh-csrf', action_token: 'nfc-action'});
  }, (document, w) => {
    const cards = [...document.querySelectorAll('[data-record-id]')];
    target = cards[5].dataset;
    const browser = document.querySelector('[data-record-browser]');
    browser.dataset.preview = 'false';
    browser.dataset.autoplayId = target.recordId;
    w.sessionStorage.setItem('fauxvinyl-selected', cards[0].dataset.recordId);
    w.sessionStorage.setItem('fauxvinyl-test-mode', 'true');
    w.history.replaceState(null, '', target.play);
  });
  assert.equal(ui.$('.is-selected').dataset.recordId, target.recordId);
  assert.equal(ui.w.location.pathname, '/');
  assert.equal(ui.w.location.hash, '#record=' + target.recordId);
  assert.equal(ui.$('[data-record-browser]').dataset.testMode, undefined);
  await new Promise(resolve => ui.w.requestAnimationFrame(resolve)); await settle();
  assert.deepEqual(calls.map(call => call.url), [target.play, target.play + '/play']);
  assert.equal(calls[1].options.method, 'POST');
  assert.equal(calls[1].options.body.get('action_token'), 'nfc-action');
  assert.equal(ui.$('.is-playing').dataset.recordId, target.recordId);
  assert.equal(ui.$('.playback-feedback').hidden, true);
});
test('NFC failures stay on the selected shelf and do not automatically retry', async t => {
  let calls = 0;
  const ui = setup(t, async (url, options) => {
    calls++;
    return options.method ? response({error: 'Your selected device is offline.'}, 503) : response({csrf: 'csrf', action_token: 'action'});
  }, document => {
    const browser = document.querySelector('[data-record-browser]');
    browser.dataset.preview = 'false';
    browser.dataset.autoplayId = document.querySelectorAll('[data-record-id]')[3].dataset.recordId;
  });
  await new Promise(resolve => ui.w.requestAnimationFrame(resolve)); await settle();
  assert.equal(calls, 2);
  assert.equal(ui.$('.playback-feedback').classList.contains('is-error'), true);
  assert.equal(ui.$('.playback-settings').hidden, false);
  assert.equal(ui.$('.selected-play').textContent, 'Try again');
  assert.equal(ui.w.location.pathname, '/');
  assert.equal(ui.$('.record-player').hidden, false);
});
test('a refreshed shelf link selects its record without starting playback', async t => {
  let calls = 0;
  let target;
  const ui = setup(t, () => {calls++; throw Error('A shelf link must not play');}, (document, w) => {
    target = document.querySelectorAll('[data-record-id]')[4].dataset.recordId;
    w.history.replaceState(null, '', '/#record=' + target);
  });
  await new Promise(resolve => ui.w.requestAnimationFrame(resolve)); await settle();
  assert.equal(ui.$('.is-selected').dataset.recordId, target);
  assert.equal(calls, 0);
});
test('NFC in local preview simulates playback without sending music requests', async t => {
  let calls = 0;
  const ui = setup(t, () => {calls++; throw Error('Local NFC preview must stay simulated');}, (document, w) => {
    const browser = document.querySelector('[data-record-browser]');
    browser.dataset.autoplayId = document.querySelectorAll('[data-record-id]')[2].dataset.recordId;
    document.querySelector('[data-record-browser]').dataset.preview = 'true';
  });
  await new Promise(resolve => ui.w.requestAnimationFrame(resolve)); await settle();
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(ui.$('.is-playing').dataset.recordId, ui.$('.is-selected').dataset.recordId);
  assert.equal(calls, 0);
});
test('play stays on shelf, prevents duplicate submits and allows browsing while pending', async t => {
  const action = deferred(); const played = deferred(); const calls = [];
  const ui = setup(t, (url, options) => {calls.push({url, options}); return calls.length === 1 ? action.promise : played.promise;});
  const [first, second] = ui.cards();
  ui.$('.selected-play').click(); ui.$('.selected-play').click();
  assert.equal(calls.length, 1);
  assert.equal(ui.$('.selected-play').disabled, true);
  assert.equal(ui.$('.playback-feedback').hidden, true);
  second.querySelector('.album-artwork').click();
  assert.equal(ui.$('.selected-title-text').textContent, second.dataset.title);
  assert.equal(ui.$('.selected-play').disabled, true);
  action.resolve(response({csrf: 'fresh-csrf', action_token: 'fresh-action'})); await settle();
  assert.equal(calls.length, 2);
  assert.equal(calls[1].url, first.dataset.play + '/play');
  assert.equal(calls[1].options.body.get('csrf'), 'fresh-csrf');
  assert.equal(calls[1].options.body.get('action_token'), 'fresh-action');
  played.resolve(response({device: 'TV', preview: false})); await settle();
  assert.equal(ui.$('.selected-play').disabled, false);
  assert.equal(ui.$('.selected-title-text').textContent, second.dataset.title);
  assert.equal(ui.$('.playback-feedback').hidden, true);
  assert.equal(first.classList.contains('is-playing'), true);
  assert.equal(ui.w.location.pathname, '/');
});
test('play errors are inline and explicit retry obtains a new action', async t => {
  const calls = [];
  const ui = setup(t, async (url, options) => {
    calls.push({url, options});
    if (!options.method) return response({csrf: 'csrf', action_token: 'action-' + calls.length});
    return calls.length === 2 ? response({error: 'Your selected device is offline.'}, 503) : response({device: 'TV'});
  });
  ui.$('.selected-play').click(); await settle();
  assert.match(ui.$('[data-playback-message]').textContent, /offline/);
  assert.equal(ui.$('.playback-settings').hidden, false);
  assert.equal(ui.$('.selected-play').textContent, 'Try again');
  ui.$('.selected-play').click(); await settle();
  assert.equal(calls.length, 4);
  assert.equal(calls[3].options.body.get('action_token'), 'action-3');
  assert.equal(ui.$('.playback-settings').hidden, true);
  assert.equal(ui.$('.playback-feedback').hidden, true);
});
test('expired sign-in and uncertain network results do not silently retry', async t => {
  let calls = 0;
  const ui = setup(t, async () => {calls++; return response({error: 'Your session expired.'}, 401);});
  ui.$('.selected-play').click(); await settle();
  assert.equal(calls, 1);
  assert.equal(ui.$('.playback-login').hidden, false);
  assert.equal(ui.$('.selected-play').disabled, false);
  let networkCalls = 0;
  ui.w.fetch = async () => {networkCalls++; if (networkCalls === 1) return response({csrf: 'csrf', action_token: 'action'}); throw Error('Connection lost');};
  ui.$('.selected-play').click(); await settle();
  assert.equal(networkCalls, 2);
  assert.match(ui.$('[data-playback-message]').textContent, /Could not confirm playback/);
});
test('custom move buttons save every record once and keep the selection', async t => {
  const calls = []; const saved = deferred();
  const ui = setup(t, (url, options) => {calls.push({url, options}); return saved.promise;});
  const original = ui.ids(); const selected = ui.cards()[0];
  ui.$('.arrange-records').click();
  assert.equal(ui.$('#record-search').disabled, true);
  assert.equal(ui.$('#shelf-sort').disabled, true);
  ui.$('.arrange-right').click();
  assert.deepEqual(ui.ids().slice(0, 2), [original[1], original[0]]);
  assert.equal(calls.length, 0);
  assert.equal(ui.$('.selected-title-text').textContent, selected.dataset.title);
  ui.$('.arrange-save').click(); await settle();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/shelf/order');
  assert.deepEqual([...calls[0].options.body.getAll('card_id')], ui.ids());
  assert.equal(new Set(calls[0].options.body.getAll('card_id')).size, ui.cards().length);
  assert.equal(ui.$('.arrange-left').disabled, true);
  saved.resolve(response({order_version: 'saved-version'})); await settle();
  assert.equal(ui.$('.arrange-toolbar').hidden, true);
  assert.equal(ui.$('#record-search').disabled, false);
  assert.equal(ui.$('[data-record-browser]').dataset.orderVersion, 'saved-version');
  assert.equal(ui.$('.order-feedback').textContent, 'Order saved');
});
test('cancel restores order and search without sending changes', async t => {
  const ui = setup(t); const original = ui.ids();
  ui.$('#record-search').value = ui.cards()[0].dataset.title;
  ui.$('#record-search').dispatchEvent(new ui.w.Event('input'));
  const query = ui.$('#record-search').value;
  ui.$('.arrange-records').click();
  assert.equal(ui.cards().filter(c => !c.hidden).length, ui.cards().length);
  ui.$('.arrange-right').click();
  ui.$('.arrange-cancel').click();
  assert.deepEqual(ui.ids(), original);
  assert.equal(ui.$('#record-search').value, query);
  assert.equal(ui.$('.arrange-toolbar').hidden, true);
});
test('keyboard reordering retains focus and Escape cancels', t => {
  const ui = setup(t); const original = ui.ids(); const first = ui.cards()[0];
  ui.$('.arrange-records').click();
  first.querySelector('a').dispatchEvent(new ui.w.KeyboardEvent('keydown', {key: 'ArrowRight', altKey: true, bubbles: true}));
  assert.deepEqual(ui.ids().slice(0, 2), [original[1], original[0]]);
  assert.equal(ui.w.document.activeElement, first.querySelector('a'));
  first.querySelector('a').dispatchEvent(new ui.w.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
  assert.deepEqual(ui.ids(), original);
  assert.equal(ui.$('.arrange-toolbar').hidden, true);
});
test('pointer dragging reorders packed spines; cancelled gestures restore their order', t => {
  const ui = setup(t); const original = ui.ids(); const first = ui.cards()[0];
  ui.cards().forEach(card => {card.getBoundingClientRect = () => ({left: ui.cards().indexOf(card) * 20, width: 20});});
  function pointer(target, type, x) {
    const event = new ui.w.MouseEvent(type, {bubbles: true, cancelable: true, clientX: x, clientY: 10, button: 0, buttons: 1});
    Object.defineProperties(event, {pointerType: {value: 'touch'}, pointerId: {value: 1}});
    target.dispatchEvent(event);
  }
  ui.$('.arrange-records').click();
  pointer(first.querySelector('a'), 'pointerdown', 10);
  const end = ui.cards().length * 20 - 10;
  pointer(ui.$('.collection'), 'pointermove', end);
  assert.equal(ui.ids().at(-1), original[0]);
  pointer(ui.$('.collection'), 'pointercancel', end);
  assert.deepEqual(ui.ids(), original);
  pointer(first.querySelector('a'), 'pointerdown', 10);
  pointer(ui.$('.collection'), 'pointermove', 50);
  pointer(ui.$('.collection'), 'pointerup', 50);
  assert.equal(ui.ids()[2], original[0]);
  assert.equal(first.classList.contains('is-dragging'), false);
});
test('stale-tab save leaves the draft visible and provides a reload action', async t => {
  const ui = setup(t, async () => response({error: 'The shelf changed in another tab.'}, 409));
  ui.$('.arrange-records').click(); ui.$('.arrange-right').click(); ui.$('.arrange-save').click(); await settle();
  assert.equal(ui.$('.arrange-toolbar').hidden, false);
  assert.match(ui.$('.arrange-status').textContent, /another tab/);
  assert.equal(ui.$('.arrange-status a').getAttribute('href'), '/?sort=custom');
  assert.equal(ui.$('.arrange-save').disabled, false);
});

test('real playback toggles Pause and Resume without restarting the album, and follows external state', async t => {
  const actions = [];
  let playing = true;
  let gate;
  let external;
  const ui = setup(t, async (url, options) => {
    assert.equal(url, '/playback');
    if (!options.method) return response(external);
    const body = options.body;
    actions.push({action: body.get('action'), id: body.get('card_id'), csrf: body.get('csrf')});
    if (gate) await gate.promise;
    playing = body.get('action') === 'resume';
    return response({is_playing: playing, context_uri: first.dataset.discKey});
  }, document => {document.querySelector('[data-record-browser]').dataset.preview = 'false';});
  const first = ui.cards()[0];
  const browser = ui.$('[data-record-browser]');
  external = {is_playing: true, context_uri: first.dataset.discKey};
  await ui.timers.run(0);
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(ui.$('.selected-play').getAttribute('aria-pressed'), 'true');
  ui.cards()[1].querySelector('a').click();
  assert.equal(ui.$('.selected-play').textContent, 'Play');
  first.querySelector('a').click();
  gate = deferred();
  ui.$('.selected-play').click(); ui.$('.selected-play').click();
  assert.equal(actions.length, 1, 'duplicate taps must not send duplicate controls');
  assert.equal(ui.$('.selected-play').textContent, 'Pausing…');
  gate.resolve(); await settle(); gate = null;
  assert.equal(ui.$('.selected-play').textContent, 'Resume');
  assert.equal(ui.$('.playback-feedback').hidden, true);
  assert.equal(first.classList.contains('is-playing'), false);
  ui.$('.selected-play').click(); await settle();
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.deepEqual(actions.map(a => a.action), ['pause', 'resume']);
  assert.ok(actions.every(a => a.id === first.dataset.recordId && a.csrf));
  external = {is_playing: false, context_uri: first.dataset.discKey};
  ui.w.FauxVinylPlayback.refresh();
  await ui.timers.run(0);
  assert.equal(ui.$('.selected-play').textContent, 'Resume');
  external = {is_playing: true, context_uri: 'spotify:album:another'};
  ui.w.FauxVinylPlayback.refresh();
  await ui.timers.run(0);
  assert.equal(ui.$('.selected-play').textContent, 'Play');
});

test('failed pause keeps the current state and reports a recoverable error', async t => {
  let requests = 0;
  let external;
  const ui = setup(t, async (url, options) => {if (!options.method) return response(external); requests++; return response({error: 'Playback changed on your device.'}, 409);}, document => {document.querySelector('[data-record-browser]').dataset.preview = 'false';});
  const first = ui.cards()[0];
  const browser = ui.$('[data-record-browser]');
  external = {is_playing: true, context_uri: first.dataset.discKey};
  await ui.timers.run(0);
  ui.$('.selected-play').click(); await settle();
  assert.equal(requests, 1);
  assert.equal(first.classList.contains('is-playing'), true);
  assert.equal(ui.$('.selected-play').disabled, false);
  assert.match(ui.$('[data-playback-message]').textContent, /Playback changed/);
});

function fakeTimers(w) {
  const timers = new Map();
  let id = 0;
  w.setTimeout = (callback, delay) => {timers.set(++id, {callback, delay}); return id;};
  w.clearTimeout = timer => timers.delete(timer);
  return {
    has: delay => [...timers.values()].some(timer => timer.delay === delay),
    async run(delay) {
      const entry = [...timers].find(([, timer]) => timer.delay === delay);
      assert.ok(entry, 'Expected a scheduled timer at ' + delay + 'ms');
      timers.delete(entry[0]);
      await entry[1].callback();
      await settle();
    }
  };
}

for (const failure of ['503', 'lost response']) {
  test('failed Play restarts status polling without replaying: ' + failure, async t => {
    let timers, polls = 0, starts = 0, external;
    const ui = setup(t, async (url, options) => {
      if (url === '/playback') {
        polls++;
        return response(polls === 1 ? {is_playing: false} : {is_playing: true, context_uri: external});
      }
      if (!options.method) return response({csrf: 'csrf', action_token: 'one-time'});
      starts++;
      if (failure === 'lost response') throw new Error('Response lost');
      return response({error: 'Device unavailable.'}, 503);
    }, (document, w) => {timers = fakeTimers(w);});
    const [first, second] = ui.cards();
    external = second.dataset.discKey;
    first.querySelector('a').click();
    ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
    await timers.run(0);
    assert.equal(timers.has(20000), true);
    ui.$('.selected-play').click();
    await settle();
    assert.equal(starts, 1);
    assert.equal(timers.has(0), true, 'failed Play must restart status polling');
    await timers.run(0);
    assert.equal(second.classList.contains('is-playing'), true, 'external playback must still update');
    assert.equal(ui.$('.now-playing').hidden, false);
    assert.equal(timers.has(20000), true);
    assert.equal(starts, 1, 'status recovery must never replay the one-time action');
  });
}

test('track playback stays recognized after polling and Pause preserves the track', async t => {
  let timers;
  const writes = [];
  const track = 'spotify:track:one';
  const album = 'spotify:album:parent';
  const ui = setup(t, async (url, options) => {
    assert.equal(url, '/playback', 'transport must not start a new one-time action');
    if (!options.method) return response({is_playing: true, item_uri: track, album_uri: album});
    writes.push(options.body.get('action'));
    return response({is_playing: false, context_uri: track});
  }, (document, w) => {
    timers = fakeTimers(w);
    const first = document.querySelector('[data-record-id]');
    const withDisc = [...document.querySelectorAll('[data-record-id]')].find(card => JSON.parse(card.dataset.discOptions || 'null')?.length);
    first.dataset.discKey = track;
    first.dataset.discOptions = withDisc.dataset.discOptions;
  });
  ui.cards()[0].querySelector('a').click();
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  await timers.run(0);
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(ui.cards()[0].classList.contains('is-playing'), true);
  assert.equal(ui.$('.now-playing').hidden, false);
  assert.equal(ui.$('.record-disc').classList.contains('is-spinning'), true);
  ui.$('.selected-play').click(); await settle();
  assert.deepEqual(writes, ['pause']);
  assert.equal(ui.$('.selected-play').textContent, 'Resume');
});

test('shared playback matching prefers playlist context over track and album cards', t => {
  const ui = setup(t);
  const cards = ui.cards().slice(0, 3);
  const state = {album_uri: 'spotify:album:one', item_uri: 'spotify:track:one', context_uri: 'spotify:playlist:one'};
  cards[0].dataset.discKey = state.album_uri;
  cards[1].dataset.discKey = state.item_uri;
  cards[2].dataset.discKey = state.context_uri;
  const playback = ui.w.FauxVinylPlayback;
  assert.equal(playback.findCard(cards, state), cards[2]);
  assert.deepEqual(cards.map(card => playback.matches(card, state)), [false, false, true]);
  assert.equal(playback.findCard(cards, {...state, context_uri: ''}), cards[1]);
  assert.equal(playback.findCard(cards, {album_uri: state.album_uri}), cards[0]);
});

test('development reload polling pauses in hidden tabs and never overlaps requests', async t => {
  const dom = new JSDOM('', {url: 'http://127.0.0.1', runScripts: 'outside-only'});
  t.after(() => dom.window.close());
  const w = dom.window;
  const timers = fakeTimers(w);
  let hidden = false, calls = 0, pending = deferred();
  Object.defineProperty(w.document, 'hidden', {get: () => hidden});
  w.fetch = async () => {calls++; return pending.promise;};
  w.eval(liveScript);
  assert.equal(calls, 1);
  w.document.dispatchEvent(new w.Event('visibilitychange'));
  w.dispatchEvent(new w.Event('pageshow'));
  assert.equal(calls, 1, 'visibility/pageshow must not overlap an active request');
  hidden = true;
  w.document.dispatchEvent(new w.Event('visibilitychange'));
  pending.resolve({ok: true, text: async () => 'revision'}); await settle();
  assert.equal(timers.has(1500), false, 'hidden tabs should have no reload timer');
  hidden = false;
  pending = deferred();
  w.document.dispatchEvent(new w.Event('visibilitychange'));
  assert.equal(calls, 2, 'returning to the tab should check immediately');
  pending.resolve({ok: true, text: async () => 'revision'}); await settle();
  assert.equal(timers.has(1500), true);
  w.dispatchEvent(new w.Event('pagehide'));
  assert.equal(timers.has(1500), false);
  w.dispatchEvent(new w.Event('pageshow'));
  await settle();
  assert.equal(calls, 3, 'a restored page should resume checks');
});


test('playback status and transport work without loading disc artwork code', async t => {
  let card;
  const writes = [];
  const ui = setup(t, async (url, options) => {
    assert.equal(url, '/playback');
    if (!options.method) return response({is_playing: true, context_uri: card.dataset.discKey});
    writes.push(options.body.get('action'));
    return response({is_playing: false});
  });
  card = ui.cards()[0];
  await ui.timers.run(0);
  assert.equal(ui.$('.record-disc'), null);
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  ui.$('.selected-play').click(); await settle();
  assert.deepEqual(writes, ['pause']);
  assert.equal(ui.$('.selected-play').textContent, 'Resume');
});

test('a failed status read preserves playback and the next click pauses instead of restarting', async t => {
  let card, reads = 0;
  const writes = [];
  const ui = setup(t, async (url, options) => {
    assert.equal(url, '/playback', 'status failures must never restart the queue');
    if (!options.method) {
      if (++reads > 1) throw new Error('Status unavailable');
      return response({is_playing: true, context_uri: card.dataset.discKey});
    }
    writes.push(options.body.get('action'));
    return response({is_playing: false});
  });
  card = ui.cards()[0];
  await ui.timers.run(0);
  await ui.timers.run(20000);
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(ui.timers.has(60000), true);
  ui.$('.selected-play').click(); await settle();
  assert.deepEqual(writes, ['pause']);
});

test('a stale status response cannot overwrite a successful Play', async t => {
  const gate = deferred();
  const ui = setup(t, async (url, options) => {
    if (url === '/playback') return gate.promise;
    return response(options.method ? {status: 'playing'} : {csrf: 'csrf', action_token: 'once'});
  });
  const poll = ui.timers.run(0);
  ui.$('.selected-play').click(); await settle();
  gate.resolve(response({is_playing: false}));
  await poll;
  assert.equal(ui.$('.selected-play').textContent, 'Pause');
  assert.equal(ui.cards()[0].classList.contains('is-playing'), true);
});

test('glow reveals follow catalogue metadata with arbitrary album and edition IDs', t => {
  const ui = setup(t, undefined, document => {
    document.querySelector('[data-record-browser]').dataset.preview = 'true';
    const card = document.querySelector('[data-record-id]');
    card.dataset.discKey = 'spotify:album:7777777777777777777777';
    card.dataset.discOptions = JSON.stringify([
      {id: 'ordinary', kind: 'cd', label: 'Ordinary CD', image: '/normal.webp'},
      {id: 'secret', kind: 'cd', label: 'Secret CD', image: '/secret.webp'}
    ]);
    card.dataset.glow = JSON.stringify({variants: {ordinary: 'secret'}, words: ['one', 'two', 'three', 'four']});
  });
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  const button = ui.$('[data-disc-id="ordinary"]');
  assert.equal(ui.$('[data-disc-id="secret"]'), null);
  for (let i = 0; i < 5; i++) button.click();
  assert.equal(ui.$('.record-disc-image').getAttribute('src'), '/secret.webp');
  assert.equal(ui.w.document.documentElement.classList.contains('glow-mode'), true);
  assert.equal(button.textContent, 'Secret CD');
  assert.equal(ui.$('.glow-word').textContent, 'four');
});

test('an album without glow metadata exposes its editions as ordinary choices', t => {
  const ui = setup(t, undefined, document => {
    document.querySelector('[data-record-browser]').dataset.preview = 'true';
    const card = document.querySelector('[data-disc-key="' + glowAlbumKey + '"]');
    delete card.dataset.glow;
  });
  ui.w.eval(fs.readFileSync(path.join(serverRoot, 'static/discs.js'), 'utf8'));
  ui.cards().find(card => card.dataset.discKey === glowAlbumKey).querySelector('a').click();
  assert.equal(ui.$('.disc-choices').children.length, 4);
  for (let i = 0; i < 5; i++) ui.$('[data-disc-id="' + normalCDID + '"]').click();
  assert.equal(ui.w.document.documentElement.classList.contains('glow-mode'), false);
});

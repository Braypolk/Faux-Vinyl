'use strict';
(() => {
  const browser = document.querySelector('[data-record-browser]');
  if (!browser) return;
  let cards = [...browser.querySelectorAll('[data-record-id]')];
  const normalizeSearch = (value) => value.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase().replace(/['’‘]/g, '').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const searchText = new Map(cards.map((card) => [card, normalizeSearch(card.dataset.search || card.dataset.title)]));
  if (!cards.length) return;
  const find = (selector) => browser.querySelector(selector);
  const player = find('.record-player');
  const crate = find('.collection');
  const sleeve = find('.sleeve');
  const front = find('.sleeve-front');
  const back = find('.sleeve-back');
  const search = find('#record-search');
  const sort = find('#shelf-sort');
  sort.addEventListener('change', () => {
    sort.form.elements.q.value = search.value;
    sort.form.requestSubmit();
  });
  const previous = find('.record-previous');
  const next = find('.record-next');
  const dialog = document.querySelector('.sleeve-dialog');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const title = find('.selected-title');
  const titleText = find('.selected-title-text');
  const titleTrack = document.createElement('span');
  titleTrack.className = 'selected-title-track';
  titleText.before(titleTrack);
  titleTrack.append(titleText);
  const titleRepeat = document.createElement('span');
  titleRepeat.className = 'selected-title-repeat';
  titleRepeat.setAttribute('aria-hidden', 'true');
  titleRepeat.hidden = true;
  titleTrack.append(titleRepeat);
  let titleAnimation = null;
  let visible = [...cards];
  let current = null;
  let flipped = false;
  let suppressClickUntil = 0;
  const playButton = find('.selected-play');
  const feedback = find('.playback-feedback');
  const playback = window.FauxVinylPlayback;
  const arrangeButton = find('.arrange-records');
  const arrangeBar = find('.arrange-toolbar');
  const matchesPlayback = card => playback.matches(card);
  let failedID = null;
  let arranging = false;
  let savingOrder = false;
  let beforeArrange = null;
  let beforeSearch = '';
  let drag = null;
  let savedFeedbackTimer;

  function updatePlayButton() {
    playButton.disabled = playback.pending;
    playButton.setAttribute('aria-busy', String(playback.pending));
    playButton.setAttribute('aria-pressed', String(Boolean(matchesPlayback(current) && playback.state.is_playing)));
    playButton.textContent = playback.pending ? playback.pendingLabel : current?.dataset.recordId === failedID ? 'Try again' : matchesPlayback(current) ? playback.state.is_playing ? 'Pause' : 'Resume' : 'Play';
  }

  function updatePlayingCards() {
    const id = playback.state.is_playing ? playback.findCard()?.dataset.recordId : null;
    cards.forEach((card) => card.classList.toggle('is-playing', card.dataset.recordId === id));
  }

  browser.addEventListener('shelf:playback-state', () => {
    updatePlayingCards();
    updatePlayButton();
  });

  function playbackMessage(message, {error = false, settings = false, login = false} = {}) {
    feedback.hidden = !message;
    feedback.classList.toggle('is-error', error);
    feedback.querySelector('[data-playback-message]').textContent = message;
    feedback.querySelector('.playback-settings').hidden = !settings;
    feedback.querySelector('.playback-login').hidden = !login;
  }

  async function readResponse(response) {
    const type = response.headers.get('Content-Type') || '';
    if (!type.includes('application/json')) throw new Error('Unexpected response');
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(data.error || 'The request could not be completed.');
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function changePlayback(card = current, restart = false) {
    if (playback.pending || !card) return;
    failedID = null;
    playbackMessage('');
    try {
      const result = await (restart ? playback.start(card) : playback.toggle(card));
      playbackMessage(result?.warning || '');
    } catch (error) {
      failedID = card.dataset.recordId;
      playbackMessage(error.message, {error: true, settings: error.status === 503, login: error.status === 401});
    } finally {
      updatePlayButton();
    }
  }
  playButton.addEventListener('click', () => changePlayback());

  function arrangeControls() {
    const index = cards.indexOf(current);
    find('.arrange-left').disabled = savingOrder || index <= 0;
    find('.arrange-right').disabled = savingOrder || index < 0 || index >= cards.length - 1;
    find('.arrange-save').disabled = savingOrder;
    find('.arrange-cancel').disabled = savingOrder;
  }

  function renderOrder() {
    const focused = document.activeElement;
    crate.append(...cards);
    if (crate.contains(focused)) focused.focus({preventScroll: true});
    visible = [...cards];
    controls();
  }

  function moveRecord(card, index) {
    const from = cards.indexOf(card);
    if (from < 0 || from === index || index < 0 || index >= cards.length) return;
    cards.splice(from, 1);
    cards.splice(index, 0, card);
    renderOrder();
    find('.shelf-status').textContent = card.dataset.title + ', position ' + (index + 1) + ' of ' + cards.length + '.';
  }

  function shiftRecord(direction) {
    if (arranging && !savingOrder && current) moveRecord(current, cards.indexOf(current) + direction);
  }

  function endArrange(cancel = false) {
    if (drag) finishDrag({pointerId: drag.pointer});
    if (cancel) { cards = beforeArrange; renderOrder(); }
    arranging = false;
    beforeArrange = null;
    browser.classList.remove('is-arranging');
    arrangeBar.hidden = true;
    arrangeButton.hidden = false;
    sort.disabled = false;
    search.disabled = false;
    search.value = beforeSearch;
    filterRecords();
    arrangeButton.focus({preventScroll: true});
  }

  arrangeButton.hidden = sort.value !== 'custom';
  arrangeButton.addEventListener('click', () => {
    beforeArrange = [...cards];
    beforeSearch = search.value;
    search.value = '';
    filterRecords();
    arranging = true;
    browser.classList.add('is-arranging');
    arrangeButton.hidden = true;
    arrangeBar.hidden = false;
    find('.arrange-status').replaceChildren();
    find('.order-feedback').hidden = true;
    sort.disabled = true;
    search.disabled = true;
    arrangeControls();
    current?.querySelector('.album-artwork').focus({preventScroll: true});
  });
  find('.arrange-left').addEventListener('click', () => shiftRecord(-1));
  find('.arrange-right').addEventListener('click', () => shiftRecord(1));
  find('.arrange-cancel').addEventListener('click', () => { if (!savingOrder) endArrange(true); });
  find('.arrange-save').addEventListener('click', async () => {
    if (savingOrder) return;
    savingOrder = true;
    arrangeControls();
    const status = find('.arrange-status');
    status.textContent = 'Saving…';
    const body = new URLSearchParams({csrf: browser.dataset.csrf, order_version: browser.dataset.orderVersion});
    cards.forEach((card) => body.append('card_id', card.dataset.recordId));
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const result = await readResponse(await fetch('/shelf/order', {method: 'POST', headers: {Accept: 'application/json'}, body, signal: controller.signal}));
      browser.dataset.orderVersion = result.order_version;
      savingOrder = false;
      endArrange();
      const message = find('.order-feedback');
      message.textContent = 'Order saved';
      message.hidden = false;
      clearTimeout(savedFeedbackTimer);
      savedFeedbackTimer = setTimeout(() => { message.hidden = true; }, 4000);
    } catch (error) {
      status.textContent = error.status ? error.message : 'Could not confirm the save. Reload to check the saved order.';
      const reload = document.createElement('a');
      reload.href = '/?sort=custom';
      reload.textContent = 'Reload shelf';
      status.append(' ', reload);
    } finally {
      clearTimeout(timeout);
      savingOrder = false;
      arrangeControls();
    }
  });

  function stopTitleScroll() {
    titleAnimation?.cancel();
    titleAnimation = null;
    titleRepeat.hidden = true;
    title.classList.remove('is-scrolling');
  }

  function updateTitleScroll() {
    stopTitleScroll();
    title.scrollLeft = 0;
    const overflow = titleText.getBoundingClientRect().width - title.clientWidth;
    if (overflow <= 1) { title.removeAttribute('tabindex'); return; }
    title.tabIndex = 0;
    // The second copy meets the first at the loop boundary, keeping motion forward.
    // Touch/focus switches to one copy with native scrolling, as does reduced motion.
    if (reducedMotion.matches || title.matches(':hover, :focus')) return;
    titleRepeat.textContent = titleText.textContent;
    titleRepeat.hidden = false;
    const distance = titleRepeat.getBoundingClientRect().left - titleText.getBoundingClientRect().left;
    title.classList.add('is-scrolling');
    titleAnimation = titleTrack.animate([
      {transform: 'translateX(0)'},
      {transform: 'translateX(-' + distance + 'px)'},
    ], {duration: distance / 40 * 1000, iterations: Infinity, easing: 'linear'});
  }

  title.addEventListener('pointerenter', () => titleAnimation?.pause());
  title.addEventListener('pointerleave', () => {
    if (!title.matches(':focus')) {
      if (titleAnimation) titleAnimation.play();
      else updateTitleScroll();
    }
  });
  title.addEventListener('pointerdown', stopTitleScroll);
  title.addEventListener('focus', stopTitleScroll);
  title.addEventListener('blur', updateTitleScroll);
  new ResizeObserver(updateTitleScroll).observe(title);
  reducedMotion.addEventListener('change', updateTitleScroll);

  function blankFront() {
    return document.querySelector('#blank-sleeve').content.cloneNode(true);
  }

  function blankBack() {
    return document.querySelector('#blank-back').content.cloneNode(true);
  }

  // Keep loaded and in-flight nodes for this page, without preloading unseen backs.
  // Separate containers need separate nodes (the enlarged view can be open too).
  const faceImages = new WeakMap();
  function fillFace(face, url, alt, fallback, srcset = '') {
    if (!url) { face.replaceChildren(fallback()); return; }
    let cache = faceImages.get(face);
    if (!cache) { cache = new Map(); faceImages.set(face, cache); }
    const cached = cache.get(url);
    if (cached) {
      cached.image.alt = alt;
      if (cached.image.parentNode !== face) face.replaceChildren(...cached.nodes);
      return;
    }
    const image = new Image();
    image.alt = alt;
    image.decoding = 'async';
    image.sizes = face.classList.contains('dialog-artwork') ? '(max-width: 560px) 90vw, min(74vh, 800px)' : '(max-width: 560px) 72vw, (max-width: 800px) 40vw, 340px';
    if (srcset) image.srcset = srcset;
    const loading = document.createElement('span');
    loading.className = 'sleeve-loading';
    loading.textContent = 'Loading artwork…';
    const entry = {image, nodes: [image, loading]};
    cache.set(url, entry);
    image.addEventListener('load', async () => {
      try { await image.decode(); } catch { /* The error handler provides a fallback. */ }
      entry.nodes = [image];
      loading.remove();
      if (image.parentNode === face && dialog.open) updateDialog();
    }, {once: true});
    image.addEventListener('error', () => {
      cache.delete(url); // A later visit can retry a transient failure.
      if (image.parentNode !== face) return;
      face.replaceChildren(fallback());
      if (dialog.open) updateDialog();
    }, {once: true});
    face.replaceChildren(image, loading);
    image.src = url;
  }

  function updateDialog() {
    if (!current) return;
    dialog.querySelector('.dialog-title').textContent = current.dataset.title;
    const face = flipped ? back : front;
    const image = face.querySelector('img');
    fillFace(dialog.querySelector('.dialog-artwork'), image?.getAttribute('src'), image?.alt, flipped ? blankBack : blankFront, image?.srcset);
    dialog.querySelector('.dialog-turn').setAttribute('aria-label', flipped ? 'Show front cover' : 'Show back cover');
  }

  function flip() {
    if (!current) return;
    flipped = !flipped;
    if (!reducedMotion.matches) {
      sleeve.classList.remove('is-turning');
      void sleeve.offsetWidth;
      sleeve.classList.add('is-turning');
    }
    sleeve.classList.toggle('is-flipped', flipped);
    sleeve.setAttribute('aria-pressed', String(flipped));
    sleeve.setAttribute('aria-label', (flipped ? 'Show front cover of ' : 'Turn over ') + current.dataset.title);
    front.setAttribute('aria-hidden', String(flipped));
    back.setAttribute('aria-hidden', String(!flipped));
    find('.turn-sleeve').setAttribute('aria-label', flipped ? 'Show front cover' : 'Show back cover');
    find('.shelf-status').textContent = current.dataset.title + (flipped ? ', back of sleeve.' : ', front cover.');
    if (dialog.open) updateDialog();
  }

  function controls() {
    const index = visible.indexOf(current);
    previous.disabled = index <= 0;
    next.disabled = index < 0 || index >= visible.length - 1;
    arrangeControls();
  }

  function select(card, {focus = false} = {}) {
    if (!card) return;
    if (card === current) {
      if (focus) card.querySelector('.album-artwork').focus({preventScroll: true});
      return;
    }
    current = card;
    const record = card.dataset;
    sleeve.classList.remove('is-flipped', 'is-turning');
    flipped = false;
    sleeve.setAttribute('aria-pressed', 'false');
    sleeve.setAttribute('aria-label', 'Turn over ' + record.title);
    front.setAttribute('aria-hidden', 'false');
    back.setAttribute('aria-hidden', 'true');
    find('.turn-sleeve').setAttribute('aria-label', 'Show back cover');
    fillFace(front, record.front, record.title + ' front cover', blankFront, record.frontCandidates);
    fillFace(back, record.back, record.title + ' back artwork and tracklist', blankBack, record.backCandidates);
    titleText.textContent = record.title;
    updateTitleScroll();
    updatePlayButton();
    find('.selected-edit').href = record.edit;
    const copy = find('.selected-copy');
    copy.dataset.copy = record.nfc;
    copy.textContent = 'Copy NFC URL';
    cards.forEach((item) => {
      const chosen = item === card;
      item.classList.toggle('is-selected', chosen);
      const link = item.querySelector('.album-artwork');
      link.tabIndex = chosen ? 0 : -1;
      if (chosen) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
    controls();
    find('.shelf-status').textContent = record.title + ', ' + (visible.indexOf(card) + 1) + ' of ' + visible.length + '.';
    if (focus) card.querySelector('.album-artwork').focus({preventScroll: true});
    try { sessionStorage.setItem('fauxvinyl-selected', record.recordId); } catch { /* Browsing works without storage. */ }
    browser.dispatchEvent(new CustomEvent('shelf:selection', {detail: {id: record.recordId}}));
    if (dialog.open) updateDialog();
  }

  function move(direction, focus = false) {
    const index = Math.max(0, Math.min(visible.length - 1, visible.indexOf(current) + direction));
    select(visible[index], {focus});
  }

  browser.addEventListener('shelf:show-playing', event => {
    const card = cards.find(card => card.dataset.recordId === event.detail.id);
    if (!card) return;
    if (card.hidden) {
      search.value = '';
      filterRecords();
    }
    select(card, {focus: true});
  });

  cards.forEach((card) => {
    const link = card.querySelector('.album-artwork');
    link.setAttribute('aria-label', 'View ' + card.dataset.title);
    card.addEventListener('pointerenter', (event) => {
      if (!arranging && (event.pointerType === 'mouse' || event.pointerType === 'pen')) select(card);
    });
    const image = link.querySelector('img');
    if (image) {
      image.loading = 'eager';
      // Explicit decoding also paints every sleeve promptly in WebKit.
      image.decode().catch(() => {});
    }
    link.addEventListener('click', (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      if (Date.now() < suppressClickUntil) return;
      select(card);
    });
  });
  previous.addEventListener('click', () => move(-1));
  next.addEventListener('click', () => move(1));
  [crate, sleeve].forEach((element) => element.addEventListener('keydown', (event) => {
    if (arranging && !savingOrder && event.key === 'Escape') { event.preventDefault(); endArrange(true); return; }
    if (arranging && event.altKey && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
      event.preventDefault(); shiftRecord(event.key === 'ArrowRight' ? 1 : -1); return;
    }
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    if (event.key === 'Home') select(visible[0], {focus: element === crate});
    else if (event.key === 'End') select(visible[visible.length - 1], {focus: element === crate});
    else move(event.key === 'ArrowRight' ? 1 : -1, element === crate);
  }));
  sleeve.addEventListener('animationend', () => sleeve.classList.remove('is-turning'));
  sleeve.addEventListener('click', () => { if (Date.now() >= suppressClickUntil) flip(); });
  find('.turn-sleeve').addEventListener('click', flip);
  find('.enlarge-sleeve').addEventListener('click', () => { updateDialog(); dialog.showModal(); });
  dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
  dialog.querySelector('.dialog-turn').addEventListener('click', flip);
  dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });

  let swipeStart = null;
  sleeve.addEventListener('pointerdown', (event) => { swipeStart = {x: event.clientX, y: event.clientY}; });
  sleeve.addEventListener('pointerup', (event) => {
    if (!swipeStart) return;
    const dx = event.clientX - swipeStart.x;
    const dy = event.clientY - swipeStart.y;
    swipeStart = null;
    if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      suppressClickUntil = Date.now() + 350;
      move(dx < 0 ? 1 : -1);
    }
  });
  sleeve.addEventListener('pointercancel', () => { swipeStart = null; });

  // Touch the packed shelf or slide a finger across its spines to preview.
  function previewAtPointer(event) {
    const card = document.elementFromPoint(event.clientX, event.clientY)?.closest('[data-record-id]');
    if (card && crate.contains(card)) select(card);
  }
  crate.addEventListener('pointerdown', (event) => {
    if (arranging) {
      if (savingOrder || event.button !== 0) return;
      const card = event.target.closest('[data-record-id]');
      if (!card || !crate.contains(card)) return;
      event.preventDefault();
      select(card, {focus: true});
      drag = {card, x: event.clientX, y: event.clientY, pointer: event.pointerId, active: false, before: [...cards]};
      crate.setPointerCapture(event.pointerId);
    } else if (event.pointerType === 'touch') previewAtPointer(event);
  });
  crate.addEventListener('pointermove', (event) => {
    if (savingOrder) return;
    if (drag && drag.pointer === event.pointerId) {
      if (!drag.active && Math.hypot(event.clientX - drag.x, event.clientY - drag.y) < 5) return;
      drag.active = true;
      drag.card.classList.add('is-dragging');
      const index = cards.reduce((best, card, i) => {
        const rect = card.getBoundingClientRect();
        const distance = Math.abs(event.clientX - (rect.left + rect.width / 2));
        return distance < best.distance ? {index: i, distance} : best;
      }, {index: 0, distance: Infinity}).index;
      moveRecord(drag.card, index);
    } else if (!arranging && event.pointerType === 'touch' && event.buttons) previewAtPointer(event);
  });
  function finishDrag(event, cancel = false) {
    if (!drag || event.pointerId !== drag.pointer) return;
    const finished = drag;
    drag = null;
    finished.card.classList.remove('is-dragging');
    if (cancel) { cards = finished.before; renderOrder(); }
    if (crate.hasPointerCapture(event.pointerId)) crate.releasePointerCapture(event.pointerId);
    suppressClickUntil = Date.now() + 350;
  }
  crate.addEventListener('pointerup', (event) => finishDrag(event));
  crate.addEventListener('pointercancel', (event) => finishDrag(event, true));
  crate.addEventListener('lostpointercapture', (event) => finishDrag(event, true));
  crate.addEventListener('dragstart', (event) => event.preventDefault());

  function filterRecords() {
    const words = normalizeSearch(search.value).split(/\s+/).filter(Boolean);
    visible = cards.filter((card) => words.every((word) => searchText.get(card).includes(word)));
    cards.forEach((card) => { card.hidden = !visible.includes(card); });
    player.hidden = !visible.length;
    find('.no-records').hidden = Boolean(visible.length);
    crate.hidden = !visible.length;
    if (visible.length) {
      select(visible.includes(current) ? current : visible[0]);
      controls();
      find('.shelf-status').textContent = visible.length + (visible.length === 1 ? ' record found.' : ' records found.');
    }
    else {
      current = null;
      controls();
      find('.shelf-status').textContent = 'No records found.';
    }
  }
  search.addEventListener('input', filterRecords);
  browser.classList.add('is-enhanced');
  [player, find('.shelf-toolbar')].forEach((element) => { element.hidden = false; });
  let remembered;
  try { remembered = sessionStorage.getItem('fauxvinyl-selected'); } catch { /* Optional. */ }
  const autoplayCard = cards.find(card => card.dataset.recordId === browser.dataset.autoplayId);
  const linkedID = new URLSearchParams(location.hash.slice(1)).get('record');
  select(autoplayCard || cards.find(card => card.dataset.recordId === linkedID) || cards.find(card => card.dataset.recordId === remembered) || cards[0]);
  if (search.value) search.dispatchEvent(new Event('input'));
  if (autoplayCard) {
    if (autoplayCard.hidden) { search.value = ''; filterRecords(); }
    select(autoplayCard);
    // Reloading the shelf should not repeat a tap's playback request.
    try { history.replaceState(history.state, '', '/#record=' + encodeURIComponent(autoplayCard.dataset.recordId)); } catch { /* Playback still works without history access. */ }
    requestAnimationFrame(() => changePlayback(autoplayCard, true));
  }
})();

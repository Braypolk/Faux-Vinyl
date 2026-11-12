'use strict';
(() => {
  const browser = document.querySelector('[data-record-browser]');
  if (!browser) return;
  const cards = [...browser.querySelectorAll('[data-record-id]')];
  const catalogue = new Map();
  for (const card of cards) {
    try {
      const options = JSON.parse(card.dataset.discOptions || 'null');
      if (Array.isArray(options) && options.length) catalogue.set(card.dataset.discKey, options);
    } catch { /* A missing catalogue never interferes with the shelf. */ }
  }
  const stage = browser.querySelector('.sleeve-stage');
  const choices = browser.querySelector('.disc-choices');
  const frame = document.createElement('div');
  frame.className = 'record-disc';
  frame.hidden = true;
  frame.setAttribute('aria-hidden', 'true');
  const images = new Map();
  const albumChoices = new Map();
  const choiceArtwork = new WeakMap();
  const glowAlbum = 'spotify:album:0S0KGZnfBGSIssfF54WSJh';
  const normalCD = '30664206604';
  const glowCD = '30439409589';
  const glowVariants = new Map([[normalCD, glowCD], ['30672682790', 'billie-glow-vinyl']]);
  const hiddenVariants = new Set(glowVariants.values());
  let revealPresses = 0;
  let revealChoice = null;
  let glowActive = null;
  let wordBubble = null;
  let wordBubbleTimer;
  const glowWords = ['where', 'do', 'we', 'go'];
  const glowStatus = document.createElement('span');
  glowStatus.className = 'sr-only';
  glowStatus.setAttribute('role', 'status');
  browser.append(glowStatus);
  stage.prepend(frame);
  if (catalogue.size) stage.classList.add('has-disc-layout');
  const nowPlaying = document.createElement('button');
  nowPlaying.type = 'button';
  nowPlaying.className = 'now-playing';
  nowPlaying.hidden = true;
  const nowArt = document.createElement('span');
  nowArt.className = 'now-playing-art';
  nowArt.setAttribute('aria-hidden', 'true');
  const nowFallback = document.createElement('span');
  nowFallback.className = 'now-playing-fallback';
  const nowImages = new Map();
  const failedNowImages = new WeakSet();
  let nowCard = null;
  nowPlaying.append(nowArt);
  document.querySelector('header')?.append(nowPlaying);
  nowPlaying.addEventListener('click', () => {
    if (nowCard) browser.dispatchEvent(new CustomEvent('shelf:show-playing', {detail: {id: nowCard.dataset.recordId}}));
  });
  const storageKey = 'fauxvinyl-disc-preferences-v1';
  let preferences = {albums: {}, kind: 'vinyl'};
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
    if (saved && saved.albums && typeof saved.albums === 'object' && !Array.isArray(saved.albums)) {
      preferences = {albums: saved.albums, kind: saved.kind === 'cd' ? 'cd' : 'vinyl'};
    }
  } catch { /* Artwork selection also works when browser storage is disabled. */ }
  let selected = null;
  let lastAlbum = null;
  let previewID = null;
  let state = {is_playing: false};
  let testState = {is_playing: false};
  let revision = 0;
  let timer;
  let inFlight = false;

  function clearWordBubble() {
    clearTimeout(wordBubbleTimer);
    wordBubble?.remove();
    wordBubble = null;
  }
  function showGlowWord(button, word) {
    clearWordBubble();
    const rect = button.getBoundingClientRect();
    wordBubble = document.createElement('span');
    wordBubble.className = 'glow-word';
    wordBubble.textContent = word;
    wordBubble.setAttribute('aria-hidden', 'true');
    wordBubble.style.left = Math.max(48, Math.min(window.innerWidth - 48, rect.left + rect.width / 2)) + 'px';
    wordBubble.style.top = Math.max(56, rect.top - 8) + 'px';
    document.body.append(wordBubble);
    wordBubbleTimer = setTimeout(clearWordBubble, 1200);
  }

  function updateSpin() {
    const key = selected?.dataset.discKey;
    const playing = browser.dataset.testMode === 'true'
      ? testState.is_playing && selected?.dataset.recordId === testState.id
      : browser.dataset.preview === 'true'
      ? selected?.dataset.recordId === previewID
      : state.is_playing && (state.context_uri === key || state.album_uri === key);
    frame.classList.toggle('is-spinning', Boolean(playing && !document.hidden && !frame.hidden));
    let card = null;
    if (browser.dataset.testMode === 'true') {
      if (testState.is_playing) card = cards.find(card => card.dataset.recordId === testState.id);
    } else if (browser.dataset.preview === 'true') {
      card = cards.find(card => card.dataset.recordId === previewID);
    } else if (state.is_playing) {
      card = cards.find(card => card.dataset.discKey === state.context_uri) || cards.find(card => card.dataset.discKey === state.album_uri);
    }
    updateNowPlaying(card);
  }

  function optionsFor(card) {
    const key = card?.dataset.discKey;
    const options = catalogue.get(key) || [];
    // Hidden editions are revealed only by a five-press sequence, never a saved choice.
    return key === glowAlbum ? options.filter(o => !hiddenVariants.has(o.id)) : options;
  }
  function chosen(options, key) {
    if (glowActive && key === glowAlbum) {
      const secret = catalogue.get(key)?.find(o => o.id === glowActive);
      if (secret) return secret;
    }
    return options.find(o => o.id === preferences.albums[key]) || options.find(o => o.kind === preferences.kind) || options[0];
  }
  function updateNowPlaying(card) {
    nowCard = card;
    nowPlaying.hidden = !card;
    nowPlaying.classList.toggle('is-spinning', Boolean(card && !document.hidden));
    nowPlaying.classList.toggle('is-glowing', Boolean(card && glowActive && card.dataset.discKey === glowAlbum));
    nowPlaying.classList.toggle('is-glow-vinyl', Boolean(card && glowActive === 'billie-glow-vinyl' && card.dataset.discKey === glowAlbum));
    if (!card) return;
    const label = 'Return to ' + card.dataset.title + ', now playing';
    nowPlaying.setAttribute('aria-label', label);
    nowPlaying.title = label;
    const option = chosen(optionsFor(card), card.dataset.discKey);
    if (!option) {
      if (nowFallback.parentNode !== nowArt) nowArt.replaceChildren(nowFallback);
      return;
    }
    let image = nowImages.get(option.image);
    if (!image) {
      image = new Image();
      image.alt = '';
      image.width = image.height = 52;
      image.decoding = 'async';
      image.addEventListener('error', () => {
        failedNowImages.add(image);
        if (image.parentNode === nowArt) nowArt.replaceChildren(nowFallback);
      }, {once: true});
      nowImages.set(option.image, image);
      image.sizes = '52px';
      if (option.srcset) image.srcset = option.srcset;
      image.src = option.image;
    }
    const artwork = failedNowImages.has(image) ? nowFallback : image;
    if (artwork.parentNode !== nowArt) nowArt.replaceChildren(artwork);
  }
  function discImage(url, srcset) {
    if (images.has(url)) return images.get(url);
    const image = document.createElement('img');
    image.className = 'record-disc-image';
    image.width = image.height = 648;
    image.alt = '';
    image.decoding = 'async';
    const entry = {image, loaded: false};
    images.set(url, entry);
    image.addEventListener('load', () => {
      entry.loaded = true;
      if (image.parentNode !== frame) return;
      frame.classList.remove('is-loading');
      updateSpin();
    }, {once: true});
    image.addEventListener('error', () => {
      images.delete(url); // Retry on the next visit instead of caching an error.
      if (image.parentNode !== frame) return;
      frame.hidden = true;
      stage.classList.remove('has-disc');
      frame.classList.remove('is-loading', 'is-spinning');
    }, {once: true});
    image.sizes = '(max-width: 560px) 72vw, (max-width: 800px) 40vw, 340px';
    if (srcset) image.srcset = srcset;
    image.src = url;
    return entry;
  }
  function render() {
    const next = browser.querySelector('.is-selected');
    if (next !== selected) {
      resetSequence();
    }
    selected = next;
    const key = selected?.dataset.discKey;
    const options = optionsFor(selected);
    const option = chosen(options, key);
    const glowing = hiddenVariants.has(option?.id) && key === glowAlbum;
    if (document.documentElement.classList.contains('glow-mode') !== Boolean(glowActive)) {
      const secret = catalogue.get(glowAlbum)?.find(o => o.id === glowActive);
      glowStatus.textContent = glowActive ? secret.label + ' unlocked. Glow-in-the-dark mode.' : 'Glow mode off.';
    }
    document.documentElement.classList.toggle('glow-mode', Boolean(glowActive));
    frame.classList.toggle('is-glowing', glowing);
    frame.classList.toggle('is-glow-vinyl', glowing && option.kind === 'vinyl');
    const available = Boolean(option);
    stage.classList.toggle('has-disc', available);
    frame.hidden = !available;
    choices.hidden = options.length < 2;
    if (!available) {
      frame.replaceChildren();
      choices.replaceChildren();
      lastAlbum = null;
      updateSpin();
      return;
    }
    if (lastAlbum !== key) {
      lastAlbum = key;
      let buttons = albumChoices.get(key);
      if (!buttons) buttons = options.map(o => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'disc-choice';
        button.dataset.discId = o.id;
        button.setAttribute('aria-label', 'Show ' + o.label + ' artwork');
        const thumb = document.createElement('img');
        thumb.sizes = '30px';
        if (o.srcset) thumb.srcset = o.srcset;
        thumb.src = o.image;
        thumb.alt = '';
        thumb.width = thumb.height = 30;
        const label = document.createElement('span');
        label.textContent = o.label;
        button.append(thumb, label);
        choiceArtwork.set(button, {option: o, thumb, label, glowThumb: null});
        button.addEventListener('click', () => {
          const secretID = key === glowAlbum ? glowVariants.get(o.id) : null;
          if (secretID) {
            if (glowActive && glowActive !== secretID) glowActive = null;
            if (revealChoice !== o.id) resetSequence();
            revealChoice = o.id;
            revealPresses = Math.min(revealPresses + 1, 5);
            if (!glowActive && revealPresses >= 2) showGlowWord(button, glowWords[revealPresses - 2]);
            if (revealPresses === 5 && catalogue.get(key)?.some(option => option.id === secretID)) glowActive = secretID;
          } else {
            resetSequence();
            if (chosen(optionsFor(selected), key)?.id !== o.id) glowActive = null;
          }
          preferences.albums[key] = o.id;
          preferences.kind = o.kind;
          try { localStorage.setItem(storageKey, JSON.stringify(preferences)); } catch { /* Optional. */ }
          render();
        });
        return button;
      });
      albumChoices.set(key, buttons);
      choices.replaceChildren(...buttons);
    }
    for (const button of choices.querySelectorAll('button')) {
      const artwork = choiceArtwork.get(button);
      const revealed = glowing && glowVariants.get(button.dataset.discId) === option.id;
      button.setAttribute('aria-pressed', String(revealed || button.dataset.discId === option.id));
      button.classList.toggle('is-glowing', revealed);
      button.classList.toggle('is-glow-vinyl', revealed && option.kind === 'vinyl');
      artwork.label.textContent = revealed ? option.label : artwork.option.label;
      button.setAttribute('aria-label', 'Show ' + artwork.label.textContent + ' artwork');
      if (revealed && !artwork.glowThumb) {
        artwork.glowThumb = document.createElement('img');
        artwork.glowThumb.alt = '';
        artwork.glowThumb.width = artwork.glowThumb.height = 30;
        artwork.glowThumb.sizes = '30px';
        if (option.srcset) artwork.glowThumb.srcset = option.srcset;
        artwork.glowThumb.src = option.image;
      }
      const thumb = revealed ? artwork.glowThumb : artwork.thumb;
      if (button.firstChild !== thumb) button.replaceChildren(thumb, artwork.label);
    }
    const entry = discImage(option.image, option.srcset);
    if (entry.image.parentNode !== frame) frame.replaceChildren(entry.image);
    frame.classList.toggle('is-loading', !entry.loaded);
    updateSpin();
  }
  function resetSequence() {
    revealPresses = 0;
    revealChoice = null;
    clearWordBubble();
  }
  function endGlow() {
    if (!glowActive) return;
    glowActive = null;
    resetSequence();
    render();
  }
  browser.addEventListener('shelf:selection', render);
  document.addEventListener('click', event => {
    const button = event.composedPath().find(node => node.classList?.contains('disc-choice'));
    if (selected?.dataset.discKey !== glowAlbum || button?.dataset.discId !== revealChoice) resetSequence();
  });
  browser.addEventListener('shelf:test-playback', event => {
    revision++;
    const previousID = testState.id;
    testState = event.detail;
    if (testState.is_playing && testState.id !== previousID && cards.find(c => c.dataset.recordId === testState.id)?.dataset.discKey !== glowAlbum) endGlow();
    clearTimeout(timer);
    if (!event.detail.enabled) schedulePoll(0);
    updateSpin();
  });
  browser.addEventListener('shelf:playback-started', event => {
    revision++;
    const card = cards.find(c => c.dataset.recordId === event.detail.id);
    if (card?.dataset.discKey !== glowAlbum) endGlow();
    if (event.detail.preview) previewID = event.detail.id;
    else {
      state = {is_playing: true, context_uri: card?.dataset.discKey};
      // Allow Spotify a moment to apply the playback request before reading it.
      schedulePoll(4000);
    }
    updateSpin();
  });

  browser.addEventListener('shelf:playback-pending', () => { revision++; clearTimeout(timer); });
  browser.addEventListener('shelf:transport-changed', event => {
    revision++;
    state = event.detail;
    if (browser.dataset.preview === 'true') previewID = state.is_playing ? cards.find(card => card.dataset.discKey === state.context_uri)?.dataset.recordId : null;
    updateSpin();
    schedulePoll(4000);
  });
  browser.addEventListener('shelf:refresh-playback', () => schedulePoll(0));

  function schedulePoll(delay = 20000) {
    clearTimeout(timer);
    if (browser.dataset.testMode !== 'true' && browser.dataset.preview !== 'true' && !document.hidden) timer = setTimeout(poll, delay);
  }
  async function poll() {
    if (inFlight || document.hidden || browser.dataset.testMode === 'true') return;
    inFlight = true;
    const atStart = revision;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    let nextDelay = 20000;
    try {
      const response = await fetch('/playback', {headers: {Accept: 'application/json'}, signal: controller.signal});
      if (!response.ok) throw new Error('Playback state unavailable');
      const current = await response.json();
      if (atStart === revision) {
        const changed = current.context_uri !== state.context_uri || current.album_uri !== state.album_uri;
        state = current;
        browser.dispatchEvent(new CustomEvent('shelf:playback-state', {detail: state}));
        if (changed && current.is_playing && current.context_uri !== glowAlbum && current.album_uri !== glowAlbum) endGlow();
      }
    } catch {
      if (atStart === revision) {
        state = {is_playing: false};
        browser.dispatchEvent(new CustomEvent('shelf:playback-state', {detail: state}));
      }
      nextDelay = 60000;
    } finally {
      clearTimeout(timeout);
      inFlight = false;
      updateSpin();
      schedulePoll(nextDelay);
    }
  }
  document.addEventListener('visibilitychange', () => {
    updateSpin();
    clearTimeout(timer);
    if (!document.hidden) schedulePoll(0);
  });
  window.addEventListener('pagehide', () => clearTimeout(timer));
  render();
  schedulePoll(0);
})();

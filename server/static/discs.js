'use strict';
(() => {
  const browser = document.querySelector('[data-record-browser]');
  if (!browser) return;
  const cards = [...browser.querySelectorAll('[data-record-id]')];
  const playback = window.FauxVinylPlayback;
  const catalogue = new Map();
  const effects = new Map();
  for (const card of cards) {
    try {
      const options = JSON.parse(card.dataset.discOptions || 'null');
      if (Array.isArray(options) && options.length) catalogue.set(card.dataset.discKey, options);
      const effect = JSON.parse(card.dataset.glow || 'null');
      if (effect?.variants) effects.set(card.dataset.discKey, effect);
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
  let revealPresses = 0;
  let revealChoice = null;
  let glowActive = null; // {key, id}: one revealed edition owns the room theme.
  let wordBubble = null;
  let wordBubbleTimer;
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
    const playing = playback.state.is_playing && playback.matches(selected);
    frame.classList.toggle('is-spinning', Boolean(playing && !document.hidden && !frame.hidden));
    updateNowPlaying(playback.state.is_playing ? playback.findCard() : null);
  }

  function optionsFor(card) {
    const key = card?.dataset.discKey;
    const options = catalogue.get(key) || [];
    // Hidden editions are revealed only by a five-press sequence, never a saved choice.
    const hidden = new Set(Object.values(effects.get(key)?.variants || {}));
    return options.filter(o => !hidden.has(o.id));
  }
  function chosen(options, key) {
    if (glowActive?.key === key) {
      const secret = catalogue.get(key)?.find(o => o.id === glowActive.id);
      if (secret) return secret;
    }
    return options.find(o => o.id === preferences.albums[key]) || options.find(o => o.kind === preferences.kind) || options[0];
  }
  function updateNowPlaying(card) {
    nowCard = card;
    nowPlaying.hidden = !card;
    nowPlaying.classList.toggle('is-spinning', Boolean(card && !document.hidden));
    nowPlaying.classList.toggle('is-glowing', Boolean(card && glowActive?.key === card.dataset.discKey));
    nowPlaying.classList.toggle('is-glow-vinyl', Boolean(card && glowActive?.key === card.dataset.discKey && chosen(optionsFor(card), card.dataset.discKey)?.kind === 'vinyl'));
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
    const glowing = Boolean(glowActive && glowActive.key === key && option?.id === glowActive.id);
    if (document.documentElement.classList.contains('glow-mode') !== Boolean(glowActive)) {
      const secret = catalogue.get(glowActive?.key)?.find(o => o.id === glowActive.id);
      glowStatus.textContent = glowActive ? secret.label + ' unlocked. Glow-in-the-dark mode.' : 'Glow mode off.';
    }
    document.documentElement.classList.toggle('glow-mode', Boolean(glowActive));
    frame.classList.toggle('is-glowing', glowing);
    frame.classList.toggle('is-glow-vinyl', glowing && option.kind === 'vinyl');
    const available = Boolean(option);
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
          const secretID = effects.get(key)?.variants[o.id];
          if (secretID) {
            if (glowActive && (glowActive.key !== key || glowActive.id !== secretID)) glowActive = null;
            if (revealChoice !== o.id) resetSequence();
            revealChoice = o.id;
            revealPresses = Math.min(revealPresses + 1, 5);
            const word = effects.get(key)?.words?.[revealPresses - 2];
            if (!glowActive && word) showGlowWord(button, word);
            if (revealPresses === 5 && catalogue.get(key)?.some(option => option.id === secretID)) glowActive = {key, id: secretID};
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
      const revealed = glowing && effects.get(key)?.variants[button.dataset.discId] === option.id;
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
    if (!effects.has(selected?.dataset.discKey) || button?.dataset.discId !== revealChoice) resetSequence();
  });
  browser.addEventListener('shelf:playback-state', () => {
    if (playback.state.is_playing && glowActive && playback.findCard()?.dataset.discKey !== glowActive.key) endGlow();
    updateSpin();
  });
  document.addEventListener('visibilitychange', updateSpin);
  render();
})();

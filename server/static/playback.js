'use strict';
(() => {
  const browser = document.querySelector('[data-record-browser]');
  if (!browser) return;
  const cards = [...browser.querySelectorAll('[data-record-id]')];
  const preview = browser.dataset.preview === 'true';
  let state = {is_playing: false};
  let pending = false;
  let pendingLabel = '';
  let revision = 0;
  let timer;
  let inFlight = false;
  let stopped = false;

  function findCard(choices = cards, current = state) {
    if (current.card_id) return choices.find(card => card.dataset.recordId === current.card_id);
    for (const uri of [current.context_uri, current.item_uri, current.album_uri]) {
      if (uri) {
        const card = choices.find(card => card.dataset.discKey === uri);
        if (card) return card;
      }
    }
  }
  function matches(card, current = state) {
    return Boolean(card && findCard(cards, current) === card);
  }
  function publish() {
    browser.dispatchEvent(new CustomEvent('shelf:playback-state', {detail: state}));
  }
  function schedulePoll(delay = 20000) {
    clearTimeout(timer);
    if (!preview && !pending && !stopped && !document.hidden) timer = setTimeout(poll, delay);
  }
  async function readResponse(response) {
    if (!(response.headers.get('Content-Type') || '').includes('application/json')) throw new Error('Unexpected response');
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(data.error || 'The request could not be completed.');
      error.status = response.status;
      throw error;
    }
    return data;
  }
  async function poll() {
    if (inFlight || pending || stopped || document.hidden || preview) return;
    inFlight = true;
    const atStart = revision;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    let nextDelay = 20000;
    try {
      const current = await readResponse(await fetch('/playback', {headers: {Accept: 'application/json'}, signal: controller.signal}));
      if (atStart === revision) {
        state = current;
        publish();
      }
    } catch {
      // A failed status read is not evidence that music stopped. Keep the last
      // confirmed state so the next click can still pause rather than restart.
      nextDelay = 60000;
    } finally {
      clearTimeout(timeout);
      inFlight = false;
      schedulePoll(nextDelay);
    }
  }
  async function change(card, restart) {
    if (pending || !card) return;
    const record = {...card.dataset};
    const transport = !restart && matches(card);
    const playing = !transport || !state.is_playing;
    if (preview) {
      state = {card_id: record.recordId, context_uri: record.discKey, is_playing: playing};
      publish();
      return {};
    }
    revision++;
    pending = true;
    pendingLabel = transport ? playing ? 'Resuming…' : 'Pausing…' : 'Starting…';
    clearTimeout(timer);
    publish();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), transport ? 45000 : 110000);
    let sent = false;
    let succeeded = false;
    try {
      let result;
      if (transport) {
        sent = true;
        result = await readResponse(await fetch('/playback', {
          method: 'POST', headers: {Accept: 'application/json'}, signal: controller.signal,
          body: new URLSearchParams({csrf: browser.dataset.csrf, card_id: record.recordId, action: playing ? 'resume' : 'pause'})
        }));
      } else {
        // One explicit Play or NFC tap gets one fresh action. Status recovery
        // never retries this write when its response is lost.
        const action = await readResponse(await fetch(record.play, {headers: {Accept: 'application/json'}, signal: controller.signal}));
        browser.dataset.csrf = action.csrf;
        sent = true;
        result = await readResponse(await fetch(record.play + '/play', {
          method: 'POST', headers: {Accept: 'application/json'}, signal: controller.signal,
          body: new URLSearchParams({csrf: action.csrf, action_token: action.action_token})
        }));
      }
      state = {is_playing: playing, context_uri: record.discKey, card_id: record.recordId};
      succeeded = true;
      return result;
    } catch (error) {
      if (!error.status) error.message = sent ? 'Could not confirm playback. Check your device before trying again.' : 'Could not reach your shelf. Try again.';
      throw error;
    } finally {
      clearTimeout(timeout);
      pending = false;
      publish();
      schedulePoll(succeeded ? 4000 : 0);
    }
  }
  window.FauxVinylPlayback = {
    get state() { return state; },
    get pending() { return pending; },
    get pendingLabel() { return pendingLabel; },
    matches,
    findCard,
    start: card => change(card, true),
    toggle: card => change(card, false),
    refresh: () => schedulePoll(0)
  };
  document.addEventListener('visibilitychange', () => {
    clearTimeout(timer);
    if (!document.hidden) schedulePoll(0);
  });
  window.addEventListener('pagehide', () => { stopped = true; clearTimeout(timer); });
  window.addEventListener('pageshow', () => { stopped = false; schedulePoll(0); });
  schedulePoll(0);
})();

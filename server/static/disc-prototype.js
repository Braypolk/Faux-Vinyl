/* Throwaway local experiment: two real CD cutouts beside the existing sleeve.
   Loaded only in dev mode. No artwork/database changes or real pause requests. */
'use strict';
(() => {
  const browser = document.querySelector('[data-record-browser]');
  if (!browser) return;
  const samples = [
    {key: 'maad-city', title: 'maad city', label: 'maad city', file: 'maad-city.png'},
    {key: 'billie', title: 'WHEN WE ALL FALL ASLEEP, WHERE DO WE GO?', label: 'Billie Eilish', file: 'when-we-all-fall-asleep.png'},
  ];
  const cards = [...browser.querySelectorAll('[data-record-id]')];
  samples.forEach(sample => {sample.card = cards.find(card => card.dataset.title === sample.title);});
  const stage = browser.querySelector('.sleeve-stage');
  const frame = document.createElement('div');
  frame.className = 'disc-preview';
  frame.hidden = true;
  frame.setAttribute('aria-hidden', 'true');
  const image = document.createElement('img');
  image.alt = '';
  image.width = image.height = 594;
  image.className = 'disc-preview-image';
  frame.append(image);
  stage.prepend(frame);

  const bar = document.createElement('div');
  bar.className = 'disc-prototype-bar';
  bar.setAttribute('aria-label', 'Local disc artwork experiment');
  const caption = document.createElement('span');
  caption.textContent = 'Disc preview';
  bar.append(caption);
  const buttons = samples.map(sample => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = sample.label;
    button.disabled = !sample.card;
    button.addEventListener('click', () => {
      const search = browser.querySelector('#record-search');
      if (search.value) {search.value = ''; search.dispatchEvent(new Event('input'));}
      sample.card.querySelector('.album-artwork').click();
      const url = new URL(location.href);
      url.searchParams.set('disc', sample.key);
      history.replaceState(null, '', url);
      render();
    });
    bar.append(button);
    return button;
  });
  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'disc-preview-toggle';
  bar.append(toggle);
  browser.after(bar);
  let selected = null;
  let spinningID = null;
  let lastImage = '';

  function render() {
    const card = browser.querySelector('.is-selected');
    selected = samples.find(sample => sample.card === card) || null;
    stage.classList.toggle('has-disc-preview', Boolean(selected));
    frame.hidden = !selected;
    if (selected && lastImage !== selected.file) {
      lastImage = selected.file;
      image.src = '/static/disc-prototype/' + selected.file;
    }
    const spinning = Boolean(selected && spinningID === selected.card.dataset.recordId);
    frame.classList.toggle('is-spinning', spinning);
    toggle.disabled = !selected;
    toggle.textContent = spinning ? 'Pause spin' : 'Preview spin';
    toggle.setAttribute('aria-pressed', String(spinning));
    buttons.forEach((button, index) => button.setAttribute('aria-pressed', String(selected === samples[index])));
  }
  toggle.addEventListener('click', () => {
    if (!selected) return;
    const id = selected.card.dataset.recordId;
    spinningID = spinningID === id ? null : id;
    render();
  });
  browser.addEventListener('shelf:playback-started', event => {
    // This experiment only follows simulated local Play. Pause spin is visual only.
    if (event.detail.preview) {spinningID = event.detail.id; render();}
  });
  const observer = new MutationObserver(render);
  cards.forEach(card => observer.observe(card, {attributes: true, attributeFilter: ['class']}));
  image.addEventListener('error', () => {frame.hidden = true; stage.classList.remove('has-disc-preview');});
  const requested = new URLSearchParams(location.search).get('disc');
  const initial = samples.find(sample => sample.key === requested);
  if (initial?.card) buttons[samples.indexOf(initial)].click();
  render();
})();

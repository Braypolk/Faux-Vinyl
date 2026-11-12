'use strict';
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const previous = button.textContent;
    try {
      await navigator.clipboard.writeText(button.dataset.copy);
      button.textContent = 'Copied ✓';
      setTimeout(() => { button.textContent = previous; }, 2000);
    } catch {
      button.textContent = 'Select the URL to copy';
      const field = document.querySelector('#nfc-url');
      if (field) { field.focus(); field.select(); }
    }
  });
}
const play = document.querySelector('#autoplay');
if (play && !document.querySelector('[data-record-browser]')) {
  let submitted = false;
  play.addEventListener('submit', (event) => {
    if (submitted) { event.preventDefault(); return; }
    submitted = true;
    play.querySelector('button').disabled = true;
  });
  requestAnimationFrame(() => play.requestSubmit());
}

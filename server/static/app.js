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

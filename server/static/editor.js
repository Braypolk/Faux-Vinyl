'use strict';
document.querySelectorAll('[data-cover-upload]').forEach((input) => {
  const preview = document.querySelector('[data-cover-preview="' + input.id + '"]');
  const original = preview.cloneNode(true);
  const reset = document.querySelector('[name="reset_' + input.id + '"]');
  let revision = 0;
  reset?.addEventListener('change', () => {
    revision++;
    input.disabled = reset.checked;
    input.value = '';
    input.setCustomValidity('');
    if (reset.checked) {
      const label = document.createElement('span');
      label.textContent = 'Original artwork after saving';
      preview.replaceChildren(label);
    } else {
      preview.replaceChildren(...[...original.childNodes].map((node) => node.cloneNode(true)));
    }
  });
  input.addEventListener('change', () => {
    const currentRevision = ++revision;
    const file = input.files[0];
    input.setCustomValidity('');
    preview.replaceChildren(...[...original.childNodes].map((node) => node.cloneNode(true)));
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) {
      input.setCustomValidity('Choose an image smaller than 8 MB.');
      input.reportValidity();
      return;
    }
    if (reset) reset.checked = false;
    const reader = new FileReader();
    reader.addEventListener('load', () => {
      if (currentRevision !== revision) return;
      const image = new Image();
      image.alt = input.id === 'front' ? 'New front artwork' : 'New back artwork';
      image.src = reader.result;
      preview.replaceChildren(image);
    });
    reader.readAsDataURL(file);
  });
});

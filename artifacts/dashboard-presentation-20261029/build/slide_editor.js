(function () {
  'use strict';

  const articles = Array.from(document.querySelectorAll('article[data-index]'));
  const editableSelector = [
    'h2', 'h3', 'p', 'li', 'td', 'th', 'figcaption', '.slideno', '.message',
    '.stamp', '.slidefoot', '.mark b', '.flowhead', '.flowrow', '.flow-caption',
    '.flow-bottom', '.label', '.running-comparison-heading',
    '.running-comparison-caption'
  ].join(',');
  const editable = [];

  articles.forEach((article, slideIndex) => {
    const canvas = article.querySelector('.canvas');
    if (!canvas) return;
    Array.from(canvas.querySelectorAll(editableSelector)).forEach((element, textIndex) => {
      const id = `slide-${slideIndex + 1}-text-${textIndex + 1}`;
      element.dataset.slideEditable = id;
      editable.push(element);
    });
  });

  const storageKey = 'paysim-slide-content-v1:' + location.pathname;
  const controls = document.createElement('span');
  controls.className = 'slide-editor-controls';
  controls.dataset.editorUi = 'true';

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'slide-edit-toggle';
  toggle.setAttribute('aria-pressed', 'false');
  toggle.textContent = 'Sửa nội dung slide';

  const download = document.createElement('button');
  download.type = 'button';
  download.textContent = 'Tải HTML đã sửa';

  const state = document.createElement('span');
  state.className = 'slide-edit-state';
  state.setAttribute('role', 'status');
  controls.append(toggle, download, state);

  const toolbar = document.querySelector('.toolbar');
  const modeButton = document.getElementById('mode');
  if (toolbar && modeButton) modeButton.after(controls);

  function setState(message, warning) {
    state.textContent = message;
    state.classList.toggle('warning', Boolean(warning));
  }

  function values() {
    const result = {};
    editable.forEach(element => {
      result[element.dataset.slideEditable] = element.innerHTML;
    });
    return result;
  }

  function save() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ version: 1, values: values() }));
      setState('Đã tự lưu trong trình duyệt. Tải HTML để lưu thành tệp.', false);
    } catch (error) {
      setState('Không tự lưu được. Hãy tải HTML đã sửa trước khi đóng trang.', true);
    }
  }

  function restore() {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return false;
      const data = JSON.parse(raw);
      if (data.version !== 1 || !data.values || typeof data.values !== 'object') return false;
      editable.forEach(element => {
        const saved = data.values[element.dataset.slideEditable];
        if (typeof saved === 'string') element.innerHTML = saved;
      });
      return true;
    } catch (error) {
      return false;
    }
  }

  function setEditing(enabled) {
    document.body.classList.toggle('editing-slides', enabled);
    editable.forEach(element => {
      if (enabled) element.setAttribute('contenteditable', 'true');
      else element.removeAttribute('contenteditable');
    });
    toggle.setAttribute('aria-pressed', String(enabled));
    toggle.textContent = enabled ? 'Hoàn tất chỉnh sửa' : 'Sửa nội dung slide';
    if (enabled) {
      if (document.body.classList.contains('deck')) modeButton.click();
      setState('Bấm vào chữ để sửa. Ảnh và bố cục giữ nguyên.', false);
    } else {
      save();
    }
  }

  function downloadPresentation() {
    const clone = document.documentElement.cloneNode(true);
    clone.querySelectorAll('[data-editor-ui]').forEach(node => node.remove());
    clone.querySelectorAll('[contenteditable]').forEach(node => node.removeAttribute('contenteditable'));
    clone.querySelectorAll('[data-slide-editable]').forEach(node => node.removeAttribute('data-slide-editable'));
    clone.querySelectorAll('.stage').forEach(node => node.removeAttribute('style'));
    clone.querySelector('body').classList.remove('deck', 'editing-slides');
    const mode = clone.querySelector('#mode');
    if (mode) mode.textContent = 'Trình chiếu';
    const modal = clone.querySelector('.modal');
    if (modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
      const content = modal.querySelector('.modal-content');
      if (content) content.replaceChildren();
    }
    const blob = new Blob(['<!doctype html>\n', clone.outerHTML], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'PaySim_slide_da_chinh_sua.html';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setState('Đã tải bản HTML gồm nội dung đã sửa.', false);
  }

  const restored = restore();
  toggle.addEventListener('click', () => {
    setEditing(toggle.getAttribute('aria-pressed') !== 'true');
  });
  download.addEventListener('click', downloadPresentation);
  editable.forEach(element => {
    element.addEventListener('input', save);
    element.addEventListener('paste', event => {
      if (!element.isContentEditable) return;
      event.preventDefault();
      const text = event.clipboardData?.getData('text/plain') || '';
      document.execCommand('insertText', false, text);
    });
  });

  if (restored) setState('Đã khôi phục nội dung slide đã sửa trong trình duyệt.', false);
  else setState('Bật chế độ rồi bấm vào chữ trên slide.', false);
})();

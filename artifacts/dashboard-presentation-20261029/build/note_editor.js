(function () {
  'use strict';

  const noteSections = Array.from(document.querySelectorAll('article .notes'));
  const paragraphGroups = noteSections.map(section => Array.from(section.querySelectorAll('.spoken')));
  const initialGroups = paragraphGroups.map(group => group.map(p => p.innerHTML));
  const storageKey = 'paysim-presenter-notes-v1:' + location.pathname;
  let storageAvailable = true;

  function setState(message, warning) {
    document.querySelectorAll('.note-editor-controls .save-state').forEach(label => {
      label.textContent = message;
      label.classList.toggle('warning', Boolean(warning));
    });
  }

  function saveNotes() {
    const groups = paragraphGroups.map(group => group.map(p => p.innerHTML));
    try {
      localStorage.setItem(storageKey, JSON.stringify({ version: 1, groups }));
      storageAvailable = true;
      setState('Đã tự lưu trong trình duyệt này. Tải bản HTML để lưu thành tệp.', false);
    } catch (error) {
      storageAvailable = false;
      setState('Không tự lưu được. Hãy tải bản HTML đã sửa trước khi đóng trang.', true);
    }
  }

  function restoreNotes() {
    try {
      const saved = localStorage.getItem(storageKey);
      if (!saved) return false;
      const data = JSON.parse(saved);
      if (data.version !== 1 || !Array.isArray(data.groups) || data.groups.length !== paragraphGroups.length ||
          !data.groups.every((group, i) => Array.isArray(group) && group.length <= paragraphGroups[i].length &&
            group.every(value => typeof value === 'string'))) {
        throw new Error('The saved notes do not match the slides');
      }
      data.groups.forEach((group, i) => group.forEach((value, j) => {
        paragraphGroups[i][j].innerHTML = value;
      }));
      return true;
    } catch (error) {
      storageAvailable = false;
      return false;
    }
  }

  function downloadPresentation() {
    // Export a clean copy of the currently visible content, including restored edits.
    const clone = document.documentElement.cloneNode(true);
    clone.querySelectorAll('[data-editor-ui]').forEach(node => node.remove());
    clone.querySelectorAll('[contenteditable]').forEach(node => node.removeAttribute('contenteditable'));
    clone.querySelectorAll('.stage').forEach(node => node.removeAttribute('style'));
    clone.querySelector('body').classList.remove('deck');
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
  }

  const restored = restoreNotes();
  noteSections.forEach((section, index) => {
    const controls = document.createElement('div');
    controls.className = 'note-editor-controls';
    controls.dataset.editorUi = 'true';
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'edit-toggle';
    toggle.setAttribute('aria-pressed', 'false');
    toggle.textContent = 'Sửa lời thoại';
    const download = document.createElement('button');
    download.type = 'button';
    download.textContent = 'Tải bản HTML đã sửa';
    download.addEventListener('click', downloadPresentation);
    const state = document.createElement('span');
    state.className = 'save-state';
    state.setAttribute('role', 'status');
    controls.append(toggle, download, state);
    section.querySelector('h3').after(controls);

    toggle.addEventListener('click', () => {
      const editing = toggle.getAttribute('aria-pressed') !== 'true';
      toggle.setAttribute('aria-pressed', String(editing));
      toggle.textContent = editing ? 'Xong' : 'Sửa lời thoại';
      paragraphGroups[index].forEach(p => {
        if (editing) p.setAttribute('contenteditable', 'true');
        else p.removeAttribute('contenteditable');
      });
      if (editing) {
        paragraphGroups[index][0]?.focus();
        if (storageAvailable) setState('Bấm vào lời thoại để sửa. Nội dung tự lưu trong trình duyệt này.', false);
      } else {
        saveNotes();
      }
    });

    paragraphGroups[index].forEach(p => {
      p.addEventListener('input', saveNotes);
      p.addEventListener('paste', event => {
        if (!p.isContentEditable) return;
        event.preventDefault();
        const text = event.clipboardData?.getData('text/plain') || '';
        document.execCommand('insertText', false, text);
      });
    });
  });

  if (!storageAvailable) {
    setState('Không tự lưu được. Hãy tải bản HTML đã sửa trước khi đóng trang.', true);
  } else if (restored) {
    setState('Đã khôi phục bản sửa lưu trong trình duyệt này.', false);
  } else {
    setState('Sau khi sửa, nội dung tự lưu trong trình duyệt này.', false);
  }
})();

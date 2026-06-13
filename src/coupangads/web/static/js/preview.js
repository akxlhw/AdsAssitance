export function initPreview() {
  const modal = document.getElementById('preview-modal');
  const body = document.getElementById('preview-body');
  const closeBtn = document.getElementById('preview-close');
  if (!modal || !body) return;

  function open(html) {
    body.innerHTML = html;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    modal.classList.add('hidden');
    body.innerHTML = '';
    document.body.style.overflow = '';
  }

  closeBtn?.addEventListener('click', close);
  modal.querySelector('.preview-backdrop')?.addEventListener('click', close);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
  });

  window.previewText = async function(url, filename) {
    try {
      const res = await fetch(url);
      const text = await res.text();
      const ext = filename.split('.').pop().toLowerCase();
      const isMarkdown = ext === 'md' || ext === 'markdown';
      const contentHtml = isMarkdown && window.marked
        ? window.marked.parse(text)
        : `<pre class="preview-plain">${escapeHtml(text)}</pre>`;
      open(`
        <div class="preview-text">
          <h2>${escapeHtml(filename)}</h2>
          <div class="preview-text-body">${contentHtml}</div>
        </div>
      `);
    } catch (err) {
      alert('加载失败：' + err.message);
    }
  };

  window.previewImage = function(url, filename) {
    open(`
      <div class="preview-image">
        <img src="${url}" alt="${escapeHtml(filename)}">
        <p>${escapeHtml(filename)}</p>
      </div>
    `);
  };

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

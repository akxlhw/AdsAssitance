export function initUpload(onStart) {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');
  const grid = document.getElementById('thumbnail-grid');
  const startBtn = document.getElementById('start-btn');
  let files = [];
  let objectUrls = [];

  zone.addEventListener('click', () => input.click());
  input.addEventListener('change', (e) => handleFiles(e.target.files));

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('dragover');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
  });

  startBtn.addEventListener('click', async () => {
    if (files.length === 0) return alert('请先上传图片');
    startBtn.disabled = true;
    startBtn.textContent = '上传中...';

    try {
      const productName = document.getElementById('product-name').value.trim() || `prod-${Date.now()}`;
      const formData = new FormData();
      formData.append('product_name', productName);
      files.forEach(f => formData.append('files', f));

      const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
      if (!uploadRes.ok) throw new Error('上传失败');

      const genRes = await fetch(`/api/generate/${productName}`, { method: 'POST' });
      if (!genRes.ok) throw new Error('生成任务启动失败');

      if (onStart) onStart(productName);
    } catch (err) {
      alert(err.message);
      startBtn.disabled = false;
      startBtn.textContent = '开始生成';
    }
  });

  function handleFiles(fileList) {
    files = [...files, ...Array.from(fileList)];
    renderThumbnails();
  }

  function removeFile(idx) {
    files = files.filter((_, i) => i !== idx);
    renderThumbnails();
  }

  function renderThumbnails() {
    objectUrls.forEach(url => URL.revokeObjectURL(url));
    objectUrls = [];
    grid.innerHTML = files.map((file, idx) => {
      const url = URL.createObjectURL(file);
      objectUrls.push(url);
      return `
      <div class="thumb-wrapper">
        <img src="${url}" class="thumbnail" alt="${file.name}">
        <button type="button" data-idx="${idx}" class="remove-btn">×</button>
      </div>
    `;
    }).join('');

    grid.querySelectorAll('.remove-btn').forEach(btn => {
      btn.addEventListener('click', () => removeFile(parseInt(btn.dataset.idx, 10)));
    });
  }
}

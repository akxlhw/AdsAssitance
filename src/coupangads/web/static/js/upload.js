export function initUpload(onStart) {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');
  const grid = document.getElementById('thumbnail-grid');
  const startBtn = document.getElementById('start-btn');
  let files = [];

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

    const productName = `prod-${Date.now()}`;
    const formData = new FormData();
    formData.append('product_name', productName);
    files.forEach(f => formData.append('files', f));

    const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
    if (!uploadRes.ok) {
      alert('上传失败');
      startBtn.disabled = false;
      startBtn.textContent = '开始生成';
      return;
    }

    const genRes = await fetch(`/api/generate/${productName}`, { method: 'POST' });
    if (!genRes.ok) {
      alert('生成任务启动失败');
      startBtn.disabled = false;
      startBtn.textContent = '开始生成';
      return;
    }

    if (onStart) onStart(productName);
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
    grid.innerHTML = files.map((file, idx) => `
      <div class="thumb-wrapper">
        <img src="${URL.createObjectURL(file)}" class="thumbnail" alt="${file.name}">
        <button type="button" data-idx="${idx}" class="remove-btn">×</button>
      </div>
    `).join('');

    grid.querySelectorAll('.remove-btn').forEach(btn => {
      btn.addEventListener('click', () => removeFile(parseInt(btn.dataset.idx, 10)));
    });
  }
}

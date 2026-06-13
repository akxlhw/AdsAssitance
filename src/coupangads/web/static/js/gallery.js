export async function loadResult(productId) {
  showState('result-state');
  const res = await fetch(`/api/result/${productId}`);
  if (!res.ok) {
    alert('获取结果失败');
    return;
  }
  const data = await res.json();

  renderTextCards(data.text_files, productId);
  renderImageGallery(data.images, productId);
  setupDownload(productId);
}

function renderTextCards(files, productId) {
  const container = document.getElementById('text-cards');
  container.innerHTML = files.map(name => `
    <div class="card">
      <h3>${name}</h3>
      <a href="/api/result/${productId}/${name}" target="_blank">查看</a>
    </div>
  `).join('');
}

function renderImageGallery(images, productId) {
  const container = document.getElementById('image-gallery');
  container.innerHTML = images.map(name => `
    <div class="result-image-card">
      <img src="/api/result/${productId}/${name}" alt="${name}" loading="lazy">
      <span>${name}</span>
    </div>
  `).join('');
}

function setupDownload(productId) {
  const btn = document.getElementById('download-btn');
  btn.href = `/api/download/${productId}`;
  btn.download = `${productId}.zip`;
}

function showState(id) {
  document.querySelectorAll('.state').forEach(el => el.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
}

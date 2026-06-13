const STEPS = [
  { key: 'product_report', label: '商品画像' },
  { key: 'title', label: '标题' },
  { key: 'keywords', label: '关键词' },
  { key: 'selling_points', label: '卖点' },
  { key: 'instagram', label: 'INS 文案' },
  { key: 'images', label: '图片生成' },
];

export function startProgress(productId) {
  showState('progress-state');
  renderSteps();
  const evtSource = new EventSource(`/api/progress/${productId}`);

  evtSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateProgress(data);
    updateSteps(data);
    if (data.status === 'completed' || data.status === 'error') {
      evtSource.close();
      if (data.status === 'completed') {
        import('./gallery.js').then(m => m.loadResult(productId));
      } else {
        alert('生成失败：' + (data.message || '未知错误'));
      }
    }
  };

  evtSource.onerror = () => evtSource.close();
}

function updateProgress(data) {
  const bar = document.getElementById('progress-bar');
  const percent = document.getElementById('progress-percent');
  if (bar) bar.style.width = `${data.progress || 0}%`;
  if (percent) percent.textContent = `${data.progress || 0}%`;
}

function renderSteps() {
  const container = document.getElementById('steps');
  container.innerHTML = STEPS.map(s => `
    <span class="step" data-step="${s.key}">${s.label}</span>
  `).join('');
}

function updateSteps(data) {
  if (!data.step) return;
  document.querySelectorAll('.step').forEach(el => {
    if (el.dataset.step === data.step) {
      el.classList.remove('done');
      el.classList.add('active');
    }
    if (data.status === 'completed') {
      el.classList.add('done');
      el.classList.remove('active');
    }
  });
}

function showState(id) {
  document.querySelectorAll('.state').forEach(el => el.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
}

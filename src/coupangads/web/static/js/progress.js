const STEPS = [
  { key: 'product_report', label: '商品画像', message: '正在分析商品画像...' },
  { key: 'title', label: '标题', message: '正在生成商品标题...' },
  { key: 'keywords', label: '关键词', message: '正在挖掘关键词...' },
  { key: 'selling_points', label: '卖点', message: '正在提炼卖点文案...' },
  { key: 'instagram', label: 'INS 文案', message: '正在撰写 INS 文案...' },
  { key: 'images', label: '图片生成', message: '正在生成详情页图片...' },
];

const ANIMATION_DURATION = 600;

export function startProgress(productId, selectedSteps) {
  showState('progress-state');
  const steps = selectedSteps && selectedSteps.length
    ? STEPS.filter(s => selectedSteps.includes(s.key))
    : STEPS;
  renderSteps(steps);

  const evtSource = new EventSource(`/api/progress/${productId}`);

  evtSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('[progress] SSE message:', data);
    updateProgress(data);
    updateSteps(data, steps);
    updateMessage(data, steps);

    if (data.status === 'error') {
      console.log('[progress] SSE error, closing');
      evtSource.close();
      showError(data.message || '未知错误');
      return;
    }

    if (data.status === 'completed' && data.progress === 100) {
      console.log('[progress] SSE final completed, closing');
      evtSource.close();
      setTimeout(() => {
        import('./gallery.js').then(m => {
          m.loadResult(productId, selectedSteps, data);
        }).catch(err => {
          console.error('[progress] failed to load gallery:', err);
        });
      }, 300);
    }
  };

  evtSource.onerror = () => evtSource.close();
}

function updateProgress(data) {
  const bar = document.getElementById('progress-bar');
  const percentEl = document.getElementById('progress-percent');
  if (!bar || !percentEl) return;

  const target = data.progress || 0;
  const current = parseInt(percentEl.textContent, 10) || 0;

  bar.style.width = `${target}%`;
  animateNumber(percentEl, current, target, ANIMATION_DURATION);
}

function animateNumber(element, from, to, duration) {
  const start = performance.now();
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(from + (to - from) * eased);
    element.textContent = `${value}%`;
    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }
  requestAnimationFrame(step);
}

function updateMessage(data, steps) {
  const messageEl = document.getElementById('progress-message');
  if (!messageEl) return;

  const activeStep = steps.find(s => s.key === data.step);
  const nextMessage = data.status === 'completed'
    ? '生成完成'
    : (activeStep?.message || '准备中...');

  if (messageEl.textContent === nextMessage) return;

  messageEl.classList.add('is-fading');
  setTimeout(() => {
    messageEl.textContent = nextMessage;
    messageEl.classList.remove('is-fading');
  }, 300);
}

function renderSteps(steps) {
  const container = document.getElementById('steps');
  container.innerHTML = steps.map(s => `
    <span class="progress-step" data-step="${s.key}">${s.label}</span>
  `).join('');
}

function updateSteps(data, steps) {
  const activeKeys = new Set(steps.map(s => s.key));
  const stepIndex = steps.findIndex(s => s.key === data.step);

  document.querySelectorAll('.progress-step').forEach(el => {
    const key = el.dataset.step;
    const index = steps.findIndex(s => s.key === key);
    el.classList.remove('is-done', 'is-active');

    if (data.status === 'completed' && activeKeys.has(key)) {
      el.classList.add('is-done');
    } else if (index < stepIndex) {
      el.classList.add('is-done');
    } else if (key === data.step && activeKeys.has(key)) {
      el.classList.add('is-active');
    }
  });
}

function showError(message) {
  const messageEl = document.getElementById('progress-message');
  const bar = document.getElementById('progress-bar');
  if (messageEl) messageEl.textContent = `生成失败：${message}`;
  if (bar) bar.style.background = 'var(--error, #ff3b30)';
}

function showState(id) {
  document.querySelectorAll('.state').forEach(el => {
    el.classList.add('hidden');
    el.classList.remove('state-transition');
  });
  const target = document.getElementById(id);
  target.classList.remove('hidden');
  // Trigger reflow for transition
  void target.offsetWidth;
  target.classList.add('state-transition');
}

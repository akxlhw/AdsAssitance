import { initPreview } from './preview.js';

const STEPS = [
  { key: 'product_report', label: '商品画像', message: '正在分析商品画像...' },
  { key: 'title', label: '标题', message: '正在生成商品标题...' },
  { key: 'keywords', label: '关键词', message: '正在挖掘关键词...' },
  { key: 'selling_points', label: '卖点', message: '正在提炼卖点文案...' },
  { key: 'instagram', label: 'INS 文案', message: '正在撰写 INS 文案...' },
  { key: 'images', label: '图片生成', message: '正在生成详情页图片...' },
];

const ANIMATION_DURATION = 600;

let _cachedSteps = [];
let _currentNumberAnimation = null;

function getStepForFile(name) {
  if (name === 'productreport.md') return 'product_report';
  if (name === 'product_title.md') return 'title';
  if (name === 'wing_keywords.md') return 'keywords';
  if (name.startsWith('selling_points')) return 'selling_points';
  if (name === 'instagram.md') return 'instagram';
  if (name.endsWith('.png')) return 'images';
  return null;
}

function getRepresentativeFile(files, step) {
  if (step === 'images') {
    return files.find(f => f.type === 'image') || files[0];
  }
  return files.find(f => f.name.endsWith('.md')) || files[0];
}

async function syncPreviewBar(productId) {
  const safeProductId = encodeURIComponent(productId);
  const res = await fetch(`/api/result/${safeProductId}`, { cache: 'no-store' });
  if (!res.ok) return;
  const data = await res.json();
  const textFiles = data.text_files || [];
  const images = data.images || [];
  const allFiles = [
    ...textFiles.map(name => ({ name, type: 'text' })),
    ...images.map(name => ({ name, type: 'image' })),
  ];

  const filesByStep = {};
  for (const file of allFiles) {
    const step = getStepForFile(file.name);
    if (!step) continue;
    if (!filesByStep[step]) filesByStep[step] = [];
    filesByStep[step].push(file);
  }

  const completedSteps = Object.keys(filesByStep);
  const newSteps = completedSteps.filter(s => !_cachedSteps.includes(s));

  if (newSteps.length > 0) {
    _cachedSteps = completedSteps;
    renderPreviewCards(productId, newSteps, filesByStep);
  }
}

export function startProgress(productId, selectedSteps) {
  _cachedSteps = [];
  initPreview();

  const previewBar = document.getElementById('progress-preview-bar');
  if (previewBar) previewBar.innerHTML = '';

  showState('progress-state');
  const steps = selectedSteps && selectedSteps.length
    ? STEPS.filter(s => selectedSteps.includes(s.key))
    : STEPS;
  renderSteps(steps);

  const safeProductId = encodeURIComponent(productId);
  const evtSource = new EventSource(`/api/progress/${safeProductId}`);

  evtSource.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.error('[progress] failed to parse SSE data:', err);
      evtSource.close();
      showError('进度数据异常');
      return;
    }

    console.log('[progress] SSE message:', data);
    updateProgress(data);
    updateSteps(data, steps);
    updateMessage(data, steps);

    syncPreviewBar(productId).catch(err => {
      console.error('[progress] preview sync failed:', err);
    });

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
      }, 500);
    }
  };

  evtSource.onerror = (err) => {
    console.error('[progress] SSE error:', err);
    showError('连接异常，请刷新页面重试');
    evtSource.close();
  };
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
  if (_currentNumberAnimation !== null) {
    cancelAnimationFrame(_currentNumberAnimation);
    _currentNumberAnimation = null;
  }

  const start = performance.now();
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(from + (to - from) * eased);
    element.textContent = `${value}%`;
    if (progress < 1) {
      _currentNumberAnimation = requestAnimationFrame(step);
    } else {
      _currentNumberAnimation = null;
    }
  }
  _currentNumberAnimation = requestAnimationFrame(step);
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

function renderPreviewCards(productId, newSteps, filesByStep) {
  const container = document.getElementById('progress-preview-bar');
  if (!container) return;

  const safeProductId = encodeURIComponent(productId);
  const fragment = document.createDocumentFragment();

  for (const step of newSteps) {
    const files = filesByStep[step];
    const file = getRepresentativeFile(files, step);
    const stepLabel = STEPS.find(s => s.key === step)?.label || step;

    const card = document.createElement('div');
    card.className = step === 'images'
      ? 'progress-preview-card progress-preview-card--image'
      : 'progress-preview-card';
    card.dataset.step = step;
    card.dataset.name = file.name;
    card.dataset.type = file.type;

    if (step === 'images') {
      card.innerHTML = `
        <img class="progress-preview-card__image"
             src="/api/result/${safeProductId}/${encodeURIComponent(file.name)}"
             alt="${escapeHtml(file.name)}"
             loading="lazy">
      `;
    } else {
      card.innerHTML = `
        <div class="progress-preview-card__name">${escapeHtml(stepLabel)}</div>
      `;
      loadTextPreview(productId, file.name, card);
    }

    card.addEventListener('click', () => {
      const url = `/api/result/${safeProductId}/${encodeURIComponent(file.name)}`;
      if (file.type === 'image') {
        window.previewImage(url, file.name);
      } else {
        window.previewText(url, file.name);
      }
    });

    fragment.appendChild(card);
  }

  container.appendChild(fragment);
  // Scroll to the newest card
  container.scrollLeft = container.scrollWidth;
}

async function loadTextPreview(productId, name, card) {
  try {
    const res = await fetch(`/api/result/${encodeURIComponent(productId)}/${encodeURIComponent(name)}`, {
      cache: 'no-store',
    });
    if (!res.ok) return;
    const text = await res.text();
    let previewEl = card.querySelector('.progress-preview-card__preview');
    if (!previewEl) {
      previewEl = document.createElement('div');
      previewEl.className = 'progress-preview-card__preview';
      card.appendChild(previewEl);
    }
    const clean = text.replace(/[#*_`\-]/g, ' ').replace(/\s+/g, ' ').trim();
    previewEl.textContent = clean.slice(0, 80) || '（空文件）';
  } catch (err) {
    console.error('[progress] failed to load text preview:', err);
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

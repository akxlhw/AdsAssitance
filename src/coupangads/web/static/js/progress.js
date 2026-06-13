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
let _currentProductId = null;
let _currentSteps = [];
let _abortRequested = false;
let _isCompleted = false;
let _evtSource = null;
let _lastProgress = 0;

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

function updateUrlProductId(productId) {
  const url = new URL(window.location.href);
  url.searchParams.set('product_id', productId);
  window.history.replaceState({}, '', url);
}

function clearUrlProductId() {
  const url = new URL(window.location.href);
  url.searchParams.delete('product_id');
  window.history.replaceState({}, '', url);
}

function getAbortLink() {
  return document.getElementById('abort-link');
}

function getAbortError() {
  return document.getElementById('abort-error');
}

function getAbortedState() {
  return document.getElementById('aborted-state');
}

function getProgressBar() {
  return document.getElementById('progress-bar');
}

function getProgressMessage() {
  return document.getElementById('progress-message');
}

function getProgressMessageText() {
  return document.getElementById('progress-message-text');
}

function getProgressPercent() {
  return document.getElementById('progress-percent');
}

function getProgressShimmer() {
  return document.getElementById('progress-bar-shimmer');
}

function resetAbortUI() {
  const link = getAbortLink();
  const error = getAbortError();
  const abortedState = getAbortedState();
  if (link) {
    link.disabled = false;
    link.textContent = '中止';
    link.classList.remove('hidden', 'is-loading');
  }
  if (error) {
    error.textContent = '';
    error.classList.add('hidden');
  }
  if (abortedState) abortedState.classList.add('hidden');
}

function showAbortError(message) {
  const error = getAbortError();
  if (!error) return;
  error.textContent = message;
  error.classList.remove('hidden');
}

function setAbortLoading(loading) {
  const link = getAbortLink();
  if (!link) return;
  link.disabled = loading;
  link.textContent = loading ? '正在中止...' : '中止';
  link.classList.toggle('is-loading', loading);
}

function setViewResultsHref(productId) {
  const btn = document.getElementById('view-results-btn');
  if (btn) {
    btn.href = `/result/${encodeURIComponent(productId)}`;
  }
}

async function requestAbort(productId) {
  if (_abortRequested) return;
  _abortRequested = true;
  setAbortLoading(true);

  try {
    const res = await fetch(`/api/abort/${encodeURIComponent(productId)}`, {
      method: 'POST',
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (err) {
    console.error('[progress] abort request failed:', err);
    _abortRequested = false;
    setAbortLoading(false);
    showAbortError('中止请求失败，请重试');
  }
}

function stopProgressAnimation() {
  const shimmer = getProgressShimmer();
  if (shimmer) {
    shimmer.style.animation = 'none';
    shimmer.style.opacity = '0';
  }
}

function showAbortedState(productId, data) {
  stopProgressAnimation();

  const messageTextEl = getProgressMessageText();
  if (messageTextEl) messageTextEl.textContent = '生成已中止';

  const progress = data?.progress ?? _lastProgress;
  updateProgress({ progress });

  const link = getAbortLink();
  if (link) link.classList.add('hidden');

  setViewResultsHref(productId);
  const abortedState = getAbortedState();
  if (abortedState) abortedState.classList.remove('hidden');
}

function handleAborted(productId, data) {
  // 如果已经正常完成，忽略迟到的 aborted 事件
  if (_isCompleted) return;

  if (_evtSource) {
    _evtSource.close();
    _evtSource = null;
  }

  showAbortedState(productId, data);
}

export function renderAbortedState(productId, data = {}) {
  initPreview();

  const previewBar = document.getElementById('progress-preview-bar');
  if (previewBar) {
    previewBar.innerHTML = '';
    enableDragScroll(previewBar);
  }

  showState('progress-state');
  const steps = STEPS;
  renderSteps(steps);

  _currentProductId = productId;
  _currentSteps = steps;
  _isCompleted = false;
  _abortRequested = true;

  resetAbortUI();
  showAbortedState(productId, data);
  syncPreviewBar(productId).catch(err => {
    console.error('[progress] preview sync failed:', err);
  });
}

export function startProgress(productId, selectedSteps) {
  _cachedSteps = [];
  _currentProductId = productId;
  _currentSteps = selectedSteps;
  _abortRequested = false;
  _isCompleted = false;
  initPreview();

  const previewBar = document.getElementById('progress-preview-bar');
  if (previewBar) {
    previewBar.innerHTML = '';
    enableDragScroll(previewBar);
  }

  showState('progress-state');
  updateUrlProductId(productId);
  resetAbortUI();

  const steps = selectedSteps && selectedSteps.length
    ? STEPS.filter(s => selectedSteps.includes(s.key))
    : STEPS;
  renderSteps(steps);

  const safeProductId = encodeURIComponent(productId);
  const evtSource = new EventSource(`/api/progress/${safeProductId}`);
  _evtSource = evtSource;

  const abortLink = getAbortLink();
  if (abortLink) {
    abortLink.onclick = () => requestAbort(productId);
  }

  evtSource.addEventListener('aborted', (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.error('[progress] failed to parse aborted event:', err);
      return;
    }
    console.log('[progress] SSE aborted event:', data);
    handleAborted(productId, data);
  });

  evtSource.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.error('[progress] failed to parse SSE data:', err);
      evtSource.close();
      _evtSource = null;
      showError('进度数据异常');
      return;
    }

    console.log('[progress] SSE message:', data);

    // 后端未发送命名事件时的降级处理
    if (data.status === 'aborted') {
      handleAborted(productId, data);
      return;
    }

    updateProgress(data);
    updateSteps(data, steps);
    updateMessage(data, steps);

    syncPreviewBar(productId).catch(err => {
      console.error('[progress] preview sync failed:', err);
    });

    if (data.status === 'error') {
      console.log('[progress] SSE error, closing');
      evtSource.close();
      _evtSource = null;
      showError(data.message || '未知错误');
      return;
    }

    if (data.status === 'completed' && data.progress === 100) {
      console.log('[progress] SSE final completed, closing');
      _isCompleted = true;
      evtSource.close();
      _evtSource = null;
      clearUrlProductId();
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
    _evtSource = null;

    const link = getAbortLink();
    if (link && link.disabled && link.textContent === '正在中止...') {
      setAbortLoading(false);
      _abortRequested = false;
    }
  };
}

function updateProgress(data) {
  const bar = getProgressBar();
  const percentEl = getProgressPercent();
  if (!bar || !percentEl) return;

  const target = data.progress || 0;
  _lastProgress = target;
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
  const messageEl = getProgressMessage();
  const messageTextEl = getProgressMessageText();
  if (!messageEl || !messageTextEl) return;

  const activeStep = steps.find(s => s.key === data.step);
  let nextMessage = '准备中...';
  if (data.status === 'completed') {
    nextMessage = '生成完成';
  } else if (activeStep) {
    nextMessage = activeStep.message;
  }

  if (messageTextEl.textContent === nextMessage) return;

  messageEl.classList.add('is-fading');
  setTimeout(() => {
    messageTextEl.textContent = nextMessage;
    messageEl.classList.remove('is-fading');
  }, 300);
}

function renderSteps(steps) {
  const container = document.getElementById('steps');
  if (!container) return;
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
  const messageTextEl = getProgressMessageText();
  const bar = getProgressBar();
  if (messageTextEl) messageTextEl.textContent = `生成失败：${message}`;
  if (bar) bar.style.background = 'var(--error, #ff3b30)';
}

function showState(id) {
  document.querySelectorAll('.state').forEach(el => {
    el.classList.add('hidden');
    el.classList.remove('state-transition');
  });
  const target = document.getElementById(id);
  if (!target) return;
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

function enableDragScroll(container) {
  let isDown = false;
  let startX = 0;
  let scrollLeft = 0;

  container.addEventListener('mousedown', (e) => {
    isDown = true;
    container.classList.add('is-dragging');
    startX = e.pageX - container.offsetLeft;
    scrollLeft = container.scrollLeft;
  });

  container.addEventListener('mouseleave', () => {
    isDown = false;
    container.classList.remove('is-dragging');
  });

  container.addEventListener('mouseup', () => {
    isDown = false;
    container.classList.remove('is-dragging');
  });

  container.addEventListener('mousemove', (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - container.offsetLeft;
    const walk = (x - startX) * 1.5;
    container.scrollLeft = scrollLeft - walk;
  });

  // Touch support
  container.addEventListener('touchstart', (e) => {
    isDown = true;
    startX = e.touches[0].pageX - container.offsetLeft;
    scrollLeft = container.scrollLeft;
  }, { passive: true });

  container.addEventListener('touchend', () => {
    isDown = false;
  });

  container.addEventListener('touchmove', (e) => {
    if (!isDown) return;
    const x = e.touches[0].pageX - container.offsetLeft;
    const walk = (x - startX) * 1.5;
    container.scrollLeft = scrollLeft - walk;
  }, { passive: true });
}

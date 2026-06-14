/**
 * 进度视图：渲染进 canvas 容器，SSE 推送进度。
 *
 * 导出：
 *   renderProgressWorkspace(container, productId, steps, { onCompleted, onAbortedView }) -> cleanup
 *   renderAbortedState(productId, data) - 保留兼容（不再切换视图，仅用于极少数异常路径）
 */

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

const PROGRESS_HTML = `
  <div class="progress-container">
    <div class="progress-percentage" data-el="percent">0%</div>
    <div class="progress-message" data-el="message">
      <span data-el="message-text">准备中...</span>
      <button class="abort-link" type="button" data-el="abort">中止</button>
      <span class="abort-error hidden" data-el="abort-error"></span>
    </div>
    <div class="progress-bar-track progress-bar-track--minimal">
      <div class="progress-bar-fill" data-el="bar"></div>
      <div class="progress-bar-shimmer" data-el="shimmer"></div>
    </div>
    <div class="aborted-state hidden" data-el="aborted">
      <p class="aborted-state__message">生成已中止</p>
      <a class="primary-button" href="#" data-el="view-results">查看已生成结果</a>
    </div>
    <div class="progress-preview-bar" data-el="preview"></div>
    <div class="progress-steps" data-el="steps"></div>
  </div>
`;

// 模块级状态（与原 progress.js 一致，用于跨函数共享）
let _cachedSteps = [];
let _currentNumberAnimation = null;
let _currentProductId = null;
let _currentSteps = [];
let _abortRequested = false;
let _isCompleted = false;
let _evtSource = null;
let _lastProgress = 0;
// 当前容器引用（renderProgressWorkspace 设置）
let _container = null;

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
  if (!_container) return;
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

function resetAbortUI() {
  const link = _container?.querySelector('[data-el="abort"]');
  const error = _container?.querySelector('[data-el="abort-error"]');
  const abortedState = _container?.querySelector('[data-el="aborted"]');
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
  const error = _container?.querySelector('[data-el="abort-error"]');
  if (!error) return;
  error.textContent = message;
  error.classList.remove('hidden');
}

function setAbortLoading(loading) {
  const link = _container?.querySelector('[data-el="abort"]');
  if (!link) return;
  link.disabled = loading;
  link.textContent = loading ? '正在中止...' : '中止';
  link.classList.toggle('is-loading', loading);
}

function setViewResultsHref(productId) {
  const btn = _container?.querySelector('[data-el="view-results"]');
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
  const shimmer = _container?.querySelector('[data-el="shimmer"]');
  if (shimmer) {
    shimmer.style.animation = 'none';
    shimmer.style.opacity = '0';
  }
}

function showAbortedState(productId, data) {
  if (!_container) return;
  stopProgressAnimation();

  const messageTextEl = _container.querySelector('[data-el="message-text"]');
  if (messageTextEl) messageTextEl.textContent = '生成已中止';

  const progress = data?.progress ?? _lastProgress;
  updateProgress({ progress });

  const link = _container.querySelector('[data-el="abort"]');
  if (link) link.classList.add('hidden');

  setViewResultsHref(productId);
  const abortedState = _container.querySelector('[data-el="aborted"]');
  if (abortedState) abortedState.classList.remove('hidden');
}

function handleAborted(productId, data, callbacks) {
  if (_isCompleted) return;
  if (_evtSource) {
    _evtSource.close();
    _evtSource = null;
  }
  showAbortedState(productId, data);
  if (callbacks?.onAbortedView) {
    setTimeout(() => callbacks.onAbortedView(productId), 800);
  }
}

/**
 * @param {HTMLElement} container
 * @param {string} productId
 * @param {string[]|null} selectedSteps
 * @param {object} callbacks { onCompleted(pid, data), onAbortedView(pid) }
 * @returns {() => void} cleanup
 */
export async function renderProgressWorkspace(container, productId, selectedSteps, callbacks = {}) {
  _container = container;
  _cachedSteps = [];
  _currentProductId = productId;
  _currentSteps = selectedSteps || [];
  _abortRequested = false;
  _isCompleted = false;
  initPreview();

  container.innerHTML = PROGRESS_HTML;

  const previewBar = container.querySelector('[data-el="preview"]');
  if (previewBar) {
    previewBar.innerHTML = '';
    enableDragScroll(previewBar);
  }

  resetAbortUI();

  const steps = selectedSteps && selectedSteps.length
    ? STEPS.filter(s => selectedSteps.includes(s.key))
    : STEPS;

  renderSteps(steps);

  const safeProductId = encodeURIComponent(productId);
  const evtSource = new EventSource(`/api/progress/${safeProductId}`);
  _evtSource = evtSource;

  const abortLink = container.querySelector('[data-el="abort"]');
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
    handleAborted(productId, data, callbacks);
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

    if (data.status === 'aborted') {
      handleAborted(productId, data, callbacks);
      return;
    }

    updateProgress(data);
    updateSteps(data, steps);
    updateMessage(data, steps);

    syncPreviewBar(productId).catch(err => {
      console.error('[progress] preview sync failed:', err);
    });

    if (data.status === 'error') {
      evtSource.close();
      _evtSource = null;
      showError(data.message || '未知错误');
      return;
    }

    if (data.status === 'completed' && data.progress === 100) {
      _isCompleted = true;
      evtSource.close();
      _evtSource = null;
      setTimeout(() => {
        if (callbacks.onCompleted) callbacks.onCompleted(productId, data);
      }, 500);
    }
  };

  evtSource.onerror = (err) => {
    console.error('[progress] SSE error:', err);
    showError('连接异常，请刷新页面重试');
    evtSource.close();
    _evtSource = null;

    const link = container.querySelector('[data-el="abort"]');
    if (link && link.disabled && link.textContent === '正在中止...') {
      setAbortLoading(false);
      _abortRequested = false;
    }
  };

  return () => {
    if (_evtSource) {
      _evtSource.close();
      _evtSource = null;
    }
    _container = null;
  };
}

function updateProgress(data) {
  if (!_container) return;
  const bar = _container.querySelector('[data-el="bar"]');
  const percentEl = _container.querySelector('[data-el="percent"]');
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
  if (!_container) return;
  const messageEl = _container.querySelector('[data-el="message"]');
  const messageTextEl = _container.querySelector('[data-el="message-text"]');
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
  if (!_container) return;
  const container = _container.querySelector('[data-el="steps"]');
  if (!container) return;
  container.innerHTML = steps.map(s => `
    <span class="progress-step" data-step="${s.key}">${s.label}</span>
  `).join('');
}

function updateSteps(data, steps) {
  if (!_container) return;
  const activeKeys = new Set(steps.map(s => s.key));
  const stepIndex = steps.findIndex(s => s.key === data.step);

  _container.querySelectorAll('.progress-step').forEach(el => {
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
  if (!_container) return;
  const messageTextEl = _container.querySelector('[data-el="message-text"]');
  const bar = _container.querySelector('[data-el="bar"]');
  if (messageTextEl) messageTextEl.textContent = `生成失败：${message}`;
  if (bar) bar.style.background = 'var(--error, #ff3b30)';
}

function renderPreviewCards(productId, newSteps, filesByStep) {
  if (!_container) return;
  const container = _container.querySelector('[data-el="preview"]');
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
  return String(str)
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

// 兼容旧入口：极少使用，仅当某些路径仍调用 startProgress 时
export function startProgress(productId, selectedSteps) {
  // 简化版：渲染到 body 临时容器（不应被调用，保留以防意外）
  const container = document.createElement('div');
  document.body.appendChild(container);
  return renderProgressWorkspace(container, productId, selectedSteps, {});
}

export function renderAbortedState(productId, data = {}) {
  initPreview();
  return renderProgressWorkspace(document.body, productId, null, {})
    .then(() => showAbortedState(productId, data));
}

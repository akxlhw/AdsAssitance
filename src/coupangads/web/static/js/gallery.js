/**
 * 结果视图：渲染进 canvas 容器。
 *
 * 导出：
 *   renderResultWorkspace(container, productId, prefetchedData, { onRefresh }) -> cleanup
 *   loadResult(productId, selectedSteps, prefetchedData) - 兼容旧入口
 */

import { initPreview } from './preview.js';

let _currentProductId = null;
let _pollTimer = null;
const STATUS_POLL_INTERVAL = 2000;
const STATUS_MAX_POLLS = 300;

const RESULT_HTML = `
  <div class="result-workspace">
    <h2>生成结果</h2>
    <div class="result-summary" data-el="summary"></div>
    <div class="polling-status" data-el="polling"></div>
    <div class="text-cards" data-el="text-cards"></div>
    <div class="image-gallery" data-el="image-gallery"></div>
    <div class="result-actions">
      <button class="secondary-button" data-el="refresh">刷新结果</button>
      <a class="primary-button" data-el="download" download>下载全部资产</a>
    </div>
  </div>
`;

/**
 * @param {HTMLElement} container
 * @param {string} productId
 * @param {object|null} prefetchedData
 * @param {object} callbacks { onRefresh }
 * @returns {() => void} cleanup
 */
export function renderResultWorkspace(container, productId, prefetchedData = null, callbacks = {}) {
  _currentProductId = productId;
  if (_pollTimer) clearTimeout(_pollTimer);

  container.innerHTML = RESULT_HTML;
  initPreview();

  const refreshBtn = container.querySelector('[data-el="refresh"]');
  refreshBtn?.addEventListener('click', () => {
    if (_pollTimer) clearTimeout(_pollTimer);
    fetchAndRender(container, productId, callbacks);
  });

  // 主流程
  (async () => {
    if (prefetchedData &&
        (prefetchedData.status === 'completed' || prefetchedData.status === 'aborted') &&
        (prefetchedData.text_files || prefetchedData.images)) {
      setPollingStatus(container, prefetchedData.status === 'aborted' ? '生成已中止' : '生成已完成');
      await renderFromData(container, productId, prefetchedData);
      return;
    }

    setPollingStatus(container, '正在获取任务状态...');
    try {
      const state = await fetchStatus(productId);
      if (state.status === 'completed') {
        setPollingStatus(container, '生成已完成，正在加载结果...');
        await renderFromData(container, productId, state);
        return;
      }
      if (state.status === 'aborted') {
        setPollingStatus(container, '生成已中止，正在加载已生成结果...');
        await fetchAndRender(container, productId, callbacks);
        return;
      }
      if (state.status === 'error') {
        setPollingStatus(container, '生成失败：' + (state.message || '未知错误'));
        return;
      }
      setPollingStatus(container, '生成中... ' + (state.message || ''));
      await pollStatus(container, productId, callbacks, 0);
    } catch (err) {
      setPollingStatus(container, '获取状态失败：' + err.message);
    }
  })();

  return () => {
    if (_pollTimer) clearTimeout(_pollTimer);
    _pollTimer = null;
  };
}

async function fetchStatus(productId) {
  const res = await fetch(`/api/status/${productId}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('status ' + res.status);
  return res.json();
}

async function pollStatus(container, productId, callbacks, attempt) {
  if (attempt > STATUS_MAX_POLLS) {
    setPollingStatus(container, '等待任务状态超时，请稍后手动刷新');
    return;
  }
  try {
    const state = await fetchStatus(productId);
    if (state.status === 'completed') {
      setPollingStatus(container, '生成已完成，正在加载结果...');
      await renderFromData(container, productId, state);
      return;
    }
    if (state.status === 'aborted') {
      setPollingStatus(container, '生成已中止，正在加载已生成结果...');
      await fetchAndRender(container, productId, callbacks);
      return;
    }
    if (state.status === 'error') {
      setPollingStatus(container, '生成失败：' + (state.message || '未知错误'));
      return;
    }
    setPollingStatus(
      container,
      state.status === 'unknown' ? '任务状态未知，继续等待...' : `生成中... ${state.message || ''}`,
    );
    _pollTimer = setTimeout(
      () => pollStatus(container, productId, callbacks, attempt + 1),
      STATUS_POLL_INTERVAL,
    );
  } catch (err) {
    setPollingStatus(container, '轮询异常：' + err.message);
    _pollTimer = setTimeout(
      () => pollStatus(container, productId, callbacks, attempt + 1),
      5000,
    );
  }
}

async function renderFromData(container, productId, data) {
  renderSummary(container, (data.text_files || []).length, (data.images || []).length);
  renderTextCards(container, data.text_files || [], productId);
  renderImageGallery(container, data.images || [], productId);
  setupDownload(container, productId);
  setPollingStatus(container, '结果加载完成');
}

async function fetchAndRender(container, productId, callbacks) {
  const res = await fetch(`/api/result/${productId}`, { cache: 'no-store' });
  if (!res.ok) {
    setPollingStatus(container, '获取结果失败');
    return;
  }
  const data = await res.json();
  await renderFromData(container, productId, data);
}

function renderSummary(container, textCount, imageCount) {
  const el = container.querySelector('[data-el="summary"]');
  if (el) el.textContent = `共 ${textCount} 个文本文件，${imageCount} 张图片`;
}

function setPollingStatus(container, message) {
  const el = container.querySelector('[data-el="polling"]');
  if (el) el.textContent = message;
}

function renderTextCards(container, files, productId) {
  const cardsEl = container.querySelector('[data-el="text-cards"]');
  if (!cardsEl) return;
  cardsEl.innerHTML = files.map(name => `
    <div class="card" data-name="${escapeHtml(name)}">
      <h3>${escapeHtml(name)}</h3>
      <div class="card-actions">
        <button class="secondary-button preview-text-btn" data-url="/api/result/${productId}/${encodeURIComponent(name)}" data-name="${escapeHtml(name)}">预览</button>
        <a href="/api/result/${productId}/${encodeURIComponent(name)}" target="_blank" class="link-button">新窗口打开</a>
      </div>
    </div>
  `).join('');

  cardsEl.querySelectorAll('.preview-text-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      window.previewText(btn.dataset.url, btn.dataset.name);
    });
  });
}

function renderImageGallery(container, images, productId) {
  const galleryEl = container.querySelector('[data-el="image-gallery"]');
  if (!galleryEl) return;
  galleryEl.innerHTML = images.map(name => `
    <div class="result-image-card" data-name="${escapeHtml(name)}">
      <img src="/api/result/${productId}/${encodeURIComponent(name)}" alt="${escapeHtml(name)}" loading="lazy">
      <span>${escapeHtml(name)}</span>
    </div>
  `).join('');

  galleryEl.querySelectorAll('.result-image-card').forEach(card => {
    const name = card.dataset.name;
    const url = card.querySelector('img')?.src;
    card.addEventListener('click', () => {
      if (url) window.previewImage(url, name);
    });
  });
}

function setupDownload(container, productId) {
  const btn = container.querySelector('[data-el="download"]');
  if (!btn) return;
  btn.href = `/api/download/${productId}`;
  btn.download = `${productId}.zip`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// 兼容旧入口：loadResult
export async function loadResult(productId, selectedSteps, prefetchedData = null) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  return renderResultWorkspace(container, productId, prefetchedData);
}

import { initPreview } from './preview.js';

let _currentProductId = null;
let _pollTimer = null;
const STATUS_POLL_INTERVAL = 2000;   // 状态轮询 2 秒
const STATUS_MAX_POLLS = 300;        // 状态轮询最多 10 分钟

export async function loadResult(productId, selectedSteps, prefetchedData = null) {
  console.log('[gallery] loadResult called', productId, selectedSteps, prefetchedData);
  _currentProductId = productId;
  if (_pollTimer) clearTimeout(_pollTimer);
  showState('result-state');

  // 正常流程：SSE 已经把结果文件列表带过来了，直接渲染
  if (prefetchedData &&
      (prefetchedData.status === 'completed' || prefetchedData.status === 'aborted') &&
      (prefetchedData.text_files || prefetchedData.images)) {
    console.log('[gallery] rendering from prefetched SSE data');
    setPollingStatus(prefetchedData.status === 'aborted' ? '生成已中止' : '生成已完成');
    await renderFromData(productId, selectedSteps, prefetchedData);
    return;
  }

  setPollingStatus('正在获取任务状态...');

  try {
    const state = await fetchStatus(productId);
    console.log('[gallery] initial status:', state);

    if (state.status === 'completed') {
      setPollingStatus('生成已完成，正在加载结果...');
      await renderFromData(productId, selectedSteps, state);
      return;
    }

    if (state.status === 'aborted') {
      setPollingStatus('生成已中止，正在加载已生成结果...');
      await fetchAndRender(productId, selectedSteps);
      return;
    }

    if (state.status === 'error') {
      alert('生成失败：' + (state.message || '未知错误'));
      return;
    }

    // 页面刷新后任务还在进行中，轮询状态
    setPollingStatus('生成中... ' + (state.message || ''));
    await pollStatus(productId, selectedSteps, 0);
  } catch (err) {
    setPollingStatus('获取状态失败：' + err.message);
  }
}

async function fetchStatus(productId) {
  console.log('[gallery] fetching status for', productId);
  const res = await fetch(`/api/status/${productId}`, { cache: 'no-store' });
  console.log('[gallery] status response', res.status);
  if (!res.ok) throw new Error('status ' + res.status);
  return res.json();
}

async function pollStatus(productId, selectedSteps, attempt) {
  if (attempt > STATUS_MAX_POLLS) {
    setPollingStatus('等待任务状态超时，请稍后手动刷新');
    return;
  }

  try {
    const state = await fetchStatus(productId);
    console.log('[gallery] status:', state);

    if (state.status === 'completed') {
      setPollingStatus('生成已完成，正在加载结果...');
      await renderFromData(productId, selectedSteps, state);
      return;
    }

    if (state.status === 'aborted') {
      setPollingStatus('生成已中止，正在加载已生成结果...');
      await fetchAndRender(productId, selectedSteps);
      return;
    }

    if (state.status === 'error') {
      alert('生成失败：' + (state.message || '未知错误'));
      return;
    }

    setPollingStatus(
      state.status === 'unknown'
        ? '任务状态未知，继续等待...'
        : `生成中... ${state.message || ''}`
    );
    _pollTimer = setTimeout(
      () => pollStatus(productId, selectedSteps, attempt + 1),
      STATUS_POLL_INTERVAL
    );
  } catch (err) {
    setPollingStatus('轮询异常：' + err.message);
    _pollTimer = setTimeout(
      () => pollStatus(productId, selectedSteps, attempt + 1),
      5000
    );
  }
}

async function renderFromData(productId, selectedSteps, data) {
  console.log('[gallery] renderFromData', data);
  initPreview();
  renderSummary((data.text_files || []).length, (data.images || []).length);
  renderTextCards(data.text_files || [], productId);
  renderImageGallery(data.images || [], productId);
  setupDownload(productId);
  setupRefresh(productId, selectedSteps);
  setPollingStatus('结果加载完成');
  console.log('[gallery] render done');
}

async function fetchAndRender(productId, selectedSteps) {
  console.log('[gallery] fetching result for', productId);
  const res = await fetch(`/api/result/${productId}`, { cache: 'no-store' });
  console.log('[gallery] result response', res.status);
  if (!res.ok) {
    setPollingStatus('获取结果失败');
    return;
  }
  const data = await res.json();
  console.log('[gallery] result data:', data);
  await renderFromData(productId, selectedSteps, data);
}

function renderSummary(textCount, imageCount) {
  let summary = document.getElementById('result-summary');
  if (!summary) {
    summary = document.createElement('div');
    summary.id = 'result-summary';
    summary.className = 'result-summary';
    const heading = document.querySelector('#result-state h2');
    heading?.parentNode.insertBefore(summary, heading.nextSibling);
  }
  summary.textContent = `共 ${textCount} 个文本文件，${imageCount} 张图片`;
}

function setPollingStatus(message) {
  let status = document.getElementById('polling-status');
  if (!status) {
    status = document.createElement('div');
    status.id = 'polling-status';
    status.className = 'polling-status';
    const summary = document.getElementById('result-summary');
    summary?.parentNode.insertBefore(status, summary.nextSibling);
  }
  status.textContent = message;
}

function renderTextCards(files, productId) {
  const container = document.getElementById('text-cards');
  console.log('[gallery] renderTextCards container=', !!container, 'files=', files.length, files);
  container.innerHTML = files.map(name => `
    <div class="card" data-name="${escapeHtml(name)}">
      <h3>${escapeHtml(name)}</h3>
      <div class="card-actions">
        <button class="secondary-button preview-text-btn" data-url="/api/result/${productId}/${encodeURIComponent(name)}" data-name="${escapeHtml(name)}">预览</button>
        <a href="/api/result/${productId}/${encodeURIComponent(name)}" target="_blank" class="link-button">新窗口打开</a>
      </div>
    </div>
  `).join('');

  container.querySelectorAll('.preview-text-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      window.previewText(btn.dataset.url, btn.dataset.name);
    });
  });
}

function renderImageGallery(images, productId) {
  const container = document.getElementById('image-gallery');
  console.log('[gallery] renderImageGallery container=', !!container, 'images=', images.length);
  container.innerHTML = images.map(name => `
    <div class="result-image-card" data-name="${escapeHtml(name)}">
      <img src="/api/result/${productId}/${encodeURIComponent(name)}" alt="${escapeHtml(name)}" loading="lazy">
      <span>${escapeHtml(name)}</span>
    </div>
  `).join('');

  container.querySelectorAll('.result-image-card').forEach(card => {
    const name = card.dataset.name;
    const url = card.querySelector('img')?.src;
    card.addEventListener('click', () => {
      if (url) window.previewImage(url, name);
    });
  });
}

function setupDownload(productId) {
  const btn = document.getElementById('download-btn');
  btn.href = `/api/download/${productId}`;
  btn.download = `${productId}.zip`;
}

function setupRefresh(productId, selectedSteps) {
  const btn = document.getElementById('refresh-result');
  if (!btn) return;
  const newBtn = btn.cloneNode(true);
  btn.parentNode.replaceChild(newBtn, btn);
  newBtn.addEventListener('click', () => {
    if (_pollTimer) clearTimeout(_pollTimer);
    fetchAndRender(productId, selectedSteps);
  });
}

function showState(id) {
  document.querySelectorAll('.state').forEach(el => el.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

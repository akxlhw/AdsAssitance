import { initConfigPanel } from './config.js';
import { initUpload } from './upload.js';
import { startProgress, renderAbortedState } from './progress.js';
import { HomeWorkbench } from './home.js';
import { PromptStudio } from './prompt-studio.js';

const views = {
  home: document.getElementById('home-view'),
  upload: document.getElementById('upload-state'),
  progress: document.getElementById('progress-state'),
  result: document.getElementById('result-state'),
};

function hideAllViews() {
  Object.values(views).forEach((el) => el?.classList.add('hidden'));
}

function showView(name) {
  hideAllViews();
  views[name]?.classList.remove('hidden');
}

function navigateToHome() {
  window.history.replaceState({}, '', '/');
  showView('home');
  homeWorkbench.mount();
}

function navigateToCreate() {
  window.history.pushState({}, '', '/create');
  homeWorkbench.unmount();
  showView('upload');
  initUpload((pid, steps) => navigateToProgress(pid, steps));
}

async function navigateToProgress(productId, steps = null) {
  window.history.pushState({}, '', `/progress/${encodeURIComponent(productId)}`);
  homeWorkbench.unmount();
  showView('progress');
  try {
    const res = await fetch(`/api/status/${encodeURIComponent(productId)}`, { cache: 'no-store' });
    const data = await res.json();
    if (data.status === 'aborted') {
      renderAbortedState(productId, data);
    } else if (data.status === 'completed') {
      navigateToResult(productId);
    } else {
      startProgress(productId, steps || data.steps || []);
    }
  } catch (err) {
    console.error('[main] failed to resume status:', err);
    navigateToHome();
  }
}

async function navigateToResult(productId) {
  window.history.pushState({}, '', `/result/${encodeURIComponent(productId)}`);
  homeWorkbench.unmount();
  showView('result');
  const { loadResult } = await import('./gallery.js');
  await loadResult(productId);
}

const homeWorkbench = new HomeWorkbench(
  () => navigateToCreate(),
  (productId) => navigateToProgress(productId)
);
const promptStudio = new PromptStudio();

document.addEventListener('DOMContentLoaded', () => {
  initConfigPanel();

  document.getElementById('prompt-studio-btn')?.addEventListener('click', () => promptStudio.open());
  document.getElementById('header-create-btn')?.addEventListener('click', () => navigateToCreate());

  window.addEventListener('popstate', () => {
    resolveRoute();
  });

  resolveRoute();
});

function resolveRoute() {
  const path = window.location.pathname;

  const resultMatch = path.match(/^\/result\/([^/]+)\/?$/);
  if (resultMatch) {
    navigateToResult(decodeURIComponent(resultMatch[1]));
    return;
  }

  const progressMatch = path.match(/^\/progress\/([^/]+)\/?$/);
  if (progressMatch) {
    navigateToProgress(decodeURIComponent(progressMatch[1]));
    return;
  }

  if (path === '/create') {
    navigateToCreate();
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const productId = params.get('product_id');
  if (productId) {
    navigateToProgress(productId);
    return;
  }

  navigateToHome();
}

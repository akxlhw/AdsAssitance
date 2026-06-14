import { initConfigPanel } from './config.js';
import { initPreview } from './preview.js';
import { Workspace } from './workspace.js';

const workspace = new Workspace();

// 把外部行为注入 workspace
workspace.onCreate = () => navigateToCreate();
workspace.onEdit = (productId) => navigateToEdit(productId);
workspace.onOpenProduct = (productId) => navigateToProgress(productId);

function navigateToHome(selectProductId = null) {
  window.history.replaceState({}, '', '/');
  workspace.mount();
  if (selectProductId) {
    workspace.selectProduct(selectProductId, 'assets');
  } else if (!workspace.selectedProductId) {
    workspace.setMode('empty');
  }
}

function navigateToCreate() {
  window.history.pushState({}, '', '/create');
  workspace.mount();
  workspace.setMode('create');
}

function navigateToEdit(productId) {
  window.history.pushState({}, '', `/edit/${encodeURIComponent(productId)}`);
  workspace.mount();
  workspace.setMode('edit', { productId });
}

async function navigateToProgress(productId, steps = null) {
  window.history.pushState({}, '', `/progress/${encodeURIComponent(productId)}`);
  workspace.mount();
  // 优先用现有 status 决定进入 progress 还是 result
  try {
    const res = await fetch(`/api/status/${encodeURIComponent(productId)}`, { cache: 'no-store' });
    const data = await res.json();
    if (data.status === 'completed') {
      workspace.setMode('result', { productId });
    } else if (data.status === 'aborted') {
      workspace.setMode('result', { productId });
    } else {
      workspace.setMode('progress', { productId, steps });
    }
  } catch (err) {
    console.error('[main] failed to resume status:', err);
    workspace.setMode('progress', { productId, steps });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initConfigPanel();
  initPreview();

  // 全局：当 Prompt Studio 有未保存改动时，刷新/关闭页面也拦截
  window.addEventListener('beforeunload', (e) => {
    if (workspace.promptStudio?.isDirty && workspace.promptStudio.isDirty()) {
      e.preventDefault();
      e.returnValue = '';
    }
  });

  window.addEventListener('popstate', () => {
    resolveRoute();
  });

  resolveRoute();
});

function resolveRoute() {
  const path = window.location.pathname;

  const resultMatch = path.match(/^\/result\/([^/]+)\/?$/);
  if (resultMatch) {
    workspace.mount();
    workspace.setMode('result', { productId: decodeURIComponent(resultMatch[1]) });
    return;
  }

  const progressMatch = path.match(/^\/progress\/([^/]+)\/?$/);
  if (progressMatch) {
    navigateToProgress(decodeURIComponent(progressMatch[1]));
    return;
  }

  const editMatch = path.match(/^\/edit\/([^/]+)\/?$/);
  if (editMatch) {
    navigateToEdit(decodeURIComponent(editMatch[1]));
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

// 暴露给浏览器调试用
window.__workspace = workspace;

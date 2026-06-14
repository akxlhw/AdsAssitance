/**
 * Workspace: 单页工作台主控。
 *
 * 三栏布局：sidebar | canvas (mode 切换) | prompt panel
 * 路由变化只换 canvas 内容，sidebar / prompt panel 永久常驻。
 */

import { PromptStudio } from './prompt-studio.js';

const MODES = ['empty', 'create', 'edit', 'progress', 'result', 'assets'];

export class Workspace {
  constructor() {
    this.view = document.getElementById('workspace-view');
    this.sidebarListEl = document.getElementById('workspace-product-list');
    this.canvasEl = document.getElementById('workspace-canvas-content');
    this.toolbarTitleEl = document.getElementById('workspace-canvas-toolbar-title');
    this.toolbarActionsEl = document.getElementById('workspace-canvas-toolbar-actions');
    this.promptPanelEl = document.getElementById('workspace-prompt-panel');

    this.products = [];
    this.selectedProductId = null;
    this.currentMode = null;
    this.currentModeCleanup = null;
    this.pollTimer = null;
    this.promptCollapsed = true;
    this.openMenuProductId = null;

    // Prompt Studio 默认折叠，减少首屏信息过载
    this.view.classList.add('is-prompt-collapsed');

    this.onCreate = null;       // 外部注入：点 + 新建
    this.onEdit = null;         // 外部注入：编辑产品
    this.onOpenProduct = null;  // 外部注入：重新生成

    this.promptStudio = new PromptStudio({
      mode: 'inline',
      container: this.promptPanelEl,
      onToggle: () => this._togglePromptPanel(),
      onDirtyChange: () => this._updateToolbar(),
    });

    this._insertResizer();
    this._restorePromptWidth();
    this._bindEvents();
  }

  // ===== Lifecycle =====

  mount() {
    this.view.classList.remove('hidden');
    this.promptStudio.open();
    this._loadProducts();
    this._startPolling();
  }

  // ===== Public API =====

  /**
   * 切换 canvas mode。
   * @param {string} mode - empty | create | edit | progress | result | assets
   * @param {object} params - { productId?, steps?, prefetchedData?, mode? }
   */
  async setMode(mode, params = {}) {
    if (!MODES.includes(mode)) {
      console.warn('[workspace] unknown mode:', mode);
      return;
    }

    // Dirty 拦截：Prompt Studio 有未保存改动时弹确认
    if (this.promptStudio.isDirty && this.promptStudio.isDirty()) {
      if (!confirm('Prompt Studio 有未保存改动，是否放弃？')) return;
    }

    // 清理上一 mode 的副作用（SSE、轮询等）
    if (this.currentModeCleanup) {
      try { this.currentModeCleanup(); } catch (e) { console.warn('[workspace] mode cleanup failed:', e); }
      this.currentModeCleanup = null;
    }

    this.currentMode = mode;
    this.canvasEl.innerHTML = '';
    this.toolbarActionsEl.innerHTML = '';

    try {
      switch (mode) {
        case 'empty':
          this._renderEmpty();
          break;
        case 'create':
          await this._renderCreate();
          break;
        case 'edit':
          await this._renderEdit(params.productId);
          break;
        case 'progress':
          await this._renderProgress(params.productId, params.steps);
          break;
        case 'result':
          await this._renderResult(params.productId, params.prefetchedData);
          break;
        case 'assets':
          this._renderAssets(params.productId);
          break;
      }
    } catch (err) {
      console.error('[workspace] setMode failed:', err);
      this.canvasEl.innerHTML = `<div class="workspace-canvas__error">加载失败：${err.message}</div>`;
    }

    this._updateToolbar();
  }

  /**
   * 选中某产品（sidebar 高亮 + 默认进入 assets mode）。
   */
  selectProduct(productId, mode = 'assets') {
    this.selectedProductId = productId;
    this._closeMenu();
    this._renderSidebar();
    this.setMode(mode, { productId });
  }

  /**
   * 刷新 sidebar 产品列表（外部触发）。
   */
  async refreshProducts() {
    await this._loadProducts();
  }

  // ===== Sidebar =====

  _bindEvents() {
    document.getElementById('workspace-create-btn')?.addEventListener('click', () => {
      this.onCreate && this.onCreate();
    });

    this.sidebarListEl.addEventListener('click', (e) => {
      const menuBtn = e.target.closest('.workspace-product-item__menu-btn');
      if (menuBtn) {
        e.stopPropagation();
        this._toggleMenu(menuBtn.dataset.productId);
        return;
      }
      const menuItem = e.target.closest('.workspace-product-menu__item');
      if (menuItem) {
        e.stopPropagation();
        this._handleMenuAction(menuItem.dataset.action, menuItem.dataset.productId);
        return;
      }
      const item = e.target.closest('.workspace-product-item');
      if (item) {
        this.selectProduct(item.dataset.productId);
      }
    });

    this.sidebarListEl.addEventListener('dblclick', (e) => {
      const title = e.target.closest('.workspace-product-item__title');
      if (title) {
        const item = title.closest('.workspace-product-item');
        if (item) this._startRename(item.dataset.productId);
      }
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('.workspace-product-item__menu')) {
        this._closeMenu();
      }
    });

    this.canvasEl.addEventListener('click', (e) => {
      const action = e.target.closest('[data-action]');
      if (action) {
        e.stopPropagation();
        this._handleAssetAction(this.selectedProductId, action.dataset.action, action.dataset.value);
      }
    });
  }

  async _loadProducts() {
    try {
      const res = await fetch('/api/products');
      const data = await res.json();
      this.products = data.products || [];
      this._renderSidebar();
    } catch (err) {
      console.error('[workspace] failed to load products:', err);
    }
  }

  _renderSidebar() {
    if (!this.products.length) {
      this.sidebarListEl.innerHTML = `
        <div class="workspace-empty-sidebar">
          <div class="workspace-empty-sidebar__icon">${this._logoIcon(44)}</div>
          <div class="workspace-empty-sidebar__title">还没有商品</div>
          <div class="workspace-empty-sidebar__desc">点击上方 + 号上传你的第一个商品</div>
        </div>
      `;
      return;
    }

    this.sidebarListEl.innerHTML = this.products.map((p) => {
      const isActive = p.product_id === this.selectedProductId;
      const statusDot = p.status === 'completed' ? 'is-completed'
        : p.status === 'running' ? 'is-running'
        : p.status === 'error' ? 'is-error'
        : 'is-draft';
      const menuOpen = this.openMenuProductId === p.product_id ? 'is-open' : '';
      return `
        <div class="workspace-product-item ${isActive ? 'is-active' : ''}" data-product-id="${p.product_id}">
          <span class="workspace-product-item__dot ${statusDot}"></span>
          <div class="workspace-product-item__info">
            <div class="workspace-product-item__title">${this._escapeHtml(p.name)}</div>
            <div class="workspace-product-item__meta">${this._formatStatus(p)}</div>
          </div>
          <button class="workspace-product-item__menu-btn" data-product-id="${p.product_id}" type="button" aria-label="更多">⋮</button>
          <div class="workspace-product-item__menu ${menuOpen}">
            <button class="workspace-product-menu__item" data-action="rename" data-product-id="${p.product_id}" type="button">重命名</button>
            <button class="workspace-product-menu__item" data-action="edit" data-product-id="${p.product_id}" type="button">编辑资料</button>
            <button class="workspace-product-menu__item workspace-product-menu__item--danger" data-action="delete" data-product-id="${p.product_id}" type="button">删除</button>
          </div>
        </div>
      `;
    }).join('');
  }

  _toggleMenu(productId) {
    this.openMenuProductId = this.openMenuProductId === productId ? null : productId;
    this._renderSidebar();
  }

  _closeMenu() {
    if (this.openMenuProductId) {
      this.openMenuProductId = null;
      this._renderSidebar();
    }
  }

  async _handleMenuAction(action, productId) {
    this._closeMenu();
    if (action === 'rename') {
      this._startRename(productId);
    } else if (action === 'edit') {
      this.onEdit && this.onEdit(productId);
    } else if (action === 'delete') {
      this._confirmDelete(productId);
    }
  }

  _startRename(productId) {
    const p = this.products.find((x) => x.product_id === productId);
    if (!p) return;
    this._closeMenu();

    const item = this.sidebarListEl.querySelector(`.workspace-product-item[data-product-id="${productId}"]`);
    if (!item) return;
    const titleEl = item.querySelector('.workspace-product-item__title');
    if (!titleEl) return;

    titleEl.innerHTML = `<input type="text" class="workspace-product-item__rename-input" value="${this._escapeHtml(p.name)}">`;
    const input = titleEl.querySelector('input');
    input.focus();
    input.select();

    const save = async () => {
      const newName = input.value.trim();
      if (newName && newName !== p.product_id) {
        await this._renameProduct(p.product_id, newName);
      }
      this._renderSidebar();
    };

    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        input.blur();
      } else if (e.key === 'Escape') {
        input.removeEventListener('blur', save);
        this._renderSidebar();
      }
    });
  }

  async _renameProduct(productId, newName) {
    try {
      const res = await fetch(`/api/products/${encodeURIComponent(productId)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_product_id: newName }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || '重命名失败');
        return;
      }
      const data = await res.json();
      if (this.selectedProductId === productId) {
        this.selectedProductId = data.new_product_id;
      }
      await this._loadProducts();
    } catch (err) {
      console.error('[workspace] rename failed:', err);
      alert('重命名失败');
    }
  }

  _confirmDelete(productId) {
    const p = this.products.find((x) => x.product_id === productId);
    if (!p) return;
    if (!confirm(`确定删除商品 "${p.name}"？\n此操作会同时删除已生成的所有图片和文案，且无法恢复。`)) {
      return;
    }
    this._deleteProduct(productId);
  }

  async _deleteProduct(productId) {
    try {
      const res = await fetch(`/api/products/${encodeURIComponent(productId)}`, { method: 'DELETE' });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || '删除失败');
        return;
      }
      if (this.selectedProductId === productId) {
        this.selectedProductId = null;
      }
      await this._loadProducts();
      if (!this.selectedProductId) {
        this.setMode('empty');
      }
    } catch (err) {
      console.error('[workspace] delete failed:', err);
      alert('删除失败');
    }
  }

  // ===== Canvas modes =====

  _renderEmpty() {
    this.toolbarTitleEl.textContent = '';
    if (!this.products.length) {
      this.canvasEl.innerHTML = `
        <div class="workspace-canvas__empty workspace-canvas__empty--onboarding">
          <div class="workspace-canvas__empty-icon workspace-canvas__empty-icon--logo">${this._logoIcon(72, 'workspace-canvas__empty-logo')}</div>
          <div class="workspace-canvas__empty-title">开始你的商品创作</div>
          <div class="workspace-canvas__empty-desc">
            上传商品实拍图，AI 将自动生成商品画像、标题、关键词、卖点文案与详情页图片。
          </div>
          <button class="btn-primary workspace-canvas__empty-btn" id="workspace-onboarding-create-btn" type="button">上传商品信息</button>
        </div>
      `;
      document.getElementById('workspace-onboarding-create-btn')?.addEventListener('click', () => {
        this.onCreate && this.onCreate();
      });
    } else {
      this.canvasEl.innerHTML = `
        <div class="workspace-canvas__empty">
          <div class="workspace-canvas__empty-icon workspace-canvas__empty-icon--logo">${this._logoIcon(48, 'workspace-canvas__empty-logo')}</div>
          <div class="workspace-canvas__empty-title">从左侧选择一个商品</div>
          <div class="workspace-canvas__empty-desc">或点击 + 号新建商品。</div>
        </div>
      `;
    }
  }

  async _renderCreate() {
    this.toolbarTitleEl.textContent = '新建商品';
    const { renderCreateWorkspace } = await import('./upload.js');
    const cleanup = renderCreateWorkspace(this.canvasEl, {
      onStart: (pid, steps) => {
        this.selectedProductId = pid;
        this.setMode('progress', { productId: pid, steps });
      },
    });
    this.currentModeCleanup = cleanup;
  }

  async _renderEdit(productId) {
    this.toolbarTitleEl.textContent = '编辑商品';
    const { renderEditWorkspace } = await import('./upload.js');
    const cleanup = renderEditWorkspace(this.canvasEl, {
      productId,
      onSaved: (pid) => {
        this.selectedProductId = pid;
        this._loadProducts().then(() => this.selectProduct(pid));
      },
    });
    this.currentModeCleanup = cleanup;
  }

  async _renderProgress(productId, steps) {
    this.selectedProductId = productId;
    this.toolbarTitleEl.textContent = '生成中';
    const { renderProgressWorkspace } = await import('./progress.js');
    const cleanup = await renderProgressWorkspace(this.canvasEl, productId, steps, {
      onCompleted: (pid, data) => {
        this.setMode('result', { productId: pid, prefetchedData: data });
      },
      onAbortedView: (pid) => {
        this.setMode('result', { productId: pid });
      },
    });
    this.currentModeCleanup = cleanup;
  }

  async _renderResult(productId, prefetchedData) {
    this.selectedProductId = productId;
    this.toolbarTitleEl.textContent = '生成结果';
    const { renderResultWorkspace } = await import('./gallery.js');
    const cleanup = renderResultWorkspace(this.canvasEl, productId, prefetchedData, {
      onRefresh: () => this._renderResult(productId),
    });
    this.currentModeCleanup = cleanup;
  }

  _renderAssets(productId) {
    this.selectedProductId = productId;
    const p = this.products.find((x) => x.product_id === productId);
    this.toolbarTitleEl.textContent = p ? p.name : '';

    this.canvasEl.innerHTML = `
      <div class="workspace-canvas__progress">
        <span class="workspace-canvas__progress-label">进度</span>
        <div class="workspace-canvas__dots">${p ? this._renderDots(p) : ''}</div>
      </div>
      <div id="workspace-canvas-assets"></div>
    `;

    // 重建 toolbar
    this.toolbarActionsEl.innerHTML = `
      <button class="btn-ghost" id="workspace-export-btn" type="button">导出</button>
      <button class="btn-primary" id="workspace-regenerate-btn" type="button">重新生成</button>
    `;
    document.getElementById('workspace-export-btn')?.addEventListener('click', () => {
      window.open(`/api/download/${encodeURIComponent(productId)}`, '_blank');
    });
    document.getElementById('workspace-regenerate-btn')?.addEventListener('click', () => {
      this.onOpenProduct && this.onOpenProduct(productId);
    });

    this._loadAssets(productId);
  }

  _renderDots(p) {
    return p.progress.map((done, i) => {
      const active = !done && p.status === 'running' && i === p.progress.filter(Boolean).length;
      return `<span class="workspace-canvas__dot ${done ? 'is-done' : ''} ${active ? 'is-active' : ''}"></span>`;
    }).join('');
  }

  async _loadAssets(productId) {
    const container = document.getElementById('workspace-canvas-assets');
    if (!container) return;
    try {
      const res = await fetch(`/api/result/${encodeURIComponent(productId)}`);
      if (!res.ok) {
        this._renderEmptyAssets(container, productId);
        return;
      }
      const data = await res.json();
      const images = (data.images || []).slice(0, 4);
      const textFiles = (data.text_files || []).slice(0, 2);

      if (!images.length && !textFiles.length) {
        this._renderEmptyAssets(container, productId);
        return;
      }

      const imageHtml = images.length
        ? `<div class="workspace-canvas__section-title">生成的图片</div>
           <div class="workspace-canvas__image-grid">${images.map((img) => `
             <div class="workspace-canvas__asset-card workspace-canvas__asset-card--image">
               <img src="/api/result/${productId}/${img}" alt="">
               <div class="workspace-canvas__asset-actions">
                 <a class="workspace-canvas__asset-action" href="/api/result/${productId}/${img}" download title="下载">⬇️</a>
                 <button class="workspace-canvas__asset-action" data-action="delete-result" data-value="${img}" type="button" title="删除">🗑️</button>
               </div>
             </div>
           `).join('')}</div>`
        : '';

      const textHtml = textFiles.length
        ? `<div class="workspace-canvas__section-title">生成的文案</div>
           <div class="workspace-canvas__text-grid">${textFiles.map((file) => `
             <div class="workspace-canvas__asset-card workspace-canvas__asset-card--text">
               <div class="workspace-canvas__asset-card-text-name">${this._escapeHtml(file)}</div>
               <div class="workspace-canvas__asset-actions">
                 <button class="workspace-canvas__asset-action" data-action="view-text" data-value="${file}" type="button" title="查看">👁️</button>
                 <button class="workspace-canvas__asset-action" data-action="delete-result" data-value="${file}" type="button" title="删除">🗑️</button>
               </div>
             </div>
           `).join('')}</div>`
        : '';

      container.innerHTML = imageHtml + textHtml;
    } catch (err) {
      console.error('[workspace] failed to load assets:', err);
      this._renderEmptyAssets(container, productId);
    }
  }

  _renderEmptyAssets(container, productId) {
    container.innerHTML = `
      <div class="workspace-canvas__section-title">Generated Images</div>
      <div class="workspace-canvas__image-grid">
        <div class="workspace-canvas__asset-card workspace-canvas__asset-card--placeholder" data-action="start">+ 上传商品信息</div>
      </div>
    `;
  }

  async _handleAssetAction(productId, action, value) {
    if (!productId) return;
    if (action === 'start' || action === 'regenerate') {
      this.onOpenProduct && this.onOpenProduct(productId);
    } else if (action === 'delete-result') {
      if (!confirm('确定删除该生成结果？')) return;
      try {
        const res = await fetch(`/api/result/${encodeURIComponent(productId)}/${encodeURIComponent(value)}`, { method: 'DELETE' });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          alert(data.detail || '删除失败');
          return;
        }
        this._renderAssets(productId);
      } catch (err) {
        console.error('[workspace] delete result failed:', err);
        alert('删除失败');
      }
    } else if (action === 'view-text') {
      try {
        const url = `/api/result/${encodeURIComponent(productId)}/${encodeURIComponent(value)}`;
        if (window.previewText) {
          window.previewText(url, value);
        }
      } catch (err) {
        console.error('[workspace] view text failed:', err);
      }
    }
  }

  // ===== Prompt panel =====

  _togglePromptPanel() {
    this.promptCollapsed = !this.promptCollapsed;
    this.view.classList.toggle('is-prompt-collapsed', this.promptCollapsed);
    // 折叠前清掉 resizer 写入的内联宽度（否则会覆盖 CSS 的 44px），
    // 展开时再恢复用户上次的宽度。
    if (this.promptCollapsed) {
      this._savedInlineWidth = this.promptPanelEl.style.width || '';
      this.promptPanelEl.style.width = '';
    } else if (this._savedInlineWidth) {
      this.promptPanelEl.style.width = this._savedInlineWidth;
    }
  }

  // ===== Resizer（手动拖拽调整 prompt panel 宽度） =====

  _insertResizer() {
    this.resizerEl = document.createElement('div');
    this.resizerEl.className = 'workspace-resizer';
    this.resizerEl.setAttribute('role', 'separator');
    this.resizerEl.setAttribute('aria-orientation', 'vertical');
    this.view.insertBefore(this.resizerEl, this.promptPanelEl);

    let startX = 0;
    let startWidth = 0;

    const onMouseMove = (e) => {
      const delta = e.clientX - startX;
      // prompt panel 在右侧，向右拖 = 缩窄面板，向左拖 = 加宽
      const newWidth = startWidth - delta;
      const min = 320;
      const max = Math.min(900, window.innerWidth - 600);
      const clamped = Math.max(min, Math.min(max, newWidth));
      this.promptPanelEl.style.width = `${clamped}px`;
      this._persistPromptWidth(clamped);
    };

    const onMouseUp = () => {
      this.resizerEl.classList.remove('is-dragging');
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    const onMouseDown = (e) => {
      if (this.promptCollapsed) return;
      e.preventDefault();
      startX = e.clientX;
      startWidth = this.promptPanelEl.offsetWidth;
      this.resizerEl.classList.add('is-dragging');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    };

    this.resizerEl.addEventListener('mousedown', onMouseDown);

    // 双击重置为默认宽度
    this.resizerEl.addEventListener('dblclick', () => {
      this.promptPanelEl.style.width = '';
      localStorage.removeItem('workspace.promptWidth');
    });
  }

  _persistPromptWidth(width) {
    try { localStorage.setItem('workspace.promptWidth', String(width)); } catch (e) { /* ignore */ }
  }

  _restorePromptWidth() {
    try {
      const saved = localStorage.getItem('workspace.promptWidth');
      if (saved) this.promptPanelEl.style.width = `${saved}px`;
    } catch (e) { /* ignore */ }
  }

  _updateToolbar() {
    // toolbar 在不同 mode 下已经渲染；这里只确保 prompt 折叠按钮可用
  }

  // ===== Polling =====

  _startPolling() {
    this._stopPolling();
    this.pollTimer = setInterval(() => {
      const hasRunning = this.products.some((p) => p.status === 'running');
      if (hasRunning) this._loadProducts();
    }, 3000);
  }

  _stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  // ===== Utils =====

  _formatStatus(p) {
    const label = p.status === 'completed' ? '已完成'
      : p.status === 'running' ? '生成中'
      : p.status === 'error' ? '失败'
      : '草稿';
    return `${label} · ${p.image_count}图 · ${p.text_count}文`;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  _logoIcon(size = 28, className = '') {
    const cls = className ? ` class="${className}"` : '';
    return `
      <svg width="${size}" height="${size}" viewBox="0 0 120 120" fill="none"${cls}>
        <rect x="10" y="10" width="100" height="100" rx="28" fill="#111111"/>
        <path d="M84 38C84 38 56 30 40 48C24 66 36 88 56 88C72 88 82 76 84 72" stroke="white" stroke-width="10" stroke-linecap="round" fill="none"/>
        <circle cx="88" cy="60" r="8" fill="#FF5A5A"/>
      </svg>
    `;
  }
}

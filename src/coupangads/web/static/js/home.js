import { PromptStudio } from './prompt-studio.js';

export class HomeWorkbench {
  constructor(onCreate, onOpenProduct) {
    this.view = document.getElementById('home-view');
    this.sidebarListEl = document.getElementById('home-product-list');
    this.canvasEl = document.getElementById('home-canvas');
    this.promptPanelEl = document.getElementById('home-prompt-panel');
    this.onCreate = onCreate;
    this.onOpenProduct = onOpenProduct;

    this.products = [];
    this.selectedProductId = null;
    this.pollTimer = null;
    this.promptCollapsed = false;

    this.promptStudio = new PromptStudio({
      mode: 'inline',
      container: this.promptPanelEl,
      onToggle: () => this._togglePromptPanel(),
    });

    this._bindEvents();
  }

  mount() {
    this.view.classList.remove('hidden');
    this.promptStudio.open();
    this._loadProducts();
    this._startPolling();
  }

  unmount() {
    this.view.classList.add('hidden');
    this._stopPolling();
  }

  _bindEvents() {
    document.getElementById('home-create-btn')?.addEventListener('click', () => this.onCreate());
    this.sidebarListEl.addEventListener('click', (e) => {
      const item = e.target.closest('.home-product-item');
      if (item) {
        this._selectProduct(item.dataset.productId);
      }
    });

    this.canvasEl.addEventListener('click', (e) => {
      const action = e.target.closest('[data-action]');
      if (action) {
        e.stopPropagation();
        const actionName = action.dataset.action;
        this._handleAction(this.selectedProductId, actionName);
      }
    });
  }

  async _loadProducts() {
    try {
      const res = await fetch('/api/products');
      const data = await res.json();
      this.products = data.products || [];
      this._renderSidebar();
      if (this.products.length && !this.selectedProductId) {
        this._selectProduct(this.products[0].product_id);
      } else if (this.selectedProductId) {
        this._renderCanvas();
      }
    } catch (err) {
      console.error('[home] failed to load products:', err);
    }
  }

  _selectProduct(productId) {
    this.selectedProductId = productId;
    this._renderSidebar();
    this._renderCanvas();
  }

  _renderSidebar() {
    if (!this.products.length) {
      this.sidebarListEl.innerHTML = `
        <div class="home-empty-sidebar">
          <div class="home-empty-sidebar__icon">📦</div>
          <div>还没有商品</div>
          <button class="btn-primary home-empty-sidebar__btn" id="home-empty-create-btn">新建商品</button>
        </div>
      `;
      document.getElementById('home-empty-create-btn')?.addEventListener('click', () => this.onCreate());
      return;
    }

    this.sidebarListEl.innerHTML = this.products.map((p) => {
      const isActive = p.product_id === this.selectedProductId;
      const statusDot = p.status === 'completed' ? 'is-completed'
        : p.status === 'running' ? 'is-running'
        : p.status === 'error' ? 'is-error'
        : 'is-draft';
      return `
        <div class="home-product-item ${isActive ? 'is-active' : ''}" data-product-id="${p.product_id}">
          <span class="home-product-item__dot ${statusDot}"></span>
          <div class="home-product-item__info">
            <div class="home-product-item__title">${this._escapeHtml(p.name)}</div>
            <div class="home-product-item__meta">${this._formatStatus(p)}</div>
          </div>
        </div>
      `;
    }).join('');
  }

  _renderCanvas() {
    const p = this.products.find((x) => x.product_id === this.selectedProductId);
    if (!p) {
      this.canvasEl.innerHTML = `
        <div class="home-canvas__empty">
          <div class="home-canvas__empty-icon">🎨</div>
          <div class="home-canvas__empty-title">选择一个商品</div>
          <div class="home-canvas__empty-desc">在左侧列表中选择商品，即可在此预览已生成的内容。</div>
        </div>
      `;
      return;
    }

    const thumb = p.thumbnail
      ? `<div class="home-canvas__hero"><img src="${p.thumbnail}" alt=""></div>`
      : `<div class="home-canvas__hero home-canvas__hero--placeholder">+ 上传商品信息</div>`;

    const progressDots = p.progress.map((done, i) => {
      const active = !done && p.status === 'running' && i === p.progress.filter(Boolean).length;
      return `<span class="home-canvas__dot ${done ? 'is-done' : ''} ${active ? 'is-active' : ''}"></span>`;
    }).join('');

    const actions = p.status === 'completed'
      ? `<button class="btn-primary" data-action="view">查看结果</button><button class="btn-ghost" data-action="regenerate">重新生成</button>`
      : p.status === 'running'
      ? `<button class="btn-ghost" data-action="continue">继续</button><button class="btn-ghost" data-action="abort" style="color: var(--error, #ef4444);">中止</button>`
      : p.status === 'error'
      ? `<button class="btn-primary" data-action="retry">重试</button><button class="btn-ghost" data-action="delete">删除</button>`
      : `<button class="btn-primary" data-action="start">开始生成</button><button class="btn-ghost" data-action="delete">删除</button>`;

    this.canvasEl.innerHTML = `
      <div class="home-canvas__header">
        <div>
          <h2 class="home-canvas__title">${this._escapeHtml(p.name)}</h2>
          <div class="home-canvas__meta">${this._formatMeta(p)}</div>
        </div>
        <div class="home-canvas__actions">${actions}</div>
      </div>
      ${thumb}
      <div class="home-canvas__progress">
        <span class="home-canvas__progress-label">进度</span>
        <div class="home-canvas__dots">${progressDots}</div>
      </div>
      <div class="home-canvas__assets" id="home-canvas-assets"></div>
    `;

    this._loadAssets(p.product_id);
  }

  async _loadAssets(productId) {
    const container = document.getElementById('home-canvas-assets');
    if (!container) return;
    try {
      const res = await fetch(`/api/result/${encodeURIComponent(productId)}`);
      if (!res.ok) {
        container.innerHTML = '';
        return;
      }
      const data = await res.json();
      const images = (data.images || []).slice(0, 4);
      const textFiles = (data.text_files || []).slice(0, 2);

      const imageHtml = images.length
        ? `<div class="home-canvas__section-title">图片</div>
           <div class="home-canvas__image-grid">${images.map((img) => `
             <div class="home-canvas__asset-card"><img src="/api/result/${productId}/${img}" alt=""></div>
           `).join('')}</div>`
        : '';

      const textHtml = textFiles.length
        ? `<div class="home-canvas__section-title">文案</div>
           <div class="home-canvas__text-grid">${textFiles.map((file) => `
             <div class="home-canvas__asset-card home-canvas__asset-card--text">${this._escapeHtml(file)}</div>
           `).join('')}</div>`
        : '';

      container.innerHTML = imageHtml + textHtml;
    } catch (err) {
      console.error('[home] failed to load assets:', err);
      container.innerHTML = '';
    }
  }

  _handleAction(productId, action) {
    if (!productId) return;
    if (action === 'view' || action === 'continue' || action === 'retry' || action === 'start' || action === 'regenerate') {
      this.onOpenProduct(productId);
    } else if (action === 'abort') {
      fetch(`/api/abort/${encodeURIComponent(productId)}`, { method: 'POST' });
    } else if (action === 'delete') {
      alert('删除功能后续开放');
    }
  }

  _togglePromptPanel() {
    this.promptCollapsed = !this.promptCollapsed;
    this.view.classList.toggle('is-prompt-collapsed', this.promptCollapsed);
    const btn = this.promptPanelEl.querySelector('.prompt-panel__toggle');
    if (btn) btn.textContent = this.promptCollapsed ? '‹' : '›';
  }

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

  _formatStatus(p) {
    const label = p.status === 'completed' ? '已完成'
      : p.status === 'running' ? '生成中'
      : p.status === 'error' ? '失败'
      : '草稿';
    return `${label} · ${p.image_count}图 · ${p.text_count}文`;
  }

  _formatMeta(p) {
    const parts = [
      p.created_at ? this._formatTime(p.created_at) : '',
      p.status === 'completed' && p.completed_at ? `耗时 ${this._formatDuration(p.created_at, p.completed_at)}` : '',
    ].filter(Boolean);
    return parts.join(' · ') || p.message || '尚未开始';
  }

  _formatTime(iso) {
    const date = new Date(iso);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    return `${Math.floor(diff / 86400)}天前`;
  }

  _formatDuration(startIso, endIso) {
    const diff = Math.floor((new Date(endIso) - new Date(startIso)) / 1000);
    if (diff < 60) return `${diff}秒`;
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟`;
    return `${Math.floor(diff / 3600)}小时`;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

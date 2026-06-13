const FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '生成中' },
  { key: 'completed', label: '已完成' },
  { key: 'error', label: '失败' },
];

export class HomeWorkbench {
  constructor(onCreate, onOpenProduct) {
    this.view = document.getElementById('home-view');
    this.filtersEl = document.getElementById('home-filters');
    this.gridEl = document.getElementById('product-grid');
    this.onCreate = onCreate;
    this.onOpenProduct = onOpenProduct;

    this.products = [];
    this.activeFilter = 'all';
    this.pollTimer = null;

    this._bindEvents();
  }

  mount() {
    this.view.classList.remove('hidden');
    this._loadProducts();
    this._startPolling();
  }

  unmount() {
    this.view.classList.add('hidden');
    this._stopPolling();
  }

  _bindEvents() {
    this.filtersEl.addEventListener('click', (e) => {
      const pill = e.target.closest('.filter-pill');
      if (pill) {
        this.activeFilter = pill.dataset.filter;
        this._renderFilters();
        this._renderGrid();
      }
    });
    this.gridEl.addEventListener('click', (e) => {
      const card = e.target.closest('.product-card');
      if (!card) return;
      const action = e.target.closest('[data-action]');
      if (action) {
        e.stopPropagation();
        const productId = card.dataset.productId;
        const actionName = action.dataset.action;
        this._handleAction(productId, actionName);
      } else {
        this.onOpenProduct(card.dataset.productId);
      }
    });
  }

  async _loadProducts() {
    try {
      const res = await fetch('/api/products');
      const data = await res.json();
      this.products = data.products || [];
      this._renderFilters();
      this._renderGrid();
    } catch (err) {
      console.error('[home] failed to load products:', err);
    }
  }

  _filteredProducts() {
    if (this.activeFilter === 'all') return this.products;
    return this.products.filter((p) => p.status === this.activeFilter);
  }

  _renderFilters() {
    this.filtersEl.innerHTML = FILTERS.map((f) => `
      <button class="filter-pill ${f.key === this.activeFilter ? 'is-active' : ''}" data-filter="${f.key}">
        ${f.label}
      </button>
    `).join('');
  }

  _renderGrid() {
    const items = this._filteredProducts();
    if (!items.length) {
      this.gridEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">📦</div>
          <div class="empty-state__title">还没有商品</div>
          <div class="empty-state__desc">点击右上角「新建商品」开始生成你的第一套内容。</div>
        </div>
      `;
      return;
    }

    this.gridEl.innerHTML = items.map((p) => this._renderCard(p)).join('');
  }

  _renderCard(p) {
    const badgeClass = p.status === 'completed' ? 'product-card__badge--completed'
      : p.status === 'running' ? 'product-card__badge--progress'
      : p.status === 'error' ? 'product-card__badge--error'
      : '';
    const badgeLabel = p.status === 'completed' ? '已完成'
      : p.status === 'running' ? '生成中'
      : p.status === 'error' ? '失败'
      : '草稿';

    const thumb = p.thumbnail
      ? `<img src="${p.thumbnail}" alt="">`
      : (p.status === 'running' ? '<div class="product-card__thumb--shimmer"></div>' : '+ 上传商品信息');

    const dots = p.progress.map((done, i) => {
      const active = !done && p.status === 'running' && i === p.progress.filter(Boolean).length;
      return `<span class="product-card__dot ${done ? 'is-done' : ''} ${active ? 'is-active' : ''}"></span>`;
    }).join('');

    const meta = [
      p.created_at ? this._formatTime(p.created_at) : '',
      p.image_count ? `${p.image_count}张图片` : '',
      p.text_count ? `${p.text_count}段文案` : '',
    ].filter(Boolean).join(' · ');

    const actions = p.status === 'completed'
      ? `<button class="btn-ghost" data-action="view">查看</button><button class="btn-ghost" data-action="regenerate">重新生成</button>`
      : p.status === 'running'
      ? `<button class="btn-ghost" data-action="continue">继续</button><button class="btn-ghost" data-action="abort" style="color: var(--error, #ef4444);">中止</button>`
      : p.status === 'error'
      ? `<button class="btn-ghost" data-action="retry">重试</button><button class="btn-ghost" data-action="delete">删除</button>`
      : `<button class="btn-primary" data-action="start">开始生成</button><button class="btn-ghost" data-action="delete">删除</button>`;

    return `
      <div class="product-card" data-product-id="${p.product_id}">
        <span class="product-card__badge ${badgeClass}">${badgeLabel}</span>
        <div class="product-card__thumb">${thumb}</div>
        <div class="product-card__body">
          <div class="product-card__title">${this._escapeHtml(p.name)}</div>
          <div class="product-card__meta">${meta || p.message || '尚未开始'}</div>
          <div class="product-card__dots">${dots}</div>
          <div class="product-card__actions">${actions}</div>
        </div>
      </div>
    `;
  }

  _handleAction(productId, action) {
    if (action === 'view' || action === 'continue' || action === 'retry' || action === 'start' || action === 'regenerate') {
      this.onOpenProduct(productId);
    } else if (action === 'abort') {
      fetch(`/api/abort/${encodeURIComponent(productId)}`, { method: 'POST' });
    } else if (action === 'delete') {
      // MVP 暂不实现删除
      alert('删除功能后续开放');
    }
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

  _formatTime(iso) {
    const date = new Date(iso);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
    return `${Math.floor(diff / 86400)}天前`;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

/**
 * Prompt Studio — 常驻工作台右侧的提示词编辑面板。
 *
 * 功能：
 *   - 菜单覆盖全部已注册模板（含 style_rules / image_global_constraints）
 *   - "已修改" 文字标签替代原本的圆点
 *   - Dirty 标记 + 切换拦截（外部 workspace 通过 isDirty() 检查）
 *   - 变量 hover 说明 + 点击插入反馈
 *   - 预览渲染按钮（拉取真实产品数据）
 *   - 历史抽屉（快照列表 + 一键回滚）
 *   - 行号 + {var} 高亮（textarea + 同步 overlay）
 *   - Tab 缩进
 */

const PROMPT_MENU_ORDER = [
  { name: 'product_report.txt', label: '商品画像' },
  { name: 'product_title.txt', label: '标题' },
  { name: 'wing_keywords.txt', label: '关键词' },
  { name: 'selling_points.txt', label: '卖点文案' },
  { name: 'instagram.txt', label: 'INS 文案' },
  { name: 'image_prompt.txt', label: '图片生成' },
  { name: 'style_rules.txt', label: '风格规则' },
  { name: 'image_global_constraints.txt', label: '图片全局约束' },
];

const VAR_DESCRIPTIONS = {
  image_count: '产品图片张数（整数）',
  product_report: '上游生成的商品画像 Markdown',
  product_title: '上游生成的商品标题',
  wing_keywords: '上游生成的关键词矩阵',
  selling_points: '上游生成的 B1-B9 卖点 Markdown',
  style_rules: '从 style_rules.txt 解析出的当前风格规则段落',
  product_context: '组装后的产品上下文（约束 + 标题 + 关键词 + 画像摘要）',
  screen: '当前屏位置（"第 N 屏"）',
  block: '当前卖点块编号（B1-B9）',
  block_content: '当前卖点块对应的韩文文案',
};

export class PromptStudio {
  constructor(options = {}) {
    this.mode = options.mode || 'inline';
    this.container = options.container || null;
    this.onToggle = options.onToggle || null;
    this.onDirtyChange = options.onDirtyChange || null;

    this.prompts = [];
    this.currentName = null;
    this.originalContent = '';
    this._suppressDirtyCheck = false;

    this._buildDom();
    this._bindEvents();
  }

  // ===== Public =====

  isDirty() {
    if (!this.currentName) return false;
    if (this._suppressDirtyCheck) return false;
    return this.textareaEl.value !== this.originalContent;
  }

  async open() {
    await this._loadPrompts();
    if (!this.currentName && this.prompts.length) {
      await this._select(this.prompts[0].name);
    }
  }

  close() {
    // 兼容：inline 模式下 close 由 workspace 处理
  }

  // ===== DOM =====

  _buildDom() {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="prompt-panel__header">
        <h2 class="prompt-panel__title">
          <span data-el="dirty-dot" class="prompt-panel__dirty-dot"></span>
          ⚙️ Prompt Studio
        </h2>
        <button class="prompt-panel__toggle btn-ghost" type="button" aria-label="收起">收起</button>
      </div>
      <div class="prompt-panel__body">
        <nav class="prompt-menu"></nav>
        <div class="prompt-editor">
          <div class="prompt-editor__meta">
            <div class="prompt-editor__name"></div>
            <div class="prompt-editor__desc"></div>
          </div>

          <div class="prompt-editor__wrap">
            <div class="prompt-editor__gutter" data-el="gutter" aria-hidden="true"></div>
            <pre class="prompt-editor__overlay" data-el="overlay" aria-hidden="true"></pre>
            <textarea class="prompt-editor__textarea" data-el="textarea" spellcheck="false"></textarea>
          </div>

          <div class="prompt-editor__insert-hint" data-el="insert-hint"></div>
          <div class="prompt-editor__vars" data-el="vars"></div>

          <div class="prompt-editor__actions">
            <button class="btn-ghost prompt-reset" type="button">恢复默认</button>
            <button class="btn-ghost prompt-history" type="button">历史</button>
            <button class="btn-ghost prompt-preview" type="button">预览</button>
            <button class="btn-primary prompt-save" type="button">保存</button>
          </div>
        </div>
      </div>
      <div class="prompt-history-drawer" data-el="history-drawer">
        <div class="prompt-history-drawer__header">
          <span>历史快照</span>
          <button class="prompt-history-drawer__close" type="button" data-el="history-close">&times;</button>
        </div>
        <div class="prompt-history-drawer__list" data-el="history-list"></div>
      </div>
      <div class="prompt-preview-modal" data-el="preview-modal">
        <div class="prompt-preview-modal__panel">
          <div class="prompt-preview-modal__header">
            <span>预览渲染</span>
            <button type="button" data-el="preview-close">&times;</button>
          </div>
          <div class="prompt-preview-modal__body">
            <div class="prompt-preview-modal__controls">
              <label>样本产品：
                <select data-el="preview-product"></select>
              </label>
              <button class="btn-primary" type="button" data-el="preview-run">渲染</button>
            </div>
            <pre class="prompt-preview-modal__output" data-el="preview-output"></pre>
          </div>
        </div>
      </div>
    `;

    this.dirtyDotEl = this.container.querySelector('[data-el="dirty-dot"]');
    this.menuEl = this.container.querySelector('.prompt-menu');
    this.nameEl = this.container.querySelector('.prompt-editor__name');
    this.descEl = this.container.querySelector('.prompt-editor__desc');
    this.varsEl = this.container.querySelector('[data-el="vars"]');
    this.gutterEl = this.container.querySelector('[data-el="gutter"]');
    this.overlayEl = this.container.querySelector('[data-el="overlay"]');
    this.textareaEl = this.container.querySelector('[data-el="textarea"]');
    this.insertHintEl = this.container.querySelector('[data-el="insert-hint"]');
    this.toastEl = document.getElementById('prompt-toast');
    this.historyDrawerEl = this.container.querySelector('[data-el="history-drawer"]');
    this.historyListEl = this.container.querySelector('[data-el="history-list"]');
    this.previewModalEl = this.container.querySelector('[data-el="preview-modal"]');
    this.previewOutputEl = this.container.querySelector('[data-el="preview-output"]');
    this.previewProductSelectEl = this.container.querySelector('[data-el="preview-product"]');
  }

  _bindEvents() {
    this.container.querySelector('.prompt-panel__toggle').addEventListener('click', () => {
      if (this.onToggle) this.onToggle();
    });

    this.menuEl.addEventListener('click', (e) => {
      const item = e.target.closest('.prompt-menu__item');
      if (item) this._select(item.dataset.name);
    });

    this.varsEl.addEventListener('click', (e) => {
      const tag = e.target.closest('.prompt-editor__var-tag');
      if (tag) this._insertText(tag.dataset.var, tag.dataset.label);
    });

    this.container.querySelector('.prompt-save').addEventListener('click', () => this._save());
    this.container.querySelector('.prompt-reset').addEventListener('click', () => this._reset());
    this.container.querySelector('.prompt-history').addEventListener('click', () => this._openHistory());
    this.container.querySelector('[data-el="history-close"]').addEventListener('click', () => this._closeHistory());
    this.container.querySelector('.prompt-preview').addEventListener('click', () => this._openPreview());
    this.container.querySelector('[data-el="preview-close"]').addEventListener('click', () => this._closePreview());
    this.container.querySelector('[data-el="preview-run"]').addEventListener('click', () => this._runPreview());

    // 编辑器联动：input → dirty + overlay + gutter
    this.textareaEl.addEventListener('input', () => {
      this._updateDirty();
      this._syncOverlay();
    });
    this.textareaEl.addEventListener('scroll', () => {
      this.overlayEl.scrollTop = this.textareaEl.scrollTop;
      this.overlayEl.scrollLeft = this.textareaEl.scrollLeft;
      this.gutterEl.scrollTop = this.textareaEl.scrollTop;
    });
    this.textareaEl.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        this._insertText('  ');
      }
    });
  }

  // ===== Menu =====

  async _loadPrompts() {
    const res = await fetch('/api/prompts');
    if (!res.ok) {
      this._showToast('加载 Prompt 列表失败');
      return;
    }
    const data = await res.json();
    const orderMap = new Map(PROMPT_MENU_ORDER.map((m, i) => [m.name, i]));
    this.prompts = data
      .filter((p) => orderMap.has(p.name))
      .sort((a, b) => (orderMap.get(a.name) ?? 0) - (orderMap.get(b.name) ?? 0))
      .map((p) => ({
        ...p,
        label: PROMPT_MENU_ORDER.find((m) => m.name === p.name)?.label || p.label,
      }));
    this._renderMenu();
  }

  _renderMenu() {
    this.menuEl.innerHTML = this.prompts.map((p) => `
      <div class="prompt-menu__item ${p.name === this.currentName ? 'is-active' : ''}" data-name="${p.name}">
        <span>${p.label}</span>
        ${p.is_overridden ? '<span class="prompt-menu__modified">已修改</span>' : ''}
      </div>
    `).join('');
  }

  async _select(name) {
    if (this.isDirty()) {
      if (!confirm('当前修改未保存，是否放弃？')) return;
    }
    this.currentName = name;
    const res = await fetch(`/api/prompts/${encodeURIComponent(name)}`);
    if (!res.ok) {
      this._showToast('加载 Prompt 失败');
      return;
    }
    const data = await res.json();
    this._suppressDirtyCheck = true;
    this.originalContent = data.content;
    this.textareaEl.value = data.content;
    this._suppressDirtyCheck = false;

    this.nameEl.textContent = data.label;
    this.descEl.textContent = data.description;
    this.varsEl.innerHTML = data.variables?.length
      ? '可用变量（点击插入）：' + data.variables.map((v) => {
          const desc = VAR_DESCRIPTIONS[v] || '';
          return `<span class="prompt-editor__var-tag" data-var="{${v}}" data-label="${v}" title="${desc}">{${v}}</span>`;
        }).join('')
      : '无变量';

    this._renderMenu();
    this._updateDirty();
    this._syncOverlay();
  }

  // ===== Editor overlay =====

  _syncOverlay() {
    const text = this.textareaEl.value;
    // 转义 HTML
    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    // 给 {var} 染色
    const highlighted = escaped.replace(/\{(\w+)\}/g, '<span class="prompt-overlay__var">{$1}</span>');
    // 末尾补一个空格避免末行无换行
    this.overlayEl.innerHTML = highlighted + '\n';
    this._renderGutter(text);
  }

  _renderGutter(text) {
    const lines = text.split('\n').length;
    let html = '';
    for (let i = 1; i <= lines; i++) {
      html += `${i}\n`;
    }
    this.gutterEl.textContent = html;
  }

  _updateDirty() {
    const dirty = this.isDirty();
    this.dirtyDotEl.classList.toggle('is-dirty', dirty);
    if (this.onDirtyChange) this.onDirtyChange();
  }

  // ===== Variables =====

  _insertText(text, label) {
    const textarea = this.textareaEl;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    textarea.value = value.slice(0, start) + text + value.slice(end);
    textarea.selectionStart = textarea.selectionEnd = start + text.length;
    textarea.focus();
    this._updateDirty();
    this._syncOverlay();

    if (label) {
      const desc = VAR_DESCRIPTIONS[label] || '';
      this.insertHintEl.textContent = `插入 {${label}}：${desc}`;
      this.insertHintEl.classList.add('is-visible');
      clearTimeout(this._hintTimer);
      this._hintTimer = setTimeout(() => {
        this.insertHintEl.classList.remove('is-visible');
      }, 2500);
    }
  }

  // ===== Save / Reset =====

  async _save() {
    if (!this.currentName) return;
    const content = this.textareaEl.value;
    const res = await fetch(`/api/prompts/${encodeURIComponent(this.currentName)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      alert(data.detail || '保存失败');
      return;
    }
    this.originalContent = content;
    const meta = this.prompts.find((p) => p.name === this.currentName);
    if (meta) meta.is_overridden = true;
    this._renderMenu();
    this._updateDirty();
    this._showToast('已保存');
  }

  async _reset() {
    if (!this.currentName) return;
    if (!confirm('确定恢复为默认 prompt？')) return;
    const res = await fetch(`/api/prompts/${encodeURIComponent(this.currentName)}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      alert(data.detail || '恢复失败');
      return;
    }
    const meta = this.prompts.find((p) => p.name === this.currentName);
    if (meta) meta.is_overridden = false;
    await this._select(this.currentName);
    this._showToast('已恢复默认');
  }

  // ===== History =====

  async _openHistory() {
    if (!this.currentName) return;
    this.historyDrawerEl.classList.add('is-open');
    this.historyListEl.innerHTML = '<div class="prompt-history-drawer__loading">加载中...</div>';
    try {
      const res = await fetch(`/api/prompts/${encodeURIComponent(this.currentName)}/history`);
      if (!res.ok) {
        this.historyListEl.innerHTML = '<div class="prompt-history-drawer__empty">加载失败</div>';
        return;
      }
      const list = await res.json();
      if (!list.length) {
        this.historyListEl.innerHTML = '<div class="prompt-history-drawer__empty">暂无历史快照</div>';
        return;
      }
      this.historyListEl.innerHTML = list.map((item) => `
        <div class="prompt-history-item" data-id="${item.id}">
          <div class="prompt-history-item__meta">
            <div class="prompt-history-item__time">${this._formatTime(item.timestamp)}</div>
            <div class="prompt-history-item__size">${item.size} 字节</div>
          </div>
          <div class="prompt-history-item__actions">
            <button type="button" class="link-button" data-action="view" data-id="${item.id}">查看</button>
            <button type="button" class="link-button" data-action="restore" data-id="${item.id}">恢复</button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      this.historyListEl.innerHTML = '<div class="prompt-history-drawer__empty">加载失败</div>';
    }
  }

  _closeHistory() {
    this.historyDrawerEl.classList.remove('is-open');
  }

  _formatTime(ts) {
    try {
      const d = new Date(ts);
      return d.toLocaleString();
    } catch (e) {
      return ts;
    }
  }

  // 历史列表点击委托
  // 绑定在 drawer 容器上一次性
  _bindHistoryActions() {
    this.historyListEl.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const id = btn.dataset.id;
      const action = btn.dataset.action;
      if (action === 'view') {
        const res = await fetch(`/api/prompts/${encodeURIComponent(this.currentName)}/history/${encodeURIComponent(id)}`);
        if (res.ok) {
          const data = await res.json();
          alert(data.content);
        }
      } else if (action === 'restore') {
        if (!confirm('确定把这条快照恢复为当前覆盖？')) return;
        const res = await fetch(`/api/prompts/${encodeURIComponent(this.currentName)}/history/${encodeURIComponent(id)}/restore`, {
          method: 'POST',
        });
        if (!res.ok) {
          alert('恢复失败');
          return;
        }
        await this._select(this.currentName);
        this._showToast('已恢复历史版本');
      }
    });
  }

  // ===== Preview =====

  async _openPreview() {
    if (!this.currentName) return;
    this.previewModalEl.classList.add('is-open');
    // 加载产品列表
    try {
      const res = await fetch('/api/products');
      const data = await res.json();
      const products = data.products || [];
      this.previewProductSelectEl.innerHTML = '<option value="">（使用占位样本）</option>' +
        products.map((p) => `<option value="${p.product_id}">${p.name}</option>`).join('');
    } catch (err) {
      this.previewProductSelectEl.innerHTML = '<option value="">（无法加载产品）</option>';
    }
    this.previewOutputEl.textContent = '点击"渲染"按钮生成预览...';
  }

  _closePreview() {
    this.previewModalEl.classList.remove('is-open');
  }

  async _runPreview() {
    if (!this.currentName) return;
    const productId = this.previewProductSelectEl.value || null;
    this.previewOutputEl.textContent = '渲染中...';
    try {
      const res = await fetch(`/api/prompts/${encodeURIComponent(this.currentName)}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        this.previewOutputEl.textContent = `渲染失败：${data.detail || res.status}`;
        return;
      }
      const data = await res.json();
      this.previewOutputEl.textContent = data.rendered;
    } catch (err) {
      this.previewOutputEl.textContent = `渲染失败：${err.message}`;
    }
  }

  // ===== Utils =====

  _showToast(message) {
    if (!this.toastEl) return;
    this.toastEl.textContent = message;
    this.toastEl.classList.add('is-visible');
    setTimeout(() => this.toastEl.classList.remove('is-visible'), 2000);
  }
}

// 注：因为 _bindHistoryActions 需要 list 元素已存在，把它直接在 _bindEvents 调用
// 在 _buildDom 后 _bindEvents 调用一次即可
const __originalBind = PromptStudio.prototype._bindEvents;
PromptStudio.prototype._bindEvents = function () {
  __originalBind.call(this);
  this._bindHistoryActions();
};

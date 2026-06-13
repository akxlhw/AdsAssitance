const PROMPT_MENU_ORDER = [
  { name: 'product_report.txt', label: '商品画像' },
  { name: 'product_title.txt', label: '标题' },
  { name: 'wing_keywords.txt', label: '关键词' },
  { name: 'selling_points.txt', label: '卖点文案' },
  { name: 'instagram.txt', label: 'INS 文案' },
  { name: 'image_prompt.txt', label: '图片生成' },
];

export class PromptStudio {
  constructor(options = {}) {
    this.mode = options.mode || 'modal';
    this.container = options.container || null;
    this.onToggle = options.onToggle || null;

    this.prompts = [];
    this.currentName = null;
    this.originalContent = '';

    this._buildDom();
    this._bindEvents();
  }

  _buildDom() {
    if (this.mode === 'modal') {
      this.modal = document.getElementById('prompt-modal');
      this.menuEl = document.getElementById('prompt-menu');
      this.nameEl = document.getElementById('prompt-editor-name');
      this.descEl = document.getElementById('prompt-editor-desc');
      this.textareaEl = document.getElementById('prompt-editor-textarea');
      this.varsEl = document.getElementById('prompt-editor-vars');
      this.toastEl = document.getElementById('prompt-toast');
    } else if (this.mode === 'inline' && this.container) {
      this.container.innerHTML = `
        <div class="prompt-panel__header">
          <h2 class="prompt-panel__title">⚙️ Prompt Studio</h2>
          <button class="prompt-panel__toggle" type="button" aria-label="收起">›</button>
        </div>
        <div class="prompt-panel__body">
          <nav class="prompt-menu"></nav>
          <div class="prompt-editor">
            <div class="prompt-editor__meta">
              <div class="prompt-editor__name"></div>
              <div class="prompt-editor__desc"></div>
            </div>
            <textarea class="prompt-editor__textarea" spellcheck="false"></textarea>
            <div class="prompt-editor__vars"></div>
            <div class="prompt-editor__actions">
              <button class="btn-ghost prompt-reset" type="button">恢复默认</button>
              <button class="btn-primary prompt-save" type="button">保存</button>
            </div>
          </div>
        </div>
      `;
      this.menuEl = this.container.querySelector('.prompt-menu');
      this.nameEl = this.container.querySelector('.prompt-editor__name');
      this.descEl = this.container.querySelector('.prompt-editor__desc');
      this.textareaEl = this.container.querySelector('.prompt-editor__textarea');
      this.varsEl = this.container.querySelector('.prompt-editor__vars');
      this.toastEl = document.getElementById('prompt-toast');
    }
  }

  async open() {
    if (this.mode === 'modal') {
      this.modal.classList.add('is-open');
    }
    await this._loadPrompts();
    if (!this.currentName && this.prompts.length) {
      this._select(this.prompts[0].name);
    }
  }

  close() {
    if (this.mode === 'modal') {
      this.modal.classList.remove('is-open');
    }
  }

  _bindEvents() {
    if (this.mode === 'modal') {
      document.getElementById('prompt-modal-close').addEventListener('click', () => this.close());
      this.modal.addEventListener('click', (e) => {
        if (e.target === this.modal || e.target.classList.contains('prompt-backdrop')) {
          this.close();
        }
      });
      document.getElementById('prompt-cancel').addEventListener('click', () => this.close());
    } else if (this.mode === 'inline') {
      this.container.querySelector('.prompt-panel__toggle').addEventListener('click', () => {
        if (this.onToggle) this.onToggle();
      });
    }

    this.menuEl.addEventListener('click', (e) => {
      const item = e.target.closest('.prompt-menu__item');
      if (item) {
        this._select(item.dataset.name);
      }
    });

    this.varsEl.addEventListener('click', (e) => {
      const tag = e.target.closest('.prompt-editor__var-tag');
      if (tag) {
        this._insertText(tag.dataset.var);
      }
    });

    const saveBtn = this.mode === 'modal'
      ? document.getElementById('prompt-save')
      : this.container.querySelector('.prompt-save');
    saveBtn.addEventListener('click', () => this._save());

    const resetBtn = this.mode === 'modal'
      ? document.getElementById('prompt-reset')
      : this.container.querySelector('.prompt-reset');
    resetBtn.addEventListener('click', () => this._reset());
  }

  _insertText(text) {
    const textarea = this.textareaEl;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    textarea.value = value.slice(0, start) + text + value.slice(end);
    textarea.selectionStart = textarea.selectionEnd = start + text.length;
    textarea.focus();
  }

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
        <span class="prompt-menu__badge ${p.is_overridden ? '' : 'is-hidden'}"></span>
      </div>
    `).join('');
  }

  async _select(name) {
    if (this.currentName && this.textareaEl.value !== this.originalContent) {
      if (!confirm('当前修改未保存，是否放弃？')) return;
    }
    this.currentName = name;
    const res = await fetch(`/api/prompts/${encodeURIComponent(name)}`);
    if (!res.ok) {
      this._showToast('加载 Prompt 失败');
      return;
    }
    const data = await res.json();
    this.originalContent = data.content;
    this.textareaEl.value = data.content;

    this.nameEl.textContent = data.label;
    this.descEl.textContent = data.description;
    this.varsEl.innerHTML = data.variables?.length
      ? '可用变量：' + data.variables.map((v) => `<span class="prompt-editor__var-tag" data-var="{${v}}">{${v}}</span>`).join('')
      : '无变量';
    this._renderMenu();
  }

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

  _showToast(message) {
    if (!this.toastEl) return;
    this.toastEl.textContent = message;
    this.toastEl.classList.add('is-visible');
    setTimeout(() => this.toastEl.classList.remove('is-visible'), 2000);
  }
}

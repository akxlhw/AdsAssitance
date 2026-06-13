const PROMPT_MENU_ORDER = [
  { name: 'product_report.txt', label: '商品画像' },
  { name: 'product_title.txt', label: '标题' },
  { name: 'wing_keywords.txt', label: '关键词' },
  { name: 'selling_points.txt', label: '卖点文案' },
  { name: 'instagram.txt', label: 'INS 文案' },
  { name: 'image_prompt.txt', label: '图片生成' },
];

export class PromptStudio {
  constructor() {
    this.modal = document.getElementById('prompt-modal');
    this.menuEl = document.getElementById('prompt-menu');
    this.nameEl = document.getElementById('prompt-editor-name');
    this.descEl = document.getElementById('prompt-editor-desc');
    this.textareaEl = document.getElementById('prompt-editor-textarea');
    this.varsEl = document.getElementById('prompt-editor-vars');
    this.toastEl = document.getElementById('prompt-toast');

    this.prompts = [];
    this.currentName = null;
    this.originalContent = '';

    this._bindEvents();
  }

  async open() {
    this.modal.classList.add('is-open');
    await this._loadPrompts();
    if (!this.currentName && this.prompts.length) {
      this._select(this.prompts[0].name);
    }
  }

  close() {
    this.modal.classList.remove('is-open');
  }

  _bindEvents() {
    document.getElementById('prompt-modal-close').addEventListener('click', () => this.close());
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal || e.target.classList.contains('prompt-backdrop')) {
        this.close();
      }
    });

    document.getElementById('prompt-save').addEventListener('click', () => this._save());
    document.getElementById('prompt-reset').addEventListener('click', () => this._reset());
    document.getElementById('prompt-cancel').addEventListener('click', () => this.close());

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
    // 按 PROMPT_MENU_ORDER 排序，仅保留后端返回的 prompt
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
    this.toastEl.textContent = message;
    this.toastEl.classList.add('is-visible');
    setTimeout(() => this.toastEl.classList.remove('is-visible'), 2000);
  }
}

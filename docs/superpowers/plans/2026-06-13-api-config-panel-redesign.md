# API 配置面板重设计 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有简陋的 API 配置 modal 重设计为符合「沉静极简」风格的分块卡片式面板，用 segmented control 选择 provider，并动态显示相关字段。

**Architecture：** 仅改动前端三层：HTML 结构重写成两个 provider 卡片区块 + 动态字段区；CSS 新增 modal 动画、卡片、segmented control、状态标签、Mock 提示条样式；JS 重写 provider 切换与字段显隐逻辑，保持 `/api/config` 调用不变。

**Tech Stack：** HTML / CSS / Vanilla JS / FastAPI（仅验证）

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/coupangads/web/templates/index.html` | `#config-modal` 新结构：标题区、两个 provider 卡片、动态字段容器 |
| `src/coupangads/web/static/css/components.css` | modal 动画、卡片、segmented control、状态标签、Mock 提示条、保存按钮样式 |
| `src/coupangads/web/static/js/config.js` | provider 切换、字段显隐、状态渲染、保存提交 |

---

## Task 1: 重写 HTML 结构

**Files:**
- Modify: `src/coupangads/web/templates/index.html:91-134`

**目标：** 用新的分块卡片结构替换原有表单。

- [ ] **Step 1: 替换 `#config-modal` 内容**

  当前结构：
  ```html
  <div id="config-modal" class="modal hidden">
    <div class="modal-content">
      <h2>API 配置</h2>
      <form id="config-form">...</form>
    </div>
  </div>
  ```

  替换为：
  ```html
  <div id="config-modal" class="modal hidden">
    <div class="modal-backdrop"></div>
    <div class="modal-panel config-panel">
      <div class="config-panel__header">
        <h2>API 配置</h2>
        <p class="config-panel__subtitle">选择模型提供商并填写密钥</p>
      </div>

      <form id="config-form">
        <!-- 文本生成 -->
        <div class="config-card" data-config-group="text">
          <h3 class="config-card__title">文本生成</h3>
          <div class="segmented-control" role="group" aria-label="文本生成提供商">
            <button type="button" class="segmented-control__btn is-active" data-provider="gemini" data-target="text">Gemini</button>
            <button type="button" class="segmented-control__btn" data-provider="deepseek" data-target="text">DeepSeek</button>
            <button type="button" class="segmented-control__btn" data-provider="mock" data-target="text">Mock</button>
          </div>

          <div class="config-fields" data-fields-for="text-gemini">
            <div class="config-field">
              <div class="config-field__label-row">
                <label for="gemini-key">Gemini API Key</label>
                <span id="gemini-status" class="config-status config-status--unconfigured">未配置</span>
              </div>
              <input type="password" id="gemini-key" name="gemini_api_key" placeholder="输入 API Key">
            </div>
          </div>

          <div class="config-fields hidden" data-fields-for="text-deepseek">
            <div class="config-field">
              <div class="config-field__label-row">
                <label for="deepseek-key">DeepSeek API Key</label>
                <span id="deepseek-status" class="config-status config-status--unconfigured">未配置</span>
              </div>
              <input type="password" id="deepseek-key" name="deepseek_api_key" placeholder="输入 API Key">
            </div>
            <div class="config-field">
              <label for="deepseek-model">DeepSeek Model</label>
              <input type="text" id="deepseek-model" name="deepseek_model" value="deepseek-v4-pro">
            </div>
          </div>

          <div class="config-fields hidden" data-fields-for="text-mock">
            <div class="config-mock-hint">Mock 模式：离线开发，不调用真实 API</div>
          </div>
        </div>

        <!-- 图片生成 -->
        <div class="config-card" data-config-group="image">
          <h3 class="config-card__title">图片生成</h3>
          <div class="segmented-control" role="group" aria-label="图片生成提供商">
            <button type="button" class="segmented-control__btn is-active" data-provider="gemini" data-target="image">Gemini</button>
            <button type="button" class="segmented-control__btn" data-provider="doubao" data-target="image">Doubao</button>
            <button type="button" class="segmented-control__btn" data-provider="mock" data-target="image">Mock</button>
          </div>

          <div class="config-fields" data-fields-for="image-gemini">
            <div class="config-field">
              <div class="config-field__label-row">
                <label for="image-gemini-key">Gemini API Key</label>
                <span id="gemini-status-image" class="config-status config-status--unconfigured">未配置</span>
              </div>
              <input type="password" id="image-gemini-key" name="image_gemini_api_key" placeholder="输入 API Key">
            </div>
          </div>

          <div class="config-fields hidden" data-fields-for="image-doubao">
            <div class="config-field">
              <div class="config-field__label-row">
                <label for="doubao-key">Doubao API Key</label>
                <span id="doubao-status" class="config-status config-status--unconfigured">未配置</span>
              </div>
              <input type="password" id="doubao-key" name="doubao_api_key" placeholder="输入 API Key">
            </div>
          </div>

          <div class="config-fields hidden" data-fields-for="image-mock">
            <div class="config-mock-hint">Mock 模式：离线开发，不调用真实 API</div>
          </div>
        </div>

        <button type="submit" class="config-submit">保存配置</button>
      </form>
    </div>
  </div>
  ```

- [ ] **Step 2: 验证 HTML 标签平衡**

  Run: `python -c "from pathlib import Path; html = Path('src/coupangads/web/templates/index.html').read_text(encoding='utf-8'); assert html.count('<div') == html.count('</div')"`
  Expected: no assertion error

---

## Task 2: 新增 CSS 样式

**Files:**
- Modify: `src/coupangads/web/static/css/components.css`

**目标：** 定义 modal 动画、配置面板、卡片、segmented control、字段、状态标签、Mock 提示条。

- [ ] **Step 1: 重写/扩展 modal 样式**

  在文件末尾或合适位置添加：
  ```css
  .modal {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }

  .modal.hidden {
    display: none;
  }

  .modal-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    animation: modal-backdrop-in 0.2s ease;
  }

  @keyframes modal-backdrop-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .modal-panel {
    position: relative;
    z-index: 1001;
    background: var(--bg-primary);
    border-radius: var(--radius);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
    width: 100%;
    max-width: 420px;
    max-height: 90vh;
    overflow-y: auto;
    padding: 2rem;
    animation: modal-panel-in 0.3s ease;
  }

  @keyframes modal-panel-in {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  ```

- [ ] **Step 2: 添加配置面板组件样式**

  ```css
  .config-panel__header {
    text-align: center;
    margin-bottom: 1.5rem;
  }

  .config-panel__header h2 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
    letter-spacing: -0.01em;
  }

  .config-panel__subtitle {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin: 0.25rem 0 0;
  }

  .config-card {
    background: var(--bg-tertiary, #fafafa);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .config-card__title {
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0 0 0.75rem;
    color: var(--text-primary);
  }

  .segmented-control {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 0.875rem;
  }

  .segmented-control__btn {
    flex: 1;
    padding: 0.4rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: transparent;
    color: var(--text-secondary);
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .segmented-control__btn:hover {
    border-color: var(--text-primary);
    color: var(--text-primary);
  }

  .segmented-control__btn.is-active {
    background: var(--text-primary);
    border-color: var(--text-primary);
    color: var(--bg-primary);
  }

  .config-fields {
    animation: fade-in 0.2s ease;
  }

  .config-field {
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.625rem;
  }

  .config-field__label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.25rem;
  }

  .config-field label {
    font-size: 0.75rem;
    color: var(--text-secondary);
  }

  .config-field input[type="password"],
  .config-field input[type="text"] {
    width: 100%;
    padding: 0.4rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-tertiary);
    font-size: 0.75rem;
    color: var(--text-primary);
    box-sizing: border-box;
  }

  .config-field input::placeholder {
    color: var(--text-secondary);
    opacity: 0.6;
  }

  .config-status {
    font-size: 0.7rem;
  }

  .config-status--configured {
    color: var(--accent);
  }

  .config-status--unconfigured {
    color: var(--error);
  }

  .config-mock-hint {
    padding: 0.625rem;
    background: #f0f9f4;
    border: 1px solid #d4edda;
    border-radius: var(--radius);
    color: #2a6;
    font-size: 0.75rem;
  }

  .config-submit {
    width: 100%;
    padding: 0.65rem;
    background: var(--text-primary);
    color: var(--bg-primary);
    border: none;
    border-radius: var(--radius);
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .config-submit:hover {
    opacity: 0.9;
  }
  ```

- [ ] **Step 3: 删除旧 modal 相关样式（如果存在冲突）**

  检查并移除旧的 `.modal-content` 等可能与 `.modal-panel` 冲突的样式。

---

## Task 3: 重写 JS 逻辑

**Files:**
- Modify: `src/coupangads/web/static/js/config.js`

**目标：** 实现 provider 切换、字段显隐、状态渲染、保存。

- [ ] **Step 1: 重写 `initConfigPanel`**

  ```javascript
  const PROVIDER_FIELDS = {
    text: {
      gemini: ['text-gemini'],
      deepseek: ['text-deepseek'],
      mock: ['text-mock'],
    },
    image: {
      gemini: ['image-gemini'],
      doubao: ['image-doubao'],
      mock: ['image-mock'],
    },
  };

  export async function initConfigPanel() {
    const modal = document.getElementById('config-modal');
    if (!modal) return;

    const btn = document.getElementById('config-btn');
    const form = document.getElementById('config-form');
    if (!btn || !form) return;

    // 绑定打开/关闭
    btn.addEventListener('click', () => modal.classList.remove('hidden'));
    modal.querySelector('.modal-backdrop')?.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
        modal.classList.add('hidden');
      }
    });

    // 绑定 provider 切换
    modal.querySelectorAll('.segmented-control__btn').forEach((button) => {
      button.addEventListener('click', () => {
        const target = button.dataset.target;
        const provider = button.dataset.provider;
        setProvider(target, provider);
      });
    });

    // 加载当前配置
    const statusRes = await fetch('/api/config');
    const status = await statusRes.json();

    updateStatusLabel('gemini-status', status.gemini_configured);
    updateStatusLabel('gemini-status-image', status.gemini_configured);
    updateStatusLabel('doubao-status', status.doubao_configured);
    updateStatusLabel('deepseek-status', status.deepseek_configured);

    setProvider('text', status.text_provider || 'gemini');
    setProvider('image', status.image_provider || 'gemini');

    document.getElementById('deepseek-model').value =
      status.deepseek_model || 'deepseek-v4-pro';

    setPlaceholder('gemini-key', status.gemini_configured);
    setPlaceholder('image-gemini-key', status.gemini_configured);
    setPlaceholder('doubao-key', status.doubao_configured);
    setPlaceholder('deepseek-key', status.deepseek_configured);

    // 绑定保存
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(form);
      const payload = {
        text_provider: getActiveProvider('text'),
        image_provider: getActiveProvider('image'),
        gemini_api_key: formData.get('gemini_api_key') || '',
        doubao_api_key: formData.get('doubao_api_key') || '',
        deepseek_api_key: formData.get('deepseek_api_key') || '',
        deepseek_model: formData.get('deepseek_model') || 'deepseek-v4-pro',
      };

      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      modal.classList.add('hidden');
      initConfigPanel();
    });
  }
  ```

- [ ] **Step 2: 添加辅助函数**

  ```javascript
  function updateStatusLabel(elementId, configured) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.textContent = configured ? '已配置' : '未配置';
    el.classList.toggle('config-status--configured', configured);
    el.classList.toggle('config-status--unconfigured', !configured);
  }

  function setProvider(target, provider) {
    const buttons = document.querySelectorAll(
      `.segmented-control__btn[data-target="${target}"]`
    );
    buttons.forEach((btn) => {
      btn.classList.toggle('is-active', btn.dataset.provider === provider);
    });

    const allFields = document.querySelectorAll(
      `.config-card[data-config-group="${target}"] .config-fields`
    );
    allFields.forEach((field) => field.classList.add('hidden'));

    const activeKey = `${target}-${provider}`;
    const activeFields = document.querySelector(`[data-fields-for="${activeKey}"]`);
    if (activeFields) activeFields.classList.remove('hidden');
  }

  function getActiveProvider(target) {
    const activeBtn = document.querySelector(
      `.segmented-control__btn[data-target="${target}"].is-active`
    );
    return activeBtn?.dataset.provider || 'gemini';
  }

  function setPlaceholder(inputId, configured) {
    const input = document.getElementById(inputId);
    if (input) {
      input.placeholder = configured ? '留空以保持不变' : '输入 API Key';
    }
  }
  ```

- [ ] **Step 3: JS 语法检查**

  Run: `node --check src/coupangads/web/static/js/config.js`
  Expected: no output (success)

---

## Task 4: 后端测试回归

**Files:**
- None (仅验证)

- [ ] **Step 1: 运行完整测试套件**

  Run: `venv/Scripts/python -m pytest -q`
  Expected: `61 passed`（或当前最新通过数）

- [ ] **Step 2: 若失败则定位修复**

  仅当模板/JS 改动意外影响测试输出时修复。

---

## Task 5: 手动浏览器验证

**Files:**
- None (仅验证)

- [ ] **Step 1: 启动服务**

  Run: `venv/Scripts/python -m uvicorn src.coupangads.web.app:app --host 127.0.0.1 --port 8080`

- [ ] **Step 2: 打开 http://127.0.0.1:8080 并点击 ⚙️**

- [ ] **Step 3: 验证 Modal 打开动画**

  确认：backdrop 淡入，卡片上滑。

- [ ] **Step 4: 验证文本生成 provider 切换**

  - Gemini：显示 Gemini API Key 输入
  - DeepSeek：显示 DeepSeek API Key + DeepSeek Model
  - Mock：显示绿色提示条，无输入框

- [ ] **Step 5: 验证图片生成 provider 切换**

  - Gemini：显示 Gemini API Key 输入
  - Doubao：显示 Doubao API Key 输入
  - Mock：显示绿色提示条

- [ ] **Step 6: 验证状态标签**

  根据 `/api/config` 返回的 `*_configured` 值，确认标签显示「已配置」或「未配置」，颜色正确。

- [ ] **Step 7: 验证保存**

  - 切换 provider 为 Mock，点击保存
  - Modal 关闭
  - 重新打开 Modal，确认 Mock 仍处于选中状态

- [ ] **Step 8: 验证关闭方式**

  - 点击 backdrop 关闭
  - 重新打开后按 ESC 关闭

- [ ] **Step 9: 停止服务**

  Run: 关闭 uvicorn 窗口或 `taskkill /F /IM uvicorn.exe`

---

## 自我审查

1. **Spec 覆盖：** 全部覆盖：modal 容器、标题区、分块卡片、segmented control、动态字段、状态标签、Mock 提示、保存按钮、动画、交互逻辑。
2. **无占位符：** 所有步骤包含具体代码或命令。
3. **类型/命名一致：** `segmented-control__btn`、`config-card`、`config-fields`、`data-target`、`data-provider`、`data-fields-for` 在全文中保持一致。

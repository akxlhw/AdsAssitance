# 中止按钮视觉布局重设计 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将进度页的「中止生成」控件从突兀的红色描边按钮改为状态消息行末尾的轻量文字链，使其符合「沉静极简 · 流体进度」的视觉风格。

**Architecture：** 仅调整前端呈现层：HTML 结构内嵌中止控件到状态消息行，CSS 定义 `.abort-link` 的默认/hover/loading 样式并清理旧按钮样式，JS 更新选择器和状态切换逻辑。后端 API、SSE 事件、中止业务流程完全不变。

**Tech Stack：** HTML / CSS / Vanilla JS / FastAPI (仅验证)

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/coupangads/web/templates/index.html` | 进度页模板：移除独立 abort 按钮容器，把中止控件内嵌到状态消息行 |
| `src/coupangads/web/static/css/components.css` | 新增/调整 abort link 样式，清理旧 `.abort-button` / `.progress-actions` 样式 |
| `src/coupangads/web/static/js/progress.js` | 更新 DOM 选择器、loading/error/aborted 状态切换逻辑 |

---

## Task 1: 调整 HTML 结构

**Files:**
- Modify: `src/coupangads/web/templates/index.html:60-77`

**目标：** 把中止控件从进度条下方移到状态消息行末尾。

- [ ] **Step 1: 修改状态消息容器，内嵌 abort 控件**

  当前代码：
  ```html
  <div class="progress-percentage" id="progress-percent">0%</div>
  <div class="progress-message" id="progress-message">准备中...</div>
  ```

  改为：
  ```html
  <div class="progress-percentage" id="progress-percent">0%</div>
  <div class="progress-message" id="progress-message">
    <span id="progress-message-text">准备中...</span>
    <button id="abort-link" class="abort-link" type="button">中止</button>
    <span id="abort-error" class="abort-error hidden"></span>
  </div>
  ```

- [ ] **Step 2: 移除旧的独立 abort 按钮容器**

  删除：
  ```html
  <div class="progress-actions" id="progress-actions">
    <button id="abort-btn" class="abort-button" type="button">中止生成</button>
    <span id="abort-error" class="abort-error hidden"></span>
  </div>
  ```

  保留：
  ```html
  <div class="aborted-state hidden" id="aborted-state">
    <p class="aborted-state__message">生成已中止</p>
    <a id="view-results-btn" class="primary-button" href="#">查看已生成结果</a>
  </div>
  ```

- [ ] **Step 3: 验证 HTML 语法**

  Run: `python -c "from pathlib import Path; html = Path('src/coupangads/web/templates/index.html').read_text(encoding='utf-8'); assert html.count('<div') == html.count('</div')"`
  Expected: no assertion error

---

## Task 2: 更新 CSS 样式

**Files:**
- Modify: `src/coupangads/web/static/css/components.css`

**目标：** 定义新 `.abort-link` 样式，清理旧 `.abort-button` / `.progress-actions` 样式。

- [ ] **Step 1: 让状态消息行支持 flex 布局**

  修改 `.progress-message`：
  ```css
  .progress-message {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-bottom: 2rem;
    min-height: 1.5rem;
    transition: opacity 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  ```

- [ ] **Step 2: 新增 `.abort-link` 样式**

  在 `.progress-message` 之后添加：
  ```css
  .abort-link {
    font-size: 0.8rem;
    color: var(--text-secondary);
    opacity: 0.55;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
    cursor: pointer;
    text-decoration: none;
    transition: color 0.2s ease, opacity 0.2s ease;
    line-height: inherit;
  }

  .abort-link:hover:not(:disabled),
  .abort-link:focus-visible:not(:disabled) {
    color: var(--error);
    opacity: 1;
    text-decoration: underline;
  }

  .abort-link:disabled,
  .abort-link.is-loading {
    opacity: 0.55;
    cursor: not-allowed;
    color: var(--text-secondary);
    text-decoration: none;
  }
  ```

- [ ] **Step 3: 调整 `.abort-error` 位置**

  改为块级、占满整行：
  ```css
  .abort-error {
    display: block;
    width: 100%;
    text-align: center;
    font-size: 0.8rem;
    color: var(--error);
    animation: fade-in 0.2s ease;
  }
  ```

- [ ] **Step 4: 删除旧的 abort 按钮与 progress-actions 样式**

  删除以下选择器及全部规则：
  - `.progress-actions`
  - `.abort-button`

  保留 `.aborted-state`、`.aborted-state__message`、`.aborted-state .primary-button` 以及 `@keyframes fade-in`。

- [ ] **Step 5: 验证 CSS 无语法错误**

  Run: `node --check /dev/null 2>/dev/null; echo "node available"`
  （注：本项目无 CSS 解析器；可通过浏览器 devtools 或手动检查。）

---

## Task 3: 更新 JS 选择器与状态逻辑

**Files:**
- Modify: `src/coupangads/web/static/js/progress.js`

**目标：** 让 JS 使用新的 `#abort-link` 和 `#progress-message-text`，保持原有行为不变。

- [ ] **Step 1: 更新 DOM 选择器辅助函数**

  把现有 `getAbortButton()` 改为：
  ```javascript
  function getAbortLink() {
    return document.getElementById('abort-link');
  }
  ```

  新增：
  ```javascript
  function getProgressMessageText() {
    return document.getElementById('progress-message-text');
  }
  ```

  删除 `getProgressActions()` 或改为不再使用。

- [ ] **Step 2: 更新消息渲染函数**

  现有设置消息的逻辑（如 `messageEl.textContent = ...`）改为：
  ```javascript
  const textEl = getProgressMessageText();
  if (textEl) textEl.textContent = message;
  ```

  需要查找所有直接给 `#progress-message` 赋值的地方并替换。

- [ ] **Step 3: 更新 abort 请求与状态函数**

  `setAbortLoading(loading)` 改为：
  ```javascript
  function setAbortLoading(loading) {
    const link = getAbortLink();
    if (!link) return;
    link.disabled = loading;
    link.textContent = loading ? '正在中止...' : '中止';
    if (loading) {
      link.classList.add('is-loading');
    } else {
      link.classList.remove('is-loading');
    }
  }
  ```

  `requestAbort(productId)` 中把事件监听从 `#abort-btn` 改为 `#abort-link`。

- [ ] **Step 4: 更新 aborted 状态显示**

  `showAbortedState(productId, data)` 中：
  - 隐藏 `#abort-link`（如 `link.classList.add('hidden')` 或设置 `display: none`）。
  - 保持消息文字改为「生成已中止」。
  - 保持 `#aborted-state` 显示。

  建议 CSS 中给 `.progress-message:has(.abort-link.hidden)` 不做特殊处理，直接在 JS 中控制。

- [ ] **Step 5: 更新初始化事件绑定**

  查找类似 `getAbortButton().addEventListener('click', ...)` 的代码，改为：
  ```javascript
  const abortLink = getAbortLink();
  if (abortLink) {
    abortLink.addEventListener('click', () => requestAbort(productId));
  }
  ```

- [ ] **Step 6: 检查并更新 `renderAbortedState()`**

  在 `renderAbortedState` 中同样确保 `#abort-link` 被隐藏，并设置消息文字为「生成已中止」。

- [ ] **Step 7: JS 语法检查**

  Run: `node --check src/coupangads/web/static/js/progress.js`
  Expected: no output (success)

---

## Task 4: 运行后端测试确保无回归

**Files:**
- None (仅验证)

- [ ] **Step 1: 运行完整测试套件**

  Run: `venv/Scripts/python -m pytest -q`
  Expected: `61 passed` (或当前最新通过数)

- [ ] **Step 2: 若测试失败，定位并修复**

  仅当前端选择器或模板改动意外影响测试输出时才会失败。修复后再运行。

---

## Task 5: 手动 mock 模式验证

**Files:**
- None (仅验证)

- [ ] **Step 1: 启动服务**

  Run: `venv/Scripts/python -m uvicorn src.coupangads.web.app:app --host 127.0.0.1 --port 8080`

- [ ] **Step 2: 浏览器打开 http://127.0.0.1:8080**

- [ ] **Step 3: 上传图片并开始生成**

  确保 provider.json 已设置为 mock 模式。

- [ ] **Step 4: 观察进度页**

  确认：
  - 中止控件显示为状态消息末尾的浅灰细字「中止」。
  - hover 时变红并出现下划线。

- [ ] **Step 5: 点击中止**

  确认：
  - 文字变为「正在中止...」。
  - 不可再次点击。

- [ ] **Step 6: 等待已中止状态**

  确认：
  - 状态消息变为「生成已中止」。
  - 中止控件消失。
  - 出现「查看已生成结果」按钮。

- [ ] **Step 7: 点击查看已生成结果**

  确认结果页正常显示已生成的文本文件和图片，不为 0。

- [ ] **Step 8: 停止服务**

  Run: 关闭 uvicorn 窗口或 `taskkill /F /IM uvicorn.exe`

---

## 自我审查

1. **Spec 覆盖：** 全部覆盖：位置（C1）、默认样式、hover 样式、loading 状态、error 状态、aborted 状态、无障碍。
2. **无占位符：** 所有步骤包含具体代码或命令，无 TBD。
3. **类型/命名一致：** `#abort-link`、`.abort-link`、`.is-loading`、`#progress-message-text` 在全文中保持一致。

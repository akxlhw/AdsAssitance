# Progress Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the generation progress page into a calm, minimalist, fluid progress UI with smooth number transitions, shimmer progress bar, and elegant step labels.

**Architecture:** Update the progress state markup to a centered layout, add refined CSS animations and variables, and rewrite the progress JavaScript to drive percentage animation, step label states, and a shimmer progress bar using existing SSE data.

**Tech Stack:** Vanilla JavaScript, CSS animations, FastAPI static file serving, existing SSE endpoint.

---

## File Structure

- `src/coupangads/web/templates/index.html` — progress-state DOM structure
- `src/coupangads/web/static/css/components.css` — progress page styles and keyframe animations
- `src/coupangads/web/static/js/progress.js` — progress update logic and animations
- `tests/test_web_api.py` — existing backend tests; run full suite after changes

---

### Task 1: Update progress-state markup

**Files:**
- Modify: `src/coupangads/web/templates/index.html:65-72`

- [ ] **Step 1: Replace progress-state content with new centered layout**

```html
<div id="progress-state" class="state hidden">
  <div class="progress-container">
    <div class="progress-percentage" id="progress-percent">0%</div>
    <div class="progress-message" id="progress-message">准备中...</div>
    <div class="progress-bar-track progress-bar-track--minimal">
      <div class="progress-bar-fill" id="progress-bar"></div>
      <div class="progress-bar-shimmer" id="progress-bar-shimmer"></div>
    </div>
    <div class="progress-steps" id="steps"></div>
  </div>
</div>
```

- [ ] **Step 2: Verify template renders without error**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest tests/test_web_api.py::test_index_page -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/coupangads/web/templates/index.html
git commit -m "feat(progress): update progress state markup for minimal fluid design"
```

---

### Task 2: Add progress page CSS

**Files:**
- Modify: `src/coupangads/web/static/css/components.css`

- [ ] **Step 1: Append progress page styles after existing `.progress-bar-fill` block**

```css
.progress-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  padding: 2rem;
  text-align: center;
}

.progress-percentage {
  font-family: 'Playfair Display', serif;
  font-size: 3rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
  margin-bottom: 0.75rem;
  transition: color var(--transition);
}

.progress-message {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 2rem;
  min-height: 1.5rem;
  transition: opacity 0.3s ease;
}

.progress-message.is-fading {
  opacity: 0;
}

.progress-bar-track--minimal {
  width: 100%;
  max-width: 280px;
  height: 3px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.progress-bar-track--minimal .progress-bar-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
  border-radius: 2px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 12px rgba(74, 222, 128, 0.3);
}

.progress-bar-shimmer {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.4) 50%,
    transparent 100%
  );
  transform: translateX(-100%);
  animation: progress-shimmer 1.5s infinite;
  pointer-events: none;
}

@keyframes progress-shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-steps {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1rem;
  margin-top: 2rem;
}

.progress-step {
  font-size: 0.75rem;
  color: var(--text-secondary);
  opacity: 0.5;
  transition: opacity 0.3s ease, color 0.3s ease;
}

.progress-step.is-done {
  opacity: 1;
}

.progress-step.is-done::before {
  content: '✓ ';
}

.progress-step.is-active {
  opacity: 1;
  color: var(--accent);
  text-shadow: 0 0 8px rgba(17, 17, 17, 0.08);
}

.state-transition {
  transition: opacity 0.4s ease;
}
```

- [ ] **Step 2: Run backend tests to ensure no regressions**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

- [ ] **Step 3: Commit**

```bash
git add src/coupangads/web/static/css/components.css
git commit -m "feat(progress): add minimal fluid progress styles and shimmer animation"
```

---

### Task 3: Rewrite progress JavaScript

**Files:**
- Modify: `src/coupangads/web/static/js/progress.js`

- [ ] **Step 1: Replace entire file content**

```javascript
const STEPS = [
  { key: 'product_report', label: '商品画像', message: '正在分析商品画像...' },
  { key: 'title', label: '标题', message: '正在生成商品标题...' },
  { key: 'keywords', label: '关键词', message: '正在挖掘关键词...' },
  { key: 'selling_points', label: '卖点', message: '正在提炼卖点文案...' },
  { key: 'instagram', label: 'INS 文案', message: '正在撰写 INS 文案...' },
  { key: 'images', label: '图片生成', message: '正在生成详情页图片...' },
];

const ANIMATION_DURATION = 600;

export function startProgress(productId, selectedSteps) {
  showState('progress-state');
  const steps = selectedSteps && selectedSteps.length
    ? STEPS.filter(s => selectedSteps.includes(s.key))
    : STEPS;
  renderSteps(steps);

  const evtSource = new EventSource(`/api/progress/${productId}`);

  evtSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('[progress] SSE message:', data);
    updateProgress(data);
    updateSteps(data, steps);
    updateMessage(data, steps);

    if (data.status === 'error') {
      console.log('[progress] SSE error, closing');
      evtSource.close();
      showError(data.message || '未知错误');
      return;
    }

    if (data.status === 'completed' && data.progress === 100) {
      console.log('[progress] SSE final completed, closing');
      evtSource.close();
      setTimeout(() => {
        import('./gallery.js').then(m => {
          m.loadResult(productId, selectedSteps, data);
        }).catch(err => {
          console.error('[progress] failed to load gallery:', err);
        });
      }, 300);
    }
  };

  evtSource.onerror = () => evtSource.close();
}

function updateProgress(data) {
  const bar = document.getElementById('progress-bar');
  const percentEl = document.getElementById('progress-percent');
  if (!bar || !percentEl) return;

  const target = data.progress || 0;
  const current = parseInt(percentEl.textContent, 10) || 0;

  bar.style.width = `${target}%`;
  animateNumber(percentEl, current, target, ANIMATION_DURATION);
}

function animateNumber(element, from, to, duration) {
  const start = performance.now();
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(from + (to - from) * eased);
    element.textContent = `${value}%`;
    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }
  requestAnimationFrame(step);
}

function updateMessage(data, steps) {
  const messageEl = document.getElementById('progress-message');
  if (!messageEl) return;

  const activeStep = steps.find(s => s.key === data.step);
  const nextMessage = data.status === 'completed'
    ? '生成完成'
    : (activeStep?.message || '准备中...');

  if (messageEl.textContent === nextMessage) return;

  messageEl.classList.add('is-fading');
  setTimeout(() => {
    messageEl.textContent = nextMessage;
    messageEl.classList.remove('is-fading');
  }, 300);
}

function renderSteps(steps) {
  const container = document.getElementById('steps');
  container.innerHTML = steps.map(s => `
    <span class="progress-step" data-step="${s.key}">${s.label}</span>
  `).join('');
}

function updateSteps(data, steps) {
  const activeKeys = new Set(steps.map(s => s.key));
  const stepIndex = steps.findIndex(s => s.key === data.step);

  document.querySelectorAll('.progress-step').forEach(el => {
    const key = el.dataset.step;
    const index = steps.findIndex(s => s.key === key);
    el.classList.remove('is-done', 'is-active');

    if (data.status === 'completed' && activeKeys.has(key)) {
      el.classList.add('is-done');
    } else if (index < stepIndex) {
      el.classList.add('is-done');
    } else if (key === data.step && activeKeys.has(key)) {
      el.classList.add('is-active');
    }
  });
}

function showError(message) {
  const messageEl = document.getElementById('progress-message');
  const bar = document.getElementById('progress-bar');
  if (messageEl) messageEl.textContent = `生成失败：${message}`;
  if (bar) bar.style.background = 'var(--error, #ff3b30)';
}

function showState(id) {
  document.querySelectorAll('.state').forEach(el => {
    el.classList.add('hidden');
    el.classList.remove('state-transition');
  });
  const target = document.getElementById(id);
  target.classList.remove('hidden');
  // Trigger reflow for transition
  void target.offsetWidth;
  target.classList.add('state-transition');
}
```

- [ ] **Step 2: Run full test suite**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

- [ ] **Step 3: Commit**

```bash
git add src/coupangads/web/static/js/progress.js
git commit -m "feat(progress): implement fluid number animation, shimmer, and step labels"
```

---

### Task 4: Manual verification with mock mode

**Files:**
- None (manual check)

- [ ] **Step 1: Restart the web service**

```bash
cd .worktrees/mvp-v1.0
./stop-service.bat || taskkill /F /IM uvicorn.exe 2>/dev/null || true
source venv/Scripts/activate
uvicorn coupangads.web.app:app --host 127.0.0.1 --port 8080
```

- [ ] **Step 2: Open browser and configure mock providers**

Open `http://127.0.0.1:8080`
- Click ⚙️
- Set Text Provider = `Mock（离线开发）`
- Set Image Provider = `Mock（离线开发）`
- Save

- [ ] **Step 3: Upload images and start generation**

- Upload 3+ product images
- Click 开始生成
- Observe progress page: large percentage animates, shimmer bar moves, step labels update, message fades

- [ ] **Step 4: Verify completion transition**

- Wait for 100%
- Confirm progress page fades out and result page fades in
- Confirm result page shows generated placeholder text and images

- [ ] **Step 5: Commit verification notes**

No code changes if manual check passes.

---

## Self-Review

### Spec coverage

- Large percentage display → Task 1 markup + Task 2 CSS
- Current step message → Task 1 markup + Task 3 `updateMessage`
- Fluid progress bar → Task 2 CSS + Task 3 `updateProgress`
- Step labels row → Task 1 markup + Task 2 CSS + Task 3 `updateSteps`
- Number animation → Task 3 `animateNumber`
- Shimmer animation → Task 2 CSS keyframes
- Message fade → Task 2 CSS + Task 3 `updateMessage`
- Completion transition → Task 3 `setTimeout` + gallery import + Task 2 opacity transition

### Placeholder scan

- No TBD/TODO/fill-in details
- All code blocks contain complete code
- Exact file paths provided

### Type consistency

- `data.step`, `data.status`, `data.progress` match existing SSE payload
- DOM IDs (`progress-percent`, `progress-message`, `progress-bar`, `steps`) consistent across HTML/CSS/JS

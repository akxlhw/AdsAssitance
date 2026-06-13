# Partial Result Preview During Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bottom horizontal preview bar to the progress page so users can view generated text and image results as each pipeline step completes.

**Architecture:** Extend the progress page with a preview bar container, fetch the result file list on each SSE progress event, diff against cached results, and render new cards with fade-in animations. Reuse the existing preview modal for inspecting individual files.

**Tech Stack:** Vanilla JavaScript, CSS animations, existing FastAPI endpoints (`/api/progress`, `/api/result`, `/api/result/{filename}`).

---

## File Structure

- `src/coupangads/web/templates/index.html` — add preview bar container inside progress-state
- `src/coupangads/web/static/css/components.css` — add preview bar, card, and animation styles
- `src/coupangads/web/static/js/progress.js` — fetch results on SSE messages, render preview cards, handle clicks
- `src/coupangads/web/static/js/preview.js` — existing preview modal (no changes expected)
- `tests/test_web_api.py` — existing backend tests; run full suite after changes

---

### Task 1: Add preview bar container to progress-state

**Files:**
- Modify: `src/coupangads/web/templates/index.html`

- [ ] **Step 1: Insert preview bar container inside `.progress-container`**

Open `src/coupangads/web/templates/index.html` and locate the `.progress-container` block added in the previous redesign. Insert the following element between the `.progress-bar-track--minimal` block and `.progress-steps`:

```html
<div class="progress-preview-bar" id="progress-preview-bar"></div>
```

The relevant section should look like:

```html
<div id="progress-state" class="state hidden">
  <div class="progress-container">
    <div class="progress-percentage" id="progress-percent">0%</div>
    <div class="progress-message" id="progress-message">准备中...</div>
    <div class="progress-bar-track progress-bar-track--minimal">
      <div class="progress-bar-fill" id="progress-bar"></div>
      <div class="progress-bar-shimmer" id="progress-bar-shimmer"></div>
    </div>
    <div class="progress-preview-bar" id="progress-preview-bar"></div>
    <div class="progress-steps" id="steps"></div>
  </div>
</div>
```

- [ ] **Step 2: Run backend tests to verify no regressions**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

- [ ] **Step 3: Commit**

```bash
git add src/coupangads/web/templates/index.html
git commit -m "feat(preview): add preview bar container to progress page"
```

---

### Task 2: Add preview bar CSS

**Files:**
- Modify: `src/coupangads/web/static/css/components.css`

- [ ] **Step 1: Append preview bar styles after the progress step styles**

Append the following CSS block to `src/coupangads/web/static/css/components.css` after the existing `.state-transition` rule:

```css
.progress-preview-bar {
  display: flex;
  gap: 0.75rem;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  width: 100%;
  max-width: 280px;
  margin-top: 1.5rem;
  padding-bottom: 0.5rem;
}

.progress-preview-bar::-webkit-scrollbar {
  display: none;
}

.progress-preview-card {
  flex: 0 0 120px;
  height: 80px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.75rem;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  opacity: 0;
  transform: translateY(12px);
  animation: preview-card-enter 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
}

.progress-preview-card:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.progress-preview-card.is-loading {
  border-style: dashed;
  border-color: var(--accent);
  cursor: default;
  animation: preview-card-enter 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards,
             preview-card-pulse 1.5s ease-in-out infinite;
}

.progress-preview-card__name {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress-preview-card__preview {
  font-size: 0.65rem;
  color: var(--text-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.progress-preview-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: calc(var(--radius) / 2);
}

@keyframes preview-card-enter {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes preview-card-pulse {
  0%, 100% {
    opacity: 0.7;
  }
  50% {
    opacity: 1;
  }
}
```

- [ ] **Step 2: Run backend tests**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

- [ ] **Step 3: Commit**

```bash
git add src/coupangads/web/static/css/components.css
git commit -m "feat(preview): add preview bar and card styles"
```

---

### Task 3: Implement preview bar JavaScript

**Files:**
- Modify: `src/coupangads/web/static/js/progress.js`

- [ ] **Step 1: Add result cache and fetch helper**

At the top of `src/coupangads/web/static/js/progress.js`, after the `ANIMATION_DURATION` constant, add:

```javascript
let _cachedFiles = [];

async function syncPreviewBar(productId) {
  const res = await fetch(`/api/result/${productId}`, { cache: 'no-store' });
  if (!res.ok) return;
  const data = await res.json();
  const textFiles = data.text_files || [];
  const images = data.images || [];
  const allFiles = [
    ...textFiles.map(name => ({ name, type: 'text' })),
    ...images.map(name => ({ name, type: 'image' })),
  ];

  const newFiles = allFiles.filter(
    f => !_cachedFiles.some(c => c.name === f.name && c.type === f.type)
  );

  if (newFiles.length > 0) {
    _cachedFiles = allFiles;
    renderPreviewCards(productId, newFiles, allFiles);
  }
}
```

- [ ] **Step 2: Add preview card rendering function**

Append the following functions to `src/coupangads/web/static/js/progress.js`:

```javascript
function renderPreviewCards(productId, newFiles, allFiles) {
  const container = document.getElementById('progress-preview-bar');
  if (!container) return;

  const fragment = document.createDocumentFragment();
  for (const file of newFiles) {
    const card = document.createElement('div');
    card.className = 'progress-preview-card';
    card.dataset.name = file.name;
    card.dataset.type = file.type;

    if (file.type === 'image') {
      card.innerHTML = `
        <img class="progress-preview-card__image"
             src="/api/result/${productId}/${encodeURIComponent(file.name)}"
             alt="${escapeHtml(file.name)}"
             loading="lazy">
      `;
    } else {
      card.innerHTML = `
        <div class="progress-preview-card__name">${escapeHtml(file.name)}</div>
        <div class="progress-preview-card__preview">加载中...</div>
      `;
      loadTextPreview(productId, file.name, card);
    }

    card.addEventListener('click', () => {
      if (file.type === 'image') {
        window.previewImage(
          `/api/result/${productId}/${encodeURIComponent(file.name)}`,
          file.name
        );
      } else {
        window.previewText(
          `/api/result/${productId}/${encodeURIComponent(file.name)}`,
          file.name
        );
      }
    });

    fragment.appendChild(card);
  }

  container.appendChild(fragment);
  // Scroll to the newest card
  container.scrollLeft = container.scrollWidth;
}

async function loadTextPreview(productId, name, card) {
  try {
    const res = await fetch(`/api/result/${productId}/${encodeURIComponent(name)}`, {
      cache: 'no-store',
    });
    if (!res.ok) return;
    const text = await res.text();
    const previewEl = card.querySelector('.progress-preview-card__preview');
    if (previewEl) {
      const clean = text.replace(/[#*_`\-]/g, ' ').replace(/\s+/g, ' ').trim();
      previewEl.textContent = clean.slice(0, 80) || '（空文件）';
    }
  } catch (err) {
    console.error('[progress] failed to load text preview:', err);
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
```

- [ ] **Step 3: Wire preview sync into SSE handler**

In the `evtSource.onmessage` handler inside `startProgress`, after calling `updateMessage(data, steps)`, add:

```javascript
syncPreviewBar(productId).catch(err => {
  console.error('[progress] preview sync failed:', err);
});
```

Also clear the cache when starting a new generation. Add at the beginning of `startProgress`, before `showState('progress-state')`:

```javascript
_cachedFiles = [];
const previewBar = document.getElementById('progress-preview-bar');
if (previewBar) previewBar.innerHTML = '';
```

- [ ] **Step 4: Run backend tests**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

- [ ] **Step 5: Commit**

```bash
git add src/coupangads/web/static/js/progress.js
git commit -m "feat(preview): sync and render partial results during generation"
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

- [ ] **Step 2: Configure mock providers**

Open `http://127.0.0.1:8080`, click ⚙️, set Text Provider and Image Provider to `Mock（离线开发）`, save.

- [ ] **Step 3: Upload and generate**

- Upload 3+ images
- Click 开始生成
- Observe: as each step completes, a new card appears in the bottom preview bar
- Click cards: text files open in preview modal, images open in image lightbox

- [ ] **Step 4: Verify completion transition**

- Wait for 100%
- Confirm all result cards are shown
- Confirm progress page fades to result page

- [ ] **Step 5: Run full test suite one final time**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

---

## Self-Review

### Spec coverage

- Preview bar container → Task 1
- Preview bar/card styles and animations → Task 2
- Fetch results on SSE, diff, render new cards → Task 3
- Click to preview → Task 3 event listeners
- Completion transition → existing `progress.js` logic unchanged

### Placeholder scan

- No TBD/TODO/fill-in details
- All code blocks contain complete code
- Exact file paths provided

### Type consistency

- File objects use `{ name, type }` consistently
- DOM IDs (`progress-preview-bar`) consistent across HTML/CSS/JS
- API paths match existing `/api/result/{product_id}` and `/api/result/{product_id}/{filename}`

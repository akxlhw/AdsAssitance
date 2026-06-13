:

# Abort Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cancel button during generation that signals the backend to stop after the current step, preserving already-generated results.

**Architecture:** Use an in-memory abort flag per product. Frontend sends abort request; backend checks flag between pipeline steps. Aborted state is emitted via SSE and persisted to status file.

**Tech Stack:** FastAPI, Python threading event, vanilla JavaScript, SSE.

---

## File Structure

- `src/coupangads/web/api.py` — abort flag storage, `/api/abort/{product_id}` endpoint, abort checks in pipeline runner
- `src/coupangads/orchestration/pipeline.py` — accept abort callback, check between steps
- `src/coupangads/web/templates/index.html` — abort button markup
- `src/coupangads/web/static/css/components.css` — abort button styles
- `src/coupangads/web/static/js/progress.js` — abort button logic and SSE aborted handling
- `tests/test_web_api.py` — add abort endpoint test

---

### Task 1: Backend abort flag and endpoint

**Files:**
- Modify: `src/coupangads/web/api.py`

- [ ] **Step 1: Add abort flag storage and helper**

Near `_task_states`, add:

```python
_abort_flags: dict[str, bool] = {}


def _set_abort_flag(product_id: str) -> None:
    _abort_flags[product_id] = True


def _check_abort_flag(product_id: str) -> bool:
    return _abort_flags.get(product_id, False)


def _clear_abort_flag(product_id: str) -> None:
    _abort_flags.pop(product_id, None)
```

- [ ] **Step 2: Add abort endpoint**

After the `/api/generate/{product_id}` endpoint, add:

```python
@router.post("/abort/{product_id}")
async def abort_generation(product_id: str):
    """请求中止正在运行的生成任务。"""
    safe_id = _safe_name(product_id)
    _set_abort_flag(safe_id)
    return {"status": "abort_requested", "product_id": safe_id}
```

- [ ] **Step 3: Check abort flag in pipeline runner and raise custom exception**

Define a custom exception near the top of the file:

```python
class GenerationAborted(Exception):
    """用户主动中止生成。"""
```

In `_run_pipeline`, wrap the pipeline execution and add abort checks:

```python
def _run_pipeline(product_id: str, enabled_steps: set[str] | None = None) -> None:
    def update_progress(data: dict) -> None:
        _task_states[product_id] = data
        _write_status_file(product_id, data)

    update_progress({"status": "pending", "progress": 0, "message": "任务排队中"})
    _clear_abort_flag(product_id)

    try:
        provider_cfg = _load_provider_config()
        text_provider = provider_cfg.get("text_provider", "gemini")
        image_provider = provider_cfg.get("image_provider", "gemini")

        logger = get_logger("pipeline.web")
        logger.info(
            f"Pipeline start for {product_id}: text={text_provider}, image={image_provider}, "
            f"mock_env={os.environ.get('COUPANGADS_MOCK', '0')}"
        )

        try:
            text_adapter = _build_text_adapter(text_provider)
            image_adapter = _build_image_adapter(image_provider)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"缺少 {text_provider}/{image_provider} 的 API key 文件：{exc}. "
                "请在配置面板选择 Mock（离线开发）模式，或放置正确的 key 文件。"
            ) from exc

        vision_adapter = image_adapter if text_provider != image_provider else None

        templates = _load_templates()
        input_dir = config.DEFAULT_INPUT_DIR / product_id
        output_dir = config.DEFAULT_OUTPUT_DIR / product_id

        def check_abort() -> None:
            if _check_abort_flag(product_id):
                raise GenerationAborted()

        pipeline = ProductPipeline(
            text_adapter=text_adapter,
            image_adapter=image_adapter,
            vision_adapter=vision_adapter,
            templates=templates,
            overwrite=False,
            progress_callback=update_progress,
            request_delay=2.0,
            enabled_steps=enabled_steps,
            abort_callback=check_abort,
        )
        pipeline.run(input_dir, output_dir)
        text_files = [
            p.name for p in output_dir.glob("*.md")
            if p.name != config.RUN_LOG_FILE
        ]
        images = [p.name for p in output_dir.glob("*.png")]
        update_progress(
            {
                "status": "completed",
                "progress": 100,
                "message": "全部完成",
                "text_files": sorted(text_files),
                "images": sorted(images),
            }
        )
    except GenerationAborted:
        update_progress(
            {
                "status": "aborted",
                "progress": _task_states.get(product_id, {}).get("progress", 0),
                "message": "已中止",
            }
        )
    except Exception as exc:
        import traceback
        logger = get_logger("pipeline.web")
        logger.error(f"Pipeline failed for {product_id}: {exc}\n{traceback.format_exc()}")
        update_progress(
            {"step": "error", "status": "error", "progress": 0, "message": str(exc)}
        )
    finally:
        _clear_abort_flag(product_id)
```

- [ ] **Step 4: Run tests**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

- [ ] **Step 5: Commit**

```bash
git add src/coupangads/web/api.py
git commit -m "feat(abort): add abort flag storage and endpoint"
```

---

### Task 2: Pipeline checks abort callback

**Files:**
- Modify: `src/coupangads/orchestration/pipeline.py`

- [ ] **Step 1: Accept abort callback in __init__**

In `ProductPipeline.__init__`, add parameter:

```python
abort_callback: Callable[[], None] | None = None,
```

Store it:

```python
self.abort_callback = abort_callback
```

- [ ] **Step 2: Add check_abort helper**

Add method:

```python
def _check_abort(self) -> None:
    if self.abort_callback:
        self.abort_callback()
```

- [ ] **Step 3: Check abort between steps**

After each major step in `run()`, call `self._check_abort()`. For example, after product_report, title, keywords, selling_points, instagram, and before each image generation batch.

Specifically, insert `self._check_abort()` at the end of each step block, after emitting progress.

- [ ] **Step 4: Run tests**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

- [ ] **Step 5: Commit**

```bash
git add src/coupangads/orchestration/pipeline.py
git commit -m "feat(abort): check abort callback between pipeline steps"
```

---

### Task 3: Frontend abort button

**Files:**
- Modify: `src/coupangads/web/templates/index.html`
- Modify: `src/coupangads/web/static/css/components.css`
- Modify: `src/coupangads/web/static/js/progress.js`

- [ ] **Step 1: Add abort button to progress-state**

In `src/coupangads/web/templates/index.html`, inside `.progress-container`, after `.progress-message`, add:

```html
<button class="abort-button" id="abort-btn" type="button">中止生成</button>
```

- [ ] **Step 2: Add abort button CSS**

Append to `src/coupangads/web/static/css/components.css`:

```css
.abort-button {
  margin-top: 1rem;
  padding: 0.4rem 1rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease;
}

.abort-button:hover {
  color: var(--error, #ff3b30);
  border-color: var(--error, #ff3b30);
}

.abort-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 3: Implement abort logic in progress.js**

In `startProgress`, after setting up the preview bar, get the abort button and attach a click handler:

```javascript
const abortBtn = document.getElementById('abort-btn');
if (abortBtn) {
  abortBtn.disabled = false;
  abortBtn.textContent = '中止生成';
  const newBtn = abortBtn.cloneNode(true);
  abortBtn.parentNode.replaceChild(newBtn, abortBtn);
  newBtn.addEventListener('click', async () => {
    newBtn.disabled = true;
    newBtn.textContent = '正在中止...';
    try {
      await fetch(`/api/abort/${safeProductId}`, { method: 'POST' });
    } catch (err) {
      console.error('[progress] abort request failed:', err);
      newBtn.disabled = false;
      newBtn.textContent = '中止生成';
    }
  });
}
```

Update the SSE handler to handle `aborted` status:

```javascript
if (data.status === 'aborted') {
  console.log('[progress] generation aborted');
  evtSource.close();
  showAborted(data, productId, selectedSteps);
  return;
}
```

Add `showAborted` function:

```javascript
function showAborted(data, productId, selectedSteps) {
  const messageEl = document.getElementById('progress-message');
  if (messageEl) messageEl.textContent = '已中止';

  const abortBtn = document.getElementById('abort-btn');
  if (abortBtn) {
    abortBtn.disabled = true;
    abortBtn.textContent = '已中止';
  }

  // Add a button to view partial results
  let viewBtn = document.getElementById('view-partial-results');
  if (!viewBtn) {
    viewBtn = document.createElement('button');
    viewBtn.id = 'view-partial-results';
    viewBtn.className = 'primary-button';
    viewBtn.textContent = '查看已生成结果';
    const container = document.querySelector('.progress-container');
    container?.appendChild(viewBtn);
  }
  viewBtn.addEventListener('click', () => {
    import('./gallery.js').then(m => {
      m.loadResult(productId, selectedSteps, data);
    });
  });
}
```

Also update the existing error handler to disable the abort button:

```javascript
if (data.status === 'error') {
  console.log('[progress] SSE error, closing');
  evtSource.close();
  showError(data.message || '未知错误');
  const abortBtn = document.getElementById('abort-btn');
  if (abortBtn) {
    abortBtn.disabled = true;
    abortBtn.textContent = '中止生成';
  }
  return;
}
```

And disable abort button on completion:

```javascript
if (data.status === 'completed' && data.progress === 100) {
  console.log('[progress] SSE final completed, closing');
  evtSource.close();
  const abortBtn = document.getElementById('abort-btn');
  if (abortBtn) {
    abortBtn.disabled = true;
    abortBtn.textContent = '完成';
  }
  setTimeout(() => {
    import('./gallery.js').then(m => {
      m.loadResult(productId, selectedSteps, data);
    }).catch(err => {
      console.error('[progress] failed to load gallery:', err);
    });
  }, 500);
}
```

- [ ] **Step 4: Run tests**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 54 passed

- [ ] **Step 5: Commit**

```bash
git add src/coupangads/web/templates/index.html src/coupangads/web/static/css/components.css src/coupangads/web/static/js/progress.js
git commit -m "feat(abort): add frontend abort button and handling"
```

---

### Task 4: Add abort endpoint test

**Files:**
- Modify: `tests/test_web_api.py`

- [ ] **Step 1: Add abort endpoint test**

Append to `tests/test_web_api.py`:

```python
def test_abort_endpoint() -> None:
    from coupangads.web.api import _set_abort_flag

    response = client.post("/api/abort/test-abort-prod")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "abort_requested"
    assert data["product_id"] == "test-abort-prod"
```

- [ ] **Step 2: Run tests**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest tests/test_web_api.py::test_abort_endpoint -v`
Expected: PASS

- [ ] **Step 3: Run full suite**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 55 passed

- [ ] **Step 4: Commit**

```bash
git add tests/test_web_api.py
git commit -m "test(abort): add abort endpoint test"
```

---

### Task 5: Manual verification with mock mode

**Files:**
- None

- [ ] **Step 1: Restart service**

```bash
cd .worktrees/mvp-v1.0
./stop-service.bat || taskkill /F /IM uvicorn.exe 2>/dev/null || true
source venv/Scripts/activate
uvicorn coupangads.web.app:app --host 127.0.0.1 --port 8080
```

- [ ] **Step 2: Configure mock and start generation**

Open `http://127.0.0.1:8080`, set Text/Image providers to Mock, upload images, click 开始生成.

- [ ] **Step 3: Test abort**

- Wait for one or two steps to complete
- Click「中止生成」
- Verify status becomes「已中止」
- Verify preview cards remain
- Click「查看已生成结果」to go to result page

- [ ] **Step 4: Test normal completion**

- Start a new generation without aborting
- Verify it completes normally and transitions to result page

- [ ] **Step 5: Run full test suite**

Run: `cd .worktrees/mvp-v1.0 && source venv/Scripts/activate && pytest -q`
Expected: 55 passed

---

## Self-Review

### Spec coverage

- Abort flag storage and endpoint → Task 1
- Pipeline checks between steps → Task 2
- Frontend button and handling → Task 3
- Test coverage → Task 4

### Placeholder scan

- No TBD/TODO
- All code blocks complete

### Type consistency

- `abort_callback` signature consistent between `api.py` and `pipeline.py`
- `GenerationAborted` exception used consistently

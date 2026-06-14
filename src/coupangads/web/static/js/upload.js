/**
 * 上传/编辑产品视图：渲染进 canvas 容器。
 *
 * 导出：
 *   renderCreateWorkspace(container, { onStart }) -> cleanup
 *   renderEditWorkspace(container, { productId, onSaved }) -> cleanup
 *
 * 原有 initUpload 仍保留以兼容旧测试入口，但内部已委托给 render*Workspace。
 */

const UPLOAD_HTML = `
  <div class="upload-workspace">
    <label class="upload-field">
      <span class="upload-field__label">产品名称</span>
      <input type="text" class="upload-name-input" placeholder="例如：dog-harness-001" value="">
    </label>
    <div class="upload-zone" data-el="zone">
      <div class="upload-icon">📁</div>
      <h2>拖拽产品图到这里</h2>
      <p class="subtitle">支持 JPG / PNG / HEIC / WEBP，建议 3-10 张</p>
      <input type="file" class="upload-file-input" multiple accept="image/*" hidden>
    </div>
    <div class="thumbnail-grid" data-el="grid"></div>

    <div class="step-options" data-el="steps">
      <div class="step-options-header">
        <h3>生成选项</h3>
        <button type="button" class="link-button" data-el="toggle">取消全选</button>
      </div>
      <label class="step-option"><input type="checkbox" value="product_report" checked> 商品画像</label>
      <label class="step-option"><input type="checkbox" value="title" checked> 标题</label>
      <label class="step-option"><input type="checkbox" value="keywords" checked> 关键词</label>
      <label class="step-option"><input type="checkbox" value="selling_points" checked> 卖点文案</label>
      <label class="step-option"><input type="checkbox" value="instagram" checked> INS 文案</label>
      <label class="step-option"><input type="checkbox" value="images" checked> 详情页图片</label>
    </div>

    <button class="primary-button" data-el="start">开始生成</button>
  </div>
`;

/**
 * @param {HTMLElement} container
 * @param {object} options { mode: 'create'|'edit', productId?, onStart?, onSaved? }
 * @returns {() => void} cleanup function
 */
function renderUpload(container, options = {}) {
  const onStart = options.onStart || (() => {});
  const onSaved = options.onSaved || (() => {});
  const mode = options.mode || 'create';
  const productId = options.productId || null;

  container.innerHTML = UPLOAD_HTML;

  const zone = container.querySelector('[data-el="zone"]');
  const input = container.querySelector('[data-el="zone"] .upload-file-input');
  const grid = container.querySelector('[data-el="grid"]');
  const startBtn = container.querySelector('[data-el="start"]');
  const toggleBtn = container.querySelector('[data-el="toggle"]');
  const nameInput = container.querySelector('.upload-name-input');
  const stepsContainer = container.querySelector('[data-el="steps"]');

  let files = [];
  let objectUrls = [];
  let existingFiles = [];
  let keepFiles = new Set();
  let productData = null;
  let destroyed = false;

  function updateToggleLabel() {
    const all = container.querySelectorAll('.step-option input');
    const checked = container.querySelectorAll('.step-option input:checked');
    if (!toggleBtn) return;
    toggleBtn.textContent = all.length === checked.length ? '取消全选' : '全选';
  }

  function onToggleSteps() {
    const all = container.querySelectorAll('.step-option input');
    const checked = container.querySelectorAll('.step-option input:checked');
    const shouldCheck = checked.length !== all.length;
    all.forEach(cb => cb.checked = shouldCheck);
    updateToggleLabel();
  }

  function onZoneClick() {
    input?.click();
  }

  function onInputChange(e) {
    if (e.target.files?.length) {
      handleFiles(e.target.files);
      e.target.value = '';
    }
  }

  function onZoneDragOver(e) {
    e.preventDefault();
    zone?.classList.add('dragover');
  }

  function onZoneDragLeave() {
    zone?.classList.remove('dragover');
  }

  function onZoneDrop(e) {
    e.preventDefault();
    zone?.classList.remove('dragover');
    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files);
    }
  }

  async function onStartClick() {
    if (destroyed) return;
    if (mode === 'create' && files.length === 0) return alert('请先上传图片');
    if (mode === 'edit' && files.length === 0 && keepFiles.size === 0) return alert('请至少保留一张图片');

    startBtn.disabled = true;
    const originalText = startBtn.textContent;
    startBtn.textContent = mode === 'edit' ? '保存中...' : '上传中...';

    try {
      const productName = nameInput.value.trim() || `prod-${Date.now()}`;

      if (mode === 'edit') {
        await saveEdit(productName);
      } else {
        await createProduct(productName);
      }
    } catch (err) {
      alert(err.message);
      startBtn.disabled = false;
      startBtn.textContent = originalText;
    }
  }

  async function createProduct(productName) {
    const formData = new FormData();
    formData.append('product_name', productName);
    files.forEach(f => formData.append('files', f));

    const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
    if (!uploadRes.ok) {
      const data = await uploadRes.json().catch(() => ({}));
      throw new Error(data.detail || '上传失败');
    }

    const steps = Array.from(container.querySelectorAll('.step-option input:checked')).map(i => i.value);
    const genRes = await fetch(`/api/generate/${encodeURIComponent(productName)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steps }),
    });
    if (!genRes.ok) {
      const data = await genRes.json().catch(() => ({}));
      throw new Error(data.detail || '生成任务启动失败');
    }

    onStart(productName, steps);
  }

  async function saveEdit(productName) {
    const formData = new FormData();
    formData.append('product_name', productName);
    keepFiles.forEach((filename) => {
      formData.append('keep_files', filename);
    });
    files.forEach(f => formData.append('files', f));

    const res = await fetch(`/api/products/${encodeURIComponent(productId)}`, {
      method: 'PUT',
      body: formData,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || '保存失败');
    }
    const data = await res.json();
    onSaved(data.new_product_id || productId);
  }

  function handleFiles(fileList) {
    if (destroyed) return;
    files = [...files, ...Array.from(fileList)];
    renderThumbnails();
  }

  function removeFile(idx) {
    files = files.filter((_, i) => i !== idx);
    renderThumbnails();
  }

  function removeExisting(filename) {
    keepFiles.delete(filename);
    renderThumbnails();
  }

  function renderThumbnails() {
    if (destroyed) return;
    objectUrls.forEach(url => URL.revokeObjectURL(url));
    objectUrls = [];

    const existingHtml = existingFiles.map((file) => {
      const isKept = keepFiles.has(file.filename);
      if (!isKept) return '';
      return `
        <div class="thumb-wrapper thumb-wrapper--existing">
          <img src="${file.url}" class="thumbnail" alt="${file.filename}">
          <button type="button" data-existing="${file.filename}" class="remove-btn">×</button>
        </div>
      `;
    }).join('');

    const newHtml = files.map((file, idx) => {
      const url = URL.createObjectURL(file);
      objectUrls.push(url);
      return `
        <div class="thumb-wrapper">
          <img src="${url}" class="thumbnail" alt="${file.name}">
          <button type="button" data-idx="${idx}" class="remove-btn">×</button>
        </div>
      `;
    }).join('');

    grid.innerHTML = existingHtml + newHtml;

    grid.querySelectorAll('[data-idx]').forEach(btn => {
      btn.addEventListener('click', () => removeFile(parseInt(btn.dataset.idx, 10)));
    });
    grid.querySelectorAll('[data-existing]').forEach(btn => {
      btn.addEventListener('click', () => removeExisting(btn.dataset.existing));
    });
  }

  async function loadProduct() {
    if (mode !== 'edit' || !productId || destroyed) return;
    try {
      const res = await fetch('/api/products');
      const data = await res.json();
      productData = (data.products || []).find((p) => p.product_id === productId);
      if (!productData) {
        alert('商品不存在');
        onSaved(null);
        return;
      }
      nameInput.value = productData.name;
      existingFiles = productData.input_files || [];
      existingFiles.forEach((f) => keepFiles.add(f.filename));
      renderThumbnails();

      stepsContainer?.classList.add('hidden');
      startBtn.textContent = '保存修改';
    } catch (err) {
      console.error('[upload] failed to load product:', err);
      alert('加载商品信息失败');
    }
  }

  function bind() {
    toggleBtn?.addEventListener('click', onToggleSteps);
    container.querySelectorAll('.step-option input').forEach(cb => {
      cb.addEventListener('change', updateToggleLabel);
    });
    zone?.addEventListener('click', onZoneClick);
    input?.addEventListener('change', onInputChange);
    zone?.addEventListener('dragover', onZoneDragOver);
    zone?.addEventListener('dragleave', onZoneDragLeave);
    zone?.addEventListener('drop', onZoneDrop);
    startBtn?.addEventListener('click', onStartClick);
  }

  function destroy() {
    destroyed = true;
    toggleBtn?.removeEventListener('click', onToggleSteps);
    container.querySelectorAll('.step-option input').forEach(cb => {
      cb.removeEventListener('change', updateToggleLabel);
    });
    zone?.removeEventListener('click', onZoneClick);
    input?.removeEventListener('change', onInputChange);
    zone?.removeEventListener('dragover', onZoneDragOver);
    zone?.removeEventListener('dragleave', onZoneDragLeave);
    zone?.removeEventListener('drop', onZoneDrop);
    startBtn?.removeEventListener('click', onStartClick);
    objectUrls.forEach(url => URL.revokeObjectURL(url));
    objectUrls = [];
  }

  bind();
  loadProduct();

  return destroy;
}

export function renderCreateWorkspace(container, options = {}) {
  return renderUpload(container, { mode: 'create', ...options });
}

export function renderEditWorkspace(container, options = {}) {
  return renderUpload(container, { mode: 'edit', ...options });
}

// 兼容旧入口：原 initUpload(options) 行为
export function initUpload(options = {}) {
  // 仅作为 fallback，正常工作台流程不会走到这里
  const container = document.createElement('div');
  document.body.appendChild(container);
  return renderUpload(container, options);
}

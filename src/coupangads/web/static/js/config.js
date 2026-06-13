export async function initConfigPanel() {
  const modal = document.getElementById('config-modal');
  if (!modal) return;

  // 清理旧的 document 级监听器，防止重复绑定
  if (modal.__closeController) {
    modal.__closeController.abort();
  }

  // 克隆并替换 modal 节点，清除已绑定的事件监听
  const cleanModal = modal.cloneNode(true);
  modal.parentNode.replaceChild(cleanModal, modal);

  // 克隆并替换 config-btn，防止重复绑定点击事件
  const btn = document.getElementById('config-btn');
  if (!btn) return;
  const cleanBtn = btn.cloneNode(true);
  btn.parentNode.replaceChild(cleanBtn, btn);

  const form = cleanModal.querySelector('#config-form');
  if (!form) return;

  // Open / close
  cleanBtn.addEventListener('click', () => {
    clearTimeout(cleanModal.__closeTimeout);
    cleanModal.classList.remove('is-closing', 'hidden');
  });
  cleanModal.querySelector('.modal-backdrop')?.addEventListener('click', () => {
    closeModal(cleanModal);
  });
  const closeController = new AbortController();
  cleanModal.__closeController = closeController;
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !cleanModal.classList.contains('hidden')) {
      closeModal(cleanModal);
    }
  }, { signal: closeController.signal });

  // Provider switching
  cleanModal.querySelectorAll('.segmented-control__btn').forEach((button) => {
    button.addEventListener('click', () => {
      const target = button.dataset.target;
      const provider = button.dataset.provider;
      setProvider(target, provider);
    });
  });

  // Load current config
  const statusRes = await fetch('/api/config');
  const status = await statusRes.json();

  updateStatusLabel('gemini-status', status.gemini_configured);
  updateStatusLabel('gemini-status-image', status.gemini_configured);
  updateStatusLabel('doubao-status', status.doubao_configured);
  updateStatusLabel('deepseek-status', status.deepseek_configured);

  const textProvider = status.text_provider || 'gemini';
  const imageProvider = status.image_provider || 'gemini';
  setProvider('text', textProvider);
  setProvider('image', imageProvider);

  const deepseekModelInput = document.getElementById('deepseek-model');
  if (deepseekModelInput) {
    deepseekModelInput.value = status.deepseek_model || 'deepseek-v4-pro';
  }

  setPlaceholder('gemini-key', status.gemini_configured);
  setPlaceholder('image-gemini-key', status.gemini_configured);
  setPlaceholder('doubao-key', status.doubao_configured);
  setPlaceholder('deepseek-key', status.deepseek_configured);

  // 同步两个 Gemini key 输入框
  const geminiKeyInput = document.getElementById('gemini-key');
  const imageGeminiKeyInput = document.getElementById('image-gemini-key');
  if (geminiKeyInput && imageGeminiKeyInput) {
    geminiKeyInput.addEventListener('input', () => {
      imageGeminiKeyInput.value = geminiKeyInput.value;
    });
    imageGeminiKeyInput.addEventListener('input', () => {
      geminiKeyInput.value = imageGeminiKeyInput.value;
    });
  }

  // Save
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const payload = {
      text_provider: getActiveProvider('text'),
      image_provider: getActiveProvider('image'),
      gemini_api_key:
        formData.get('gemini_api_key') ||
        formData.get('image_gemini_api_key') ||
        '',
      doubao_api_key: formData.get('doubao_api_key') || '',
      deepseek_api_key: formData.get('deepseek_api_key') || '',
      deepseek_model: formData.get('deepseek_model') || 'deepseek-v4-pro',
    };

    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    await closeModal(cleanModal);
    initConfigPanel();
  });
}

function closeModal(modal) {
  clearTimeout(modal.__closeTimeout);
  if (modal.classList.contains('hidden')) {
    return Promise.resolve();
  }
  modal.classList.add('is-closing');
  return new Promise((resolve) => {
    modal.__closeTimeout = setTimeout(() => {
      modal.classList.add('hidden');
      modal.classList.remove('is-closing');
      resolve();
    }, 300);
  });
}

function updateStatusLabel(elementId, configured) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = configured ? '已配置' : '未配置';
  el.classList.toggle('config-status--configured', configured);
  el.classList.toggle('config-status--unconfigured', !configured);
}

function setProvider(target, provider) {
  // Update buttons
  const buttons = document.querySelectorAll(
    `.segmented-control__btn[data-target="${target}"]`
  );
  buttons.forEach((btn) => {
    const isActive = btn.dataset.provider === provider;
    btn.classList.toggle('is-active', isActive);
    btn.setAttribute('aria-pressed', String(isActive));
  });

  const card = document.querySelector(`.config-card[data-config-group="${target}"]`);
  if (!card) return;

  const allFields = card.querySelectorAll('.config-fields');
  const activeKey = `${target}-${provider}`;
  const activeFields = card.querySelector(`[data-fields-for="${activeKey}"]`);

  // Fade out currently visible fields
  allFields.forEach((field) => {
    if (!field.classList.contains('hidden') && field !== activeFields) {
      field.classList.add('is-hiding');
      setTimeout(() => {
        field.classList.add('hidden');
        field.classList.remove('is-hiding');
      }, 200);
    }
  });

  // Show active fields
  if (activeFields) {
    activeFields.classList.remove('hidden', 'is-hiding');
  }
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

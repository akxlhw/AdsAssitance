export async function initConfigPanel() {
  const btn = document.getElementById('config-btn');
  const modal = document.getElementById('config-modal');
  const form = document.getElementById('config-form');
  if (!btn || !modal || !form) return;

  const statusRes = await fetch('/api/config');
  const status = await statusRes.json();
  document.getElementById('gemini-status').textContent =
    status.gemini_configured ? '已配置' : '未配置';
  document.getElementById('doubao-status').textContent =
    status.doubao_configured ? '已配置' : '未配置';
  document.getElementById('default-provider').value = status.default_provider;

  btn.addEventListener('click', () => modal.classList.remove('hidden'));
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const geminiKey = document.getElementById('gemini-key').value;
    const doubaoKey = document.getElementById('doubao-key').value;
    const provider = document.getElementById('default-provider').value;

    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gemini_api_key: geminiKey,
        doubao_api_key: doubaoKey,
        default_provider: provider,
      }),
    });

    modal.classList.add('hidden');
    initConfigPanel();
  });
}

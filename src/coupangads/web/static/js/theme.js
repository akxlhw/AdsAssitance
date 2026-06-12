const THEME_KEY = 'coupangads-theme';
const THEMES = [
  'korean-minimal',
  'editorial',
  'warm-healing',
  'dark-industrial',
  'retro-film',
  'cyber-neon',
];

export function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || 'korean-minimal';
  setTheme(saved);
  populateThemeSelector();
}

export function setTheme(theme) {
  if (!THEMES.includes(theme)) return;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
}

function populateThemeSelector() {
  const select = document.getElementById('theme-select');
  if (!select) return;
  select.innerHTML = THEMES.map(t =>
    `<option value="${t}">${themeLabel(t)}</option>`
  ).join('');
  select.value = document.documentElement.getAttribute('data-theme');
  select.addEventListener('change', (e) => setTheme(e.target.value));
}

function themeLabel(id) {
  const labels = {
    'korean-minimal': '韩系极简高级',
    'editorial': '编辑杂志风',
    'warm-healing': '温暖治愈风',
    'dark-industrial': '暗色工业风',
    'retro-film': '复古胶片风',
    'cyber-neon': '赛博荧光风',
  };
  return labels[id] || id;
}

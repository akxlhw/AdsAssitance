import { initTheme } from './theme.js';
import { initConfigPanel } from './config.js';
import { initUpload } from './upload.js';
import { startProgress } from './progress.js';

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initConfigPanel();
  initUpload((productId) => {
    startProgress(productId);
  });
});

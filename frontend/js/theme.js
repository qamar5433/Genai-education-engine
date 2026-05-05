/* ── GENAI EDUCANTION ENGINE Theme Manager ── */
const Theme = {
  init() {
    const saved = localStorage.getItem('qg_theme') || 'light';
    this.apply(saved);
  },
  toggle() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    this.apply(next);
    localStorage.setItem('qg_theme', next);
  },
  apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) {
      btn.querySelector('.material-symbols-outlined').textContent =
        theme === 'dark' ? 'light_mode' : 'dark_mode';
      btn.title = theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    }
  }
};
// Auto-init on load
Theme.init();

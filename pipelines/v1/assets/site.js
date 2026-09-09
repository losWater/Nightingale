const root = document.documentElement;
const themeButton = document.querySelector('#theme');
function setTheme(theme) {
  root.dataset.theme = theme;
  themeButton.textContent = theme === 'light' ? '☾' : '☼';
  themeButton.setAttribute('aria-label', theme === 'light' ? '切换至深色模式' : '切换至浅色模式');
}
try { setTheme(localStorage.getItem('nightingale-theme') === 'light' ? 'light' : 'dark'); }
catch { setTheme('dark'); }
themeButton.addEventListener('click', () => {
  const theme = root.dataset.theme === 'light' ? 'dark' : 'light';
  setTheme(theme);
  try { localStorage.setItem('nightingale-theme', theme); } catch { /* Storage can be disabled. */ }
});

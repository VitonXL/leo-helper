// === СМЕНА ТЕМЫ ===
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  const newTheme = isDark ? 'light' : 'dark';
  
  html.setAttribute('data-theme', newTheme);
  const themeIcon = document.getElementById('theme-icon');
  if (themeIcon) {
    themeIcon.textContent = isDark ? 'light_mode' : 'dark_mode';
  }

  localStorage.setItem('theme', newTheme);
  document.cookie = `theme=${newTheme}; path=/; max-age=31536000`;
}

// === СКРЫТИЕ ШАПКИ ПРИ СКРОЛЛЕ ===
let lastScroll = 0;
const header = document.getElementById('combined-header');
if (header) {
  window.addEventListener('scroll', () => {
    const current = window.scrollY;
    if (current > 100 && current > lastScroll) {
      header.classList.add('hidden');
    } else if (current < lastScroll && current > 50) {
      header.classList.remove('hidden');
    }
    lastScroll = current;
  });
}

// === TOAST ===
window.Toast = {
  show: (msg, type = 'info') => {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.className = `toast show ${type}`;
    setTimeout(() => { toast.className = 'toast'; }, 3000);
  },
  info: (msg) => Toast.show(msg, 'info'),
  success: (msg) => Toast.show(msg, 'success'),
  warning: (msg) => Toast.show(msg, 'warning'),
  error: (msg) => Toast.show(msg, 'error')
};

// === ИНИЦИАЛИЗАЦИЯ ===
document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = 
    document.cookie.match(/theme=([^;]+)/)?.[1] || 
    localStorage.getItem('theme') || 
    'light';

  document.documentElement.setAttribute('data-theme', savedTheme);
  const themeIcon = document.getElementById('theme-icon');
  if (themeIcon) {
    themeIcon.textContent = savedTheme === 'dark' ? 'light_mode' : 'dark_mode';
  }

  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
  }
});
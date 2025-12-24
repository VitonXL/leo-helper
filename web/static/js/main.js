// === Смена темы ===
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  const newTheme = isDark ? 'light' : 'dark';
  
  html.setAttribute('data-theme', newTheme);
  document.getElementById('theme-icon').textContent = isDark ? 'light_mode' : 'dark_mode';
  
  localStorage.setItem('theme', newTheme);
  document.cookie = `theme=${newTheme}; path=/; max-age=31536000`;
}

// === Скрытие шапки ===
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

// === Toast ===
window.Toast = {
  show: (msg) => {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'show';
    setTimeout(() => { toast.className = ''; }, 3000);
  },
  info: (msg) => Toast.show(msg),
  success: (msg) => Toast.show(msg),
  warning: (msg) => Toast.show(msg),
  error: (msg) => Toast.show(msg)
};

// === Инициализация ===
document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = 
    document.cookie.match(/theme=([^;]+)/)?.[1] || 
    localStorage.getItem('theme') || 
    'light';
  
  document.documentElement.setAttribute('data-theme', savedTheme);
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.textContent = savedTheme === 'dark' ? 'light_mode' : 'dark_mode';
  }

  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
  }
});
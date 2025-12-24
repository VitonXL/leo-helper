// 🛠️ Гарантированная инициализация
document.addEventListener('DOMContentLoaded', () => {
  console.log('✅ DOM загружен, инициализация main.js');

  // --- Смена темы ---
  const themeToggle = document.getElementById('theme-toggle');
  const themeIcon = document.getElementById('theme-icon');
  const html = document.documentElement;

  if (!themeToggle || !themeIcon) {
    console.warn('⚠️ Элементы темы не найдены: #theme-toggle или #theme-icon');
    return;
  }

  // Восстановление темы
  const savedTheme =
    (document.cookie.match(/theme=([^;]+)/) || [])[1] ||
    localStorage.getItem('theme') ||
    'light';

  html.setAttribute('data-theme', savedTheme);
  themeIcon.textContent = savedTheme === 'dark' ? 'light_mode' : 'dark_mode';

  // Переключение
  themeToggle.onclick = () => {
    const isDark = html.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    themeIcon.textContent = isDark ? 'dark_mode' : 'light_mode';
    localStorage.setItem('theme', newTheme);
    document.cookie = `theme=${newTheme}; path=/; max-age=31536000`;
    console.log(`🌙 Тема изменена: ${newTheme}`);
  };

  // --- Скрытие шапки при скролле ---
  const header = document.getElementById('combined-header');
  let lastScroll = 0;

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

  // --- Кнопка меню ---
  const menuBtn = document.getElementById('menu-btn');
  if (menuBtn) {
    menuBtn.onclick = () => {
      console.log('☰ Меню нажато');
      // Здесь можно добавить открытие бокового меню
      Toast.info("Меню пока не реализовано, но работает!");
    };
  } else {
    console.warn('⚠️ #menu-btn не найден');
  }

  // --- Toast ---
  window.Toast = {
    show: (msg) => {
      const toast = document.getElementById('toast');
      if (!toast) return;
      toast.textContent = msg;
      toast.className = 'show';
      setTimeout(() => {
        toast.className = '';
      }, 3000);
    },
    info: (msg) => Toast.show(msg),
    success: (msg) => Toast.show(msg),
    warning: (msg) => Toast.show(msg),
    error: (msg) => Toast.show(msg)
  };
});
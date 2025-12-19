// web/static/script.js — ЧИСТЫЙ UTF-8, БЕЗ КИРИЛЛИЦЫ

document.addEventListener('DOMContentLoaded', function () {
  console.log('✅ DOM загружен');

  // === Навигация ===
  window.navigateTo = function (screen) {
  // Сначала скрываем ВСЕ экраны и убираем active
  document.querySelectorAll('.screen').forEach(s => {
    s.classList.remove('active');
    s.style.display = 'none';
  });

  // Потом показываем нужный
  const nextScreen = document.getElementById(screen + '-screen');
  if (nextScreen) {
    nextScreen.style.display = 'flex';
    // Ждём, пока отобразится, потом добавим анимацию
    setTimeout(() => {
      nextScreen.classList.add('active');
    }, 10);
  }
};

  window.navigateBack = function () {
    navigateTo('dashboard');
  };

  // === Боковое меню ===
  window.toggleSidebar = function () {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.overlay');
    if (sidebar && overlay) {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('active');
    }
  };

  // === QR-модалка ===
  window.openQRModal = function () {
    const modal = document.getElementById('qr-modal');
    if (modal) modal.style.display = 'flex';
  };

  window.closeQRModal = function () {
    const modal = document.getElementById('qr-modal');
    if (modal) modal.style.display = 'none';
  };

  // === Язык (временно без кириллицы) ===
  window.setLang = function (lang) {
    alert('Language: ' + lang);
  };

  // === Смена темы ===
  const themeToggle = document.createElement('button');
  themeToggle.className = 'btn primary';
  themeToggle.style.marginTop = '20px';

  function updateThemeButton() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    themeToggle.textContent = currentTheme === 'light' ? '🌙 Dark mode' : '☀️ Light mode';
  }

  window.toggleTheme = function () {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    updateThemeButton();

    document.cookie = `theme=${newTheme}; path=/; max-age=31536000`;

    const urlParams = new URLSearchParams(window.location.search);
    const user_id = urlParams.get('user_id');
    const hash = urlParams.get('hash');

    if (user_id && hash) {
      fetch('/api/set-theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: parseInt(user_id), theme: newTheme, hash })
      }).catch(console.warn);
    }
  };

  themeToggle.addEventListener('click', toggleTheme);

  // Добавляем кнопку в профиль
  const profileMain = document.querySelector('.profile-main');
  if (profileMain) {
    profileMain.appendChild(themeToggle);
  }

  // Восстанавливаем тему
  const savedTheme = getCookie('theme') || document.documentElement.getAttribute('data-theme');
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeButton();

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  // === Оффлайн-бар ===
  const offlineBar = document.getElementById('offline-bar');
  if (offlineBar) {
    window.addEventListener('offline', () => offlineBar.style.display = 'block');
    window.addEventListener('online', () => offlineBar.style.display = 'none');
    if (!navigator.onLine) offlineBar.style.display = 'block';
  }

  // === Авторизация ===
  window.startAuth = function () {
    console.log('🔥 startAuth: started');
    const urlParams = new URLSearchParams(window.location.search);
    const user_id = urlParams.get('user_id');
    const hash = urlParams.get('hash');

    if (!user_id || !hash) {
      alert('❌ Invalid link. Open from bot.');
      return;
    }

    console.log('🔍 Fetching user:', user_id);
    fetch(`/api/user/${user_id}`)
      .then(res => {
        if (!res.ok) throw new Error('Network error');
        return res.json();
      })
      .then(data => {
        console.log('✅ Data received:', data);

        const update = (id, value) => {
          const el = document.getElementById(id);
          if (el) el.textContent = value;
        };

        update('user-name', data.first_name || 'User');
        update('user-username', data.username ? '@' + data.username : 'no username');
        update('user-id', data.id);
        update('referrals', data.referrals || 0);
        update('premium-status', data.is_premium ? 'Premium' : 'Free');

        const photo = document.getElementById('profile-photo');
        if (photo) {
          photo.textContent = (data.first_name || '?')[0].toUpperCase();
        }

        const theme = data.theme || 'light';
        document.documentElement.setAttribute('data-theme', theme);
        updateThemeButton();

        navigateTo('dashboard');
      })
      .catch(err => {
        console.error('❌ Error:', err);
        alert('❌ Failed to load data');
      });
  };

  // === Премиум ===
  window.buyPremium = function () {
    alert('💳 Premium coming soon!');
  };

  console.log('✅ script.js: fully loaded');
});
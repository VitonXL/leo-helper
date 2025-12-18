// web/static/script.js — РАБОЧАЯ UTF-8 ВЕРСИЯ

function navigateTo(screen) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  setTimeout(() => {
    document.querySelectorAll('.screen').forEach(s => s.style.display = 'none');
    const screenElement = document.getElementById(screen + '-screen');
    if (screenElement) {
      screenElement.style.display = 'flex';
      setTimeout(() => screenElement.classList.add('active'), 10);
    }
  }, 300);
}

function navigateBack() { navigateTo('dashboard'); }

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.querySelector('.overlay');
  if (sidebar && overlay) {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');
  }
}

function openQRModal() {
  const modal = document.getElementById('qr-modal');
  if (modal) modal.style.display = 'flex';
}

function closeQRModal() {
  const modal = document.getElementById('qr-modal');
  if (modal) modal.style.display = 'none';
}

function setLang(lang) {
  alert('Язык изменён на: ' + lang);
}

// --- Синхронизация темы ---
const themeToggle = document.createElement('button');
themeToggle.className = 'btn primary';
themeToggle.style.marginTop = '20px';

function updateThemeButton() {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  themeToggle.textContent = currentTheme === 'light' ? '🌙 Включить тёмную' : '☀️ Включить светлую';
}

function toggleTheme() {
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
}

themeToggle.addEventListener('click', toggleTheme);

// Добавляем кнопку в профиль
document.addEventListener('DOMContentLoaded', () => {
  updateThemeButton();
  const profileMain = document.querySelector('.profile-main');
  if (profileMain) {
    profileMain.appendChild(themeToggle);
  }

  const savedTheme = getCookie('theme') || document.documentElement.getAttribute('data-theme');
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeButton();
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

// --- Оффлайн ---
const offlineBar = document.getElementById('offline-bar');
if (offlineBar) {
  window.addEventListener('offline', () => offlineBar.style.display = 'block');
  window.addEventListener('online', () => offlineBar.style.display = 'none');
  window.onload = () => { if (!navigator.onLine) offlineBar.style.display = 'block'; };
}

// --- Старт авторизации ---
function startAuth() {
  const urlParams = new URLSearchParams(window.location.search);
  const user_id = urlParams.get('user_id');
  const hash = urlParams.get('hash');

  if (!user_id || !hash) {
    alert('❌ Неверная ссылка. Откройте из бота.');
    return;
  }

  fetch(`/api/user/${user_id}`)
    .then(res => res.json())
    .then(data => {
      console.log('✅ Данные:', data);

      const update = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      };

      update('user-name', data.first_name || 'Пользователь');
      update('user-username', data.username ? '@' + data.username : 'не указан');
      update('user-id', data.id);
      update('referrals', data.referrals || 0);
      update('premium-status', data.is_premium ? 'Премиум' : 'Базовая');

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
      console.error('❌ Ошибка:', err);
      alert('❌ Не удалось загрузить данные');
    });
}

function buyPremium() {
  alert("💳 Премиум скоро! Ожидайте интеграцию.");
}

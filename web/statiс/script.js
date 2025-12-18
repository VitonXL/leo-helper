// web/static/script.js

function navigateTo(screen) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  setTimeout(() => {
    document.querySelectorAll('.screen').forEach(s => s.style.display = 'none');
    document.getElementById(screen + '-screen').style.display = 'flex';
    setTimeout(() => document.getElementById(screen + '-screen').classList.add('active'), 10);
  }, 300);
}

function navigateBack() { navigateTo('dashboard'); }

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.querySelector('.overlay');
  if (sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
  } else {
    sidebar.classList.add('open');
    overlay.classList.add('active');
  }
}

function openQRModal() { document.getElementById('qr-modal').style.display = 'flex'; }
function closeQRModal() { document.getElementById('qr-modal').style.display = 'none'; }

function setLang(lang) {
  alert('Язык будет изменён на: ' + lang);
  // Можно добавить /api/set-lang позже
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

  // Сохраняем в куку
  document.cookie = `theme=${newTheme}; path=/; max-age=31536000`;

  // Обновляем в БД
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
  if (profileMain) profileMain.appendChild(themeToggle);

  const savedTheme = getCookie('theme') || document.documentElement.getAttribute('data-theme');
  document.documentElement.setAttribute('data-theme', savedTheme);
  document.getElementById('current-theme').textContent = savedTheme;
  updateThemeButton();
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

// --- Оффлайн ---
const offlineBar = document.getElementById('offline-bar');
window.addEventListener('offline', () => offlineBar.style.display = 'block');
window.addEventListener('online',  () => offlineBar.style.display = 'none');
window.onload = () => { if (!navigator.onLine) offlineBar.style.display = 'block'; };

function buyPremium() {
  alert("💎 Премиум скоро! Ожидайте интеграцию с платежами.");
}

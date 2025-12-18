// web/static/script.js

let USER_DATA = null;

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
  sidebar.classList.toggle('open');
  overlay.classList.toggle('active');
}

function openQRModal() { document.getElementById('qr-modal').style.display = 'flex'; }
function closeQRModal() { document.getElementById('qr-modal').style.display = 'none'; }

function setLang(lang) {
  alert('Язык изменён на: ' + lang);
}

function buyPremium() {
  alert("💳 Премиум скоро! Ожидайте интеграцию.");
}

// === Старт авторизации ===
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
      USER_DATA = data;

      document.getElementById('user-name').textContent = data.first_name;
      document.getElementById('user-username').textContent = data.username ? '@' + data.username : 'не указан';
      document.getElementById('user-id').textContent = data.id;
      document.getElementById('referrals').textContent = data.referrals;
      document.getElementById('profile-photo').textContent = data.first_name[0]?.toUpperCase() || '?';

      const theme = data.theme || 'light';
      document.documentElement.setAttribute('data-theme', theme);
      document.getElementById('current-theme').textContent = theme === 'light' ? 'Светлая' : 'Тёмкая';

      document.getElementById('premium-status').textContent = data.is_premium ? 'Премиум' : 'Базовая';

      navigateTo('dashboard');
    })
    .catch(err => {
      console.error(err);
      alert('❌ Ошибка загрузки данных');
    });
}

// === Оффлайн ===
const offlineBar = document.getElementById('offline-bar');
window.addEventListener('offline', () => offlineBar.style.display = 'block');
window.addEventListener('online',  () => offlineBar.style.display = 'none');
window.onload = () => { if (!navigator.onLine) offlineBar.style.display = 'block'; };
};

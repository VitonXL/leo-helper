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

function setLang(lang) { alert('Язык изменён на: ' + lang); }

const tg = window.Telegram?.WebApp;

async function loadCurrency() {
  try {
    const res = await fetch('https://www.cbr-xml-daily.ru/latest.js');
    const data = await res.json();
    return data.rates.USD.toFixed(2);
  } catch (e) { return 'ошибка'; }
}

async function loadWeather() {
  const key = 'ВАШ_КЛЮЧ';
  const url = `https://api.openweathermap.org/data/2.5/weather?q=Moscow&lang=ru&units=metric&appid=${key}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    const temp = Math.round(data.main.temp);
    const desc = data.weather[0].description;
    return `${temp}°C, ${desc}`;
  } catch (e) { return 'ошибка'; }
}

async function loadData() {
  const usd = await loadCurrency();
  const weather = await loadWeather();
  document.getElementById('data-container').innerHTML = `
    <h2>📈 Главный экран</h2>
    <p><strong>Курс USD:</strong> ${usd} ₽</p>
    <p><strong>Погода в Москве:</strong> ${weather}</p>
  `;
}

function initProfile() {
  if (tg) {
    tg.ready();
    const user = tg.initDataUnsafe.user;
    if (user) {
      document.getElementById('user-name').textContent = user.first_name + (user.last_name ? ' ' + user.last_name : '');
      document.getElementById('user-username').textContent = user.username ? '@' + user.username : '-';
      document.getElementById('user-id').textContent = user.id;
      const photo = document.getElementById('profile-photo');
      photo.innerHTML = '';
      const img = document.createElement('img');
      img.src = `https://t.me/i/userpic/320/${user.username}.jpg`;
      img.style.width = '100%';
      img.style.height = '100%';
      img.style.borderRadius = '50%';
      img.style.objectFit = 'cover';
      img.onerror = () => photo.textContent = user.first_name[0].toUpperCase();
      photo.appendChild(img);
    }
  } else {
    document.getElementById('user-name').textContent = 'Тест Пользователь';
    document.getElementById('user-username').textContent = '@testuser';
    document.getElementById('user-id').textContent = '123456789';
  }
}

const offlineBar = document.getElementById('offline-bar');
window.addEventListener('offline', () => offlineBar.style.display = 'block');
window.addEventListener('online',  () => offlineBar.style.display = 'none');

window.onload = () => {
  loadData();
  initProfile();
  if (!navigator.onLine) offlineBar.style.display = 'block';
};
// web/static/js/admin.js
let statsData = {};
let usersList = [];
let currentChart = null;

document.addEventListener('DOMContentLoaded', async () => {
  console.log('✅ admin.js: загружен');
  await loadStats();
  await loadTickets();
  changeViewMode('cards');
});

// === Статистика ===
async function loadStats() {
  try {
    const res = await fetch('/api/admin/stats');
    statsData = await res.json();
    updateStatsDisplay();
  } catch (e) {
    console.error('❌ Ошибка загрузки статистики:', e);
    document.getElementById('stats-container').innerHTML = '<p>Не удалось загрузить данные</p>';
  }
}

function updateStatsDisplay() {
  const container = document.getElementById('stats-container');
  container.innerHTML = `
    <div class="stat-card">
      <h4>${statsData.total_users || 0}</h4>
      <p>Всего пользователей</p>
    </div>
    <div class="stat-card">
      <h4>${statsData.premium_users || 0}</h4>
      <p>Премиум</p>
    </div>
    <div class="stat-card">
      <h4>${statsData.active_today || 0}</h4>
      <p>Активно сегодня</p>
    </div>
  `;
}

// === Тикеты ===
async function loadTickets() {
  try {
    const res = await fetch('/api/admin/support-tickets');
    const tickets = await res.json();
    const container = document.getElementById('tickets-container');
    container.innerHTML = tickets.map(t => `
      <div class="ticket-item">
        <div><strong>🎫 ${t.ticket_id}</strong> | ${t.first_name} (@${t.username})</div>
        <p>${t.message}</p>
        <textarea id="reply-${t.ticket_id}" placeholder="Ответ..." style="width:100%; padding:8px"></textarea>
        <button onclick="sendReply('${t.ticket_id}')">Ответить</button>
      </div>
    `).join('');
  } catch (e) {
    console.error('❌ Ошибка загрузки тикетов:', e);
  }
}

async function sendReply(ticketId) {
  const textarea = document.getElementById(`reply-${ticketId}`);
  const text = textarea.value.trim();
  if (!text) return alert('Введите текст');
  await fetch('/api/admin/reply-ticket', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticket_id: ticketId, reply_text: text })
  });
  alert('✅ Ответ отправлен');
  loadTickets();
}
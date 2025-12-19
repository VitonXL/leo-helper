// web/static/js/finance.js

document.addEventListener('DOMContentLoaded', function () {
  // Инициализация при загрузке
  const financeScreen = document.getElementById('finance-screen');
  if (financeScreen) {
    initFinanceModule();
  }
});

function initFinanceModule() {
  // Привязка событий
  document.getElementById('profile-select')?.addEventListener('change', function () {
    renderFinanceOperations(this.value);
  });

  // Обновление при открытии экрана
  document.getElementById('finance-screen')?.addEventListener('click', function () {
    const profile = document.getElementById('profile-select').value;
    renderFinanceOperations(profile);
  });
}

window.addFinanceOperation = function () {
  const profile = document.getElementById('profile-select').value;
  const amount = parseFloat(document.getElementById('amount-input').value);
  const category = document.getElementById('category-select').value;
  const comment = document.getElementById('comment-input').value || 'Без цели';
  const time = document.getElementById('time-input').value || new Date().toISOString().slice(0, 16);

  if (isNaN(amount) || amount <= 0) {
    alert('Введите корректную сумму');
    return;
  }

  const operation = {
    profile,
    amount,
    category,
    comment,
    time: new Date(time).toLocaleString('ru-RU')
  };

  const operations = JSON.parse(localStorage.getItem('financeOperations') || '[]');
  operations.push(operation);
  localStorage.setItem('financeOperations', JSON.stringify(operations));

  renderFinanceOperations(profile);

  // Сброс формы
  document.getElementById('amount-input').value = '';
  document.getElementById('comment-input').value = '';
}

function renderFinanceOperations(currentProfile) {
  const list = document.getElementById('operations-list');
  const operations = JSON.parse(localStorage.getItem('financeOperations') || '[]');
  const filtered = operations.filter(op => op.profile === currentProfile);

  if (filtered.length === 0) {
    list.innerHTML = '<p style="color: #888; font-size: 14px;">Пока нет операций</p>';
    return;
  }

  list.innerHTML = '';
  filtered.reverse().forEach(op => {
    const item = document.createElement('div');
    item.style = `
      padding: 12px;
      background: ${op.category === 'income' ? 'rgba(76, 175, 80, 0.1)' : 'rgba(221, 57, 53, 0.1)'};
      border-left: 4px solid ${op.category === 'income' ? '#4CAF50' : '#DD3935'};
      border-radius: var(--radius-sm);
      font-size: 14px;
    `;
    item.innerHTML = `
      <strong style="color: ${op.category === 'income' ? '#4CAF50' : '#DD3935'}">
        ${op.category === 'income' ? '➕' : '➖'} ${op.amount} ₽
      </strong>
      <p style="margin: 5px 0;">${op.comment}</p>
      <small style="color: #888;">${op.time}</small>
    `;
    list.appendChild(item);
  });
}
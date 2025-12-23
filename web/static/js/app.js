// web/static/js/app.js
document.addEventListener("DOMContentLoaded", () => {
    console.log("✅ JS загружен");

    function updateGreeting() {
        const now = new Date();
        const hour = now.getHours();
        const greetingText = document.getElementById('greeting-text');
        const greetingIcon = document.getElementById('greeting-icon');

        if (hour >= 6 && hour < 12) {
            greetingText.textContent = 'Доброе утро!';
            greetingIcon.textContent = '🌤';
        } else if (hour >= 12 && hour < 18) {
            greetingText.textContent = 'Добрый день!';
            greetingIcon.textContent = '☀️';
        } else if (hour >= 18 && hour < 23) {
            greetingText.textContent = 'Добрый вечер!';
            greetingIcon.textContent = '🌆';
        } else {
            greetingText.textContent = 'Привет ночным!';
            greetingIcon.textContent = '🌙';
        }
    }

    updateGreeting();

    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
    }

    window.Toast = {
        show(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        },
        info(message) { this.show(message); }
    };
});
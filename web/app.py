# web/app.py
from flask import Flask, render_template_string, jsonify
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Путь к базе данных
DB_PATH = "bot.db"

# Простой HTML (можно позже заменить на шаблоны)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Leo Aide Bot — Админ-панель</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f7f7f7; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .card { background: #f0f8ff; padding: 15px; border-radius: 8px; text-align: center; }
        .card h3 { margin: 0; color: #0066cc; }
        .card p { margin: 10px 0 0; font-size: 1.2em; font-weight: bold; }
        .logs { font-size: 0.9em; background: #f8f8f8; padding: 15px; border-radius: 8px; max-height: 400px; overflow-y: auto; }
        .footer { margin-top: 40px; color: #888; font-size: 0.9em; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Leo Aide Bot — Админ-панель</h1>
        <div class="stats">
            <div class="card">
                <h3>Пользователи</h3>
                <p>{{ user_count }}</p>
            </div>
            <div class="card">
                <h3>Премиум</h3>
                <p>{{ premium_count }}</p>
            </div>
            <div class="card">
                <h3>Сегодня</h3>
                <p>{{ today_joined }}</p>
            </div>
        </div>

        <h2>📋 Последние действия</h2>
        <div class="logs">
            {% for log in logs %}
            <p><b>[{{ log['timestamp'] }}]</b> {{ log['user_id'] }} → {{ log['action'] }}</p>
            {% endfor %}
        </div>

        <div class="footer">
            🕒 Обновлено: {{ now }} | 🤖 <a href="https://t.me/LeoAideBot" target="_blank">Bot</a>
        </div>
    </div>
</body>
</html>
"""

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except:
        return None

@app.route('/')
def dashboard():
    conn = get_db_connection()
    if not conn:
        return "<h1>❌ Не удалось подключиться к базе данных</h1>", 500

    try:
        user_count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        premium_count = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_premium = 1").fetchone()["c"]
        today_joined = conn.execute("SELECT COUNT(*) as c FROM users WHERE date(last_seen) = date('now')").fetchone()["c"]

        logs = conn.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 30").fetchall()
        conn.close()

        return render_template_string(
            HTML_TEMPLATE,
            user_count=user_count,
            premium_count=premium_count,
            today_joined=today_joined,
            logs=logs,
            now=datetime.now().strftime("%H:%M:%S")
        )
    except Exception as e:
        return f"<h1>❌ Ошибка базы: {str(e)}</h1>"

@app.route('/status')
def status():
    return jsonify({
        "status": "ok",
        "service": "Leo Aide Bot",
        "uptime": "24/7",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))  # Важно: читать PORT из окружения
    app.run(host="0.0.0.0", port=port)  # host="0.0.0.0" — обязательно

# web/app.py

import os
from flask import Flask, request, send_from_directory, jsonify
from bot.database import set_premium, log_action, get_user, get_user_count, get_premium_count, get_today_joined_count
from bot.utils.payments import verify_payment
import json

app = Flask(__name__, static_folder='static')

# 🌐 Основная страница — статистика
@app.route("/")
def home():
    try:
        total = get_user_count()
        premium = get_premium_count()
        today = get_today_joined_count()
    except Exception as e:
        return f"<h1>❌ Ошибка: {str(e)}</h1>"

    return f"""
    <html>
    <head><title>📊 Статистика Лео</title></head>
    <body style="font-family: sans-serif; text-align: center; margin-top: 50px;">
        <h1>📈 Статистика бота Лео</h1>
        <p><b>Всего пользователей:</b> {total}</p>
        <p><b>Премиум:</b> {premium}</p>
        <p><b>Зашли сегодня:</b> {today}</p>
        <hr>
        <small>Обновляется в реальном времени</small>
    </body>
    </html>
    """

# 🌐 Callback — уведомление об оплате (POST)
@app.route("/payment/callback", methods=["POST"])
def payment_callback():
    data = request.form.to_dict()

    if not verify_payment(data):
        return "bad sign", 400

    order_id = int(data['inv_id'])
    amount = float(data['amount'])

    if amount < 100.0:
        return "invalid amount", 400

    if order_id in pending_payments and pending_payments[order_id]['status'] == 'waiting':
        user_id = pending_payments[order_id]['user_id']
        set_premium(user_id, days=30)
        pending_payments[order_id]['status'] = 'paid'
        log_action(user_id, "premium_paid", f"order_id={order_id}")

        # Уведомляем пользователя
        from telegram import Bot
        bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
        bot.send_message(user_id, "🎉 Премиум-доступ активирован! Спасибо за доверие 💙")

    return "OK", 200

# ✅ Успешная оплата
@app.route("/success")
def success():
    return """
    <html>
    <head><title>Успешно</title></head>
    <body style="text-align: center; margin-top: 100px; font-family: sans-serif;">
        <h1>🎉 Оплата прошла успешно!</h1>
        <p>Спасибо за покупку премиум-подписки!</p>
        <p>Вернитесь в бота: <a href="https://t.me/LeoHelperBot">t.me/LeoHelperBot</a></p>
    </body>
    </html>
    """

# ❌ Оплата не удалась
@app.route("/fail")
def fail():
    return """
    <html>
    <head><title>Ошибка</title></head>
    <body style="text-align: center; margin-top: 100px; font-family: sans-serif;">
        <h1>❌ Оплата не удалась</h1>
        <p>Произошла ошибка. Попробуйте ещё раз.</p>
        <p><a href="https://t.me/LeoHelperBot">Вернуться в бота</a></p>
    </body>
    </html>
    """


# 🌐 Mini App — профиль пользователя
@app.route("/app")
def web_app():
    # Получаем user_id из параметров (в будущем — через безопасную авторизацию)
    user_id = request.args.get("user_id")
    if not user_id:
        return "<h1>❌ Не указан user_id</h1>"

    try:
        user_id = int(user_id)
        user = get_user(user_id)
        if not user:
            return "<h1>❌ Пользователь не найден</h1>"

        # Подготовим данные
        user_data = {
            "user_id": user["user_id"],
            "first_name": user["first_name"],
            "username": user["username"],
            "joined_at": user["joined_at"].strftime("%d.%m.%Y"),
            "is_premium": bool(user["is_premium"]),
            "premium_expire": user["premium_expire"].strftime("%d.%m.%Y") if user["premium_expire"] else None
        }

        # Передаём данные в HTML
        return f"""
        <script>
            window.user_data = {json.dumps(user_data, ensure_ascii=False)};
            window.location.href = '/static/app.html';
        </script>
        """
    except Exception as e:
        return f"<h1>❌ Ошибка: {str(e)}</h1>"


# 📄 Статический файл Mini App
@app.route('/static/app.html')
def serve_app():
    return send_from_directory('static', 'app.html')


# ⚠️ Временное хранилище (позже замени на БД)
pending_payments = {}


# 🔽 Функции статистики (для /)
def get_user_count():
    from bot.database import get_user_count
    return get_user_count()

def get_premium_count():
    from bot.database import get_premium_count
    return get_premium_count()

def get_today_joined_count():
    from bot.database import get_today_joined_count
    return get_today_joined_count()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

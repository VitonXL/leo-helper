# bot/broadcast.py
import os
from telegram import Bot
import asyncio
from bot.database import get_user, get_user_cities, get_db
from bot.weather import get_weather
from bot.quotes import get_random_quote
from bot.currency import get_usd_rate


async def send_daily_broadcast():
    """
    Ежедневная рассылка: погода, курс USD, цитата
    Запускается через APScheduler
    """
    # ✅ Берём токен из переменных окружения
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return

    bot = Bot(token=TOKEN)

    try:
        # Получаем всех пользователей с включёнными уведомлениями
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE notify_enabled = TRUE")
            user_ids = [row["user_id"] for row in cur.fetchall()]
        print(f"📨 Рассылка: {len(user_ids)} получателей")
    except Exception as e:
        print(f"❌ Не удалось получить список пользователей: {e}")
        return

    # Получаем данные для рассылки
    rate = get_usd_rate()
    quote = get_random_quote()

    for user_id in user_ids:
        try:
            cities = get_user_cities(user_id)
            city = cities[0] if cities else None
            weather_text = await get_weather(city) if city else "🌤 Город не задан"

            message = f"""
🌄 <b>Доброе утро!</b>

🌤 Погода: {weather_text}
💰 Курс USD: {rate} ₽
🧠 Цитата: "{quote}"

Хорошего дня! ☕
            """.strip()

            await bot.send_message(user_id, message, parse_mode='HTML')
            print(f"✅ Сообщение отправлено: {user_id}")
            await asyncio.sleep(0.1)  # Анти-флуд (Telegram требует паузу)
        except Exception as e:
            print(f"❌ Ошибка при отправке {user_id}: {e}")
            continue

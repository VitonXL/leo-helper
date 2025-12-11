# bot/broadcast.py
from telegram import Bot
import asyncio
from bot.database import db
from bot.weather import get_weather
from bot.quotes import get_random_quote
from bot.currency import get_usd_rate

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_daily_broadcast():
    bot = Bot(token=BOT_TOKEN)
    with db.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE notify_enabled = TRUE")
        user_ids = [row["user_id"] for row in cur.fetchall()]

    rate = get_usd_rate()
    quote = get_random_quote()

    for user_id in user_ids:
        try:
            cities = db.get_user_cities(user_id)
            city = cities[0] if cities else None
            weather_text = await get_weather(city) if city else "🌤 Не задан"
            message = f"""
🌄 <b>Доброе утро!</b>

🌤 Погода: {weather_text.split('Температура:')[1] if 'Температура:' in str(weather_text) else weather_text}
💰 Курс USD: {rate} ₽
🧠 Цитата: "{quote}"

Хорошего дня! ☕
            """.strip()
            await bot.send_message(user_id, message, parse_mode='HTML')
            await asyncio.sleep(0.1)
        except:
            continue

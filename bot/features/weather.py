# bot/features/weather.py не арботоает! не привяано ничего.

import httpx
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from database import get_db_pool
from loguru import logger

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")  # ← Замени на свой или используй os.getenv
WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"

# --- Тексты ---
TEXTS = {
    "ru": {
        "enter_city": "🏙 Введите название города:",
        "saved_city": "✅ Город сохранён: <b>{city}</b>",
        "weather_in": "🌤 Погода в <b>{city}</b>:\n",
        "temp": "🌡 Температура: <b>{temp}°C</b>\n",
        "feels_like": "Ощущается как: {feels_like}°C\n",
        "humidity": "💧 Влажность: {humidity}%\n",
        "wind": "💨 Ветер: {speed} м/с\n",
        "clouds": "☁️ Облачность: {clouds}%\n",
        "error_city": "❌ Не удалось найти город. Попробуйте ещё раз.",
        "error_api": "❌ Ошибка сервиса погоды. Повторите позже.",
    },
    "en": {
        "enter_city": "🏙 Enter city name:",
        "saved_city": "✅ City saved: <b>{city}</b>",
        "weather_in": "🌤 Weather in <b>{city}</b>:\n",
        "temp": "🌡 Temperature: <b>{temp}°C</b>\n",
        "feels_like": "Feels like: {feels_like}°C\n",
        "humidity": "💧 Humidity: {humidity}%\n",
        "wind": "💨 Wind: {speed} m/s\n",
        "clouds": "☁️ Clouds: {clouds}%\n",
        "error_city": "❌ City not found. Try again.",
        "error_api": "❌ Weather API error. Try later.",
    }
}


async def get_user_lang(pool, user_id: int) -> str:
    lang = await pool.fetchval("SELECT language FROM users WHERE id = $1", user_id)
    return lang or "ru"


async def get_user_city(pool, user_id: int) -> str:
    city = await pool.fetchval("SELECT city FROM users WHERE id = $1", user_id)
    return city


async def set_user_city(pool, user_id: int, city: str):
    await pool.execute("UPDATE users SET city = $1 WHERE id = $2", city, user_id)


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']

    # Определяем язык
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]

    # Пытаемся получить город из аргументов
    if context.args:
        city = " ".join(context.args)
        await set_user_city(pool, user.id, city)
        await update.message.reply_html(texts["saved_city"].format(city=city))
    else:
        # Берём последний сохранённый город
        city = await get_user_city(pool, user.id)
        if not city:
            await update.message.reply_text(texts["enter_city"])
            return

    await fetch_and_send_weather(update, context, city, texts)


async def fetch_and_send_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, city: str, texts: dict):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                WEATHER_URL,
                params={
                    "q": city,
                    "appid": WEATHER_API_KEY,
                    "lang": "ru",
                    "units": "metric"
                },
                timeout=10.0
            )

        if response.status_code == 404:
            await update.message.reply_text(texts["error_city"])
            return

        data = response.json()
        main = data["main"]
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})

        temp = int(main["temp"])
        feels_like = int(main["feels_like"])
        humidity = main["humidity"]
        wind_speed = wind.get("speed", "нет данных")
        cloudiness = clouds.get("all", "нет данных")

        message = (
            texts["weather_in"].format(city=city) +
            texts["temp"].format(temp=temp) +
            texts["feels_like"].format(feels_like=feels_like) +
            texts["humidity"].format(humidity=humidity) +
            texts["wind"].format(speed=wind_speed) +
            texts["clouds"].format(clouds=cloudiness)
        )

        await update.message.reply_html(message)

    except httpx.RequestError as e:
        logger.error(f"❌ Ошибка запроса к погоде: {e}")
        await update.message.reply_text(texts["error_api"])
    except Exception as e:
        logger.error(f"❌ Ошибка обработки погоды: {e}")
        await update.message.reply_text(texts["error_api"])


# --- Обработчик, если пользователь просто ввёл город ---
async def handle_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if len(text) < 2 or any(c.isdigit() for c in text):
        return  # не похоже на город

    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]

    # Проверим, не команда ли это
    if text.startswith("/"):
        return

    # Сохраняем как город
    await set_user_city(pool, user.id, text)
    await update.message.reply_html(texts["saved_city"].format(city=text))


def setup_weather_handlers(app):
    app.add_handler(CommandHandler("weather", cmd_weather))
    # Группа 5 — после команд, но до поддержки
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_input), group=5)
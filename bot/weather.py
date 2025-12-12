# bot/weather.py
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ✅ Убрали: from bot.database import db
# ✅ Вместо этого:
from bot.database import get_user_cities, add_user_city, get_user, get_db

API_KEY = "ваш_ключ"  # Укажите в Service Variables
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"


async def add_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("🌤 Напишите: /city <город>")
        return
    city = " ".join(args).strip().title()
    user = get_user(user_id)
    cities = get_user_cities(user_id)
    max_cities = 5 if user["is_premium"] else 1
    if len(cities) >= max_cities:
        await update.message.reply_text(f"❌ Лимит городов: {max_cities}. Премиум — больше!")
        return
    if city in cities:
        await update.message.reply_text(f"✅ {city} уже добавлен!")
        return
    if not await is_valid_city(city):
        await update.message.reply_text("❌ Город не найден. Проверьте написание.")
        return
    add_user_city(user_id, city)
    await update.message.reply_text(f"✅ Город {city} добавлен!")


async def show_cities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cities = get_user_cities(user_id)
    if not cities:
        await update.message.reply_text("У вас нет городов. /city <город>")
        return
    max_cities = 5 if get_user(user_id)["is_premium"] else 1
    text = f"📌 Ваши города: ({len(cities)}/{max_cities})\n\n"
    for city in cities:
        text += f"• {city}\n"
    keyboard = [[InlineKeyboardButton("🌤 Погода", callback_data="weather")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cities = get_user_cities(user_id)
    if not cities:
        await update.message.reply_text("Нет городов. Добавьте: /city <город>")
        return
    await update.message.reply_text("🌤 Запрашиваю погоду...")
    for city in cities:
        weather = await get_weather(city)
        if weather:
            await update.message.reply_text(weather, parse_mode='HTML')
        else:
            await update.message.reply_text(f"❌ Нет погоды для {city}")


async def is_valid_city(city: str) -> bool:
    url = f"{BASE_URL}?q={city}&appid={API_KEY}&units=metric"
    try:
        return requests.get(url).status_code == 200
    except:
        return False


async def get_weather(city: str) -> str:
    url = f"{BASE_URL}?q={city}&appid={API_KEY}&lang=ru&units=metric"
    try:
        r = requests.get(url).json()
        temp = r["main"]["temp"]
        desc = r["weather"][0]["description"].capitalize()
        name = r["name"]
        return f"🌤 <b>{name}</b>\nТемпература: {temp}°C\nСостояние: {desc}"
    except Exception as e:
        return None

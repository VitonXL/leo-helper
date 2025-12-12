# bot/weather.py
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import get_user_cities, add_user_city, get_user, get_db

# Получите API-ключ на https://openweathermap.org/api
API_KEY = "your_openweathermap_api_key"  # Замените или укажите в переменных Railway
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"


async def add_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /city <город>
    Добавляет город в список пользователя
    """
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("🌤 Напишите: /city <город>")
        return
    city = " ".join(args).strip().title()
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Пользователь не найден.")
        return
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
    """
    Показывает список городов пользователя
    """
    user_id = update.effective_user.id
    cities = get_user_cities(user_id)
    if not cities:
        await update.message.reply_text("У вас нет городов. Добавьте: /city <город>")
        return
    user = get_user(user_id)
    max_cities = 5 if user["is_premium"] else 1
    text = f"📌 Ваши города: ({len(cities)}/{max_cities})\n\n"
    for city in cities:
        text += f"• {city}\n"
    keyboard = [[InlineKeyboardButton("🌤 Погода", callback_data="weather")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает погоду во всех добавленных городах
    """
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
    """
    Проверяет, существует ли город
    """
    url = f"{BASE_URL}?q={city}&appid={API_KEY}&units=metric"
    try:
        return requests.get(url).status_code == 200
    except:
        return False


async def get_weather(city: str) -> str:
    """
    Получает погоду для города
    """
    url = f"{BASE_URL}?q={city}&appid={API_KEY}&lang=ru&units=metric"
    try:
        r = requests.get(url).json()
        temp = r["main"]["temp"]
        desc = r["weather"][0]["description"].capitalize()
        name = r["name"]
        return f"🌤 <b>{name}</b>\nТемпература: {temp}°C\nСостояние: {desc}"
    except Exception as e:
        print(f"Ошибка получения погоды для {city}: {e}")
        return None

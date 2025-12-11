# bot/bot.py
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Импортируем функции напрямую
from bot.database import (
    get_user, add_user, set_premium, set_admin,
    get_user_count, get_premium_count, get_today_joined_count,
    log_action, get_user_cities, add_user_city, remove_city,
    get_ai_requests, increment_ai_request, reset_ai_requests
)

from bot.weather import add_city as add_city_command
from bot.ai import send_to_gigachat
from bot.currency import get_usd_rate
from bot.quotes import get_random_quote
from bot.broadcast import send_daily_broadcast

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
    db.add_user(user_data)
    db.log_action(user.id, "start")

    keyboard = [
        [InlineKeyboardButton("🌤 Погода", callback_data="weather")],
        [InlineKeyboardButton("💸 Курсы", callback_data="rates")],
        [InlineKeyboardButton("🎮 Развлечения", callback_data="entertainment")],
        [InlineKeyboardButton("🧠 GigaChat", callback_data="ai_start")],
        [InlineKeyboardButton("🌐 Mini-app", web_app=WebAppInfo(url="https://leo-aide-web.up.railway.app"))],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
    ]
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\nЯ — Leo Aide, ваш AI-помощник.\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "weather":
        await show_weather(update, context)
    elif query.data == "rates":
        rate = get_usd_rate()
        await query.edit_message_text(f"💰 Курс USD: {rate} ₽\nОбновлено: сейчас")
    elif query.data == "entertainment":
        keyboard = [
            [InlineKeyboardButton("🎬 Фильмы", url="https://t.me/durov")],
            [InlineKeyboardButton("📱 Игры Telegram", url="https://t.me/games")],
            [InlineKeyboardButton("🕹️ Наши игры", callback_data="our_games")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
        ]
        await query.edit_message_text("🎮 Развлечения", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "our_games":
        await query.edit_message_text(
            "🕹️ <b>Наши игры</b>\n\nСкоро здесь появятся наши авторские игры!\nОставайтесь на связи.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 Подписаться", url="https://t.me/LeoAideNews")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="entertainment")]
            ])
        )
    elif query.data == "ai_start":
        await query.message.reply_text(
            "🧠 Напишите ваш вопрос.\nЛимит: 1 запрос/день (премиум — 10)."
        )
    elif query.data == "settings":
        user = db.get_user(user_id)
        status = "🔔 ВКЛ" if user["notify_enabled"] else "🔕 ВЫКЛ"
        keyboard = [
            [InlineKeyboardButton(f"Уведомления: {status}", callback_data="toggle_notify")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
        ]
        await query.edit_message_text("⚙️ Настройки", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "toggle_notify":
        user = db.get_user(user_id)
        new_status = not user["notify_enabled"]
        db.set_notify_status(user_id, new_status)
        status_text = "🔔 ВКЛ" if new_status else "🔕 ВЫКЛ"
        keyboard = [[InlineKeyboardButton(f"Уведомления: {status_text}", callback_data="toggle_notify")]]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("🌤 Погода", callback_data="weather")],
            [InlineKeyboardButton("💸 Курсы", callback_data="rates")],
            [InlineKeyboardButton("🎮 Развлечения", callback_data="entertainment")],
            [InlineKeyboardButton("🧠 GigaChat", callback_data="ai_start")],
            [InlineKeyboardButton("🌐 Mini-app", web_app=WebAppInfo(url="https://leo-aide-web.up.railway.app"))],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        ]
        await query.edit_message_text("🏠 Главное меню", reply_markup=InlineKeyboardMarkup(keyboard))

async def ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    text = update.message.text
    limit = 10 if user["is_premium"] else 1
    if db.get_ai_requests(user_id) >= limit:
        await update.message.reply_text("❌ Лимит запросов исчерпан.")
        return
    await update.message.reply_text("🧠 Думаю...")
    response = await send_to_gigachat(user_id, text)
    await update.message.reply_text(response)
    db.increment_ai_request(user_id)
    db.log_action(user_id, f"ai_query: {text[:50]}...")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Используйте меню.")

# === Главная функция запуска ===
def bot_main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден")

    application = Application.builder().token(TOKEN).build()

    # Хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("city", add_city))
    application.add_handler(CommandHandler("cities", show_cities))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_message))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_broadcast, 'cron', hour=9, minute=0, timezone='Europe/Moscow')
    scheduler.start()

    # Запуск
    application.run_polling()

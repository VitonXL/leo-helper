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
import asyncio

from bot.database import (
    get_user, add_user, set_premium, set_admin,
    get_user_count, get_premium_count, get_today_joined_count,
    log_action, get_user_cities, add_user_city,
    get_ai_requests, increment_ai_request, reset_ai_requests
)

from bot.weather import add_city as add_city_command
from bot.weather import show_cities as show_cities_command
from bot.weather import show_weather as show_weather_command
from bot.ai import send_to_gigachat
from bot.currency import get_usd_rate
from bot.quotes import get_random_quote
from bot.broadcast import send_daily_broadcast

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = user.to_dict()
    add_user(user_data)
    log_action(user.id, "start")
    keyboard = [
        [InlineKeyboardButton("🌤 Погода", callback_data="weather_menu")],
        [InlineKeyboardButton("💰 Курс USD", callback_data="usd")],
        [InlineKeyboardButton("🧠 Цитата дня", callback_data="quote")],
        [InlineKeyboardButton("💬 AI", callback_data="ai")],
        [InlineKeyboardButton("📌 Мои города", callback_data="my_cities")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Привет, {user.first_name}! 👋\nЯ — многофункциональный бот.\nВыберите действие:", reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🛠 Доступные команды:
/start - Главное меню
/help - Эта справка
/city <город> - Добавить город
/weather - Погода в ваших городах
/usd - Курс доллара
/quote - Цитата дня
/ai - Общение с ИИ
/stats - Статистика бота

Админ-команды:
/setpremium <id> - Дать премиум
/setadmin <id> - Сделать админом
/resetai - Сбросить AI-лимит
    """.strip()
    await update.message.reply_text(help_text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    if not user:
        await query.message.reply_text("❌ Ошибка: пользователь не найден.")
        return

    if query.data == "weather_menu":
        keyboard = [
            [InlineKeyboardButton("🌤 Показать погоду", callback_data="weather")],
            [InlineKeyboardButton("➕ Добавить город", callback_data="add_city")],
            [InlineKeyboardButton("📌 Мои города", callback_data="my_cities")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back")]
        ]
        await query.edit_message_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "weather":
        await show_weather_command(update, context)

    elif query.data == "usd":
        rate = get_usd_rate()
        await query.edit_message_text(f"💵 Курс USD: {rate} ₽", reply_markup=back_button())

    elif query.data == "quote":
        quote = get_random_quote()
        await query.edit_message_text(f"🧠 Цитата дня:\n\n\"{quote}\"", reply_markup=back_button())

    elif query.data == "ai":
        await query.edit_message_text("💬 Напишите запрос ИИ:", reply_markup=back_button())

    elif query.data == "add_city":
        await query.edit_message_text("🌤 Напишите: /city <город>")

    elif query.data == "my_cities":
        await show_cities_command(update, context)

    elif query.data == "back":
        await query.edit_message_text("Выберите действие:", reply_markup=main_menu())


def main_menu():
    keyboard = [
        [InlineKeyboardButton("🌤 Погода", callback_data="weather_menu")],
        [InlineKeyboardButton("💰 Курс USD", callback_data="usd")],
        [InlineKeyboardButton("🧠 Цитата дня", callback_data="quote")],
        [InlineKeyboardButton("💬 AI", callback_data="ai")],
        [InlineKeyboardButton("📌 Мои города", callback_data="my_cities")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Назад", callback_data="back")]])


async def message_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text.startswith('/setpremium'):
        if not get_user(user_id)["is_admin"]:
            await update.message.reply_text("❌ Только администраторы могут использовать эту команду.")
            return
        try:
            target_id = int(text.split()[1])
            set_premium(target_id, True)
            await update.message.reply_text(f"✅ Пользователь {target_id} теперь premium")
        except:
            await update.message.reply_text("❌ Использование: /setpremium <id>")

    elif text.startswith('/setadmin'):
        if user_id != 123456789:  # ← Замените на ваш ID
            await update.message.reply_text("❌ Только владелец может назначать админов.")
            return
        try:
            target_id = int(text.split()[1])
            set_admin(target_id, True)
            await update.message.reply_text(f"✅ Пользователь {target_id} теперь админ")
        except:
            await update.message.reply_text("❌ Использование: /setadmin <id>")

    elif text == '/stats':
        if not get_user(user_id)["is_admin"]:
            await update.message.reply_text("❌ Только администраторы могут смотреть статистику.")
            return
        total = get_user_count()
        premium = get_premium_count()
        today = get_today_joined_count()
        await update.message.reply_text(f"📊 Статистика бота:\n\nВсего: {total}\nPremium: {premium}\nСегодня: {today}")

    elif text == '/resetai':
        if not get_user(user_id)["is_admin"]:
            await update.message.reply_text("❌ Только администраторы могут сбросить AI-лимит.")
            return
        reset_ai_requests()
        await update.message.reply_text("✅ Все AI-запросы сброшены")

    else:
        requests = get_ai_requests(user_id)
        if requests >= 10 and not get_user(user_id)["is_premium"]:
            await update.message.reply_text("❌ Лимит запросов исчерпан (10/день). Премиум — без лимита.")
            return
        response = await send_to_gigachat(text)
        await update.message.reply_text(response)
        increment_ai_request(user_id)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")


def bot_main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("city", add_city_command))
    application.add_handler(CommandHandler("weather", show_weather_command))
    application.add_handler(CommandHandler("usd", lambda u, c: c.bot.send_message(u.effective_chat.id, f"💵 {get_usd_rate()} ₽")))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler_func))
    application.add_error_handler(error_handler)

    # ✅ Запускаем планировщик ВНУТРИ асинхронного цикла
    async def run():
        scheduler = AsyncIOScheduler()
        scheduler.add_job(reset_ai_requests, 'cron', hour=0)
        scheduler.add_job(send_daily_broadcast, 'cron', hour=8, minute=0)
        scheduler.start()
        print("✅ Планировщик запущен")
        await application.run_polling()

    # Запускаем асинхронно
    asyncio.run(run())

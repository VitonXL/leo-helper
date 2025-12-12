# bot/bot.py

import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update

from bot.database import init_db, add_user, log_action, check_premium
from bot.commands.start import start
from bot.commands.premium import premium_command
from bot.commands.weather import weather_command
from bot.commands.currency import currency_command
from bot.commands.reminders import set_reminder, show_reminders
from bot.commands.movies import movies_command
from bot.commands.antivirus import virus_check
from bot.commands.giga import giga_chat
from bot.commands.games import games_menu
from bot.commands.admin import admin_panel
from bot.commands.support import support_chat
from bot.commands.premium import premium_command, precheckout_callback, successful_payment
from bot.commands.start import start
from bot.commands.referral import referral_command, show_referrals
from bot.commands.weather import weather_command, weather_callback

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

def bot_main():
    print("🚀 Запуск бота Лео...")
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium_command))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("currency", currency_command))
    app.add_handler(CommandHandler("remind", set_reminder))
    app.add_handler(CommandHandler("reminders", show_reminders))
    app.add_handler(CommandHandler("movies", movies_command))
    app.add_handler(CommandHandler("games", games_menu))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("support", support_chat))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.URL, virus_check))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, giga_chat))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CallbackQueryHandler(show_referrals, pattern="referrals_list"))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CallbackQueryHandler(weather_callback, pattern="^weather_"))
    app.add_handler(CallbackQueryHandler(weather_callback, pattern="^delete_city_"))
    app.add_handler(CallbackQueryHandler(weather_callback, pattern="^weather_back$"))

    print("🤖 Бот Лео запущен и слушает...")
    app.run_polling()

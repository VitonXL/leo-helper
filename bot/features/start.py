# bot/features/start.py
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\nЯ — Лео, твой личный помощник.\n"
        "Используй /help, чтобы узнать, что я умею."
    )

def setup(application):
    application.add_handler(CommandHandler("start", start_command))

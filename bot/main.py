# bot/main.py

import os
from telegram import Update, WebAppInfo, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = "https://web-production-b74ea.up.railway.app"  # ← Замени на свой, если нужно

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        text=f"Привет, <b>{user.first_name}</b>! 👋\n\n"
             f"Панель управления доступна в меню бота (кнопка в правом верхнем углу чата) — нажми 🌐 Открыть панель.",
        reply_markup=None  # Убрали клавиатуру
    )

async def post_init(application: Application):
    """Устанавливаем команды и кнопку меню"""
    # Устанавливаем команды
    await application.bot.set_my_commands([
        ("start", "Запустить бота"),
        ("help", "Помощь и поддержка")
    ])

    # Устанавливаем кнопку Web App в меню
    await application.bot.set_chat_menu_button(
        menu_button=WebAppInfo(
            text="🌐 Панель",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

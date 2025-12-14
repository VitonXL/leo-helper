# bot/main.py

import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, ContextTypes, CommandHandler

# Импортируем наше меню
from features.menu import setup as setup_menu

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = "https://web-production-b74ea.up.railway.app"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📌 Главное меню", callback_data="menu_main")],
        [InlineKeyboardButton("🌐 Открыть Mini App", url="https://web-production-b74ea.up.railway.app")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        text=f"Привет, <b>{update.effective_user.first_name}</b>! 👋\n\n"
             f"Выбери, как хочешь продолжить:",
        reply_markup=reply_markup
    )

async def post_init(application):
    # Кнопка в меню (≡)
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🌐 Панель",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Подключаем меню
    setup_menu(app)

    # Команда /start
    app.add_handler(CommandHandler("start", start))

    print("🚀 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

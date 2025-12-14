# bot/main.py

import os
from telegram import Update, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = "https://web-production-b74ea.up.railway.app"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        text=f"Привет, <b>{user.first_name}</b>! 👋\n\n"
             f"Панель управления доступна в меню (≡) — нажми 🌐 Открыть панель.",
        reply_markup=None
    )

async def post_init(application: Application):
    print("✅ post_init: старт")
    await application.bot.set_my_commands([("start", "Запустить бота")])
    print("✅ Команды установлены")

    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🌐 Панель",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )
    print("✅ Меню '🌐 Панель' установлено")

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    print("🚀 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

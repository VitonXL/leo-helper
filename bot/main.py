# bot/main.py

import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler
from features.menu import setup as setup_menu
from database import Database  # ← подключаем БД

# Глобальный экземпляр БД
db = Database()

# Кнопки под /start
def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("📌 Главное меню", callback_data="menu_main")],
        [InlineKeyboardButton("🌐 Mini App", url="https://web-production-b74ea.up.railway.app")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Сохраняем или обновляем пользователя
    await db.add_or_update_user(user)

    await update.message.reply_html(
        text=f"👋 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
             f"Выберите способ взаимодействия:",
        reply_markup=get_start_keyboard()
    )

# Фоновая задача: удаляем неактивных каждые 24 часа
async def cleanup_task(application: Application):
    while True:
        try:
            await asyncio.sleep(24 * 3600)  # Каждые 24 часа
            await db.delete_inactive_users()
        except Exception as e:
            print(f"❌ Ошибка в cleanup: {e}")

async def post_init(application: Application):
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🌐 Панель",
            web_app=WebAppInfo(url="https://web-production-b74ea.up.railway.app")
        )
    )

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Подключаем меню
    setup_menu(app)

    # Обработчики
    app.add_handler(CommandHandler("start", start))

    # Запускаем БД и фоновую задачу
    app.add_post_init_task(lambda app: db.connect())
    app.job_queue.run_once(lambda _: app.create_task(cleanup_task(app)), when=10)

    print("🚀 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

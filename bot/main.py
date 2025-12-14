# bot/main.py

import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonWebApp, WebAppInfo
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    TypeHandler  # ← добавь это
)

from database import create_db_pool, init_db, add_or_update_user, delete_inactive_users
from features.menu import setup as setup_menu
import asyncio

# Глобальный пул БД
db_pool = None


def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("📌 Главное меню", callback_data="menu_main")],
        [InlineKeyboardButton("🌐 Mini App", url="https://web-production-b74ea.up.railway.app")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_or_update_user(db_pool, user)

    await update.message.reply_html(
        text=f"👋 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
             f"Выберите способ взаимодействия:",
        reply_markup=get_start_keyboard()
    )


# Фоновая задача: удаление неактивных пользователей
async def cleanup_task(context: ContextTypes.DEFAULT_TYPE):
    global db_pool
    if db_pool:
        await delete_inactive_users(db_pool, days=90)


async def on_post_init(application: Application):
    global db_pool
    print("🔧 Инициализация БД...")
    db_pool = await create_db_pool()
    await init_db(db_pool)
    print("✅ База данных инициализирована")

    # Устанавливаем кнопку в меню (≡)
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🌐 Панель",
            web_app=WebAppInfo(url="https://web-production-b74ea.up.railway.app")
        )
    )
    print("🚀 Меню (≡) установлено")

    # Запускаем фоновую задачу каждые 24 часа
    application.job_queue.run_repeating(
        cleanup_task,
        interval=24 * 3600,  # каждые 24 часа
        first=10  # начать через 10 секунд после старта
    )
    print("⏰ Фоновая задача: очистка неактивных пользователей — запущена")


def main():
    app = (
        Application.builder()
        .token(os.getenv("BOT_TOKEN"))
        .post_init(on_post_init)
        .build()
    )

    # Подключаем меню
    setup_menu(app)

    # Самый первый обработчик — отслеживание активности
    app.add_handler(TypeHandler(Update, track_user_activity), group=-1)

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))

    print("🚀 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()

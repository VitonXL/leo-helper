# bot/main.py

import os
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler

# Импортируем БД
from database import create_db_pool, init_db, add_or_update_user, delete_inactive_users
from features.menu import setup as setup_menu

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


async def cleanup_task(application: Application):
    while True:
        try:
            await asyncio.sleep(24 * 3600)
            await delete_inactive_users(db_pool, days=90)
        except Exception as e:
            print(f"❌ Ошибка в cleanup: {e}")


# Функция, которая вызывается при старте
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

    # Запускаем фоновую задачу
    application.create_task(cleanup_task(application))


def main():
    app = (
        Application.builder()
        .token(os.getenv("BOT_TOKEN"))
        .post_init(on_post_init)  # ← здесь передаём
        .build()
    )

    # Подключаем меню
    setup_menu(app)

    # Обработчики
    app.add_handler(CommandHandler("start", start))

    print("🚀 Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()

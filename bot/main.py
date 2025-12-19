# bot/main.py

import os
import asyncio
from database import cleanup_support_tickets
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonWebApp, WebAppInfo
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    TypeHandler,
    MessageHandler,
    filters,
)

# Импортируем БД
from database import (
    create_db_pool,
    init_db,
    add_or_update_user,
    delete_inactive_users,
    log_command_usage,
    get_user_role,
    register_referral,
)

# Импорты фичей — БЕЗ "bot."
from features.menu import setup as setup_menu
from features.admin import setup_admin_handlers
from features.roles import setup_role_handlers
from features.referrals import setup_referral_handlers
from features.premium import setup_premium_handlers
from features.help import setup as help_setup  # ✅ Без "bot."

from loguru import logger

# Глобальный пул БД
db_pool = None


# --- Отслеживание активности ---
async def track_user_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        await add_or_update_user(db_pool, user)

    if update.message and update.message.text and update.message.text.startswith('/'):
        command = update.message.text.split()[0]
        await log_command_usage(db_pool, user.id, command)


# --- Клавиатура после /start ---
def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("📌 Главное меню", callback_data="menu_main")],
        [InlineKeyboardButton("🌐 Mini App", url="https://leo-aide.online/")]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Обработчик /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await add_or_update_user(db_pool, user)

    # Обработка реферала
    if context.args and context.args[0].startswith("ref"):
        referrer_id = int(context.args[0][3:])
        if referrer_id != user.id:
            await register_referral(db_pool, referrer_id, user.id)

    # Роль
    role = await get_user_role(db_pool, user.id)
    role_text = {"user": "👤 Обычный", "premium": "💎 Премиум", "admin": "👮‍♂️ Админ"}.get(role, "👤 Обычный")

    await update.message.reply_html(
        text=f"👋 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
             f"🔹 Ваш статус: <b>{role_text}</b>\n\n"
             f"Выберите способ взаимодействия:",
        reply_markup=get_start_keyboard()
    )


# --- Фоновая очистка ---
async def cleanup_task(context: ContextTypes.DEFAULT_TYPE):
    if not db_pool:
        return
    await delete_inactive_users(db_pool, days=90)
    await cleanup_support_tickets(db_pool, days=7)


# --- Инициализация ---
async def on_post_init(application: Application):
    global db_pool
    logger.info("🔧 Инициализация БД...")
    db_pool = await create_db_pool()
    await init_db(db_pool)
    logger.info("✅ База данных инициализирована")

    application.bot_data['db_pool'] = db_pool

    # Устанавливаем кнопку (≡)
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🌐 Панель",
            web_app=WebAppInfo(url="https://leo-aide.online/")
        )
    )
    logger.info("🚀 Меню (≡) установлено")

    # Устанавливаем команды
    await application.bot.set_my_commands([
        ("start", "🚀 Начать"),
        ("menu", "🏠 Открыть меню"),
        ("help", "🔧 Помощь и поддержка"),
    ])
    logger.info("✅ Команды бота установлены")

    # Фоновая задача
    application.job_queue.run_repeating(
        cleanup_task,
        interval=24 * 3600,
        first=10
    )
    logger.info("⏰ Фоновая задача: очистка — запущена")


# --- Главная ---
def main():
    app = (
        Application.builder()
        .token(os.getenv("BOT_TOKEN"))
        .post_init(on_post_init)
        .build()
    )

    # Самый первый — отслеживаем активность
    app.add_handler(TypeHandler(Update, track_user_activity), group=-1)

    # Подключаем фичи
    setup_menu(app)
    setup_admin_handlers(app)
    setup_role_handlers(app)
    setup_referral_handlers(app)
    setup_premium_handlers(app)
    help_setup(app)  # ✅ Подключаем систему поддержки

    # Команда /start
    app.add_handler(CommandHandler("start", start))

    logger.info("🚀 Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
# bot/main.py

import sys
import os

# 🔴 САМОЕ ПЕРВОЕ — добавляем корневую директорию в путь
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Теперь можно импортировать из корня
from bot.instance import application as global_app, bot as global_bot
from database import (
    create_db_pool,
    init_db,
    add_or_update_user,
    delete_inactive_users,
    log_command_usage,
    get_user_role,
    register_referral,
    cleanup_support_tickets,
    ensure_support_table_exists,
    get_db_pool,
    get_user_lang,  # ✅ Добавлен: нужен для локализации напоминаний и подписок
)

# Фичи
from features.menu import setup as setup_menu
from features.admin import setup_admin_handlers
from features.roles import setup_role_handlers
from features.referrals import setup_referral_handlers
from features.premium import setup_premium_handlers
from features.help import setup as help_setup
from features.help import handle_support_message  # ✅ Обработчик сообщений поддержки
from features.currency import setup_currency_handlers
from features.reminders import setup_reminder_handlers
from features.subscriptions import setup_subscription_handlers
from features.weather import setup_weather_handlers  # ✅ Добавлен: погода

# Telegram
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
from loguru import logger

# Глобальная переменная пула
db_pool = None

# --- FAQ: автоответы на частые вопросы ---
SUPPORT_FAQ = {
    "сменить тему": "Чтобы сменить тему, открой личный кабинет → Настройки → Тема.",
    "сменить язык": "В кабинете выберите язык интерфейса в разделе Настройки.",
    "не работает": "Попробуйте перезагрузить страницу или нажмите /start.",
    "кабинет": "Ваш кабинет: https://leo-aide.online/cabinet",
    "оплата": "Поддержка оплаты временно недоступна. Следите за обновлениями!",
    "премиум": "Чтобы получить премиум, зайдите в кабинет → Финансы.",
    "админ": "Администратор ответит в течение 24 часов.",
    "тикет": "Вы уже отправили обращение. Ожидайте ответа.",
    "помощь": "Используйте /menu или зайдите в кабинет для помощи.",
    "обновить": "Перезагрузите страницу или нажмите /start.",
}

# --- Обработчик FAQ — должен быть ПОСЛЕДНИМ! ---
async def handle_support_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    for keyword, answer in SUPPORT_FAQ.items():
        if keyword in text:
            await update.message.reply_text(
                f"🤖 Автоответ:\n\n{answer}\n\nЕсли не помогло — администратор ответит в течение 24 часов.",
                disable_web_page_preview=True
            )
            return

# --- Дебаг: логируем ВСЕ входящие сообщения ---
async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        logger.debug(f"📨 DEBUG: Входящее сообщение: '{update.message.text}' от user_id={update.effective_user.id}")

# --- Отслеживание активности пользователя ---
async def track_user_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        await add_or_update_user(db_pool, user)

    # Логируем команды
    if update.message and update.message.text and update.message.text.startswith('/'):
        command = update.message.text.split()[0]
        await log_command_usage(db_pool, user.id, command)

# --- Клавиатура после /start ---
def get_start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Главное меню", callback_data="menu_main")],
        [InlineKeyboardButton("🌐 Mini App", url="https://leo-aide.online/")]
    ])

# --- Обработчик /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_or_update_user(db_pool, user)

    # Обработка реферальной ссылки
    if context.args and context.args[0].startswith("ref"):
        referrer_id = int(context.args[0][3:])
        if referrer_id != user.id:
            await register_referral(db_pool, referrer_id, user.id)

    role = await get_user_role(db_pool, user.id)
    role_text = {"user": "👤 Обычный", "premium": "💎 Премиум", "admin": "👮‍♂️ Админ"}.get(role, "👤 Обычный")

    await update.message.reply_html(
        f"👋 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
        f"🔹 Ваш статус: <b>{role_text}</b>\n\n"
        f"Выберите способ взаимодействия:",
        reply_markup=get_start_keyboard()
    )

# --- Фоновая задача: очистка неактивных пользователей и тикетов ---
async def cleanup_task(context: ContextTypes.DEFAULT_TYPE):
    if not db_pool:
        return
    await delete_inactive_users(db_pool, days=90)
    await cleanup_support_tickets(db_pool, days=7)

# --- Инициализация после запуска ---
async def on_post_init(app: Application):
    global db_pool
    logger.info("🔧 Инициализация БД...")
    db_pool = await create_db_pool()
    await init_db(db_pool)
    logger.info("✅ База данных инициализирована")

    await ensure_support_table_exists()
    app.bot_data['db_pool'] = db_pool

    # Сохраняем в bot.instance
    global_app = app
    global_bot = app.bot
    logger.info("✅ Бот и application сохранены в bot.instance")

    # Устанавливаем кнопку меню (≡)
    try:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🌐 Панель",
                web_app=WebAppInfo(url="https://leo-aide.online/")
            )
        )
        logger.info("🚀 Меню (≡) установлено")
    except Exception as e:
        logger.error(f"❌ Не удалось установить menu button: {e}")

    # Устанавливаем команды
    await app.bot.set_my_commands([
        ("start", "🚀 Начать"),
        ("menu", "🏠 Открыть меню"),
        ("help", "🔧 Помощь и поддержка"),
    ])
    logger.info("✅ Команды бота установлены")

    # Запуск фоновой задачи
    app.job_queue.run_repeating(cleanup_task, interval=24 * 3600, first=10)
    logger.info("⏰ Фоновая задача: очистка — запущена")

# --- Главная функция запуска ---
def main():
    app = (
        Application.builder()
        .token(os.getenv("BOT_TOKEN"))
        .post_init(on_post_init)
        .build()
    )

    # Группа -2: дебаг всех сообщений
    app.add_handler(MessageHandler(filters.ALL, debug_all_messages), group=-2)

    # Группа -1: отслеживание активности
    app.add_handler(TypeHandler(Update, track_user_activity), group=-1)

    # Группа 0: основные фичи
    help_setup(app)
    setup_menu(app)
    setup_admin_handlers(app)
    setup_role_handlers(app)
    setup_referral_handlers(app)
    setup_premium_handlers(app)
    setup_currency_handlers(app)
    setup_reminder_handlers(app)
    setup_subscription_handlers(app)
    setup_weather_handlers(app)  # ✅ Добавлено

    # Команда /start
    app.add_handler(CommandHandler("start", start), group=0)

    # Режим поддержки — группа 50
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message),
        group=50
    )

    # FAQ — последний обработчик, группа 100
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_faq),
        group=100
    )

    logger.info("🚀 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
# bot/features/admin.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,  # ← добавлен
    filters  # ← добавлен
)
from loguru import logger

from database import (
    get_user_role,
    set_user_role,
    is_admin,
    get_referral_stats,
    log_command_usage,
)

# Состояние: кто в режиме поиска
user_search_state = {}

# --- Проверка доступа ---
async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pool = context.application.bot_data['db_pool']
    user_id = update.effective_user.id
    if not await is_admin(pool, user_id):
        await update.message.reply_text("❌ Доступ запрещён")
        return False
    return True


# --- Главное меню админа ---
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    pool = context.application.bot_data['db_pool']
    user_id = update.effective_user.id

    # Логируем
    await log_command_usage(pool, user_id, '/admin')

    keyboard = [
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📣 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📝 Модерация", callback_data="admin_moderation")],
        [InlineKeyboardButton("🧩 Настройки", callback_data="admin_settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        "<b>👮‍♂️ Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=reply_markup
    )


# --- Обработчик нажатий ---
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pool = context.application.bot_data['db_pool']
    data = query.data

    if data == "admin_stats":
        total_users = await pool.fetchval("SELECT COUNT(*) FROM users")
        active_24h = await pool.fetchval("SELECT COUNT(*) FROM users WHERE last_seen > NOW() - INTERVAL '24 hours'")
        premium_users = await pool.fetchval("SELECT COUNT(*) FROM users WHERE role = 'premium'")

        # Топ команд за неделю
        cmd_count = await pool.fetch('''
            SELECT command, COUNT(*) FROM usage_stats
            WHERE timestamp > NOW() - INTERVAL '7 days'
            GROUP BY command ORDER BY COUNT(*) DESC LIMIT 5
        ''')
        cmd_text = "\n".join([f"  • <code>{c[0]}</code>: {c[1]}" for c in cmd_count]) if cmd_count else "Нет данных"

        text = f"""
📊 <b>Статистика (7 дней)</b>

👥 Всего пользователей: <b>{total_users}</b>
🟢 Активны за 24ч: <b>{active_24h}</b>
💎 Премиум: <b>{premium_users}</b>

🔥 Топ команд:
{cmd_text}
        """
        await query.edit_message_text(text, parse_mode='HTML', disable_web_page_preview=True)

    elif data == "admin_users":
        keyboard = [
            [InlineKeyboardButton("🔍 Найти пользователя", callback_data="admin_search_user")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👥 Управление пользователями", reply_markup=reply_markup)

    elif data == "admin_search_user":
        await query.edit_message_text("🆔 Введите ID пользователя:")
        user_search_state[query.from_user.id] = 'awaiting_id'

    elif data == "admin_back":
        await cmd_admin(update, context)


# --- Поиск пользователя ---
async def handle_message_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_search_state or user_search_state[user_id] != 'awaiting_id':
        return  # Игнорируем, если не ожидаем ввод

    try:
        target_id = int(update.message.text)
        pool = context.application.bot_data['db_pool']
        user = await pool.fetchrow("SELECT * FROM users WHERE id = $1", target_id)

        if not user:
            await update.message.reply_text("❌ Пользователь не найден")
            return

        referred = await get_referral_stats(pool, target_id)
        role_info = {'user': '👤 Обычный', 'premium': '💎 Премиум', 'admin': '👮‍♂️ Админ'}.get(user['role'], '👤')

        text = f"""
🔍 <b>Пользователь: {target_id}</b>

📝 Имя: {user['first_name']} {user['last_name'] or ''}
💬 Юзернейм: @{user['username'] or 'не указан'}
🔖 Роль: {role_info}
📅 Зарегистрирован: {user['created_at'].strftime('%d.%m.%Y')}
🕓 Последний визит: {user['last_seen'].strftime('%d.%m.%Y %H:%M')}
👥 Приглашено: {referred}
        """
        await update.message.reply_html(text)

        # Кнопки действий
        keyboard = [
            [InlineKeyboardButton("💎 Выдать премиум", callback_data=f"grant_premium_{target_id}")],
            [InlineKeyboardButton("👤 Сделать обычным", callback_data=f"grant_user_{target_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_users")]
        ]
        await update.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))

    except ValueError:
        await update.message.reply_text("❌ Введите корректный ID (число)")
    finally:
        user_search_state.pop(user_id, None)


# --- Выдача роли ---
async def grant_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("grant_"):
        _, role, target_id = data.split("_")
        target_id = int(target_id)
        pool = context.application.bot_data['db_pool']

        await set_user_role(pool, target_id, role)
        await query.edit_message_text(f"✅ Пользователю `{target_id}` выдана роль `{role}`")


# --- Регистрация обработчиков ---
def setup_admin_handlers(app):
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(grant_callback_handler, pattern="^grant_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_from_admin))

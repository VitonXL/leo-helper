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
        [InlineKeyboardButton("📩 Тикеты", callback_data="admin_support_tickets")],
        [InlineKeyboardButton("📝 Модерация", callback_data="admin_moderation")],
        [InlineKeyboardButton("🧩 Настройки", callback_data="admin_settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🛡️ <b>Панель администратора</b>\n\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
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

    elif data == "admin_support_tickets":
         pool = context.application.bot_data['db_pool']
         tickets = await pool.fetch('''
        SELECT ticket_id, user_id, first_name, message, status, created_at
        FROM support_tickets
        WHERE status = 'open'
        ORDER BY created_at DESC
        LIMIT 10
    ''')

    if not tickets:
        await query.edit_message_text("📭 Нет открытых тикетов")
        return

    text = "📬 <b>Открытые тикеты:</b>\n\n"
    for t in tickets:
        username = f"@{t['first_name']}" if t['first_name'] else "Без имени"
        created = t['created_at'].strftime('%d.%m %H:%M')
        text += f"📌 <b>ID: {t['ticket_id']}</b> | {username} | {created}\n"
        text += f"💬 {t['message'][:50]}...\n\n"

    await query.edit_message_text(text, parse_mode='HTML')

    # Кнопка "назад"
    await update.effective_message.reply_text(
        "👆 Выберите тикет и ответьте на это сообщение — ваш текст будет отправлен пользователю",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]])
    )


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

    # ✅ НОВОЕ: ответ от админа
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT & ~filters.COMMAND, forward_admin_reply))

# --- Пересылка сообщения от админа пользователю ---
async def forward_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Админ отвечает на сообщение с тикетом — бот перешлёт пользователю.
    """
    if not update.message or not update.message.reply_to_message:
        return

    reply = update.message.reply_to_message
    if not reply.text or not reply.text.startswith("ID: TICKET-"):
        return

    # Извлекаем ticket_id
    ticket_id = reply.text.split("|")[0].split("ID: ")[1].strip()

    pool = context.application.bot_data['db_pool']
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT user_id, first_name, message 
            FROM support_tickets 
            WHERE ticket_id = $1
        ''', ticket_id)

    if not row:
        await update.message.reply_text("❌ Тикет не найден.")
        return

    user_id = row['user_id']
    first_name = row['first_name']

    # Формируем сообщение
    admin_message = update.message.text_html
    response_text = f"💬 Администратор:\n\n{admin_message}"

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=response_text,
            parse_mode='HTML'
        )
        await update.message.reply_text(f"✅ Ответ отправлен пользователю {first_name}")
        logger.info(f"📨 Админ ответил пользователю {user_id} (тикет: {ticket_id})")
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось отправить: {e}")
        logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
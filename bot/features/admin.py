# bot/features/admin.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
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
        if update.message:
            await update.message.reply_text("❌ Доступ запрещён")
        return False
    return True


# --- Главное меню админа ---
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    pool = context.application.bot_data['db_pool']
    user_id = update.effective_user.id
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

    if update.message:
        await update.message.reply_text(
            "🛡️ <b>Панель администратора</b>\n\nВыберите раздел:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                "🛡️ <b>Панель администратора</b>\n\nВыберите раздел:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка редактирования: {e}")


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

        cmd_count = await pool.fetch('''
            SELECT command, COUNT(*) FROM usage_stats
            WHERE timestamp > NOW() - INTERVAL '7 days'
            GROUP BY command ORDER BY COUNT(*) DESC LIMIT 5
        ''')
        cmd_text = "\n".join([f"  • <code>{c[0]}</code>: {c[1]}" for c in cmd_count]) if cmd_count else "Нет данных"

        text = f"""
📊 <b>Статистика (7 дней)</b>

👥 Всего: <b>{total_users}</b>
🟢 Активны: <b>{active_24h}</b>
💎 Премиум: <b>{premium_users}</b>

🔥 Топ команд:
{cmd_text}
        """
        await query.edit_message_text(text, parse_mode='HTML', disable_web_page_preview=True)

    elif data == "admin_users":
        keyboard = [
            [InlineKeyboardButton("🔍 Найти", callback_data="admin_search_user")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
        ]
        await query.edit_message_text("👥 Управление", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_search_user":
        await query.edit_message_text("🆔 Введите ID:")
        user_search_state[query.from_user.id] = 'awaiting_id'

    elif data == "admin_back":
        await cmd_admin(update, context)

    elif data == "admin_support_tickets":
        tickets = await pool.fetch('''
            SELECT ticket_id, username, first_name, message, created_at
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
            username = f"@{t['username']}" if t['username'] else t['first_name']
            created = t['created_at'].strftime('%d.%m %H:%M')
            text += f"📌 <b>ID: {t['ticket_id']}</b> | {username} | {created}\n"
            text += f"💬 {t['message'][:60]}...\n\n"
        text += "\n👆 Ответьте на это сообщение, чтобы отправить ответ пользователю."

        await query.edit_message_text(
            text,
            parse_mode='HTML',
            disable_web_page_preview=True
        )


# --- Пересылка ответа админа ---
async def forward_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📩 forward_admin_reply: вызван")

    if not update.message:
        logger.warning("❌ Нет update.message")
        return
    if not update.message.reply_to_message:
        logger.warning("❌ Не ответ на сообщение")
        return

    reply = update.message.reply_to_message
    logger.info(f"📄 Реплай на: {reply.text[:100] if reply.text else 'нет текста'}")

    if not reply.text or "ID: TICKET-" not in reply.text:
        logger.warning("❌ Нет ID: TICKET- в тексте")
        return

    try:
        # Извлекаем ticket_id
        lines = reply.text.splitlines()
        ticket_line = next((line for line in lines if line.startswith("📌 ID:")), None)
        if not ticket_line:
            await update.message.reply_text("❌ Не найдена строка с ID.")
            return
        ticket_id = ticket_line.split("ID:")[1].split("|")[0].strip()
        logger.info(f"🔍 Извлечён ticket_id: {ticket_id}")

        pool = context.application.bot_data['db_pool']
        row = await pool.fetchrow('''
            SELECT user_id, username FROM support_tickets WHERE ticket_id = $1
        ''', ticket_id)

        if not row:
            await update.message.reply_text("❌ Тикет не найден.")
            logger.warning(f"❌ Тикет {ticket_id} не найден")
            return

        user_id = row['user_id']
        username = f"@{row['username']}" if row['username'] else "Пользователь"
        logger.info(f"🎯 Отправка ответа {user_id} ({username})")

        # Поддержка текст, фото, документы
        if update.message.text:
            admin_message = update.message.text_html
            await context.bot.send_message(
                chat_id=user_id,
                text=f"💬 Администратор:\n\n{admin_message}",
                parse_mode='HTML'
            )
        elif update.message.photo:
            caption = update.message.caption_html or ""
            await context.bot.send_photo(
                chat_id=user_id,
                photo=update.message.photo[-1].file_id,
                caption=f"🖼️ Администратор:\n\n{caption}",
                parse_mode='HTML'
            )
        elif update.message.document:
            caption = update.message.caption_html or ""
            await context.bot.send_document(
                chat_id=user_id,
                document=update.message.document.file_id,
                caption=f"📎 Администратор:\n\n{caption}",
                parse_mode='HTML'
            )

        await update.message.reply_text(f"✅ Ответ отправлен {username}")
        logger.info(f"✅ Ответ доставлен {user_id}")

    except Exception as e:
        logger.exception(f"💥 Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


# --- Поиск пользователя ---
async def handle_message_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_search_state or user_search_state[user_id] != 'awaiting_id':
        return

    try:
        target_id = int(update.message.text)
        pool = context.application.bot_data['db_pool']
        user = await pool.fetchrow("SELECT * FROM users WHERE id = $1", target_id)

        if not user:
            await update.message.reply_text("❌ Не найден")
            return

        referred = await get_referral_stats(pool, target_id)
        role_info = {'user': '👤', 'premium': '💎', 'admin': '👮‍♂️'}.get(user['role'], '👤')

        text = f"""
🔍 <b>Пользователь: {target_id}</b>

📝 Имя: {user['first_name']} {user['last_name'] or ''}
💬 Юзернейм: @{user['username'] or 'не указан'}
🔖 Роль: {role_info}
📅 Регистрация: {user['created_at'].strftime('%d.%m.%Y')}
🕓 Последний визит: {user['last_seen'].strftime('%d.%m %H:%M')}
👥 Приглашено: {referred}
        """
        await update.message.reply_html(text)

        keyboard = [
            [InlineKeyboardButton("💎 Премиум", callback_data=f"grant_premium_{target_id}")],
            [InlineKeyboardButton("👤 Обычный", callback_data=f"grant_user_{target_id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_users")]
        ]
        await update.message.reply_text("Действие:", reply_markup=InlineKeyboardMarkup(keyboard))

    except ValueError:
        await update.message.reply_text("❌ Введите число")
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
        await query.edit_message_text(f"✅ Роль `{role}` выдана `{target_id}`")


# --- Регистрация обработчиков ---
def setup_admin_handlers(app):
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(grant_callback_handler, pattern="^grant_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_from_admin))
    app.add_handler(MessageHandler(
        filters.REPLY & (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
        forward_admin_reply
    ))
# bot/features/admin.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
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


async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pool = context.application.bot_data['db_pool']
    user_id = update.effective_user.id
    if not await is_admin(pool, user_id):
        if update.message:
            await update.message.reply_text("❌ Доступ запрещён")
        return False
    return True


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
            logger.error(f"Ошибка: {e}")


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pool = context.application.bot_data['db_pool']
    data = query.data

    if data == "admin_stats":
        total_users = await pool.fetchval("SELECT COUNT(*) FROM users")
        active_24h = await pool.fetchval("SELECT COUNT(*) FROM users WHERE last_seen > NOW() - INTERVAL '24 hours'")
        premium_users = await pool.fetchval("SELECT COUNT(*) FROM users WHERE role = 'premium'")

        text = f"📊 <b>Статистика</b>\n\n👥 Всего: <b>{total_users}</b>\n🟢 Активны: <b>{active_24h}</b>\n💎 Премиум: <b>{premium_users}</b>"
        await query.edit_message_text(text, parse_mode='HTML')

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
        await admin_support_tickets_with_buttons(update, context)


async def admin_support_tickets_with_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pool = context.application.bot_data['db_pool']
    tickets = await pool.fetch('''
        SELECT ticket_id, username, first_name, message, created_at, status
        FROM support_tickets
        WHERE status = 'open'
        ORDER BY created_at DESC
        LIMIT 10
    ''')

    if not tickets:
        await query.edit_message_text("📭 Нет открытых тикетов")
        return

    for t in tickets:
        username = f"@{t['username']}" if t['username'] else t['first_name']
        created = t['created_at'].strftime('%d.%m %H:%M')
        text = f"📌 <b>ID: {t['ticket_id']}</b> | {username} | {created}\n\n💬 {t['message']}"

        keyboard = [
            [
                InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{t['ticket_id']}"),
                InlineKeyboardButton("✅ Закрыть", callback_data=f"close_{t['ticket_id']}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="👆 Используйте кнопки под каждым тикетом",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")
        ]])
    )

    try:
        await query.delete_message()
    except:
        pass


async def admin_ticket_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not (data.startswith("reply_") or data.startswith("close_")):
        return

    ticket_id = data.split("_", 1)[1]
    pool = context.application.bot_data['db_pool']

    row = await pool.fetchrow("SELECT user_id, username, message FROM support_tickets WHERE ticket_id = $1", ticket_id)
    if not row:
        await query.edit_message_text("❌ Тикет не найден")
        return

    if data.startswith("reply_"):
        username = f"@{row['username']}" if row['username'] else "Пользователь"
        await query.edit_message_text(
            f"📝 Ответ пользователю {username}\n\n💬 {row['message']}\n\nВведите текст ответа:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data="admin_support_tickets")
            ]])
        )
        context.user_data['awaiting_reply_to_ticket'] = ticket_id

    elif data.startswith("close_"):
        await pool.execute("UPDATE support_tickets SET status = 'closed' WHERE ticket_id = $1", ticket_id)
        username = f"@{row['username']}" if row['username'] else "Пользователь"
        try:
            await context.bot.send_message(
                chat_id=row['user_id'],
                text=f"🎫 Ваш тикет <code>{ticket_id}</code> закрыт.\n\nСпасибо за обращение!",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о закрытии: {e}")
        await query.edit_message_text(f"✅ Тикет <code>{ticket_id}</code> закрыт", parse_mode='HTML')


async def forward_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📩 forward_admin_reply: вызван")

    if not update.message:
        return

    # Проверяем, ждём ли мы ответ на тикет
    ticket_id = context.user_data.get('awaiting_reply_to_ticket')
    if not ticket_id:
        return

    pool = context.application.bot_data['db_pool']
    row = await pool.fetchrow("SELECT user_id, username FROM support_tickets WHERE ticket_id = $1", ticket_id)
    if not row:
        await update.message.reply_text("❌ Тикет не найден")
        context.user_data.pop('awaiting_reply_to_ticket', None)
        return

    user_id = row['user_id']
    username = f"@{row['username']}" if row['username'] else "Пользователь"

    try:
        if update.message.text:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"💬 Администратор:\n\n{update.message.text_html}",
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
        logger.info(f"✅ Ответ отправлен {user_id}")

    except Exception as e:
        logger.exception(f"❌ Ошибка при отправке: {e}")
        await update.message.reply_text(f"❌ Не удалось отправить: {e}")
    finally:
        context.user_data.pop('awaiting_reply_to_ticket', None)


async def handle_message_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_search_state:
        return

    if user_search_state[user_id] == 'awaiting_id':
        try:
            target_id = int(update.message.text)
            pool = context.application.bot_data['db_pool']
            user = await pool.fetchrow("SELECT * FROM users WHERE id = $1", target_id)

            if not user:
                await update.message.reply_text("❌ Пользователь не найден")
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


def setup_admin_handlers(app):
    # Высокий приоритет — group=40
    app.add_handler(CommandHandler("admin", cmd_admin), group=40)
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"), group=40)
    app.add_handler(CallbackQueryHandler(grant_callback_handler, pattern="^grant_"), group=40)
    app.add_handler(CallbackQueryHandler(admin_ticket_action, pattern="^(reply|close)_"), group=40)

    # Сначала — ответы
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            forward_admin_reply
        ),
        group=40
    )

    # Потом — поиск
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_from_admin),
        group=40
    )

    
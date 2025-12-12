# bot/commands/broadcast.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from datetime import datetime, timedelta
import asyncio
from bot.database import get_db, log_action

# Храним запланированные задачи
scheduled_broadcasts = {}

async def broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть меню рассылки"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Доступ запрещён")
        return

    keyboard = [
        [InlineKeyboardButton("📤 Создать рассылку", callback_data="broadcast_create")],
        [InlineKeyboardButton("📅 Запланированные", callback_data="broadcast_scheduled")],
        [InlineKeyboardButton("📜 История", callback_data="broadcast_history")],
        [InlineKeyboardButton("❌ Отменить рассылку", callback_data="broadcast_cancel")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📬 *Менеджер рассылок*", reply_markup=reply_markup, parse_mode='Markdown')


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if not is_admin(user_id):
        await query.answer("❌", show_alert=True)
        return

    if data == "broadcast_create":
        await query.message.reply_text(
            "Введите сообщение для рассылки.\n"
            "Поддерживается *Markdown*, кнопки и изображения.\n\n"
            "Или пришлите фото с подписью."
        )
        context.user_data['awaiting_broadcast_msg'] = True
        await query.answer()

    elif data == "broadcast_scheduled":
        await show_scheduled(query)
        await query.answer()

    elif data == "broadcast_history":
        await show_history(query)
        await query.answer()

    elif data == "broadcast_cancel":
        await show_cancellable(query)
        await query.answer()


async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id) or not context.user_data.get('awaiting_broadcast_msg'):
        return

    # Сохраним сообщение
    message_data = await save_message_for_broadcast(update, context)
    context.user_data.update({
        'broadcast_msg': message_data,
        'awaiting_broadcast_msg': False,
        'awaiting_broadcast_target': True
    })

    keyboard = [
        [InlineKeyboardButton("👥 Все", callback_data="target_all")],
        [InlineKeyboardButton("💎 Премиум", callback_data="target_premium")],
        [InlineKeyboardButton("🧍 Обычные", callback_data="target_free")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="broadcast_cancel_select")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎯 Кому отправить?", reply_markup=reply_markup)


async def broadcast_target_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "broadcast_cancel_select":
        await query.message.reply_text("❌ Создание рассылки отменено.")
        context.user_data.clear()
        await query.answer()
        return

    target_map = {
        "target_all": "all",
        "target_premium": "premium",
        "target_free": "free"
    }
    target = target_map.get(data)
    if not target:
        return

    context.user_data['broadcast_target'] = target
    context.user_data['awaiting_broadcast_target'] = False
    context.user_data['awaiting_broadcast_time'] = True

    keyboard = [
        [InlineKeyboardButton("🕐 Через 5 минут", callback_data="when_5")],
        [InlineKeyboardButton("🌅 Завтра утром (8:00)", callback_data="when_tomorrow")],
        [InlineKeyboardButton("📅 Указать дату и время", callback_data="when_custom")],
        [InlineKeyboardButton("🔙 Назад", callback_data="broadcast_back_to_target")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("⏰ Когда отправить?", reply_markup=reply_markup)


async def broadcast_time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    send_at = datetime.now()

    if data == "when_5":
        send_at += timedelta(minutes=5)
    elif data == "when_tomorrow":
        send_at = send_at.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
    elif data == "when_custom":
        await query.message.reply_text("Введите дату и время в формате: ДД.ММ.ГГГГ ЧЧ:ММ")
        context.user_data['awaiting_broadcast_time_input'] = True
        context.user_data['awaiting_broadcast_time'] = False
        await query.answer()
        return

    await schedule_broadcast(query, context, send_at)
    await query.answer()


async def schedule_broadcast(query, context: ContextTypes.DEFAULT_TYPE, send_at: datetime):
    msg_data = context.user_data['broadcast_msg']
    target = context.user_data['broadcast_target']

    # Сохраняем в БД
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO broadcasts (message, target, send_at, status)
        VALUES (%s, %s, %s, 'scheduled')
        RETURNING id
    """, (str(msg_data), target, send_at))
    broadcast_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    # Назначаем задачу
    job = context.job_queue.run_once(
        send_scheduled_broadcast,
        when=send_at,
        name=f"broadcast_{broadcast_id}",
        data={
            'broadcast_id': broadcast_id,
            'message': msg_data,
            'target': target
        }
    )
    scheduled_broadcasts[broadcast_id] = job

    await query.message.reply_text(
        f"✅ Рассылка запланирована на {send_at.strftime('%d.%m.%Y в %H:%M')}\n"
        f"🎯 Цель: {target}\n"
        f"📬 ID: {broadcast_id}"
    )
    context.user_data.clear()


async def send_scheduled_broadcast(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    broadcast_id = data['broadcast_id']
    msg_data = data['message']
    target = data['target']

    user_ids = _get_target_users(target)
    success = 0

    for uid in user_ids:
        try:
            await _send_message_by_data(context.bot, uid, msg_data)
            success += 1
        except:
            pass
        await asyncio.sleep(0.03)

    # Обновляем статус
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE broadcasts SET status = 'sent', sent_count = %s WHERE id = %s
    """, (success, broadcast_id))
    conn.commit()
    conn.close()


def _get_target_users(target: str):
    conn = get_db()
    cursor = conn.cursor()
    if target == 'all':
        cursor.execute("SELECT user_id FROM users")
    elif target == 'premium':
        cursor.execute("SELECT user_id FROM users WHERE is_premium = TRUE")
    elif target == 'free':
        cursor.execute("SELECT user_id FROM users WHERE is_premium = FALSE")
    users = [r['user_id'] for r in cursor.fetchall()]
    conn.close()
    return users


async def _send_message_by_data(bot, chat_id, data: dict):
    if data['type'] == 'text':
        await bot.send_message(chat_id, data['text'], parse_mode=ParseMode.MARKDOWN)
    elif data['type'] == 'photo':
        await bot.send_photo(chat_id, data['photo'], caption=data.get('caption'), parse_mode=ParseMode.MARKDOWN)


async def save_message_for_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        caption = update.message.caption or ""
        return {'type': 'photo', 'photo': file_id, 'caption': caption}
    else:
        text = update.message.text or update.message.caption or "Без текста"
        return {'type': 'text', 'text': text}


# --- Вспомогательные функции ---
async def show_scheduled(query):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM broadcasts WHERE status = 'scheduled' ORDER BY send_at")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await query.message.reply_text("📭 Нет запланированных рассылок.")
        return

    msg = "📅 *Запланированные рассылки*\n\n"
    for r in rows:
        when = r['send_at'].strftime('%d.%m.%Y %H:%M')
        msg += f"🔹 ID: `{r['id']}` — {when} — {r['target']}\n"
    await query.message.reply_text(msg, parse_mode='Markdown')


async def show_history(query):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM broadcasts WHERE status != 'scheduled' ORDER BY send_at DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await query.message.reply_text("📭 История пуста.")
        return

    msg = "📜 *История рассылок*\n\n"
    for r in rows:
        when = r['send_at'].strftime('%d.%m.%Y')
        msg += f"🔹 {when} | {r['target']} | ✅ {r['sent_count']} получателей\n"
    await query.message.reply_text(msg, parse_mode='Markdown')


async def show_cancellable(query):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM broadcasts WHERE status = 'scheduled'")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await query.message.reply_text("❌ Нет активных рассылок для отмены.")
        return

    keyboard = [
        [InlineKeyboardButton(f"Отменить #{r['id']}", callback_data=f"cancel_bcast_{r['id']}")]
        for r in rows
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("❌ Выберите рассылку для отмены:", reply_markup=reply_markup)


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        broadcast_id = int(query.data.split('_')[-1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE broadcasts SET status = 'cancelled' WHERE id = %s AND status = 'scheduled'", (broadcast_id,))
        if cursor.rowcount > 0:
            if broadcast_id in scheduled_broadcasts:
                scheduled_broadcasts[broadcast_id].schedule_removal()
                del scheduled_broadcasts[broadcast_id]
            await query.message.reply_text(f"✅ Рассылка #{broadcast_id} отменена.")
        else:
            await query.message.reply_text("❌ Рассылка уже отправлена или не найдена.")
        conn.commit()
        conn.close()
    except:
        await query.message.reply_text("❌ Ошибка при отмене.")
    await query.answer()

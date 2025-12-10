# bot/admin.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import db
import logging

logger = logging.getLogger(__name__)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != 17999560429:
        await query.answer("📛 Доступ запрещён", show_alert=True)
        return

    total_users = len(db.get_all_users())
    active_premium = sum(1 for u in db.get_all_users() if db.is_premium(u["user_id"]))
    referrals_total = sum(db.get_referral_count(u["user_id"]) for u in db.get_all_users())

    text = (
        f"🔐 <b>Админ-панель</b>\n\n"
        f"👥 Всего: {total_users}\n"
        f"💎 Премиум: {active_premium}\n"
        f"🔗 Рефералов: {referrals_total}"
    )
    keyboard = [
        [InlineKeyboardButton("📩 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎁 Выдать премиум", callback_data="admin_grant_premium")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📄 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != 1799560429:
        await query.answer("❌", show_alert=True)
        return

    users = db.get_all_users()
    premium_count = sum(1 for u in users if db.is_premium(u["user_id"]))
    avg_refs = sum(db.get_referral_count(u["user_id"]) for u in users) / len(users) if users else 0

    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"• Пользователей: <b>{len(users)}</b>\n"
        f"• Премиум: <b>{premium_count}</b>\n"
        f"• Среднее рефералов: <b>{avg_refs:.1f}</b>"
    )
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
    ]))

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != 1799560429:
        await query.answer("❌", show_alert=True)
        return
    await query.edit_message_text("📢 Введите сообщение для рассылки:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
    ]))
    context.user_data["awaiting"] = "admin_broadcast_message"

async def admin_broadcast_send(context: ContextTypes.DEFAULT_TYPE, message: str):
    success = 0
    for user in db.get_all_users():
        try:
            await context.bot.send_message(user["user_id"], message)
            success += 1
        except:
            pass
    logger.info(f"Рассылка завершена: {success} из {len(db.get_all_users())}")
    return success

async def admin_grant_premium_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != 1799560429:
        await query.answer("❌", show_alert=True)
        return
    await query.edit_message_text("🆔 Введите ID пользователя:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
    ]))
    context.user_data["awaiting"] = "admin_grant_premium_id"

async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != 1799560429:
        await query.answer("❌", show_alert=True)
        return

    with sqlite3.connect("bot.db") as conn:
        cursor = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10")
        logs = cursor.fetchall()

    text = "📄 Последние действия:\n\n"
    for log in logs:
        text += f"• <code>{log[1]}</code> | {log[3]}\n"
    text = text.rstrip()

    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
    ]))

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != 1799560429:
        await update.message.reply_text("⛔ Нет доступа")
        return

    text = "🔐 Добро пожаловать в админ-панель!"
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📩 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎁 Выдать премиум", callback_data="admin_grant_premium")],
        [InlineKeyboardButton("📄 Логи", callback_data="admin_logs")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

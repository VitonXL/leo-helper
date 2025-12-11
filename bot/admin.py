# bot/admin.py
import logging
import sqlite3  # ✅ Теперь импорт есть
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import db

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- АДМИН-ПАНЕЛЬ ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📤 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚡ Выдать премиум", callback_data="admin_grant_premium")],
        [InlineKeyboardButton("📋 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    await query.edit_message_text("🔧 Админ-панель", reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_count = db.get_user_count()
    premium_count = db.get_premium_count()
    today_joined = db.get_today_joined_count()

    text = (
        "📈 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{user_count}</b>\n"
        f"💎 Премиум: <b>{premium_count}</b>\n"
        f"📆 Сегодня зашло: <b>{today_joined}</b>"
    )
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=back_button())


async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("✉️ Введите сообщение для рассылки:")
    context.user_data["awaiting"] = "admin_broadcast_message"


async def admin_grant_premium_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("🆔 Введите ID пользователя:")
    context.user_data["awaiting"] = "admin_grant_premium_id"


async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        with sqlite3.connect("bot.db") as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50")
            logs = cur.fetchall()

        if logs:
            text = "📋 Последние 50 логов:\n\n"
            for log in logs:
                text += f"[{log['timestamp']}] {log['user_id']}: {log['action']}\n"
        else:
            text = "Логов пока нет"

        await query.edit_message_text(text, reply_markup=back_button())
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}", reply_markup=back_button())


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user or not user["is_admin"]:
        await update.message.reply_text("❌ Доступ запрещён")
        return
    await show_admin_panel(update, context)


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await admin_panel(update, context)
    else:
        keyboard = [[InlineKeyboardButton("🔧 Админ-панель", callback_data="admin_panel")]]
        await update.message.reply_text("Добро пожаловать, админ!", reply_markup=InlineKeyboardMarkup(keyboard))


def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]])

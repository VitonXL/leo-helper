# bot/features/roles.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_user_role, set_user_role, is_admin


async def cmd_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.application.bot_data['db_pool']  # ✅ Правильный доступ

    if not await is_admin(pool, user_id):
        await update.message.reply_text("❌ Доступ запрещён")
        return

    if len(context.args) != 2:
        await update.message.reply_text("Использование: /role <user_id> <user|premium|admin>")
        return

    try:
        target_id = int(context.args[0])
        new_role = context.args[1]
        await set_user_role(pool, target_id, new_role)
        await update.message.reply_text(f"✅ Пользователю `{target_id}` установлена роль `{new_role}`", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


def setup_role_handlers(app):
    app.add_handler(CommandHandler("role", cmd_role))

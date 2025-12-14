# bot/features/premium.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from ..database import is_premium_or_admin


async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Доступ только для premium и admin"""
    if not await is_premium_or_admin(update.get_bot().bot.db_pool, update.effective_user.id):
        await update.message.reply_text("💎 Эта функция доступна только премиум-пользователям")
        return
    await update.message.reply_text("🔓 Премиум-функция активирована!")


def setup_premium_handlers(app):
    app.add_handler(CommandHandler("premium", cmd_premium))

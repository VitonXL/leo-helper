# bot/features/premium.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

# ✅ Абсолютный импорт
from database import is_premium_or_admin


async def cmd_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.application.bot_data['db_pool']
    if not await is_premium_or_admin(pool, update.effective_user.id):
        await update.message.reply_text("💎 Эта функция доступна только премиум-пользователям")
        return
    await update.message.reply_text("🔓 Премиум-функция активирована!")


def setup_premium_handlers(app):
    app.add_handler(CommandHandler("premium", cmd_premium))

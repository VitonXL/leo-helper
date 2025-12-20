# bot/features/referrals.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from bot.database import register_referral, get_referral_stats


async def cmd_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']
    user_id = user.id

    referred = await get_referral_stats(pool, user_id)
    link = f"https://t.me/your_bot?start=ref{user_id}"

    await update.message.reply_html(
        text=f"🔗 Ваша ссылка:\n<code>{link}</code>\n\n📬 Приглашено: <b>{referred}</b>",
        parse_mode='HTML'
    )


def setup_referral_handlers(app):
    app.add_handler(CommandHandler("referral", cmd_referral))

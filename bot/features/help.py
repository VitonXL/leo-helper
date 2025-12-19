from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import get_db_pool

# Состояние для сбора сообщения
SUPPORT_WAITING = {}

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📬 Написать в поддержку", callback_data="help_support")]
    ]
    await update.message.reply_text(
        "🔧 Доступные команды:\n"
        "/start — начать\n"
        "/menu — открыть меню\n\n"
        "Если есть вопрос — пиши в поддержку!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def start_support_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    SUPPORT_WAITING[user.id] = True

    await query.edit_message_text(
        "📬 Напишите ваше сообщение в техподдержку.\n"
        "Опишите проблему — и мы ответим в ближайшее время."
    )


async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in SUPPORT_WAITING:
        return

    text = update.message.text.strip()
    if len(text) < 5:
        await update.message.reply_text("Пожалуйста, опишите проблему подробнее.")
        return

    # Сохраняем в БД
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO support_tickets (user_id, username, first_name, message)
            VALUES ($1, $2, $3, $4)
        """, user.id, user.username, user.first_name, text)

    await update.message.reply_text("✅ Ваше сообщение отправлено! Мы ответим в ближайшее время.")
    del SUPPORT_WAITING[user.id]


def setup(application):
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(start_support_chat, pattern="^help_support$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message))
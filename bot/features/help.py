# bot/features/help.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import get_db_pool
from loguru import logger

# Состояние ожидания
SUPPORT_WAITING = set()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📬 Написать в поддержку", callback_data="help_support")]]
    await update.message.reply_text(
        "🔧 Доступные команды:\n"
        "/start — начать\n"
        "/menu — главное меню\n\n"
        "Если нужна помощь — напишите в поддержку!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def start_support_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    SUPPORT_WAITING.add(user.id)
    await query.edit_message_text("📬 Опишите вашу проблему — мы ответим в ближайшее время.")


async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # ✅ Разрешаем обработку, только если пользователь в режиме поддержки
    if user.id not in SUPPORT_WAITING:
        return  # ← Просто выходим, не блокируем, чтобы FAQ мог сработать

    text = update.message.text.strip()
    if len(text) < 5:
        await update.message.reply_text("Пожалуйста, опишите проблему подробнее.")
        return

    logger.info(f"📩 Пользователь {user.id} отправляет в поддержку: {text[:50]}...")
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO support_tickets (user_id, username, first_name, message)
                VALUES ($1, $2, $3, $4)
            """, user.id, user.username, user.first_name, text)

        logger.info(f"✅ Тикет от {user.id} сохранён в БД")
        await update.message.reply_text("✅ Ваше сообщение отправлено! Мы ответим в ближайшее время.")

    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении тикета: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка отправки. Сообщим админу.")

    finally:
        SUPPORT_WAITING.discard(user.id)
        logger.info(f"🧹 {user.id} удалён из режима поддержки")


def setup(application):
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(start_support_chat, pattern="^help_support$"))
    # 🟡 Важно: handle_support_message остаётся, но НЕ блокирует других
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message))
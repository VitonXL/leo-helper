# bot/features/help.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database import get_db_pool
from loguru import logger
import random

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
    if user.id not in SUPPORT_WAITING:
        return  # пропускаем, чтобы FAQ мог сработать

    text = update.message.text.strip()
    if len(text) < 5:
        await update.message.reply_text("Пожалуйста, опишите проблему подробнее.")
        return

    logger.info(f"📩 Пользователь {user.id} отправляет в поддержку: {text[:50]}...")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Генерируем ticket_id
            ticket_id = f"TICKET-{1000 + user.id % 10000:04d}-{random.randint(10, 99)}"
            
            # Сохраняем
            await conn.execute("""
                INSERT INTO support_tickets (user_id, username, first_name, message, ticket_id)
                VALUES ($1, $2, $3, $4, $5)
            """, user.id, user.username, user.first_name, text, ticket_id)

        # ✅ Ответ пользователю
        await update.message.reply_text(
            f"📩 Ваше обращение **{ticket_id}** принято!\n\n"
            "✅ Мы уже работаем над ним.\n"
            "⏳ Администратор ответит в течение 24 часов.",
            parse_mode="Markdown"
        )

        logger.info(f"✅ Тикет {ticket_id} сохранён для {user.id}")

    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении тикета: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка отправки. Админ уже знает.")

    finally:
        SUPPORT_WAITING.discard(user.id)
        logger.info(f"🧹 {user.id} удалён из режима поддержки")


def setup(application):
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(start_support_chat, pattern="^help_support$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message))
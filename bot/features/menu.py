# bot/features/menu.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            {"text": "ℹ️ Помощь"},
            {"text": "👤 Мой профиль"}
        ],
        [
            {"text": "🚀 Возможности"},
            {"text": "❌ Скрыть меню"}
        ]
    ]

    await update.message.reply_text(
        "📌 *Главное меню*\n\nВыбери раздел:",
        reply_markup={
            "keyboard": keyboard,
            "resize_keyboard": True
        },
        parse_mode='Markdown'
    )


async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "ℹ️ Помощь":
        await update.message.reply_text(
            "🔧 Я — *Лео*, твой личный помощник.\n\n"
            "Доступные команды:\n"
            "• /start — перезапустить диалог\n"
            "• /help — показать это сообщение\n"
            "• /menu — открыть меню\n\n"
            "Скоро я научусь помогать с делами, напоминаниями и многим другим!",
            parse_mode='Markdown'
        )

    elif text == "👤 Мой профиль":
        user = update.effective_user
        await update.message.reply_text(
            f"📋 *Ваш профиль:*\n"
            f"• Имя: {user.full_name}\n"
            f"• ID: {user.id}\n"
            f"• Username: @{user.username or 'не задан'}",
            parse_mode='Markdown'
        )

    elif text == "🚀 Возможности":
        await update.message.reply_text(
            "🌟 *Возможности Лео (в разработке):*\n"
            "• Напоминания\n"
            "• Список дел\n"
            "• Интеграция с календарём\n"
            "• Веб-панель управления\n\n"
            "Следи за обновлениями!",
            parse_mode='Markdown'
        )

    elif text == "❌ Скрыть меню":
        await update.message.reply_text(
            "⌨️ Клавиатура скрыта.",
            reply_markup={"remove_keyboard": True}
        )


def setup(application):
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(
        MessageHandler(
            filters.Regex("^(ℹ️ Помощь|👤 Мой профиль|🚀 Возможности|❌ Скрыть меню)$"),
            handle_menu_buttons
        )
    )

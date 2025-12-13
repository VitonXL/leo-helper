# bot/features/menu.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler


# Функция для создания клавиатуры
def get_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help"),
            InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")
        ],
        [
            InlineKeyboardButton("🚀 Возможности", callback_data="menu_features")
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="menu_refresh"),
            InlineKeyboardButton("🗑 Закрыть", callback_data="menu_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Главное меню*\n\nВыбери действие:",
        reply_markup=get_menu_keyboard(),
        parse_mode='Markdown'
    )


async def handle_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие

    user = update.effective_user

    data = query.data

    if data == "menu_help":
        text = (
            "🔧 *Помощь*\n\n"
            "Я — *Лео*, твой личный помощник.\n\n"
            "Доступные команды:\n"
            "• /start — начать\n"
            "• /menu — открыть меню\n\n"
            "Скоро я научусь помогать с делами и напоминаниями!"
        )
        await query.edit_message_text(text, reply_markup=get_menu_keyboard(), parse_mode='Markdown')

    elif data == "menu_profile":
        text = (
            "📋 *Ваш профиль:*\n"
            f"• Имя: {user.full_name}\n"
            f"• ID: {user.id}\n"
            f"• Username: @{user.username or 'не задан'}"
        )
        await query.edit_message_text(text, reply_markup=get_menu_keyboard(), parse_mode='Markdown')

    elif data == "menu_features":
        text = (
            "🌟 *Возможности Лео (в разработке):*\n"
            "• Напоминания\n"
            "• Список дел\n"
            "• Календарь\n"
            "• Веб-панель\n\n"
            "Следи за обновлениями — скоро всё будет!"
        )
        await query.edit_message_text(text, reply_markup=get_menu_keyboard(), parse_mode='Markdown')

    elif data == "menu_refresh":
        text = "📌 *Главное меню*\n\nВыбери действие:"
        await query.edit_message_text(text, reply_markup=get_menu_keyboard(), parse_mode='Markdown')

    elif data == "menu_close":
        await query.delete_message()


def setup(application):
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CallbackQueryHandler(handle_menu_callbacks, pattern=r"^menu_"))

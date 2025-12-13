# bot/features/start.py

from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler


def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚀 Начать", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Устанавливаем команды в Telegram
    commands = [
        BotCommand("start", "Перезапустить бота"),
        BotCommand("menu", "Открыть главное меню"),
    ]
    await context.bot.set_my_commands(commands)

    # Приветственное сообщение
    await update.message.reply_text(
        "✨ *Добро пожаловать в Лео Помощник!* \n\n"
        "Я — твой личный цифровой ассистент.\n"
        "Помогу с задачами, информацией и развлечениями.\n\n"
        "Нажми кнопку ниже, чтобы начать:",
        reply_markup=get_start_keyboard(),
        parse_mode='Markdown'
    )


def setup(application):
    application.add_handler(CommandHandler("start", start_command))

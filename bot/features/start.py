# bot/features/start.py

from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler


# Кнопка "Открыть меню"
def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("📌 Открыть меню", callback_data="menu_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Устанавливаем команды в списке /
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("menu", "Открыть главное меню"),
    ]
    await context.bot.set_my_commands(commands)

    # Отправляем приветствие с inline-кнопкой
    await update.message.reply_text(
        "👋 Привет! Я — *Лео*, твой личный помощник.\n\n"
        "Я помогу тебе с задачами, информацией и развлечениями.\n\n"
        "Нажми кнопку ниже, чтобы открыть меню:",
        reply_markup=get_start_keyboard(),
        parse_mode='Markdown'
    )


def setup(application):
    application.add_handler(CommandHandler("start", start_command))

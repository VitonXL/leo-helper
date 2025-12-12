# bot/commands/games.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🎮 Игра 1", url="https://t.me/gamee"),
            InlineKeyboardButton("🎮 Игра 2", url="https://t.me/appstoregamebot")
        ],
        [InlineKeyboardButton("🕹️ Наши игры (скоро)", callback_data="our_games")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎮 Добро пожаловать в раздел игр!\n\n"
        "Здесь вы можете играть прямо в Telegram.\n"
        "Также скоро появятся наши собственные проекты!",
        reply_markup=reply_markup
    )

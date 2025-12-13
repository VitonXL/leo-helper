# bot/features/help.py
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start — начать общение",
        "/help — показать это сообщение",
        # сюда добавятся новые команды
    ]
    await update.message.reply_text("🔧 Доступные команды:\n\n" + "\n".join(commands))

def setup(application):
    application.add_handler(CommandHandler("help", help_command))

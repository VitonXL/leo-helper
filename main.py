from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from database import Database
import os
import logging

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальный экземпляр БД
db = Database()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.add_user(user.id, user.username, user.first_name)
    await update.message.reply_text(f"Привет, {user.first_name}! 👋 Я Лео — твой помощник.")
    logger.info(f"Пользователь {user.id} запустил бота")

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я пока только учусь, но уже могу запоминать пользователей! 💡\n"
        "Команды: /start — начать, /help — помощь"
    )

# Основная функция
async def main():
    # Загружаем переменные окружения
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

    # Подключаемся к БД
    await db.connect()
    await db.create_table()

    # Запускаем бота
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    print("🚀 Лео Помощник запущен и слушает обновления...")
    await app.run_polling()

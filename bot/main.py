# bot/main.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from .config import BOT_TOKEN
from .database import create_db_pool, init_db

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (id, username, first_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO NOTHING;
        ''', user.id, user.username, user.first_name)

    await update.message.reply_text(f"Привет, {user.first_name}! Я — Лео, твой помощник 🤖")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я пока только учусь. Но скоро смогу помогать с делами, напоминаниями и другим!")

# Основная функция
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Инициализация пула БД
    pool = application.bot_data['pool'] = create_db_pool()
    application.bot_data['init_db'] = init_db(pool)

    # Хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Запуск
    application.run_polling()

if __name__ == "__main__":
    main()

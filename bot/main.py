# bot/main.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import BOT_TOKEN
from bot.database import create_db_pool, init_db  # ← Должно работать
from bot.features import load_features

import logging
from telegram.ext import Application

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def post_init(application):
    try:
        pool = await create_db_pool()
        application.bot_data['pool'] = pool
        await init_db(pool)
        load_features(application)
        logger.info("✅ Бот запущен, БД подключена, модули загружены")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации: {e}")
        raise

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.run_polling()

if __name__ == "__main__":
    main()

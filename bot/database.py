# bot/database.py

import asyncpg
from .config import DATABASE_URL


async def create_db_pool():
    """
    Создаёт пул подключений к PostgreSQL.
    Вызывается при старте бота.
    """
    return await asyncpg.create_pool(DATABASE_URL)


async def init_db(pool):
    """
    Инициализирует таблицы в базе данных.
    Выполняется один раз при запуске.
    """
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                message TEXT,
                trigger_time TIMESTAMPTZ,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')

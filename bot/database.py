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
        # Таблица пользователей — обновлённая (с last_seen)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_bot BOOLEAN,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_seen TIMESTAMPTZ DEFAULT NOW()
            );
        ''')

        # Таблица напоминаний
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                message TEXT,
                trigger_time TIMESTAMPTZ,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')


# --- Работа с пользователями ---

async def add_or_update_user(pool, user):
    """
    Добавляет нового пользователя или обновляет last_seen, если уже существует.
    """
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (
                id, username, first_name, last_name, language_code, is_bot, last_seen, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            ON CONFLICT (id)
            DO UPDATE SET last_seen = NOW();
        ''', user.id, user.username, user.first_name, user.last_name,
                         user.language_code, user.is_bot)


async def delete_inactive_users(pool, days=90):
    """
    Удаляет пользователей, которые не заходили более `days` дней.
    Возвращает количество удалённых.
    """
    async with pool.acquire() as conn:
        deleted = await conn.fetchval('''
            DELETE FROM users
            WHERE last_seen < NOW() - $1 * INTERVAL '1 day'
            RETURNING COUNT(*);
        ''', days)
        print(f"🧹 Удалено неактивных пользователей: {deleted or 0}")
        return deleted or 0

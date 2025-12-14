# bot/database.py

import asyncpg
import os
from loguru import logger

# Получаем URL базы из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ Переменная DATABASE_URL не установлена в окружении")


async def create_db_pool():
    """
    Создаёт пул подключений к PostgreSQL.
    """
    return await asyncpg.create_pool(DATABASE_URL)


async def init_db(pool):
    """
    Инициализирует таблицы и применяет миграции для всех колонок.
    """
    async with pool.acquire() as conn:
        # Создаём таблицу (если ещё не создана)
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

        # Список миграций — безопасно добавляем колонки, если их нет
        migrations = [
            ('last_name', 'TEXT'),
            ('language_code', 'TEXT'),
            ('is_bot', 'BOOLEAN'),
            ('last_seen', 'TIMESTAMPTZ DEFAULT NOW()'),
        ]

        for column, type_def in migrations:
            try:
                await conn.execute(f'''
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS {column} {type_def};
                ''')
                logger.info(f"✅ Колонка {column} добавлена (если отсутствовала)")
            except Exception as e:
                logger.warning(f"⚠️ Колонка {column} уже существует или ошибка: {e}")

    logger.info("✅ База данных инициализирована")


async def add_or_update_user(pool, user):
    """
    Добавляет нового пользователя или обновляет last_seen.
    """
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (
                id, username, first_name, last_name, language_code, is_bot, last_seen, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            ON CONFLICT (id)
            DO UPDATE SET last_seen = NOW();
        ''', 
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        user.language_code,
        user.is_bot
    )
    logger.info(f"👤 Пользователь {user.id} добавлен/обновлён")


async def delete_inactive_users(pool, days=90):
    """
    Удаляет пользователей, не заходивших более `days` дней.
    Возвращает количество удалённых.
    """
    async with pool.acquire() as conn:
        count = await conn.fetchval('''
            SELECT COUNT(*) FROM users
            WHERE last_seen < NOW() - $1 * INTERVAL '1 day';
        ''', days)

        await conn.execute('''
            DELETE FROM users
            WHERE last_seen < NOW() - $1 * INTERVAL '1 day';
        ''', days)

        if count > 0:
            logger.info(f"🧹 Удалено неактивных пользователей: {count}")
        else:
            logger.debug("✅ Нет неактивных пользователей для удаления")

        return count

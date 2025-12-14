# bot/database.py

import asyncpg
import os
from loguru import logger

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ Переменная DATABASE_URL не установлена")

# Глобальный пул
db_pool = None


async def create_db_pool():
    """Создаёт пул подключений"""
    return await asyncpg.create_pool(DATABASE_URL)


async def init_db(pool):
    """Инициализирует таблицы и применяет миграции"""
    async with pool.acquire() as conn:
        # Пользователи
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_bot BOOLEAN,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_seen TIMESTAMPTZ DEFAULT NOW()
            );
        ''')

        # Напоминания
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

        # Рефералы
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                referred_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')

        # Миграции
        migrations = [
            ('last_name', 'TEXT'),
            ('language_code', 'TEXT'),
            ('is_bot', 'BOOLEAN'),
            ('last_seen', 'TIMESTAMPTZ DEFAULT NOW()'),
            ('role', "TEXT NOT NULL DEFAULT 'user'"),
        ]

        for column, type_def in migrations:
            try:
                await conn.execute(f'ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} {type_def};')
                logger.info(f"✅ Колонка {column} добавлена")
            except Exception as e:
                logger.warning(f"⚠️ Колонка {column}: {e}")

    logger.info("✅ База данных инициализирована")


# --- Работа с пользователями ---
async def add_or_update_user(pool, user):
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
    logger.info(f"👤 Пользователь {user.id} добавлен/обновлён")


async def get_user_role(pool, user_id: int) -> str:
    async with pool.acquire() as conn:
        role = await conn.fetchval('SELECT role FROM users WHERE id = $1', user_id)
        return role or 'user'


async def set_user_role(pool, user_id: int, role: str):
    valid_roles = ['user', 'premium', 'admin']
    if role not in valid_roles:
        raise ValueError(f"Роль должна быть одной из: {valid_roles}")
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET role = $1 WHERE id = $2', role, user_id)
    logger.info(f"🔐 Роль пользователя {user_id}: {role}")


async def is_admin(pool, user_id: int) -> bool:
    role = await get_user_role(pool, user_id)
    return role == 'admin'


async def is_premium_or_admin(pool, user_id: int) -> bool:
    role = await get_user_role(pool, user_id)
    return role in ['premium', 'admin']


# --- Рефералы ---
async def register_referral(pool, referrer_id: int, referred_id: int):
    async with pool.acquire() as conn:
        try:
            await conn.execute('''
                INSERT INTO referrals (referrer_id, referred_id) VALUES ($1, $2)
            ''', referrer_id, referred_id)
            logger.info(f"👥 Реферал: {referred_id} пришёл от {referrer_id}")
            return True
        except asyncpg.UniqueViolationError:
            logger.debug(f"⚠️ Пользователь {referred_id} уже был приглашён")
            return False


async def get_referral_stats(pool, user_id: int):
    async with pool.acquire() as conn:
        referred = await conn.fetchval('''
            SELECT COUNT(*) FROM referrals WHERE referrer_id = $1
        ''', user_id)
        return referred or 0


# --- Очистка ---
async def delete_inactive_users(pool, days=90):
    async with pool.acquire() as conn:
        count = await conn.fetchval('''
            SELECT COUNT(*) FROM users
            WHERE last_seen < NOW() - $1 * INTERVAL '1 day'
        ''', days)
        await conn.execute('''
            DELETE FROM users
            WHERE last_seen < NOW() - $1 * INTERVAL '1 day'
        ''', days)
        if count > 0:
            logger.info(f"🧹 Удалено неактивных: {count}")
        else:
            logger.debug("✅ Нет неактивных для удаления")
        return count

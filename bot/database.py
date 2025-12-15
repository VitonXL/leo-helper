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
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        logger.info("✅ Пул подключений к БД создан")
        return pool
    except Exception as e:
        logger.critical(f"❌ Не удалось создать пул БД: {e}")
        raise


async def init_db(pool):
    """
    Инициализирует все таблицы и применяет миграции.
    """
    async with pool.acquire() as conn:
        # --- Таблица пользователей ---
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
                last_seen TIMESTAMPTZ DEFAULT NOW(),
                premium_expires TIMESTAMPTZ,
                theme TEXT DEFAULT 'light',
                language TEXT DEFAULT 'ru'
            );
        ''')

        # --- Таблица напоминаний ---
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

        # --- Таблица рефералов ---
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                referred_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')

        # --- Таблица статистики использования команд ---
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS usage_stats (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                command TEXT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
        ''')

        # --- Миграции — расширения ---
        migrations = [
            ('theme', "TEXT DEFAULT 'light'"),
            ('language', "TEXT DEFAULT 'ru'"),
            ('last_name', 'TEXT'),
            ('language_code', 'TEXT'),
            ('is_bot', 'BOOLEAN'),
            ('last_seen', 'TIMESTAMPTZ DEFAULT NOW()'),
            ('role', "TEXT NOT NULL DEFAULT 'user'"),
            ('premium_expires', 'TIMESTAMPTZ'),
        ]

        for column, type_def in migrations:
            try:
                await conn.execute(f'''
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS {column} {type_def};
                ''')
                logger.info(f"✅ Колонка {column} добавлена (если отсутствовала)")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при добавлении колонки {column}: {e}")

    logger.info("✅ Все таблицы и миграции применены")


# --- Работа с пользователями ---
async def add_or_update_user(pool, user):
    """
    Добавляет или обновляет пользователя.
    """
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (
                id, username, first_name, last_name, language_code, is_bot, last_seen, created_at, language
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW(), $5)
            ON CONFLICT (id)
            DO UPDATE SET 
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                language_code = EXCLUDED.language_code,
                last_seen = NOW();
        ''', 
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        user.language_code,
        user.is_bot
    )
    logger.info(f"👤 Пользователь {user.id} добавлен/обновлён")


async def get_user_role(pool, user_id: int) -> str:
    """
    Возвращает роль пользователя.
    """
    async with pool.acquire() as conn:
        role = await conn.fetchval('SELECT role FROM users WHERE id = $1', user_id)
        return role or 'user'


async def set_user_role(pool, user_id: int, role: str):
    """
    Устанавливает роль пользователю.
    """
    valid_roles = ['user', 'premium', 'admin']
    if role not in valid_roles:
        raise ValueError(f"Роль должна быть одной из: {valid_roles}")

    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET role = $1 WHERE id = $2', role, user_id)
    logger.info(f"🔐 Пользователю {user_id} установлена роль: {role}")


async def is_admin(pool, user_id: int) -> bool:
    """
    Проверяет, является ли пользователь админом.
    """
    role = await get_user_role(pool, user_id)
    return role == 'admin'


async def is_premium_or_admin(pool, user_id: int) -> bool:
    """
    Проверяет, имеет ли пользователь премиум или админ-доступ.
    """
    role = await get_user_role(pool, user_id)
    return role in ['premium', 'admin']


# --- НОВОЕ: Работа с настройками интерфейса ---
async def get_user_settings(pool, user_id: int) -> dict:
    """
    Возвращает настройки пользователя: тема, язык.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT theme, language FROM users WHERE id = $1
        ''', user_id)
        if row:
            return {
                "theme": row["theme"] or "light",
                "language": row["language"] or "ru"
            }
        return {"theme": "light", "language": "ru"}


async def update_user_theme(pool, user_id: int, theme: str):
    """
    Обновляет тему пользователя.
    """
    if theme not in ["light", "dark"]:
        raise ValueError("Тема должна быть 'light' или 'dark'")

    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET theme = $1 WHERE id = $2', theme, user_id)
    logger.info(f"🎨 Пользователь {user_id} сменил тему: {theme}")


async def update_user_language(pool, user_id: int, lang: str):
    """
    Обновляет язык интерфейса пользователя.
    """
    if lang not in ["ru", "en"]:
        raise ValueError("Язык должен быть 'ru' или 'en'")

    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET language = $1 WHERE id = $2', lang, user_id)
    logger.info(f"🌐 Пользователь {user_id} сменил язык: {lang}")


# --- Рефералы ---
async def register_referral(pool, referrer_id: int, referred_id: int):
    """
    Регистрирует реферала.
    """
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


async def get_referral_stats(pool, user_id: int) -> int:
    """
    Возвращает количество приглашённых пользователем.
    """
    async with pool.acquire() as conn:
        count = await conn.fetchval('''
            SELECT COUNT(*) FROM referrals WHERE referrer_id = $1
        ''', user_id)
        return count or 0


# --- Статистика ---
async def log_command_usage(pool, user_id: int, command: str):
    """
    Логирует использование команды.
    """
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO usage_stats (user_id, command) VALUES ($1, $2)
        ''', user_id, command)
    logger.debug(f"📊 Команда: {command} от {user_id}")


# --- Очистка неактивных ---
async def delete_inactive_users(pool, days=90):
    """
    Удаляет пользователей, не заходивших более `days` дней.
    """
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


# === Глобальный пул подключений ===
_db_pool = None


async def get_db_pool():
    """
    Возвращает пул подключений к БД. Создаёт, если ещё не создан.
    """
    global _db_pool
    if _db_pool is None:
        _db_pool = await create_db_pool()
    return _db_pool

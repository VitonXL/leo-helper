# database.py
import asyncpg
import os
from loguru import logger

# Получаем URL базы из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ Переменная DATABASE_URL не установлена в окружении")

# Глобальный пул
_db_pool = None


async def create_db_pool():
    """
    Создаёт пул подключений к PostgreSQL.
    """
    global _db_pool
    try:
        _db_pool = await asyncpg.create_pool(DATABASE_URL)
        logger.info("✅ Пул подключений к БД создан")
        return _db_pool
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

        # --- Таблица отзывов ---
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                rating INT CHECK (rating >= 1 AND rating <= 5),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                is_approved BOOLEAN DEFAULT TRUE
            );
        ''')

        # --- Таблица: обращения в техподдержку ---
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS support_tickets (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                username TEXT,
                first_name TEXT,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
                -- ticket_id добавим позже через миграцию
            );
        ''')

        # Индексы (без индекса по ticket_id — он будет позже)
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_support_user ON support_tickets(user_id);')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_support_status ON support_tickets(status);')

        # --- Миграции — расширения ---
        migrations = [
            ('theme', "TEXT DEFAULT 'light'"),
            ('language', "TEXT DEFAULT 'ru'"),
            ('last_name', 'TEXT'),
            ('is_bot', 'BOOLEAN'),
            ('last_seen', 'TIMESTAMPTZ DEFAULT NOW()'),
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

        # ✅ Миграция: добавляем ticket_id в support_tickets
        try:
            await conn.execute('''
                ALTER TABLE support_tickets 
                ADD COLUMN IF NOT EXISTS ticket_id TEXT UNIQUE;
            ''')
            logger.info("✅ Колонка ticket_id добавлена в support_tickets (если отсутствовала)")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при добавлении ticket_id: {e}")

        # ✅ Теперь можно создать индекс
        try:
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_support_ticket_id ON support_tickets(ticket_id);
            ''')
            logger.info("✅ Индекс idx_support_ticket_id создан")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при создании индекса ticket_id: {e}")

    logger.info("✅ Все таблицы и миграции применены")

# --- Работа с пользователями ---
async def add_or_update_user(pool, user):
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
                is_bot = EXCLUDED.is_bot,
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
    async with pool.acquire() as conn:
        role = await conn.fetchval('SELECT role FROM users WHERE id = $1', user_id)
        return role or 'user'


async def set_user_role(pool, user_id: int, role: str):
    valid_roles = ['user', 'premium', 'admin']
    if role not in valid_roles:
        raise ValueError(f"Роль должна быть одной из: {valid_roles}")
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET role = $1 WHERE id = $2', role, user_id)
    logger.info(f"🔐 Пользователю {user_id} установлена роль: {role}")


async def is_admin(pool, user_id: int) -> bool:
    role = await get_user_role(pool, user_id)
    return role == 'admin'


async def is_premium_or_admin(pool, user_id: int) -> bool:
    role = await get_user_role(pool, user_id)
    return role in ['premium', 'admin']


# --- Работа с настройками интерфейса ---
async def get_user_settings(pool, user_id: int) -> dict:
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
    if theme not in ["light", "dark"]:
        raise ValueError("Тема должна быть 'light' или 'dark'")
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET theme = $1 WHERE id = $2', theme, user_id)
    logger.info(f"🎨 Пользователь {user_id} сменил тему: {theme}")


async def update_user_language(pool, user_id: int, lang: str):
    if lang not in ["ru", "en"]:
        raise ValueError("Язык должен быть 'ru' или 'en'")
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET language = $1 WHERE id = $2', lang, user_id)
    logger.info(f"🌐 Пользователь {user_id} сменил язык: {lang}")


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


async def get_referral_stats(pool, user_id: int) -> int:
    async with pool.acquire() as conn:
        count = await conn.fetchval('''
            SELECT COUNT(*) FROM referrals WHERE referrer_id = $1
        ''', user_id)
        return count or 0


# --- Статистика ---
async def log_command_usage(pool, user_id: int, command: str):
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO usage_stats (user_id, command) VALUES ($1, $2)
        ''', user_id, command)
    logger.debug(f"📊 Команда: {command} от {user_id}")


# --- Очистка неактивных ---
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


# --- Очистка старых тикетов поддержки ---
async def cleanup_support_tickets(pool, days=7):
    async with pool.acquire() as conn:
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM support_tickets
            WHERE status = 'resolved'
              AND updated_at < NOW() - $1 * INTERVAL '1 day';
        """, days)

        if count > 0:
            await conn.execute("""
                DELETE FROM support_tickets
                WHERE status = 'resolved'
                  AND updated_at < NOW() - $1 * INTERVAL '1 day';
            """, days)
            logger.info(f"🧹 Очищено {count} старых тикетов поддержки")
        else:
            logger.debug("✅ Нет старых тикетов для удаления")
        return count or 0


async def ensure_support_table_exists():
    """
    Гарантирует, что таблица support_tickets существует.
    Вызывается при старте бота.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    username TEXT,
                    first_name TEXT,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    ticket_id TEXT UNIQUE  -- ✅
                )
            ''')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_support_user ON support_tickets(user_id);')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_support_status ON support_tickets(status);')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_support_ticket_id ON support_tickets(ticket_id);')
            logger.info("✅ Таблица support_tickets проверена и готова")
        except Exception as e:
            logger.error(f"❌ Ошибка при создании таблицы support_tickets: {e}")


# === Глобальный пул подключений ===
async def get_db_pool():
    global _db_pool
    if _db_pool is None:
        _db_pool = await create_db_pool()
    return _db_pool
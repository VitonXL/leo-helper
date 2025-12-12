# bot/database.py
import os
import sqlite3
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import DictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    print("✅ Используем PostgreSQL")
else:
    print("⚠️ Используем SQLite (локально)")


@contextmanager
def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=DictCursor)
    else:
        conn = sqlite3.connect("bot.db")
        conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка базы: {e}")
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                last_seen TIMESTAMP,
                join_date TIMESTAMP,
                notify_enabled BOOLEAN DEFAULT TRUE,
                ai_requests_today INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                action TEXT,
                timestamp TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_cities (
                user_id BIGINT,
                city TEXT,
                PRIMARY KEY (user_id, city)
            )
        """)
        print("✅ Таблицы инициализированы")


init_db()


def get_user(user_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return cur.fetchone()


def add_user(user_data):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, join_date, last_seen)
            VALUES (%s, %s, %s, %s, COALESCE((SELECT join_date FROM users WHERE user_id = %s), NOW()), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                last_seen = NOW()
        """, (
            user_data["id"],
            user_data.get("username"),
            user_data.get("first_name"),
            user_data.get("last_name"),
            user_data["id"]
        ))


def set_premium(user_id: int, is_premium: bool):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_premium = %s WHERE user_id = %s", (is_premium, user_id))


def set_admin(user_id: int, is_admin: bool):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_admin = %s WHERE user_id = %s", (is_admin, user_id))


def get_user_count():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM users")
        return cur.fetchone()["c"]


def get_premium_count():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM users WHERE is_premium = TRUE")
        return cur.fetchone()["c"]


def get_today_joined_count():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM users WHERE DATE(last_seen) = CURRENT_DATE")
        return cur.fetchone()["c"]


def log_action(user_id: int, action: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO logs (user_id, action, timestamp) VALUES (%s, %s, NOW())", (user_id, action))


def get_user_cities(user_id: int) -> list:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT city FROM user_cities WHERE user_id = %s", (user_id,))
        return [row["city"] for row in cur.fetchall()]


def add_user_city(user_id: int, city: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO user_cities (user_id, city) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (user_id, city))


def get_ai_requests(user_id: int) -> int:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT ai_requests_today FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return row["ai_requests_today"] if row else 0


def increment_ai_request(user_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET ai_requests_today = ai_requests_today + 1 WHERE user_id = %s", (user_id,))


def reset_ai_requests():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET ai_requests_today = 0")

# bot/database.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

def get_db():
    try:
        conn = psycopg2.connect(
            os.getenv("DATABASE_URL"),
            sslmode='require',
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logging.error(f"Ошибка подключения к БД: {e}")
        raise

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Пользователи
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            joined_at TIMESTAMP DEFAULT NOW(),
            is_premium BOOLEAN DEFAULT FALSE,
            premium_expire TIMESTAMP,
            referrer_id BIGINT,
            timezone TEXT DEFAULT 'Europe/Moscow'
        )
    """)

    # Рефералы (3 уровня)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            referrer_id BIGINT NOT NULL,
            level INTEGER NOT NULL,
            reward_days INTEGER NOT NULL,
            rewarded_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Подписки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            price NUMERIC,
            due_date DATE NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
    """)

    # Напоминания
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            text TEXT NOT NULL,
            time TIMESTAMP NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
    """)

    # Рассылки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id SERIAL PRIMARY KEY,
            message TEXT NOT NULL,
            target TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            send_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            sent_count INTEGER DEFAULT 0
        )
    """)

    # Действия (лог)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT NOW()
        )
    """)

    # Оплаты
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount NUMERIC,
            order_id INTEGER,
            payment_date TIMESTAMP DEFAULT NOW(),
            status TEXT DEFAULT 'success'
        )
    """)

    conn.commit()
    conn.close()

# --- Основные функции --- 

def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_user(user_id, first_name, last_name, username, referrer_id=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, first_name, last_name, username, referrer_id)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, first_name, last_name, username, referrer_id))
    conn.commit()
    conn.close()

def set_premium(user_id, days=30):
    conn = get_db()
    cursor = conn.cursor()
    expire = datetime.now() + timedelta(days=days)
    cursor.execute("""
        UPDATE users SET is_premium = TRUE, premium_expire = %s WHERE user_id = %s
    """, (expire, user_id))
    conn.commit()
    conn.close()

def remove_premium(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET is_premium = FALSE WHERE user_id = %s
    """, (user_id,))
    conn.commit()
    conn.close()

def check_premium(user_id):
    user = get_user(user_id)
    if not user:
        return False
    if not user['is_premium']:
        return False
    if user['premium_expire'] and user['premium_expire'] < datetime.now():
        remove_premium(user_id)
        return False
    return True

def get_user_count():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()['count']
    conn.close()
    return count

def get_premium_count():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = TRUE")
    count = cursor.fetchone()['count']
    conn.close()
    return count

def get_today_joined_count():
    today = date.today()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE DATE(joined_at) = %s
    """, (today,))
    count = cursor.fetchone()['count']
    conn.close()
    return count

def log_action(user_id, action, details=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO actions (user_id, action, details)
        VALUES (%s, %s, %s)
    """, (user_id, action, details))
    conn.commit()
    conn.close()

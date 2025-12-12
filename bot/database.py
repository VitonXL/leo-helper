# bot/database.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_at TIMESTAMP NOT NULL,
            is_premium BOOLEAN DEFAULT FALSE,
            premium_expire TIMESTAMP,
            referred_by BIGINT,
            timezone TEXT DEFAULT 'UTC',
            lang TEXT DEFAULT 'ru'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            text TEXT NOT NULL,
            time TIMESTAMP NOT NULL,
            active BOOLEAN DEFAULT TRUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            price NUMERIC,
            due_date DATE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            city TEXT NOT NULL,
            is_favorite BOOLEAN DEFAULT FALSE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id SERIAL PRIMARY KEY,
            referrer_id BIGINT NOT NULL,
            referred_id BIGINT UNIQUE NOT NULL,
            level INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()
    
    CREATE TABLE payments (
    order_id INTEGER PRIMARY KEY,
    user_id BIGINT NOT NULL,
    status TEXT DEFAULT 'waiting',
    created_at TIMESTAMP DEFAULT NOW()
);

# --- Пользователи ---
def add_user(user_id, username, first_name, last_name, referred_by=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name, last_name, joined_at, referred_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, username, first_name, last_name, datetime.now(), referred_by))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def set_premium(user_id, days=30):
    conn = get_db()
    cursor = conn.cursor()
    expire = datetime.now() + timedelta(days=days)
    cursor.execute("""
        UPDATE users SET is_premium = TRUE, premium_expire = %s WHERE user_id = %s
    """, (expire, user_id))
    conn.commit()
    conn.close()

def check_premium(user_id):
    user = get_user(user_id)
    if not user or not user['is_premium']:
        return False
    if user['premium_expire'] and user['premium_expire'] < datetime.now():
        remove_premium(user_id)
        return False
    return True

def remove_premium(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET is_premium = FALSE, premium_expire = NULL WHERE user_id = %s
    """, (user_id,))
    conn.commit()
    conn.close()

# --- Статистика ---
def get_user_count():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

def get_premium_count():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = TRUE AND premium_expire > %s", (datetime.now(),))
    return cursor.fetchone()[0]

def get_today_joined_count():
    conn = get_db()
    cursor = conn.cursor()
    today = date.today()
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at) = %s", (today,))
    return cursor.fetchone()[0]

def log_action(user_id, action, details=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO actions (user_id, action, details, timestamp)
        VALUES (%s, %s, %s, %s)
    """, (user_id, action, details, datetime.now()))
    conn.commit()
    conn.close()

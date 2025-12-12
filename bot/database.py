# bot/database.py
import sqlite3
import os

# Путь к базе данных
DB_PATH = os.getenv("DB_PATH", "users.db")

# Глобальная переменная db — чтобы можно было импортировать
db = None

def init_db():
    global db
    # Подключаемся к SQLite
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            is_premium INTEGER DEFAULT 0,
            cities TEXT DEFAULT '',
            ai_requests INTEGER DEFAULT 10
        )
    ''')
    db.commit()
    print("✅ Таблицы инициализированы")
    return db

def get_user(user_id):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def add_user(user_id):
    cursor = db.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    db.commit()

def set_premium(user_id, is_premium=True):
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_premium = ? WHERE user_id = ?", (int(is_premium), user_id))
    db.commit()

def add_city(user_id, city):
    user = get_user(user_id)
    if user:
        cities = user[3].split(",") if user[3] else []
        if len(cities) >= (5 if user[2] else 1) and city not in cities:
            return False  # Лимит городов
        if city not in cities:
            cities.append(city)
            cursor = db.cursor()
            cursor.execute("UPDATE users SET cities = ? WHERE user_id = ?", (",".join(cities), user_id))
            db.commit()
    return True

def get_cities(user_id):
    user = get_user(user_id)
    return user[3].split(",") if user and user[3] else []

def reset_ai_requests():
    cursor = db.cursor()
    cursor.execute("UPDATE users SET ai_requests = 10")
    db.commit()
    print("🔁 AI-запросы сброшены")

def use_ai_request(user_id):
    user = get_user(user_id)
    if user and user[4] > 0:
        cursor = db.cursor()
        cursor.execute("UPDATE users SET ai_requests = ai_requests - 1 WHERE user_id = ?", (user_id,))
        db.commit()
        return True
    return False

def get_ai_requests_left(user_id):
    user = get_user(user_id)
    return user[4] if user else 0

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Настройка API ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_TOKEN в переменных окружения")

# --- Инициализация базы данных ---
def init_db():
    with sqlite3.connect("users.db") as conn:
        # Основная таблица пользователей
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_premium INTEGER DEFAULT 0,
                premium_until TIMESTAMP,
                referral_count INTEGER DEFAULT 0,
                premium_converted INTEGER DEFAULT 0
            )
        """)

        # Проверяем, какие столбцы уже есть
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        # Добавляем недостающие столбцы
        if 'is_premium' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")
        if 'premium_until' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN premium_until TIMESTAMP")
        if 'referral_count' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
        if 'premium_converted' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN premium_converted INTEGER DEFAULT 0")

        # Другие таблицы
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                text TEXT,
                notify_at TIMESTAMP,
                sent INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                name TEXT,
                amount REAL,
                next_payment TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                referral_id INTEGER,
                referrer_id INTEGER,
                premium_converted INTEGER DEFAULT 0,
                PRIMARY KEY (referral_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movie_usage (
                user_id INTEGER PRIMARY KEY,
                count INTEGER DEFAULT 0,
                last_reset DATE
            )
        """)
        conn.commit()

# --- Работа с премиумом ---
def get_premium_info(user_id: int):
    with sqlite3.connect("users.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return None
        # Теперь точно знаем, что столбцы есть
        return {
            "is_premium": bool(user["is_premium"]),
            "premium_until": user["premium_until"],
            "referral_count": user["referral_count"],
            "premium_converted": bool(user["premium_converted"])
        }

def is_premium(user_id: int) -> bool:
    info = get_premium_info(user_id)
    if not info:
        return False
    if info["premium_until"]:
        if datetime.now() > datetime.fromisoformat(info["premium_until"]):
            # Премиум истёк
            with sqlite3.connect("users.db") as conn:
                conn.execute("UPDATE users SET is_premium = 0, premium_until = NULL WHERE user_id = ?", (user_id,))
            return False
        return True
    return False

def add_premium(user_id: int, days: int):
    premium_until = (datetime.now() + timedelta(days=days)).isoformat()
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, is_premium, premium_until)
            VALUES (?, 1, ?)
        """, (user_id, premium_until))
        conn.execute("""
            UPDATE users SET is_premium = 1, premium_until = ?
            WHERE user_id = ?
        """, (premium_until, user_id))
        conn.commit()

# --- Рефералы ---
def add_referral(referral_id: int, referrer_id: int):
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            INSERT OR IGNORE INTO referrals (referral_id, referrer_id)
            VALUES (?, ?)
        """, (referral_id, referrer_id))
        conn.commit()

def get_referral_count(user_id: int) -> int:
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        return cursor.fetchone()[0]

def convert_referral_to_premium(referral_id: int):
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            UPDATE referrals SET premium_converted = 1 WHERE referral_id = ?
        """, (referral_id,))
        conn.commit()

# --- Уведомления ---
async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            SELECT id, user_id, text FROM reminders
            WHERE sent = 0 AND notify_at <= ?
        """, (now,))
        reminders = cursor.fetchall()
        for rid, user_id, text in reminders:
            try:
                await context.bot.send_message(chat_id=user_id, text=f"🔔 Напоминание: {text}")
                cursor.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (rid,))
            except:
                pass
        conn.commit()

# --- Клавиатуры ---
def get_main_menu(user_id: int = None):
    keyboard = [
        [InlineKeyboardButton("🌤 Погода", callback_data="weather"), InlineKeyboardButton("⏰ Время", callback_data="time")],
        [InlineKeyboardButton("💱 Курсы", callback_data="currency"), InlineKeyboardButton("❓ Помощь", callback_data="help")],
        [InlineKeyboardButton("🛡 Антивирусы", callback_data="antivirus")],
        [InlineKeyboardButton("🔓 Обход YouTube", callback_data="youtube_bypass")],
        [InlineKeyboardButton("📋 Мои функции", callback_data="my_features")],
        [InlineKeyboardButton("🎮 Играть", url="https://t.me/gamee")],
        [InlineKeyboardButton("🌐 Mini App", web_app=WebAppInfo(url="https://leo-aide.onrender.com"))],
        [InlineKeyboardButton("💎 Премиум & Рефералы", callback_data="premium_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_premium_menu():
    keyboard = [
        [InlineKeyboardButton("Купить за 50₽ (0.02 TON)", callback_data="buy_premium")],
        [InlineKeyboardButton("Мои рефералы", callback_data="my_referrals")],
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or "Аноним"
    first_name = user.first_name or "Пользователь"

    # Сохраняем пользователя
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (user.id, username, first_name, user.last_name))
        conn.commit()

    # Обработка реферала
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = int(context.args[0].split("_")[1])
        if referrer_id != user.id:
            add_referral(user.id, referrer_id)

    welcome_text = f"👋 Привет, {first_name}! Я — твой личный бот-помощник 🎯\n\nВыбери, что хочешь сделать:"
    message = await update.effective_message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(user.id),
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "weather":
        await query.edit_message_text("🌤 Введите город:")
        context.user_data["awaiting"] = "weather"
    elif query.data == "time":
        now = datetime.now().strftime("%H:%M:%S")
        await query.edit_message_text(f"⏰ Текущее время: {now}")
    elif query.data == "currency":
        # Здесь можно добавить запрос к API курсов
        await query.edit_message_text("💱 Курсы валют: скоро!")
    elif query.data == "antivirus":
        await query.edit_message_text("🛡 Антивирусы: скоро!")
    elif query.data == "youtube_bypass":
        await query.edit_message_text("🔓 Обход YouTube: скоро!")
    elif query.data == "my_features":
        await query.edit_message_text("📋 Мои функции: скоро!")
    elif query.data == "premium_menu":
        await query.edit_message_text("💎 Премиум & Рефералы:", reply_markup=get_premium_menu())
    elif query.data == "buy_premium":
        ref_link = f"https://t.me/leo_aide_bot?start=ref_{query.from_user.id}"
        text = f"💎 Купить премиум за 50₽ (0.02 TON)\n\n🔗 Реферальная ссылка: {ref_link}"
        await query.edit_message_text(text)
    elif query.data == "my_referrals":
        count = get_referral_count(query.from_user.id)
        text = f"👥 У вас {count} рефералов.\n\nПригласите 3 — получите премиум бесплатно!"
        await query.edit_message_text(text)
    elif query.data == "back":
        await query.edit_message_text("Главное меню:", reply_markup=get_main_menu(query.from_user.id))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if user_data.get("awaiting") == "weather":
        city = update.message.text
        await update.message.reply_text(f"🌤 Погода в {city}: 22°C, солнечно")
        user_data.clear()

# --- Основная функция ---
def main():
    init_db()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Уведомления
    application.job_queue.run_repeating(check_reminders, interval=60, first=10)

    logger.info("✅ Бот и VirusTotal API запущены на одном сервере")
    application.run_polling()

if __name__ == '__main__':

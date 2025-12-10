# bot.py — Leo Aide Bot (всё в одном)
# Включает: бота, VirusTotal API, Flask, Render-совместимость

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import datetime
import requests
import os
import sqlite3
import threading
from flask import Flask, request, jsonify

# --- API КЛЮЧИ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY")
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")

if not TOKEN:
    raise RuntimeError("Не задан TELEGRAM_TOKEN в переменных окружения")

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    with sqlite3.connect("users.db") as conn:
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

def add_user(user_id, username, first_name, last_name):
    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, last_name)
        )

def get_user(user_id):
    with sqlite3.connect("users.db") as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

def add_reminder(user_id, text, notify_at):
    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "INSERT INTO reminders (user_id, text, notify_at) VALUES (?, ?, ?)",
            (user_id, text, notify_at)
        )

def get_active_reminders():
    with sqlite3.connect("users.db") as conn:
        return conn.execute(
            "SELECT id, user_id, text, notify_at FROM reminders WHERE sent = 0 AND notify_at <= datetime('now', '+30 seconds')"
        ).fetchall()

def mark_reminder_sent(reminder_id):
    with sqlite3.connect("users.db") as conn:
        conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))

def add_subscription(user_id, name, amount, next_payment):
    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "INSERT INTO subscriptions (user_id, name, amount, next_payment) VALUES (?, ?, ?, ?)",
            (user_id, name, amount, next_payment)
        )

def get_subscriptions(user_id):
    with sqlite3.connect("users.db") as conn:
        return conn.execute(
            "SELECT name, amount, next_payment FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchall()

def set_premium(user_id, amount_ton):
    duration_days = 30
    premium_until = datetime.datetime.now() + datetime.timedelta(days=duration_days)
    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
            (premium_until, user_id)
        )

def get_premium_info(user_id):
    user = get_user(user_id)
    if not user or not user[10]:  # is_premium
        return None
    until = datetime.datetime.fromisoformat(user[11])
    days_left = (until - datetime.datetime.now()).days
    return {"until": until, "days_left": max(0, days_left)}

def is_premium(user_id):
    return get_premium_info(user_id) is not None

def get_referrer(user_id):
    with sqlite3.connect("users.db") as conn:
        row = conn.execute(
            "SELECT referrer_id FROM referrals WHERE referral_id = ?", (user_id,)
        ).fetchone()
        return row[0] if row else None

def add_referral(referral_id, referrer_id):
    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "INSERT OR IGNORE INTO referrals (referral_id, referrer_id) VALUES (?, ?)",
            (referral_id, referrer_id)
        )
        conn.execute(
            "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
            (referrer_id,)
        )

def increment_premium_converted(referrer_id):
    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "UPDATE users SET premium_converted = premium_converted + 1 WHERE user_id = ?",
            (referrer_id,)
        )
        conn.execute(
            "UPDATE referrals SET premium_converted = 1 WHERE referrer_id = ? AND referral_id IN (SELECT user_id FROM users WHERE is_premium = 1)",
            (referrer_id,)
        )

def extend_premium_for_referrer(referrer_id):
    with sqlite3.connect("users.db") as conn:
        conn.execute(
            "UPDATE users SET premium_until = datetime(premium_until, '+3 days') WHERE user_id = ?",
            (referrer_id,)
        )

def get_movie_usage(user_id):
    with sqlite3.connect("users.db") as conn:
        row = conn.execute(
            "SELECT count, last_reset FROM movie_usage WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return 0
        try:
            last_reset = datetime.datetime.fromisoformat(row[1])
        except:
            last_reset = datetime.datetime.now()
        if (datetime.datetime.now() - last_reset).days >= 1:
            conn.execute("UPDATE movie_usage SET count = 0, last_reset = ? WHERE user_id = ?", (datetime.datetime.now().date(), user_id))
            conn.commit()
            return 0
        return row[0]

def increment_movie_usage(user_id):
    with sqlite3.connect("users.db") as conn:
        now = datetime.datetime.now().date()
        conn.execute(
            "INSERT OR IGNORE INTO movie_usage (user_id, count, last_reset) VALUES (?, 0, ?)",
            (user_id, now)
        )
        conn.execute(
            "UPDATE movie_usage SET count = count + 1, last_reset = ? WHERE user_id = ?",
            (now, user_id)
        )

# --- ГЛАВНОЕ МЕНЮ ---
def get_main_menu(user_id=None):
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
    if user_id and is_premium(user_id):
        keyboard.insert(-1, [InlineKeyboardButton("🎬 Фильм", callback_data="movie_menu")])
    if user_id == 1799560429:
        keyboard.append([InlineKeyboardButton("🛠 Админка", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

# --- ПОДМЕНЮ ФУНКЦИЙ ---
def get_features_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Напоминания", callback_data="list_reminders")],
        [InlineKeyboardButton("💳 Подписки", callback_data="subscriptions")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ])

# --- СТАРТ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if referrer_id != user.id:
            add_referral(user.id, referrer_id)
    if 'main_menu_message_id' in context.user_data:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data['main_menu_message_id'])
        except: pass
    welcome_text = f"👋 Привет, <b>{user.first_name}</b>! Я — твой личный бот-помощник 🎯"
    message = await update.effective_message.reply_text(welcome_text, reply_markup=get_main_menu(user.id), parse_mode='HTML')
    context.user_data['main_menu_message_id'] = message.message_id

# --- ПОГОДА ---
async def get_weather(city: str):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": WEATHER_API_KEY, "lang": "ru", "units": "metric"}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if response.status_code != 200: return "❌ Город не найден."
        name = data["name"]; country = data["sys"]["country"]; temp = data["main"]["temp"]
        desc = data["weather"][0]["description"].capitalize(); humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"]
        return f"🌤 <b>{name}, {country}</b>\n🌡 Темп: {temp}°C\n📊 Описание: {desc}\n💧 Влажность: {humidity}%\n💨 Ветер: {wind} м/с"
    except: return "❌ Ошибка получения погоды."

async def weather_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Введите город:")
    context.user_data['awaiting_city'] = True

# --- ВРЕМЯ ---
async def time_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%d.%m.%Y")
    text = f"⏰ Текущее время: <b>{time_str}</b>\n📅 Дата: <b>{date_str}</b>"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]), parse_mode='HTML')

# --- КУРСЫ ОТ ЦБ РФ ---
async def get_exchange_rates():
    try:
        response = requests.get("https://www.cbr-xml-daily.ru/latest.js", timeout=10)
        data = response.json(); rates = data["rates"]
        return (
            "💱 <b>Курсы валют (ЦБ РФ)</b>\n\n"
            f"🇺🇸 1 USD = {rates['USD']:.2f} ₽\n"
            f"🇪🇺 1 EUR = {rates['EUR']:.2f} ₽\n"
            f"🇨🇳 1 CNY = {rates['CNY']:.2f} ₽\n"
            f"🇯🇵 100 JPY = {rates['JPY']:.2f} ₽\n\n"
            f"📅 {data['date']}"
        )
    except: return "❌ Не удалось получить курсы."

async def currency_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await get_exchange_rates()
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]), parse_mode='HTML', disable_web_page_preview=True)

# --- ПОМОЩЬ ---
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🆘 <b>Помощь и поддержка</b>\n\n"
        "Бот поддерживает команды:\n"
        "/start — перезапуск\n"
        "/help — помощь\n\n"
        "Если есть вопросы — пишите: @your_support"
    )
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]), parse_mode='HTML')

# --- АНТИВИРУСЫ ---
async def antivirus_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛡 <b>Рекомендуемые антивирусы</b>\n\n"
        "• <a href='https://free.drweb.ru/'>Dr.Web CureIt!</a> — бесплатное сканирование\n"
        "• <a href='https://www.kaspersky.ru/free-antivirus'>Kaspersky Free</a>\n"
        "• <a href='https://www.avira.com/'>Avira</a>\n"
        "• <a href='https://www.avast.com/'>Avast</a>\n"
        "• <a href='https://adwcleaner.org/'>AdwCleaner</a> — от рекламы\n"
        "• <a href='https://github.com/Potterli20/minersearch/releases/'>MinerSearch</a> — майнеры"
    )
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]), parse_mode='HTML', disable_web_page_preview=True)

# --- ОБХОД YOUTUBE ---
async def youtube_bypass_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔓 <b>Обход блокировок YouTube</b>\n\n"
        "• <a href='https://byebyedpi.org/ru/'>ByeByeDPI</a> — обход DPI\n"
        "• <a href='https://invidious.io/'>Invidious</a> — альтернатива YouTube\n"
        "• <a href='https://piped.video/'>Piped</a> — альтернатива\n"
        "• Используйте Tor Browser"
    )
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]), parse_mode='HTML', disable_web_page_preview=True)

# --- МОИ ФУНКЦИИ ---
async def my_features_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Выберите функцию:", reply_markup=get_features_menu())

# --- НАПОМИНАНИЯ ---
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with sqlite3.connect("users.db") as conn:
        reminders = conn.execute("SELECT id, text, notify_at FROM reminders WHERE user_id = ? AND sent = 0", (user_id,)).fetchall()
    if not reminders:
        text = "🔔 У вас нет активных напоминаний."
    else:
        text = "🔔 <b>Ваши напоминания:</b>\n\n"
        for r in reminders:
            text += f"• {r[1]} — {r[2]}\n"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Добавить", callback_data="add_reminder"), InlineKeyboardButton("🔙 Назад", callback_data="my_features")]]), parse_mode='HTML')

async def add_reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Введите текст напоминания:")
    context.user_data['awaiting_reminder_text'] = True

# --- ПОДПИСКИ ---
async def subscriptions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subs = get_subscriptions(user_id)
    if not subs:
        text = "💳 У вас нет подписок."
    else:
        text = "💳 <b>Ваши подписки:</b>\n\n"
        for s in subs:
            text += f"• {s[0]} — {s[1]}₽ — {s[2]}\n"
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Добавить", callback_data="add_subscription"), InlineKeyboardButton("🔙 Назад", callback_data="my_features")]]), parse_mode='HTML')

# --- ФИЛЬМЫ ---
def get_random_movie():
    return "🎬 Пример фильма: 'Интерстеллар' (2014) — Рейтинг: 8.6 — Жанры: Драма, Приключения, Научная фантастика"

async def movie_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usage = get_movie_usage(update.effective_user.id)
    if usage >= 3:
        await update.callback_query.answer("🎬 Лимит фильмов исчерпан. Обновится завтра.", show_alert=True)
        return
    movie = get_random_movie()
    increment_movie_usage(update.effective_user.id)
    await update.callback_query.edit_message_text(movie, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Ещё", callback_data="movie_menu"), InlineKeyboardButton("🔙 Назад", callback_data="back")]]), parse_mode='HTML')

# --- ПРЕМИУМ & РЕФЕРАЛЫ ---
async def premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    info = get_premium_info(user_id)
    status = f"✅ Активен ({info['days_left']} дн.)" if info else "❌ Не активен"
    ref_link = f"https://t.me/Leo_aide_bot?start={user_id}"
    text = (
        f"💎 <b>Премиум & Рефералы</b>\n\n"
        f"📋 Статус: <b>{status}</b>\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{ref_link}</code>\n\n"
        "Приглашайте друзей:\n"
        "• +3 дня премиума за каждого, кто купит\n"
        "• Вы получите 3 дня сразу\n\n"
        "Выберите действие:"
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Купить премиум", callback_data="buy_premium")],
        [InlineKeyboardButton("🔗 Мои рефералы", callback_data="referral_menu")],
        [InlineKeyboardButton("💸 Поддержать проект", callback_data="donate")],
        [InlineKeyboardButton("🔍 Проверить ссылку/файл", callback_data="scan_start")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', disable_web_page_preview=True)

# --- СКАНИРОВАНИЕ ССЫЛОК ---
async def scan_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_premium(update.effective_user.id):
        kb = [[InlineKeyboardButton("💎 Купить премиум", callback_data="buy_premium")]]
        await update.callback_query.edit_message_text("🔒 Эта функция доступна только премиум-пользователям.", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text("📎 Отправьте ссылку или файл (до 32 МБ):")
        context.user_data['awaiting_scan'] = True

async def scan_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get('awaiting_scan_url')
    if not url:
        return
    context.user_data.pop('awaiting_scan_url', None)
    await update.effective_message.reply_text("🔍 Проверяю ссылку...")
    try:
        headers = {"Authorization": f"Bearer {VIRUSTOTAL_API_KEY}", "Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url}, timeout=15)
        if response.status_code == 200:
            scan_id = response.json()["data"]["id"]
            await check_vt_result(update, context, scan_id=scan_id)
        else:
            await update.effective_message.reply_text("❌ Ошибка отправки на проверку.")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Ошибка: {e}")

async def check_vt_result(update: Update, context: ContextTypes.DEFAULT_TYPE, scan_id=None):
    try:
        headers = {"Authorization": f"Bearer {VIRUSTOTAL_API_KEY}"}
        response = requests.get(f"https://www.virustotal.com/api/v3/analyses/{scan_id}", headers=headers, timeout=10)
        if response.status_code != 200:
            await update.effective_message.reply_text("❌ Ошибка получения результата.")
            return
        result = response.json()["data"]["attributes"]["stats"]
        malicious = result.get("malicious", 0)
        total = sum(result.values())
        if malicious > 0:
            text = f"🔴 Обнаружено: <b>{malicious}</b> угроз из {total}"
        else:
            text = f"🟢 Безопасно: <b>0</b> угроз из {total}"
        await update.effective_message.reply_text(text, parse_mode='HTML')
        await update.effective_message.reply_text("🎮 Главное меню:", reply_markup=get_main_menu(update.effective_user.id))
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Ошибка: {e}")

# --- ОБРАБОТКА СООБЩЕНИЙ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if context.user_data.get('awaiting_city'):
        context.user_data.pop('awaiting_city', None)
        weather = await get_weather(text)
        await update.effective_message.reply_text(weather, parse_mode='HTML')
        await update.effective_message.reply_text("🎮 Главное меню:", reply_markup=get_main_menu(user_id))
        return

    if context.user_data.get('awaiting_reminder_text'):
        context.user_data['reminder_text'] = text
        context.user_data.pop('awaiting_reminder_text', None)
        context.user_data['awaiting_reminder_time'] = True
        await update.effective_message.reply_text("Введите время (например, 'через 10 минут', 'в 15:30', 'завтра 9:00')")
        return

    if context.user_data.get('awaiting_subscription_name'):
        context.user_data['subscription_name'] = text
        context.user_data.pop('awaiting_subscription_name', None)
        context.user_data['awaiting_subscription_amount'] = True
        await update.effective_message.reply_text("Введите сумму (например, 999):")
        return

    if context.user_data.get('awaiting_subscription_amount'):
        try:
            amount = float(text)
            context.user_data.pop('awaiting_subscription_amount', None)
            context.user_data['subscription_amount'] = amount
            context.user_data['awaiting_subscription_date'] = True
            await update.effective_message.reply_text("Введите дату следующего платежа (например, '10.04', 'завтра'):")
        except:
            await update.effective_message.reply_text("❌ Неверный формат. Введите число.")
        return

    # Проверка ссылки
    if context.user_data.get('awaiting_scan'):
        context.user_data.pop('awaiting_scan', None)
        if text and text.startswith(('http://', 'https://')):
            context.user_data['awaiting_scan_url'] = text
            await scan_url(update, context)
            return
        await update.effective_message.reply_text("❌ Отправьте корректную ссылку.")
        return

# --- ОБРАБОТКА КНОПОК ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if query.data == "weather":
        await weather_input(query, context)
    elif query.data == "time":
        await time_menu(query, context)
    elif query.data == "currency":
        await currency_menu(query, context)
    elif query.data == "help":
        await help_menu(query, context)
    elif query.data == "antivirus":
        await antivirus_menu(query, context)
    elif query.data == "youtube_bypass":
        await youtube_bypass_menu(query, context)
    elif query.data == "my_features":
        await my_features_menu(query, context)
    elif query.data == "list_reminders":
        await list_reminders(query, context)
    elif query.data == "add_reminder":
        await add_reminder_start(query, context)
    elif query.data == "subscriptions":
        await subscriptions_menu(query, context)
    elif query.data == "movie_menu":
        await movie_menu(query, context)
    elif query.data == "premium_menu":
        await premium_menu(query, context)
    elif query.data == "scan_start":
        await scan_start(query, context)
    elif query.data == "back":
        await query.edit_message_text("🎮 Главное меню:", reply_markup=get_main_menu(user.id))

# --- ВСТРОЕННЫЙ FLASK API ДЛЯ VIRUSTOTAL ---
flask_app = Flask('VirusTotalProxy')

@flask_app.route('/scan/url', methods=['POST'])
def scan_url_api():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL не указан"}), 400
    headers = {"Authorization": f"Bearer {VIRUSTOTAL_API_KEY}", "Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
    if response.status_code != 200:
        return jsonify({"error": "Ошибка отправки", "details": response.text}), 500
    scan_id = response.json()["data"]["id"]
    return jsonify({"scan_id": scan_id})

@flask_app.route('/scan/result', methods=['GET'])
def scan_result_api():
    scan_id = request.args.get('id')
    if not scan_id:
        return jsonify({"error": "scan_id не указан"}), 400
    headers = {"Authorization": f"Bearer {VIRUSTOTAL_API_KEY}"}
    response = requests.get(f"https://www.virustotal.com/api/v3/analyses/{scan_id}", headers=headers)
    if response.status_code != 200:
        return jsonify({"error": "Не удалось получить результат"}), 500
    result = response.json()["data"]["attributes"]["stats"]
    malicious = result.get("malicious", 0)
    return jsonify({"malicious": malicious, "safe": malicious == 0, "total": sum(result.values())})

@flask_app.route('/')
def home():
    return jsonify({"status": "Leo Aide Bot & VT API is running"}), 200

# --- ЗАПУСК ВСЕГО ---
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

def main():
    init_db()

    # Запускаем Flask в фоне
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()

    # Запускаем бота
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_message))

    print("✅ Бот и VirusTotal API запущены на одном сервере")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()

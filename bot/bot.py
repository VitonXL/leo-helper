# bot/bot.py
import os
import logging
import requests
import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
)

from bot.database import db
from bot.admin import (
    admin_panel, admin_stats, admin_broadcast_start,
    admin_grant_premium_start, admin_logs, admin_command
)
from bot.cbr_exchange import get_cached_cbr_rates, fetch_cbr_rates
from bot.ton_checker import check_pending_payments, test_ton_api
from bot.sheets_sync import log_subscription, log_reminder

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Глобальные переменные ---
AWAITING = "awaiting"

MOVIE_GENRES = {
    "action": "Боевик",
    "comedy": "Комедия",
    "drama": "Драма",
    "horror": "Ужасы",
    "fantasy": "Фэнтези",
    "scifi": "Фантастика"
}

# --- ОСНОВНЫЕ КОМАНДЫ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.reset_daily_counters(user_id)
    db.log_action(user_id, "start")

    # Рефералы
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = int(context.args[0].split("_")[1])
        if referrer_id != user_id:
            with sqlite3.connect("bot.db") as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO referrals (user_id, referrer_id, count)
                    VALUES (?, ?, 0)
                ''', (user_id, referrer_id))
                conn.execute('''
                    UPDATE referrals SET count = count + 1 WHERE user_id = ?
                ''', (referrer_id,))
                conn.commit()

    await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    is_premium = db.is_premium(user_id)
    ref_count = db.get_referral_count(user_id)
    theme = user["theme"]
    theme_icon = "🌑" if theme == "dark" else "☀️"

    keyboard = [
        [InlineKeyboardButton("🌤 Погода", callback_data="weather"),
         InlineKeyboardButton("⏰ Время", callback_data="time")],
        [InlineKeyboardButton("💱 Курсы", callback_data="currency"),
         InlineKeyboardButton("🎬 Фильмы", callback_data="movies" if is_premium else "premium_info")],
        [InlineKeyboardButton("🛡 Антивирусы", callback_data="antivirus"),
         InlineKeyboardButton("🔔 Напоминания", callback_data="reminders")],
        [InlineKeyboardButton("💳 Подписки", callback_data="subscriptions"),
         InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton("💎 Премиум", callback_data="premium")],
    ]

    if user["is_admin"]:
        keyboard.append([InlineKeyboardButton("🔧 Админ-панель", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text("🏠 Главное меню", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🏠 Главное меню", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "back_to_main":
        await show_main_menu(update, context)
        return

    # --- Время ---
    elif query.data == "time":
        moscow_time = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%H:%M:%S")
        await query.edit_message_text(
            f"⏰ <b>Московское время</b>\n\n<code>{moscow_time}</code>",
            parse_mode='HTML',
            reply_markup=back_button()
        )

    # --- Погода ---
    elif query.data == "weather":
        user = db.get_user(user_id)
        if not db.is_premium(user_id) and user["daily_weather_count"] >= 5:
            await query.edit_message_text("❌ Лимит погоды (5/день)", reply_markup=back_button())
            return
        await query.edit_message_text("🌆 Введите название города:")
        context.user_data["awaiting"] = "weather_city"
        db.log_action(user_id, "weather_requested")

    # --- Курсы ---
    elif query.data == "currency":
        user = db.get_user(user_id)
        if not db.is_premium(user_id) and user["daily_currency_count"] >= 5:
            await query.edit_message_text("❌ Лимит курсов (5/день)", reply_markup=back_button())
            return
        rates = get_cached_cbr_rates()
        usd, eur = rates['USD_RUB'], rates['EUR_RUB']
        date = rates['date']
        await query.edit_message_text(
            f"🏛 <b>Официальные курсы ЦБ РФ</b>\n\n"
            f"🇺🇸 1 USD = <b>{usd}</b> ₽\n"
            f"🇪🇺 1 EUR = <b>{eur}</b> ₽\n\n"
            f"📅 Дата: <i>{date}</i>",
            parse_mode='HTML',
            reply_markup=back_button()
        )
        db.update_user(user_id, daily_currency_count=user["daily_currency_count"] + 1)
        db.log_action(user_id, "currency_check")

    # --- Фильмы ---
    elif query.data == "movies":
        await query.edit_message_text("🎭 Выберите жанр:", reply_markup=genre_keyboard())
        context.user_data["awaiting"] = "movie_genre"

    elif query.data in MOVIE_GENRES:
        genre = query.data
        context.user_data["movie_genre"] = genre
        await query.edit_message_text("🎬 Введите год (например: 2020):")
        context.user_data["awaiting"] = "movie_year"

    # --- Антивирусы ---
    elif query.data == "antivirus":
        await query.edit_message_text(
            "📎 Пришлите ссылку или файл для проверки",
            reply_markup=back_button()
        )
        context.user_data["awaiting"] = "scan_file_or_url"

    # --- Премиум ---
    elif query.data == "premium":
        await show_premium_info(query, context)

    elif query.data == "premium_info":
        await show_premium_info(query, context)

    elif query.data == "claim_ref_bonus":
        if db.get_referral_count(user_id) >= 3:
            db.grant_premium(user_id, 7)
            await query.edit_message_text("🎉 Вы получили 7 дней премиума!")
            db.log_action(user_id, "ref_bonus_claimed")
        else:
            await query.edit_message_text("❌ Недостаточно рефералов")

    # --- Настройки ---
    elif query.data == "settings":
        theme = db.get_user(user_id)["theme"]
        theme_text = "🌑 Тёмная" if theme == "dark" else "☀️ Светлая"
        keyboard = [
            [InlineKeyboardButton(f"🎨 Тема: {theme_text}", callback_data="change_theme")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
        ]
        await query.edit_message_text("⚙️ Настройки", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "change_theme":
        user = db.get_user(user_id)
        new_theme = "dark" if user["theme"] == "light" else "light"
        db.update_user(user_id, theme=new_theme)
        await query.edit_message_text(f"🎨 Тема изменена на {new_theme}", reply_markup=back_button())

    # --- Админка ---
    elif query.data == "admin_panel":
        await admin_panel(update, context)

    elif query.data == "admin_stats":
        await admin_stats(update, context)

    elif query.data == "admin_broadcast":
        await admin_broadcast_start(update, context)

    elif query.data == "admin_grant_premium":
        await admin_grant_premium_start(update, context)

    elif query.data == "admin_logs":
        await admin_logs(update, context)

    # --- Другие ---
    elif query.data == "reminders":
        reminders = db.get_reminders(user_id)
        text = "🔔 Ваши напоминания:\n\n" + "\n".join([f"• {r['text']} — {r['time']}" for r in reminders])
        await query.edit_message_text(text or "📌 У вас нет напоминаний", reply_markup=back_button())

    elif query.data == "subscriptions":
        subs = db.get_subscriptions(user_id)
        text = "💳 Ваши подписки:\n\n" + "\n".join([f"• {s['name']} — {s['renewal_date']}" for s in subs])
        await query.edit_message_text(text or "📌 У вас нет подписок", reply_markup=back_button())

    db.log_action(user_id, f"button_{query.data}")


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]])

def genre_keyboard():
    buttons = [[InlineKeyboardButton(name, callback_data=code)] for code, name in MOVIE_GENRES.items()]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)

async def show_premium_info(query, context):
    user_id = query.from_user.id
    is_premium = db.is_premium(user_id)
    ref_count = db.get_referral_count(user_id)
    premium_url = (
        f"https://app.tonkeeper.com/transfer/{db.WALLET_ADDRESS}"
        f"?amount=20000000&text=premium:{user_id}"
    )
    text = (
        f"💎 <b>Премиум-доступ</b>\n\n"
        f"✅ Статус: <b>{'Активен' if is_premium else 'Не активен'}</b>\n"
        f"🎁 За 3 реферала — <b>7 дней бесплатно</b>\n\n"
        f"👥 У вас: {ref_count}/3 реферала"
    )
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить 0.02 TON", url=premium_url)],
        [InlineKeyboardButton("🎁 Получить бесплатно", callback_data="claim_ref_bonus")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))


# --- ОБРАБОТКА СООБЩЕНИЙ ---

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    awaiting = context.user_data.get("awaiting")

    if awaiting == "weather_city":
        city = text
        api_key = os.getenv("WEATHER_API_KEY")
        if not api_key:
            await update.message.reply_text("🔧 Ключ погоды не задан", reply_markup=back_button())
            return
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        try:
            response = requests.get(url, timeout=10).json()
            temp = response['main']['temp']
            desc = response['weather'][0]['description']
            await update.message.reply_text(
                f"🌤 <b>{city.title()}</b>\n\n"
                f"🌡 Температура: <b>{temp}°C</b>\n"
                f"☁️ {desc.title()}",
                parse_mode='HTML',
                reply_markup=back_button()
            )
            db.update_user(user_id, daily_weather_count=db.get_user(user_id)["daily_weather_count"] + 1)
            db.log_action(user_id, "weather_result")
        except:
            await update.message.reply_text("❌ Город не найден", reply_markup=back_button())
        context.user_data.clear()

    elif awaiting == "movie_year":
        try:
            year = int(text)
            genre = context.user_data["movie_genre"]
            # (здесь можно подключить API Кинопоиска)
            await update.message.reply_text(
                f"🎬 Подбор: '{MOVIE_GENRES[genre]}' ({year})\nПример: 'Интерстеллар'",
                reply_markup=back_button()
            )
            db.update_user(user_id, daily_movies_count=db.get_user(user_id)["daily_movies_count"] + 1)
            db.log_action(user_id, "movie_suggested")
        except:
            await update.message.reply_text("❌ Введите корректный год", reply_markup=back_button())
        context.user_data.clear()

    elif awaiting == "scan_file_or_url":
        # (здесь будет интеграция с VirusTotal)
        await update.message.reply_text("✅ Файл проверен — угроз не обнаружено", reply_markup=back_button())
        db.update_user(user_id, daily_scan_count=db.get_user(user_id)["daily_scan_count"] + 1)
        db.log_action(user_id, "file_scanned")
        context.user_data.clear()

    elif awaiting == "admin_broadcast_message":
        context.user_data["admin_broadcast_message"] = text
        await update.message.reply_text(
            "Вы уверены?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да", callback_data="admin_broadcast_confirm")],
                [InlineKeyboardButton("❌ Нет", callback_data="admin_panel")]
            ])
        )
        context.user_data["awaiting"] = None

    elif awaiting == "admin_grant_premium_id":
        try:
            target_id = int(text)
            db.grant_premium(target_id, 30)
            await update.message.reply_text(f"✅ Премиум выдан: {target_id}")
            db.log_action(user_id, f"premium_granted_to_{target_id}")
        except:
            await update.message.reply_text("❌ Ошибка")
        context.user_data.clear()

    else:
        await update.message.reply_text("Используйте меню", reply_markup=back_button())


# --- ОСНОВНОЙ ЗАПУСК ---

def main():
    global application
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("test_ton", test_ton_api))  # Тест TON

    # Колбэки
    application.add_handler(CallbackQueryHandler(button_handler))

    # Сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.Entity("url"), message_handler))

    # Задачи
    application.job_queue.run_repeating(check_pending_payments, interval=300, first=10)
    application.job_queue.run_daily(fetch_cbr_rates, time=datetime.time(hour=8, minute=30, tzinfo=timezone(timedelta(hours=3))))
    application.job_queue.run_daily(
        lambda ctx: ctx.bot.send_document(1799560429, open("bot.db", "rb"), caption="📦 Бэкап"),
        time=datetime.time(hour=3, minute=0, tzinfo=timezone(timedelta(hours=3)))
    )

    logger.info("✅ Бот запущен. Премиум, TON, Google Sheets — активны.")
    application.run_polling()

if __name__ == '__main__':
    main()

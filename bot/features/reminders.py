# bot/features/reminders.py

import re
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from database import get_db_pool
from loguru import logger

# --- Тексты ---
TEXTS = {
    "ru": {
        "set": "✅ Напомню через <b>{when}</b>: <i>{text}</i>",
        "at": "в {time}",
        "error_time": "❌ Неверный формат времени. Пример: <code>/remind 1h30m Сделать дело</code>",
        "error_text": "❌ Укажите, что напомнить.",
        "no_active": "📭 У вас нет активных напоминаний.",
        "list_title": "📋 Ваши активные напоминания:\n\n",
        "item": "🔔 <i>{text}</i>\n🕒 {when}\n\n",
        "alert": "📌 Напоминание!\n\n<i>{text}</i>",
    },
    "en": {
        "set": "✅ I'll remind you in <b>{when}</b>: <i>{text}</i>",
        "at": "at {time}",
        "error_time": "❌ Invalid time format. Example: <code>/remind 1h30m Do something</code>",
        "error_text": "❌ Please specify what to remind.",
        "no_active": "📭 You have no active reminders.",
        "list_title": "📋 Your active reminders:\n\n",
        "item": "🔔 <i>{text}</i>\n🕒 {when}\n\n",
        "alert": "📌 Reminder!\n\n<i>{text}</i>",
    }
}


def parse_time_string(time_str: str) -> Optional[timedelta]:
    """Парсит строки вроде: 10m, 2h, 1h30m, 5m30s"""
    pattern = r'(\d+)([hms])'
    matches = re.findall(pattern, time_str.lower())
    if not matches:
        return None

    total_seconds = 0
    for value, unit in matches:
        value = int(value)
        if unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60
        elif unit == 's':
            total_seconds += value
    return timedelta(seconds=total_seconds)


async def get_user_lang(pool, user_id: int) -> str:
    lang = await pool.fetchval("SELECT language FROM users WHERE id = $1", user_id)
    return lang or "ru"


async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]

    if not context.args:
        await update.message.reply_text(texts["error_time"])
        return

    # Разделяем аргументы: сначала время, потом текст
    time_str = context.args[0]
    reminder_text = " ".join(context.args[1:])

    if not reminder_text:
        await update.message.reply_text(texts["error_text"])
        return

    # Парсим время
    delta = parse_time_string(time_str)
    if not delta:
        await update.message.reply_text(texts["error_time"], parse_mode='HTML')
        return

    # Вычисляем время напоминания
    remind_at = datetime.now() + delta

    # Сохраняем в БД
    await pool.execute(
        "INSERT INTO reminders (user_id, text, time) VALUES ($1, $2, $3)",
        user.id, reminder_text, remind_at
    )

    # Форматируем "через X"
    when = format_when(delta, lang)
    await update.message.reply_html(texts["set"].format(when=when, text=reminder_text))

    # Планируем задачу
    context.job_queue.run_once(
        send_reminder,
        when=delta,
        chat_id=user.id,
        user_id=user.id,
        data={"text": reminder_text}
    )


async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Функция, которая вызывается по времени"""
    job = context.job
    await context.bot.send_message(
        chat_id=job.chat_id,
        text=TEXTS.get("en", {}).get("alert", "").format(text=job.data["text"]),
        parse_mode='HTML'
    )

    # Удаляем напоминание из БД после отправки
    pool = context.application.bot_data['db_pool']
    await pool.execute(
        "DELETE FROM reminders WHERE user_id = $1 AND text = $2",
        job.user_id, job.data["text"]
    )


def format_when(delta: timedelta, lang: str) -> str:
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if hours:
        if lang == "ru":
            h_text = "час" if hours == 1 else "часа" if hours < 5 else "часов"
        else:
            h_text = "hour" if hours == 1 else "hours"
        parts.append(f"{hours} {h_text}")

    if minutes:
        if lang == "ru":
            m_text = "минута" if minutes == 1 else "минуты" if minutes < 5 else "минут"
        else:
            m_text = "minute" if minutes == 1 else "minutes"
        parts.append(f"{minutes} {m_text}")

    return " и ".join(parts) if parts else "сейчас"


async def cmd_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]

    rows = await pool.fetch(
        "SELECT text, time FROM reminders WHERE user_id = $1 AND time > NOW() ORDER BY time",
        user.id
    )

    if not rows:
        await update.message.reply_text(texts["no_active"])
        return

    message = texts["list_title"]
    for row in rows:
        text = row["text"]
        when = row["time"].strftime("%d.%m %H:%M")
        message += texts["item"].format(text=text, when=texts["at"].format(time=when))

    await update.message.reply_html(message)


def setup_reminder_handlers(app):
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CommandHandler("reminders", cmd_reminders))
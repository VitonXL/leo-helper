# bot/features/reminders.py
import re
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from database import get_db_pool, get_user_lang  # ✅ импорт из database
from loguru import logger

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
    pattern = r'(\d+)([hms])'
    matches = re.findall(pattern, time_str.lower())
    if not matches:
        return None
    total_seconds = 0
    for value, unit in matches:
        value = int(value)
        if unit == 'h': total_seconds += value * 3600
        elif unit == 'm': total_seconds += value * 60
        elif unit == 's': total_seconds += value
    return timedelta(seconds=total_seconds)

async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]
    if not context.args: return await update.message.reply_text(texts["error_time"])
    time_str = context.args[0]
    reminder_text = " ".join(context.args[1:])
    if not reminder_text: return await update.message.reply_text(texts["error_text"])
    delta = parse_time_string(time_str)
    if not delta: return await update.message.reply_text(texts["error_time"], parse_mode='HTML')
    remind_at = datetime.now() + delta
    await pool.execute("INSERT INTO reminders (user_id, text, time) VALUES ($1, $2, $3)", user.id, reminder_text, remind_at)
    when = format_when(delta, lang)
    await update.message.reply_html(texts["set"].format(when=when, text=reminder_text))
    context.job_queue.run_once(send_reminder, when=delta, chat_id=user.id, user_id=user.id, data={"text": reminder_text})

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, job.user_id)
    texts = TEXTS[lang]
    await context.bot.send_message(
        chat_id=job.chat_id,
        text=texts["alert"].format(text=job.data["text"]),
        parse_mode='HTML'
    )
    await pool.execute("DELETE FROM reminders WHERE user_id = $1 AND text = $2", job.user_id, job.data["text"])

def format_when(delta: timedelta, lang: str) -> str:
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if hours: parts.append(f"{hours} {'час' if hours == 1 else 'часа' if hours < 5 else 'часов'}" if lang == "ru" else f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes: parts.append(f"{minutes} {'минута' if minutes == 1 else 'минуты' if minutes < 5 else 'минут'}" if lang == "ru" else f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " и ".join(parts) if parts else "сейчас"

async def cmd_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]
    rows = await pool.fetch("SELECT text, time FROM reminders WHERE user_id = $1 AND time > NOW() ORDER BY time", user.id)
    if not rows: return await update.message.reply_text(texts["no_active"])
    message = texts["list_title"]
    for row in rows:
        when = row["time"].strftime("%d.%m %H:%M")
        message += texts["item"].format(text=row["text"], when=texts["at"].format(time=when))
    await update.message.reply_html(message)

def setup_reminder_handlers(app):
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CommandHandler("reminders", cmd_reminders))
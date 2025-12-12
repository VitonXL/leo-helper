# bot/commands/reminders.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from datetime import datetime, timedelta
import re
from bot.database import get_user, check_premium, log_action

# Временное хранилище (позже заменим на БД)
user_states = {}  # user_id: {state: ..., data: ...}

# Словарь для задач APScheduler (управление активными задачами)
scheduled_jobs = {}

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Сначала начните бота: /start")
        return

    # Проверим, сколько активных напоминаний
    active_count = _get_active_reminders_count(user_id)
    premium = check_premium(user_id)

    if not premium and active_count >= 3:
        await update.message.reply_text(
            "❗ Вы достигли лимита в 3 активных напоминания.\n"
            "Станьте премиум-пользователем, чтобы иметь неограниченное количество."
        )
        return

    # Если есть аргументы: /remind 19:30 Позвонить маме
    if context.args:
        try:
            time_str = context.args[0]
            text = " ".join(context.args[1:])
            if not text:
                raise ValueError

            # Парсим время
            time_match = re.match(r"(\d{1,2}):(\d{2})", time_str)
            if not time_match:
                raise ValueError

            hours, minutes = map(int, time_match.groups())
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError

            now = datetime.now()
            reminder_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)

            # Если время уже прошло — на завтра
            if reminder_time <= now:
                reminder_time += timedelta(days=1)

            # Сохраняем в БД
            reminder_id = _save_reminder(user_id, text, reminder_time)

            # Назначаем задачу
            _schedule_reminder(context, user_id, reminder_id, text, reminder_time)

            await update.message.reply_text(
                f"✅ Напоминание установлено на {reminder_time.strftime('%d.%m.%Y в %H:%M')}\n"
                f"📝 Текст: {text}"
            )
            log_action(user_id, "reminder_set", f"{time_str} | {text[:50]}")

        except:
            await update.message.reply_text(
                "❌ Неверный формат.\n"
                "Используй: `/remind ЧЧ:ММ текст`", parse_mode='Markdown'
            )
    else:
        # Интерактивный режим
        keyboard = [
            [InlineKeyboardButton("🕒 Указать время", callback_data="reminder_set_time")],
            [InlineKeyboardButton("📅 Напоминание через...", callback_data="reminder_set_delay")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⏰ Как вы хотите установить напоминание?",
            reply_markup=reply_markup
        )


async def reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "reminder_set_time":
        await query.message.reply_text("Введите время в формате ЧЧ:ММ:")
        user_states[user_id] = {'state': 'waiting_time'}
        await query.answer()

    elif data == "reminder_set_delay":
        keyboard = [
            [InlineKeyboardButton("🔔 Через 5 минут", callback_data="delay_5")],
            [InlineKeyboardButton("🔔 Через 30 минут", callback_data="delay_30")],
            [InlineKeyboardButton("🔔 Через 1 час", callback_data="delay_60")],
            [InlineKeyboardButton("🔔 Завтра", callback_data="delay_1440")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Выберите задержку:", reply_markup=reply_markup)
        await query.answer()

    elif data.startswith("delay_"):
        delay_min = int(data.split("_")[1])
        delay_sec = delay_min * 60
        reminder_time = datetime.now() + timedelta(seconds=delay_sec)

        # Проверим лимит
        active_count = _get_active_reminders_count(user_id)
        premium = check_premium(user_id)
        if not premium and active_count >= 3:
            await query.message.reply_text(
                "❗ Вы достигли лимита в 3 активных напоминания."
            )
            await query.answer()
            return

        await query.message.reply_text("Введите текст напоминания:")
        user_states[user_id] = {
            'state': 'waiting_text',
            'time': reminder_time,
            'type': 'delay'
        }
        await query.answer()


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_states:
        return

    state = user_states[user_id]

    if state['state'] == 'waiting_time':
        try:
            time_match = re.match(r"(\d{1,2}):(\d{2})", text)
            if not time_match:
                raise ValueError
            hours, minutes = map(int, time_match.groups())
            now = datetime.now()
            reminder_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            if reminder_time <= now:
                reminder_time += timedelta(days=1)

            await update.message.reply_text("Введите текст напоминания:")
            user_states[user_id] = {
                'state': 'waiting_text',
                'time': reminder_time,
                'type': 'exact'
            }
        except:
            await update.message.reply_text("❌ Неверный формат времени. Попробуйте ещё раз (ЧЧ:ММ).")

    elif state['state'] == 'waiting_text':
        reminder_time = state['time']
        reminder_text = text

        # Проверим лимит перед сохранением
        active_count = _get_active_reminders_count(user_id)
        premium = check_premium(user_id)
        if not premium and active_count >= 3:
            await update.message.reply_text(
                "❗ Вы достигли лимита в 3 активных напоминания."
            )
            return

        # Сохраняем
        reminder_id = _save_reminder(user_id, reminder_text, reminder_time)
        _schedule_reminder(context, user_id, reminder_id, reminder_text, reminder_time)

        time_str = reminder_time.strftime('%d.%m.%Y в %H:%M')
        await update.message.reply_text(f"✅ Напоминание установлено на {time_str}\n📝 {reminder_text}")
        log_action(user_id, "reminder_set", f"{time_str} | {reminder_text[:50]}")

        # Очищаем состояние
        del user_states[user_id]


async def show_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = _get_user_reminders(user_id)
    if not reminders:
        await update.message.reply_text("У вас нет активных напоминаний.")
        return

    msg = "🔔 *Ваши напоминания*\n\n"
    for r in reminders:
        time_str = r['time'].strftime('%d.%m.%Y в %H:%M')
        msg += f"• {time_str} — {r['text']}\n"

    await update.message.reply_text(msg, parse_mode='Markdown')


def _save_reminder(user_id, text, time):
    """Сохранить напоминание в БД"""
    from bot.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reminders (user_id, text, time, active)
        VALUES (%s, %s, %s, TRUE)
        RETURNING id
    """, (user_id, text, time))
    reminder_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return reminder_id


def _get_user_reminders(user_id):
    """Получить активные напоминания"""
    from bot.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM reminders
        WHERE user_id = %s AND active = TRUE
        ORDER BY time
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _get_active_reminders_count(user_id):
    """Сколько активных напоминаний"""
    return len(_get_user_reminders(user_id))


def _schedule_reminder(context: ContextTypes.DEFAULT_TYPE, user_id, reminder_id, text, time):
    """Назначить задачу в боте"""
    job = context.job_queue.run_once(
        send_reminder,
        when=time,
        chat_id=user_id,
        name=str(reminder_id),
        data={'user_id': user_id, 'reminder_id': reminder_id, 'text': text}
    )
    scheduled_jobs[reminder_id] = job


async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Функция, которая вызывается при срабатывании напоминания"""
    job = context.job
    user_id = job.data['user_id']
    reminder_id = job.data['reminder_id']
    text = job.data['text']

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"⏰ Напоминание!\n\n{text}",
            parse_mode='Markdown'
        )
    except:
        pass  # Пользователь заблокировал бота

    # Деактивируем в БД
    from bot.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET active = FALSE WHERE id = %s", (reminder_id,))
    conn.commit()
    conn.close()

    # Удаляем из памяти
    if reminder_id in scheduled_jobs:
        del scheduled_jobs[reminder_id]

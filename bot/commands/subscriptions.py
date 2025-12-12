# bot/commands/subscriptions.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from datetime import datetime, date, timedelta
from bot.database import get_db, check_premium, log_action

# Состояния
ADD_NAME, ADD_PRICE, ADD_DATE, ADD_PERIOD = range(4)

async def subs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subs = _get_subscriptions(user_id)
    premium = check_premium(user_id)
    limit = 10 if premium else 3

    keyboard = [
        [InlineKeyboardButton("➕ Добавить подписку", callback_data="add_sub_start")]
    ]

    if subs:
        msg = f"📋 *Ваши подписки* (лимит: {len(subs)}/{limit})\n\n"
        now = date.today()
        for sub in subs:
            name = sub['name']
            price = sub['price']
            due = sub['due_date']
            days_left = (due - now).days
            status = "✅ Активна" if days_left >= 0 else "❌ Просрочена"
            color = "🟢" if days_left > 3 else "🟡" if days_left > 0 else "🔴"

            msg += f"{color} *{name}*\n"
            msg += f"💸 {price} ₽ | Дата: `{due}` | {status}\n\n"
        keyboard.append([InlineKeyboardButton("🗑️ Управление", callback_data="manage_subs")])
    else:
        msg = f"У вас пока нет подписок.\nЛимит: {limit} шт."

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')


async def add_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    premium = check_premium(user_id)
    count = len(_get_subscriptions(user_id))
    limit = 10 if premium else 3

    if count >= limit:
        await query.message.reply_text(
            f"❗ Достигнут лимит в {limit} подписок.\n"
            "Станьте премиум-пользователем, чтобы добавить больше."
        )
        await query.answer()
        return

    await query.message.reply_text("Введите название подписки (например: *Netflix*)", parse_mode='Markdown')
    await query.answer()
    return ADD_NAME


async def add_sub_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sub_name'] = update.message.text
    await update.message.reply_text("Введите сумму (например: 499)")
    return ADD_PRICE


async def add_sub_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['sub_price'] = float(update.message.text)
    except:
        await update.message.reply_text("❌ Неверная сумма. Введите число.")
        return ADD_PRICE
    await update.message.reply_text("Введите дату оплаты (в формате ДД.ММ):")
    return ADD_DATE


async def add_sub_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        day, month = map(int, text.split('.'))
        year = date.today().year
        # Если месяц уже прошёл — значит, на следующий год
        if month < date.today().month or (month == date.today().month and day < date.today().day):
            year += 1
        due_date = date(year, month, day)
        context.user_data['sub_date'] = due_date
    except:
        await update.message.reply_text("❌ Неверный формат. Пример: `05.04`")
        return ADD_DATE

    keyboard = [
        [InlineKeyboardButton("🔁 Каждый месяц", callback_data="period_month")],
        [InlineKeyboardButton("🔁 Каждый год", callback_data="period_year")],
        [InlineKeyboardButton("📌 Один раз", callback_data="period_once")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите периодичность:", reply_markup=reply_markup)
    return ADD_PERIOD


async def add_sub_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    period = query.data.replace("period_", "")
    name = context.user_data['sub_name']
    price = context.user_data['sub_price']
    due_date = context.user_data['sub_date']
    user_id = query.from_user.id

    # Сохраняем
    _save_subscription(user_id, name, price, due_date, period)
    await query.message.reply_text(f"✅ Подписка *{name}* добавлена!", parse_mode='Markdown')
    log_action(user_id, "sub_added", f"{name} | {price} | {due_date}")
    context.user_data.clear()
    await query.answer()


async def manage_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    subs = _get_subscriptions(user_id)
    if not subs:
        await query.message.reply_text("Нет подписок.")
        await query.answer()
        return

    keyboard = [
        [InlineKeyboardButton(f"🗑️ {s['name']} (ID: {s['id']})", callback_data=f"del_sub_{s['id']}")]
        for s in subs
    ]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_subs")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("📂 Управление подписками:", reply_markup=reply_markup)
    await query.answer()


async def delete_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    sub_id = int(query.data.replace("del_sub_", ""))
    _delete_subscription(sub_id)
    await query.message.reply_text("✅ Подписка удалена.")
    await query.answer()


async def back_to_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await subs_command(update, context)
    await update.callback_query.answer()


# --- Функции БД ---
def _get_subscriptions(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = %s AND active = TRUE ORDER BY due_date", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _save_subscription(user_id, name, price, due_date, period):
    conn = get_db()
    cursor = conn.cursor()
    # Для ежемесячных/ежегодных — active остаётся True
    cursor.execute("""
        INSERT INTO subscriptions (user_id, name, price, due_date, active)
        VALUES (%s, %s, %s, %s, TRUE)
    """, (user_id, name, price, due_date))
    conn.commit()
    conn.close()


def _delete_subscription(sub_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE subscriptions SET active = FALSE WHERE id = %s", (sub_id,))
    conn.commit()
    conn.close()


# --- Ежедневная проверка — добавь в bot.py
async def check_due_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    """Проверяет, какие подписки скоро заканчиваются"""
    conn = get_db()
    cursor = conn.cursor()
    today = date.today()
    # За 3 дня до оплаты
    due_soon = today + timedelta(days=3)

    cursor.execute("""
        SELECT s.*, u.user_id FROM subscriptions s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.due_date = %s AND s.active = TRUE
    """, (due_soon,))
    rows = cursor.fetchall()

    for row in rows:
        try:
            await context.bot.send_message(
                row['user_id'],
                f"🔔 *Напоминание*\n\n"
                f"Через 3 дня нужно оплатить:\n"
                f"💳 {row['name']}\n"
                f"💸 {row['price']} ₽\n\n"
                f"Дата оплаты: `{row['due_date']}`",
                parse_mode='Markdown'
            )
        except:
            pass

    conn.close()

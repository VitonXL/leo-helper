# bot/features/subscriptions.py
import re
from datetime import datetime, timedelta
from decimal import Decimal

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_db_pool, get_user_lang
from loguru import logger

TEXTS = {
    "ru": {
        "usage": "📌 Использование:\n<code>/subscribe Название сумма период</code>\n\nПример:\n<code>/subscribe Spotify 249 1m</code>\n<code>/subscribe Квартира 25000 1m</code>\n<code>/subscribe Доставка 99 2w</code>\n\nПериоды: <b>d</b> — день, <b>w</b> — неделя, <b>m</b> — месяц, <b>y</b> — год",
        "added": "✅ Подписка добавлена:\n🛒 <b>{name}</b>\n💰 {amount} {currency}\n📅 Следующий платёж: <b>{next}</b>\n🔄 Каждые: <i>{cycle}</i>",
        "error_amount": "❌ Сумма должна быть числом.",
        "error_cycle": "❌ Неверный период. Используйте: d=день, w=неделя, m=месяц, y=год. Пример: 1m, 2w",
        "no_subscriptions": "📭 У вас нет активных подписок.",
        "list_title": "📋 Ваши подписки:\n\n",
        "sub_item": "🛒 <b>{name}</b>\n💰 {amount} {currency}\n📅 Следующий платёж: <b>{next}</b>\n🔄 {cycle_text}\n\n",
        "reminder": "🔔 <b>Пора оплатить подписку!</b>\n\n📌 <i>{name}</i>\n💳 {amount} {currency}\n\nОплатите вовремя, чтобы не потерять доступ.",
        "cycle": {"daily": "каждый день", "weekly": "каждую неделю", "monthly": "каждый месяц", "yearly": "каждый год", "custom": "каждые {value} {unit}"},
        "unit": {"d": "дн.", "w": "нед.", "m": "мес.", "y": "год"}
    },
    "en": {
        "usage": "📌 Usage:\n<code>/subscribe Name amount period</code>\n\nExample:\n<code>/subscribe Spotify 9.99 1m</code>\n<code>/subscribe Rent 1200 1m</code>\n<code>/subscribe Food 19.9 2w</code>\n\nPeriods: <b>d</b> — day, <b>w</b> — week, <b>m</b> — month, <b>y</b> — year",
        "added": "✅ Subscription added:\n🛒 <b>{name}</b>\n💰 {amount} {currency}\n📅 Next payment: <b>{next}</b>\n🔄 Every: <i>{cycle}</i>",
        "error_amount": "❌ Amount must be a number.",
        "error_cycle": "❌ Invalid period. Use: d=day, w=week, m=month, y=year. Example: 1m, 2w",
        "no_subscriptions": "📭 You have no active subscriptions.",
        "list_title": "📋 Your subscriptions:\n\n",
        "sub_item": "🛒 <b>{name}</b>\n💰 {amount} {currency}\n📅 Next payment: <b>{next}</b>\n🔄 {cycle_text}\n\n",
        "reminder": "🔔 <b>Time to pay your subscription!</b>\n\n📌 <i>{name}</i>\n💳 {amount} {currency}\n\nPay on time to avoid losing access.",
        "cycle": {"daily": "daily", "weekly": "weekly", "monthly": "monthly", "yearly": "yearly", "custom": "every {value} {unit}"},
        "unit": {"d": "day(s)", "w": "week(s)", "m": "month(s)", "y": "year(s)"}
    }
}

def parse_cycle(cycle_str: str) -> tuple[Optional[timedelta], str]:
    match = re.match(r'^(\d+)([dwmy])$', cycle_str.strip().lower())
    if not match: return None, ""
    value, unit = int(match.group(1)), match.group(2)
    if unit == 'd': return timedelta(days=value), f"{value} day(s)"
    elif unit == 'w': return timedelta(weeks=value), f"{value} week(s)"
    elif unit == 'm': return timedelta(days=value * 30), f"{value} month(s)"
    elif unit == 'y': return timedelta(days=value * 365), f"{value} year(s)"
    return None, ""

def format_cycle_for_user(cycle_str: str, lang: str) -> str:
    texts = TEXTS[lang]
    match = re.match(r'^(\d+)([dwmy])$', cycle_str.strip().lower())
    if not match: return cycle_str
    value, unit = int(match.group(1)), match.group(2)
    if value == 1: return texts["cycle"][{"d": "daily", "w": "weekly", "m": "monthly", "y": "yearly"}[unit]]
    return texts["cycle"]["custom"].format(value=value, unit=texts["unit"][unit])

async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]
    if not context.args or len(context.args) < 3: return await update.message.reply_html(texts["usage"])
    try:
        name, amount, cycle_str = context.args[0], Decimal(context.args[1]), context.args[2]
        currency = "₽" if lang == "ru" else "$"
        delta, _ = parse_cycle(cycle_str)
        if not delta: return await update.message.reply_text(texts["error_cycle"])
        next_payment = datetime.now() + delta
        await pool.execute("INSERT INTO subscriptions (user_id, name, amount, currency, billing_cycle, next_payment) VALUES ($1, $2, $3, $4, $5, $6)", user.id, name, amount, currency, delta, next_payment)
        remind_time = next_payment - datetime.now()
        if remind_time.total_seconds() > 0:
            context.job_queue.run_once(
                send_subscription_reminder,
                when=remind_time - timedelta(days=1),
                chat_id=user.id,
                data={"name": name, "amount": amount, "currency": currency, "user_id": user.id}
            )
        cycle_text = format_cycle_for_user(cycle_str, lang)
        next_str = next_payment.strftime("%d.%m.%Y")
        await update.message.reply_html(texts["added"].format(name=name, amount=amount, currency=currency, next=next_str, cycle=cycle_text))
    except Exception as e:
        logger.error(f"Ошибка при добавлении подписки: {e}")
        await update.message.reply_text(texts["error_amount"])

async def cmd_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]
    rows = await pool.fetch("SELECT name, amount, currency, billing_cycle, next_payment FROM subscriptions WHERE user_id = $1 ORDER BY next_payment", user.id)
    if not rows: return await update.message.reply_text(texts["no_subscriptions"])
    message = texts["list_title"]
    for row in rows:
        cycle_text = format_cycle_for_user("1m", lang)
        next_str = row["next_payment"].strftime("%d.%m.%Y")
        message += texts["sub_item"].format(name=row["name"], amount=row["amount"], currency=row["currency"], next=next_str, cycle_text=cycle_text)
    await update.message.reply_html(message)

async def send_subscription_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, job.data["user_id"])
    texts = TEXTS[lang]
    await context.bot.send_message(
        chat_id=job.chat_id,
        text=texts["reminder"].format(name=job.data["name"], amount=job.data["amount"], currency=job.data["currency"]),
        parse_mode='HTML'
    )

def setup_subscription_handlers(app):
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("subscriptions", cmd_subscriptions))
# bot/commands/currency.py

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, date
import requests
import xml.etree.ElementTree as ET
from bot.database import get_user, check_premium, log_action

# Словарь для отслеживания запросов (позже — в БД)
user_currency_requests = {}  # user_id: {date: '2025-04-05', count: 2}

# Курс валют ЦБ РФ
CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"

CURRENCY_MAP = {
    'usd': 'USD',
    'доллар': 'USD',
    'доллары': 'USD',
    'доллар США': 'USD',
    'eur': 'EUR',
    'евро': 'EUR',
    'фунт': 'GBP',
    'cny': 'CNY',
    'юань': 'CNY'
}

def get_exchange_rates():
    """Получает курсы валют от ЦБ РФ"""
    try:
        response = requests.get(CBR_URL)
        response.encoding = 'windows-1251'  # ЦБ РФ использует win-1251
        root = ET.fromstring(response.text)

        rates = {}
        for valute in root.findall('Valute'):
            charcode = valute.find('CharCode').text
            if charcode in ['USD', 'EUR', 'GBP', 'CNY']:
                value = float(valute.find('Value').text.replace(',', '.'))
                name = valute.find('Name').text
                rates[charcode] = {'name': name, 'value': value}

        return rates
    except Exception as e:
        print(f"Ошибка получения курсов: {e}")
        return None


def can_request_currency(user_id):
    """Проверяет, может ли пользователь запросить курс"""
    premium = check_premium(user_id)
    max_requests = 5 if premium else 1

    today = date.today().isoformat()
    if user_id not in user_currency_requests:
        user_currency_requests[user_id] = {'date': today, 'count': 0}

    user_data = user_currency_requests[user_id]

    if user_data['date'] != today:
        user_data['date'] = today
        user_data['count'] = 0

    return user_data['count'] < max_requests


def increment_request(user_id):
    """Увеличивает счётчик запросов"""
    if user_id not in user_currency_requests:
        user_currency_requests[user_id] = {'date': date.today().isoformat(), 'count': 0}
    user_currency_requests[user_id]['count'] += 1


async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Сначала начните бота: /start")
        return

    # Проверяем лимит
    if not can_request_currency(user_id):
        premium = check_premium(user_id)
        limit = 5 if premium else 1
        await update.message.reply_text(
            f"❗ Вы исчерпали лимит запросов курсов валют на сегодня.\n"
            f"Лимит: {limit} запросов в сутки.\n"
            "Станьте премиум-пользователем, чтобы увеличить лимит."
        )
        return

    # Если есть аргументы: /currency usd
    if context.args:
        query = " ".join(context.args).lower()
        target = None
        for key, code in CURRENCY_MAP.items():
            if key in query:
                target = code
                break

        if not target:
            await update.message.reply_text(
                "❌ Неизвестная валюта. Доступно: USD, EUR, GBP, CNY.\n"
                "Пример: `/currency usd`", parse_mode='Markdown'
            )
            return

        rates = get_exchange_rates()
        if not rates or target not in rates:
            await update.message.reply_text("❌ Не удалось получить курсы. Попробуйте позже.")
            return

        rate = rates[target]
        msg = (
            f"📊 *Курс {rate['name']}*\n\n"
            f"💵 1 {target} = {rate['value']} ₽\n"
            f"🔄 Данные от ЦБ РФ на {datetime.now().strftime('%d.%m.%Y')}"
        )
        await update.message.reply_text(msg, parse_mode='Markdown')

        # Увеличиваем счётчик
        increment_request(user_id)
        log_action(user_id, "currency_check", target)

    else:
        # Показать все доступные курсы
        if not can_request_currency(user_id):
            await update.message.reply_text("Лимит запросов исчерпан.")
            return

        rates = get_exchange_rates()
        if not rates:
            await update.message.reply_text("❌ Не удалось получить курсы. Попробуйте позже.")
            return

        msg = "📊 *Актуальные курсы валют (ЦБ РФ)*\n\n"
        for code, data in rates.items():
            msg += f"• {data['name']}: **{data['value']} ₽**\n"

        msg += f"\n🔄 Обновлено: {datetime.now().strftime('%d.%m.%Y в %H:%M')}\n"
        msg += "💡 Используй: `/currency usd` для конкретной валюты"

        await update.message.reply_text(msg, parse_mode='Markdown')

        # Увеличиваем счётчик
        increment_request(user_id)
        log_action(user_id, "currency_all", "USD,EUR,GBP,CNY")

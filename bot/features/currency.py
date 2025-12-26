# bot/features/currency.py

import httpx
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from loguru import logger

from database import get_db_pool

# Официальный API ЦБ РФ
CURRENCY_API = "https://www.cbr-xml-daily.ru/latest.js"

# Коды валют
CURRENCIES = {
    "USD": {"name": {"ru": "Доллар США", "en": "US Dollar"}, "symbol": "$"},
    "EUR": {"name": {"ru": "Евро", "en": "Euro"}, "symbol": "€"},
    "GBP": {"name": {"ru": "Фунт стерлингов", "en": "British Pound"}, "symbol": "£"},
    "CNY": {"name": {"ru": "Китайский юань", "en": "Chinese Yuan"}, "symbol": "¥"},
}

# Тексты
TEXTS = {
    "ru": {
        "title": "💱 Курсы валют на {date}:\n\n",
        "rate": "<b>{name}</b> ({code} {symbol}): {value} ₽\n",
        "error": "❌ Не удалось получить курсы. Повторите позже.",
    },
    "en": {
        "title": "💱 Exchange rates for {date}:\n\n",
        "rate": "<b>{name}</b> ({code} {symbol}): {value} RUB\n",
        "error": "❌ Failed to fetch rates. Try again later.",
    }
}


async def get_user_lang(pool, user_id: int) -> str:
    lang = await pool.fetchval("SELECT language FROM users WHERE id = $1", user_id)
    return lang or "ru"


async def cmd_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    pool = context.application.bot_data['db_pool']
    lang = await get_user_lang(pool, user.id)
    texts = TEXTS[lang]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CURRENCY_API, timeout=10.0)
        if response.status_code != 200:
            await update.message.reply_text(texts["error"])
            return

        data = response.json()
        rates = data["rates"]
        date = data["date"]

        message = texts["title"].format(date=date)

        # Формируем сообщение
        for code in ["USD", "EUR", "GBP", "CNY"]:
            if code in rates:
                value = round(rates[code], 2)
                currency_info = CURRENCIES[code]
                name = currency_info["name"][lang]
                symbol = currency_info["symbol"]
                message += texts["rate"].format(
                    name=name,
                    code=code,
                    symbol=symbol,
                    value=value
                )

        await update.message.reply_html(message)

    except Exception as e:
        logger.error(f"❌ Ошибка при получении курсов: {e}")
        await update.message.reply_text(texts["error"])


def setup_currency_handlers(app):
    app.add_handler(CommandHandler("currency", cmd_currency))
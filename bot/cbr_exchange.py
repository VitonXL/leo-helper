# bot/cbr_exchange.py
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
from bot.database import db

CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"

def fetch_cbr_rates():
    """Получает курсы от ЦБ РФ и кэширует их"""
    try:
        date_req = datetime.now().strftime("%d/%m/%Y")
        response = requests.get(CBR_URL, params={'date_req': date_req}, timeout=10)

        if response.status_code != 200:
            logging.error(f"❌ Ошибка API ЦБ: {response.status_code}")
            return None

        root = ET.fromstring(response.content)
        date = root.attrib['Date']

        usd_rate = None
        eur_rate = None

        for valute in root.findall('Valute'):
            charcode = valute.find('CharCode').text
            value = float(valute.find('Value').text.replace(',', '.'))
            nominal = int(valute.find('Nominal').text)
            rate = round(value / nominal, 2)

            if charcode == 'USD':
                usd_rate = rate
            elif charcode == 'EUR':
                eur_rate = rate

        if usd_rate and eur_rate:
            rates = {
                'USD_RUB': usd_rate,
                'EUR_RUB': eur_rate,
                'date': date,
                'timestamp': datetime.now().isoformat()
            }
            db.cache_rates(rates)
            logging.info(f"✅ Курсы ЦБ обновлены: USD={usd_rate}, EUR={eur_rate}")
            return rates
    except Exception as e:
        logging.error(f"❌ Ошибка получения курсов ЦБ: {e}")
    return None

def get_cached_cbr_rates():
    """Возвращает кэшированные курсы ЦБ РФ"""
    rates = db.get_cached_rates()
    if rates:
        return rates
    # Если кэша нет — возвращаем значения по умолчанию
    return {
        'USD_RUB': 92.50,
        'EUR_RUB': 100.20,
        'date': '01.01.2025'
    }

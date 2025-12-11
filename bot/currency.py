# bot/currency.py
import requests

def get_usd_rate():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        return round(r["rates"]["RUB"], 2)
    except:
        return "91.20"

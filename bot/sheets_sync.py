# bot/sheets_sync.py
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_google_sheet():
    try:
        creds_json = json.loads(os.getenv("GOOGLE_SHEETS_CREDENTIALS"))
        credentials = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        client = gspread.authorize(credentials)
        return client.open("Leo Aide — Данные").sheet1
    except Exception as e:
        logging.error(f"❌ Ошибка подключения к Google Sheets: {e}")
        return None

def log_subscription(user_id, name, renewal_date):
    sheet = get_google_sheet()
    if sheet:
        try:
            sheet.append_row([
                str(user_id), name, renewal_date, "Активна",
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])
        except Exception as e:
            logging.error(f"❌ Ошибка записи в таблицу: {e}")

def log_reminder(user_id, text, time):
    sheet = get_google_sheet()
    if sheet:
        try:
            sheet.append_row([
                str(user_id), f"Напоминание: {text}", time, "-",
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ])
        except Exception as e:
            logging.error(f"❌ Ошибка записи напоминания: {e}")

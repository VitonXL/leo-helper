# bot/utils/giga.py

import os
import requests
import json
from datetime import datetime, timedelta
from bot.database import log_action

# Получаем данные из переменных окружения
CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")
SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

# Токен будем хранить временно (в продакшене — в Redis или БД)
TOKEN_DATA = {}

def get_access_token():
    """Получает access token через OAuth"""
    global TOKEN_DATA

    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': 'unique_request_id_' + datetime.now().isoformat()
    }
    payload = {
        'scope': SCOPE
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=payload,
            auth=(CLIENT_ID, CLIENT_SECRET),
            verify=False  # ⚠️ Временно (проблема с SSL в некоторых сетях)
        )
        if response.status_code == 200:
            data = response.json()
            TOKEN_DATA = {
                'access_token': data['access_token'],
                'expires_at': datetime.now() + timedelta(seconds=data['expires_in'] - 60)
            }
            return TOKEN_DATA['access_token']
    except Exception as e:
        print(f"❌ Ошибка получения токена GigaChat: {e}")
    return None

def is_token_valid():
    """Проверяет, действителен ли токен"""
    if not TOKEN_DATA:
        return False
    return datetime.now() < TOKEN_DATA['expires_at']

def send_to_giga(prompt: str) -> str:
    """Отправляет запрос к GigaChat"""
    if not is_token_valid():
        token = get_access_token()
        if not token:
            return "❌ Не удалось подключиться к GigaChat. Попробуйте позже."
    else:
        token = TOKEN_DATA['access_token']

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "top_p": 0.9,
        "n": 1,
        "stream": False,
        "max_tokens": 1024
    }

    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        else:
            return f"❌ Ошибка: {response.status_code}, {response.text}"
    except Exception as e:
        return f"❌ Ошибка соединения: {str(e)}"

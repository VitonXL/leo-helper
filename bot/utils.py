import hashlib
import hmac
import os
import random
import string
from typing import Optional


def verify_webapp_data(token: str, data_check_string: str, hash: str) -> bool:
    """
    Проверяет подлинность данных из Telegram Web App.
    """
    secret_key = hashlib.sha256(token.encode()).digest()
    data_check_list = data_check_string.split("&")
    data_check_list.sort()
    data_check_sorted = "\n".join(data_check_list)
    computed_hash = hmac.new(secret_key, data_check_sorted.encode(), hashlib.sha256).hexdigest()
    return computed_hash == hash


def generate_cabinet_link(user_id: int) -> str:
    """
    Генерирует защищённую ссылку на кабинет с HMAC-подписью.
    Формат: ?user_id=123&hash=...
    """
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise ValueError("AUTH_SECRET не задан в переменных окружения")

    message = f"user_id={user_id}"
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"https://leo-aide.online/cabinet?user_id={user_id}&hash={signature}"


def generate_ticket_id(user_id: int) -> str:
    """
    Генерирует уникальный ID тикета.
    Формат: TICKET-XXXX-YY, где XXXX = последние 4 цифры user_id, YY = случайные цифры.
    """
    suffix = ''.join(random.choices(string.digits, k=2))
    return f"TICKET-{user_id % 10000:04d}-{suffix}"
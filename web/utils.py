# web/utils.py
# Утилиты для проверки подлинности пользователей

import hashlib
import hmac
import os
from typing import Optional


def verify_webapp_data(token: str, data_check_string: str, hash: str) -> bool:
    """
    Проверяет подлинность данных, переданных из Telegram Web App.
    
    :param token: BOT_TOKEN (секретный ключ бота)
    :param data_check_string: строка данных (user, auth_date и т.д.)
    :param hash: хеш из параметра
    :return: True, если данные подлинные
    """
    secret_key = hashlib.sha256(token.encode()).digest()
    data_check_list = data_check_string.split("&")
    data_check_list.sort()
    data_check_sorted = "\n".join(data_check_list)
    computed_hash = hmac.new(secret_key, data_check_sorted.encode(), hashlib.sha256).hexdigest()
    return computed_hash == hash


def verify_cabinet_link(user_id: int, hash: str) -> bool:
    """
    Проверяет подлинность ссылки на личный кабинет.
    Используется, когда пользователь переходит по ссылке из бота.
    
    :param user_id: ID пользователя из URL
    :param hash: Хеш из URL
    :return: True, если хеш верный
    """
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise ValueError("AUTH_SECRET не задан в переменных окружения")
    
    expected_hash = hashlib.md5(f"{user_id}{secret}".encode()).hexdigest()
    return hash.lower() == expected_hash.lower()

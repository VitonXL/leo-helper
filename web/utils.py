# web/utils.py
# Утилиты для проверки подлинности пользователей

import hashlib
import hmac
import os
from typing import Optional
from database import get_db_pool, get_user_role


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


async def verify_cabinet_link(user_id: int, hash: str, required_role: str = None) -> bool:
    """
    Проверяет подлинность ссылки на личный кабинет.
    При необходимости — проверяет, имеет ли пользователь нужную роль.
    
    Используется в /cabinet, /admin и других защищённых роутах.
    
    :param user_id: ID пользователя из URL
    :param hash: Хеш из URL
    :param required_role: Опциональная роль: 'admin', 'moderator' и т.д.
    :return: True, если хеш верный и роль (если указана) разрешена
    """
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise ValueError("AUTH_SECRET не задан в переменных окружения")
    
    expected_hash = hashlib.md5(f"{user_id}{secret}".encode()).hexdigest()
    if hash.lower() != expected_hash.lower():
        return False

    # Если роль не требуется — доступ разрешён
    if not required_role:
        return True

    # Проверяем роль пользователя
    pool = await get_db_pool()
    user_role = await get_user_role(pool, user_id)

    if required_role == "admin":
        return user_role == "admin"
    elif required_role == "moderator":
        return user_role in ["moderator", "admin"]
    else:
        return False
# bot/utils.py

import hashlib
import hmac
import os

def verify_webapp_data(token: str, data_check_string: str, hash: str) -> bool:
    """
    Проверяет подпись Web App.
    """
    secret_key = hashlib.sha256(token.encode()).digest()
    data_check_list = data_check_string.split("&")
    data_check_list.sort()
    data_check_sorted = "\n".join(data_check_list)
    computed_hash = hmac.new(secret_key, data_check_sorted.encode(), hashlib.sha256).hexdigest()
    return computed_hash == hash

def generate_cabinet_link(user_id: int) -> str:
    """
    Генерирует безопасную ссылку на личный кабинет
    """
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise ValueError("AUTH_SECRET не задан в переменных окружения")
        
def generate_cabinet_link(user_id: int) -> str:
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise ValueError("AUTH_SECRET not set")
    hash = hashlib.md5(f"{user_id}{secret}".encode()).hexdigest()
    return f"https://leo-aide.online/cabinet?user_id={user_id}&hash={hash}"
    
    hash = hashlib.md5(f"{user_id}{secret}".encode()).hexdigest()
    return f"https://leo-aide.online/cabinet?user_id={user_id}&hash={hash}"

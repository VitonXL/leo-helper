# web/utils.py
import hashlib
import hmac
import os
from typing import Optional
from database import get_db_pool, get_user_role

def verify_webapp_data(token: str, data_check_string: str, hash: str) -> bool:
    secret_key = hashlib.sha256(token.encode()).digest()
    data_check_list = data_check_string.split("&")
    data_check_list.sort()
    data_check_sorted = "\n".join(data_check_list)
    computed_hash = hmac.new(secret_key, data_check_sorted.encode(), hashlib.sha256).hexdigest()
    return computed_hash == hash

async def verify_cabinet_link(user_id: int, hash: str, role: str = None) -> bool:
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise ValueError("AUTH_SECRET не задан в переменных окружения")
    expected_hash = hashlib.md5(f"{user_id}{secret}".encode()).hexdigest()
    if hash.lower() != expected_hash.lower():
        return False
    if role:
        pool = await get_db_pool()
        user_role = await get_user_role(pool, user_id)
        if role == "admin" and user_role != "admin":
            return False
        if role == "moderator" and user_role not in ["moderator", "admin"]:
            return False
    return True
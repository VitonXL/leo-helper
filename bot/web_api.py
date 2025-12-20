# bot/web_api.py (пример)

from fastapi import FastAPI
import uvicorn
from bot.database import get_user_role, get_user_info, get_referral_stats

app = FastAPI()

@app.get("/api/user/{user_id}")
async def api_user_status(user_id: int):
    # Получаем роль
    role = await get_user_role(db_pool, user_id)
    return {
        "role": role,
        "is_premium": role == "premium",
        "premium_expires": None  # можно добавить
    }

@app.get("/api/user/info/{user_id}")
async def api_user_info(user_id: int):
    # Можно расширить
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT first_name, username, language_code FROM users WHERE id = $1", user_id)
        if row:
            return dict(row)
        return {"first_name": "Пользователь", "username": "unknown", "language_code": "ru"}

@app.get("/api/user/referrals/{user_id}")
async def api_referrals_count(user_id: int):
    count = await get_referral_stats(db_pool, user_id)
    return {"count": count}

# Запуск: uvicorn bot.web_api:app --host 0.0.0.0 --port $PORT

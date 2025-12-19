# web/api.py

from fastapi import APIRouter, HTTPException
import asyncpg
import os
from typing import Dict, Any

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL не задана")

print(f"✅ DATABASE_URL: {DATABASE_URL[:30]}...")

db_pool = None


async def get_db_pool():
    global db_pool
    if db_pool is None:
        print("🔧 Создаём пул подключений к БД...")
        try:
            db_pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=60)
            print("✅ Пул БД создан")
        except Exception as e:
            print(f"❌ Ошибка создания пула: {e}")
            raise
    return db_pool


async def get_user_data(user_id: int) -> Dict[str, Any]:
    print(f"🔍 Запрос данных для user_id = {user_id}")
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    id, first_name, username, language_code, 
                    role, premium_expires, theme
                FROM users 
                WHERE id = $1
            """, user_id)

            print(f"📄 Результат из БД: {row}")

            if not row:
                print("⚠️ Пользователь не найден в БД")
                return None

            referrals = await conn.fetchval("""
                SELECT COUNT(*) FROM referrals WHERE referrer_id = $1
            """, user_id)
            print(f"👥 Рефералов: {referrals}")

            return {
                "id": row["id"],
                "first_name": row["first_name"] or "Пользователь",
                "username": row["username"] or "unknown",
                "language": row["language_code"] or "ru",
                "role": row["role"] or "user",
                "premium_expires": row["premium_expires"].isoformat() if row["premium_expires"] else None,
                "is_premium": row["role"] == "premium",
                "referrals": referrals or 0,
                "theme": row["theme"] or "light"
            }
    except Exception as e:
        print(f"❌ Ошибка в get_user_data: {e}")
        return None


@router.get("/user/{user_id}")
async def get_user_status(user_id: int):
    print(f"🌐 API: Получен запрос /api/user/{user_id}")
    try:
        user_data = await get_user_data(user_id)
        if not user_data:
            print("🔻 Возвращаем заглушку (пользователь не найден)")
            return {
                "role": "user",
                "is_premium": False,
                "premium_expires": None,
                "first_name": "Пользователь",
                "username": "unknown",
                "language": "ru",
                "theme": "light",
                "referrals": 0
            }
        print(f"🟢 Успешно: возвращаем данные {user_data['first_name']} (@{user_data['username']})")
        return user_data
    except Exception as e:
        print(f"💥 Ошибка в /api/user/{user_id}: {e}")
        return {
            "role": "user",
            "is_premium": False,
            "premium_expires": None,
            "first_name": "Пользователь",
            "username": "unknown",
            "language": "ru",
            "theme": "light",
            "referrals": 0
        }


# === 🌙 НОВЫЙ ЭНДПОИНТ: обновление темы ===
@router.post("/set-theme")
async def set_user_theme(user_id: int, theme: str, hash: str):
    """
    API для смены темы пользователя. Вызывается с фронтенда.
    """
    if theme not in ["light", "dark"]:
        raise HTTPException(status_code=400, detail="Theme must be 'light' or 'dark'")
    
    from .utils import verify_cabinet_link
    if not verify_cabinet_link(user_id, hash):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET theme = $1 WHERE id = $2", theme, user_id)
        return {"status": "success", "theme": theme}
    except Exception as e:
        print(f"❌ Ошибка обновления темы: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

@router.get("/admin/stats")
async def get_admin_stats():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM users")
        premium = await conn.fetchval("SELECT COUNT(*) FROM users WHERE role = 'premium'")
        active = await conn.fetchval("SELECT COUNT(*) FROM user_activity WHERE activity_date = CURRENT_DATE")

    return {
        "total_users": total,
        "premium_users": premium,
        "active_today": active
    }
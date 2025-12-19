# web/api.py

from fastapi import APIRouter, HTTPException, Body
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


# === 🌙 ЭНДПОИНТ: обновление темы ===
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


# === 🔐 АДМИН-ПАНЕЛЬ ===

@router.get("/admin/stats")
async def get_admin_stats():
    """
    Общая статистика: пользователи, премиум, активность.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM users")
        premium = await conn.fetchval("SELECT COUNT(*) FROM users WHERE role = 'premium'")
        active_today = await conn.fetchval("""
            SELECT COUNT(*) FROM usage_stats 
            WHERE timestamp >= CURRENT_DATE
        """)
        referrals_count = await conn.fetchval("SELECT COUNT(*) FROM referrals")

    return {
        "total_users": total or 0,
        "premium_users": premium or 0,
        "active_today": active_today or 0,
        "referrals_count": referrals_count or 0
    }


@router.get("/admin/users")
async def get_all_users():
    """
    Возвращает список всех пользователей (ограничение: 100 последних).
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id, first_name, username, role, language_code as language, 
                premium_expires, last_seen
            FROM users
            ORDER BY last_seen DESC
            LIMIT 100
        """)
    return [dict(row) for row in rows]


@router.get("/admin/user")
async def get_single_user(query: str):
    """
    Поиск пользователя по ID или username.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if query.startswith('@'):
            user = await conn.fetchrow("SELECT * FROM users WHERE username = $1", query[1:])
        else:
            try:
                user_id = int(query)
                user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
            except ValueError:
                return None
    return dict(user) if user else None


@router.post("/admin/grant-premium")
async def api_grant_premium(user_id: int):
    """
    Выдаёт пользователю премиум-доступ на 30 дней.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE users 
            SET role = 'premium', 
                premium_expires = NOW() + INTERVAL '30 days'
            WHERE id = $1
        """, user_id)
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="User not found")

    return {"status": "success", "message": f"Премиум выдан пользователю {user_id}"}


@router.get("/admin/activity-by-day")
async def get_activity_by_day():
    """
    Активность по дням за последние 30 дней.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                DATE(timestamp) as day,
                COUNT(*) as count
            FROM usage_stats
            WHERE timestamp > NOW() - INTERVAL '30 days'
            GROUP BY day
            ORDER BY day
        """)
    return {
        "dates": [r["day"].isoformat() for r in rows],
        "counts": [r["count"] for r in rows]
    }


@router.get("/admin/top-commands")
async def get_top_commands():
    """
    Топ-10 команд по использованию.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT command, COUNT(*) as count
            FROM usage_stats
            GROUP BY command
            ORDER BY count DESC
            LIMIT 10
        """)
    return {
        "commands": [r["command"] for r in rows],
        "counts": [r["count"] for r in rows]
    }

@router.get("/admin/reviews")
async def get_reviews():
    """
    Возвращает неподтверждённые или все отзывы для модерации.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                r.id, r.text, r.rating, r.created_at,
                u.id as user_id, u.first_name, u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            WHERE r.is_approved = false
            ORDER BY r.created_at DESC
            LIMIT 50
        """)
    return [dict(r) for r in rows]

# === ЭНДПОИНТ: снятие премиум ===
@router.post("/admin/revoke-premium")
async def api_revoke_premium(user_id: int = Body(..., embed=True)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users 
            SET premium_expires = NULL,
                role = CASE WHEN role = 'admin' THEN 'admin' ELSE 'user' END
            WHERE id = $1
        """, user_id)
    return {"status": "success", "message": f"Премиум снят с {user_id}"}

# === ЭНДПОИНТ: модерация отзывов (заглушка) ===
@router.get("/admin/reviews")
async def get_reviews():
    return [
        {"id": 1, "text": "Отличный бот!", "rating": 5, "created_at": "2025-04-05T12:30:00", "user_id": 123, "first_name": "Анна", "username": "anna"},
        {"id": 2, "text": "Работает, но медленно", "rating": 3, "created_at": "2025-04-04T09:15:00", "user_id": 456, "first_name": "Дима", "username": "dimon"}
    ]

# === ЭНДПОИНТ: техподдержка (заглушка) ===
@router.get("/admin/support-tickets")
async def get_support_tickets():
    return [
        {"id": 1, "user_id": 123, "username": "anna", "subject": "Ошибка", "message": "Не работает кнопка", "status": "open", "created_at": "2025-04-05T10:00:00"},
        {"id": 2, "user_id": 789, "username": "max", "subject": "Предложение", "message": "Добавьте календарь", "status": "open", "created_at": "2025-04-04T16:20:00"}
    ]
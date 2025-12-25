# web/api.py

import sys
import os
from typing import Dict, Any

# Добавляем путь к папке bot
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # Добавляем корень: /app

from fastapi import APIRouter, HTTPException, Body, Query, Depends
from loguru import logger
from database import (
    get_db_pool,
    ensure_support_table_exists,
)
from bot.instance import bot as global_bot  # Импортируем переменную bot

import asyncpg
from telegram.ext import Application

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL не задана")

print(f"✅ DATABASE_URL: {DATABASE_URL[:30]}...")

# --- Импорт утилит ---
from .utils import verify_cabinet_link  # ✅ Используем проверку из utils


# === Зависимости: проверка ролей ===
async def require_admin(user_id: int = Query(...), hash: str = Query(...)):
    """
    Доступ только для админов.
    """
    if not await verify_cabinet_link(user_id, hash, required_role="admin"):
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return user_id


async def require_moderator(user_id: int = Query(...), hash: str = Query(...)):
    """
    Доступ для модераторов и админов.
    """
    if not await verify_cabinet_link(user_id, hash, required_role="moderator"):
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return user_id


# === 🔍 Получение данных пользователя ===
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
        logger.error(f"❌ Ошибка в get_user_data: {e}")
        return None


# === 🌐 API: Получение статуса пользователя ===
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
        logger.error(f"💥 Ошибка в /api/user/{user_id}: {e}")
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


# === 🌙 Изменение темы ===
@router.post("/set-theme")
async def set_user_theme(user_id: int, theme: str = Body(...), hash: str = Body(...)):
    if theme not in ["light", "dark"]:
        raise HTTPException(status_code=400, detail="Theme must be 'light' or 'dark'")

    try:
        if not await verify_cabinet_link(user_id, hash):
            raise HTTPException(status_code=403, detail="Invalid signature")
    except ImportError:
        logger.error("❌ Не удалось импортировать .utils.verify_cabinet_link")
        raise HTTPException(status_code=500, detail="Сервис проверки хеша недоступен")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET theme = $1 WHERE id = $2", theme, user_id)
        return {"status": "success", "theme": theme}
    except Exception as e:
        logger.error(f"❌ Ошибка обновления темы: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


# === 🔐 АДМИН-ПАНЕЛЬ: Статистика ===
@router.get("/admin/stats")
async def get_admin_stats(user_id: int = Depends(require_admin)):
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
async def get_all_users(user_id: int = Depends(require_admin)):
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
async def get_single_user(query: str, user_id: int = Depends(require_admin)):
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


# === Премиум ===
@router.post("/admin/grant-premium")
async def api_grant_premium(user_id: int = Body(..., embed=True), admin_id: int = Depends(require_admin)):
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


@router.post("/admin/revoke-premium")
async def api_revoke_premium(user_id: int = Body(..., embed=True), admin_id: int = Depends(require_admin)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users 
            SET premium_expires = NULL,
                role = CASE WHEN role = 'admin' THEN 'admin' ELSE 'user' END
            WHERE id = $1
        """, user_id)
    return {"status": "success", "message": f"Премиум снят с {user_id}"}


# === Активность ===
@router.get("/admin/activity-by-day")
async def get_activity_by_day(user_id: int = Depends(require_admin)):
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
async def get_top_commands(user_id: int = Depends(require_admin)):
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


# === Отзывы ===
@router.get("/admin/reviews")
async def get_reviews(user_id: int = Depends(require_admin)):
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


# === 🛠 ТЕХПОДДЕРЖКА: Тикеты ===
@router.get("/admin/support-tickets")
async def get_support_tickets(user_id: int = Depends(require_moderator)):
    """
    Возвращает все открытые и в работе тикеты.
    Доступ: модераторы и админы.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, user_id, username, first_name, message, status, created_at, ticket_id
            FROM support_tickets
            WHERE status IN ('open', 'in_progress')
            ORDER BY created_at DESC
        """)
        return [
            {
                "id": r["id"],
                "ticket_id": r["ticket_id"],
                "user_id": r["user_id"],
                "username": r["username"] or "unknown",
                "first_name": r["first_name"] or "Пользователь",
                "message": r["message"],
                "status": r["status"],
                "created_at": r["created_at"].isoformat()
            }
            for r in rows
        ]


@router.post("/admin/reply-support")
async def reply_support(
    ticket_id: str = Body(..., embed=True),  # Теперь str
    reply_text: str = Body(..., embed=True),
    user_id: int = Depends(require_moderator)  # Проверка роли
):
    """
    Отправляет ответ пользователю и закрывает тикет.
    Использует ticket_id (строка), а не id.
    """
    pool = await get_db_pool()

    # Получаем данные тикета
    async with pool.acquire() as conn:
        ticket = await conn.fetchrow(
            "SELECT user_id, message FROM support_tickets WHERE ticket_id = $1", ticket_id
        )
        if not ticket:
            raise HTTPException(status_code=404, detail="Тикет не найден")

      # Пытаемся получить бот из bot.instance
    bot = None
    try:
        from bot.instance import bot as global_bot
        if global_bot is not None:
            bot = global_bot
            logger.info("✅ Бот получен из bot.instance")
    except ImportError:
        logger.warning("⚠️ Модуль bot.instance не найден — будем использовать временный бот")
    except Exception as e:
        logger.error(f"❌ Ошибка импорта bot.instance: {e}")

    # Если бот не из instance — создаём временный
    if bot is None:
        token = os.getenv("BOT_TOKEN")
        if not token:
            logger.error("❌ BOT_TOKEN не задан в переменных окружения")
            raise HTTPException(status_code=500, detail="BOT_TOKEN не задан")

        try:
            from telegram.ext import Application
            application = Application.builder().token(token).build()
            bot = application.bot
            await bot.initialize()  # ← ВАЖНО: инициализация
            logger.info("🤖 Временный бот инициализирован для ответа")
        except Exception as e:
            logger.error(f"❌ Не удалось создать временного бота: {e}")
            raise HTTPException(status_code=500, detail="Не удалось инициализировать бота")

    # Отправляем ответ
    try:
        await bot.send_message(
            ticket["user_id"],
            f"📬 Ответ от поддержки:\n\n{reply_text}\n\nСпасибо за обращение! ✅"
        )
        logger.info(f"✅ Ответ отправлен пользователю {ticket['user_id']} (тикет {ticket_id})")
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"❌ Ошибка отправки: {e}")

        # Обновляем статус тикета
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE support_tickets SET status = 'in_progress', updated_at = NOW() WHERE ticket_id = $1",
                ticket_id
            )

        if "blocked" in error_msg or "not found" in error_msg or "chat not found" in error_msg:
            raise HTTPException(status_code=500, detail="❌ Пользователь заблокировал бота")
        else:
            raise HTTPException(status_code=500, detail=f"❌ Ошибка отправки: {str(e)}")

    # Закрываем тикет
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE support_tickets SET status = 'resolved', updated_at = NOW() WHERE ticket_id = $1",
            ticket_id
        )
    logger.info(f"✅ Тикет {ticket_id} успешно закрыт")

    return {"status": "ok", "message": "Ответ отправлен, тикет закрыт"}


@router.get("/admin/reply-templates")
async def get_reply_templates(user_id: int = Depends(require_moderator)):
    return {
        "templates": [
            {"id": "thanks", "title": "Спасибо", "text": "Спасибо за обращение! ✅"},
            {"id": "fixed", "title": "Исправлено", "text": "Ошибка исправлена в последней версии. Обновите страницу."},
            {"id": "check", "title": "Проверьте", "text": "Убедитесь, что вы вошли в аккаунт и обновили страницу."},
            {"id": "info", "title": "Информация", "text": "Подробная инструкция: https://leo-aide.online/faq"},
            {"id": "delay", "title": "Обработка", "text": "Мы получили ваше обращение и уже работаем над ним."}
        ]
    }
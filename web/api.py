# web/api.py

from fastapi import APIRouter, HTTPException
import httpx
import os

router = APIRouter()

# URL бота
BOT_API_URL = os.getenv("BOT_API_URL", "https://mmuzs4kv.up.railway.app")


@router.get("/user/{user_id}")
async def get_user_status(user_id: int):
    """
    Возвращает данные пользователя.
    Использует только /api/user/{id} из бота.
    Имя и юзернейм — заглушка (пока не реализован WebApp).
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Основные данные: роль, подписка
            url = f"{BOT_API_URL.strip('/')}/api/user/{user_id}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
            else:
                data = {}

            # Возвращаем все поля, которые ждёт cabinet.html
            return {
                "role": data.get("role", "user"),
                "premium_expires": data.get("premium_expires"),
                "is_premium": data.get("role") == "premium",
                "first_name": "Пользователь",          # Пока заглушка
                "username": "unknown",                 # Бот не возвращает
                "language": "ru",                      # Можно из БД, но нет API
                "theme": "light",                      # Пока фикс
                "referrals": 0                         # Нет API для статистики
            }

        except httpx.ConnectError:
            return fallback_response()
        except httpx.TimeoutException:
            return fallback_response()
        except Exception:
            return fallback_response()


def fallback_response():
    """Заглушка при ошибках"""
    return {
        "role": "user",
        "premium_expires": None,
        "is_premium": False,
        "first_name": "Пользователь",
        "username": "unknown",
        "language": "ru",
        "theme": "light",
        "referrals": 0
    }

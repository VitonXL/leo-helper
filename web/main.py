import sys
import os
import yaml
import json
from datetime import datetime
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException
from starlette.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi import APIRouter
from loguru import logger

# Добавляем путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"🚀 ENV PORT: {os.getenv('PORT')}")
print(f"🚀 ARGS: {' '.join(sys.argv)}")
print("🔍 sys.path обновлён для импортов")

app = FastAPI(title="Лео Помощник — UI")

# --- Создаём папки ---
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

USERS_YML = "users.yml"
USAGE_JSON = os.path.join(DATA_DIR, "usage.json")

if not os.path.exists(USAGE_JSON):
    with open(USAGE_JSON, "w", encoding="utf-8") as f:
        json.dump({"gigachat": {"total": 0, "limit": 100, "users": {}}, "last_reset": str(datetime.now())}, f)

# --- Загрузка данных ---
def load_usage():
    if os.path.exists(USAGE_JSON):
        with open(USAGE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"gigachat": {"total": 0, "limit": 100, "users": {}}, "last_reset": str(datetime.now())}

def save_usage(data):
    with open(USAGE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Админ API ---
admin_api = APIRouter(prefix="/api/admin", tags=["admin"])

@admin_api.get("/stats")
async def get_admin_stats():
    usage = load_usage()
    total_users = len(usage["gigachat"]["users"])
    active_today = sum(1 for count in usage["gigachat"]["users"].values() if count > 0)
    premium = sum(1 for count in usage["gigachat"]["users"].values() if count > 5)
    return {
        "total_users": total_users,
        "active_today": active_today,
        "premium_users": premium,
        "new_last_week": 7,
        "top_features": [
            {"feature": "GigaChat", "requests": 1200, "growth": "+12%"},
            {"feature": "Финансы", "requests": 843, "growth": "+7%"},
            {"feature": "Погода", "requests": 621, "growth": "+3%"},
            {"feature": "Игры", "requests": 304, "growth": "-2%"},
        ]
    }

@admin_api.get("/api-usage")
async def get_api_usage():
    usage = load_usage()
    gigachat = usage["gigachat"]
    top_users = sorted(gigachat["users"].items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "gigachat": {
            "used": gigachat["total"],
            "limit": gigachat["limit"],
            "remaining": max(0, gigachat["limit"] - gigachat["total"]),
            "is_over": gigachat["total"] >= gigachat["limit"],
            "top_users": [{"user_id": uid, "requests": count} for uid, count in top_users]
        }
    }

@admin_api.post("/patch-users")
async def patch_users_from_yml():
    if not os.path.exists(USERS_YML):
        raise HTTPException(status_code=404, detail="Файл users.yml не найден")
    try:
        with open(USERS_YML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        usage = load_usage()
        for item in data:
            user_id = str(item.get("id"))
            if user_id not in usage["gigachat"]["users"]:
                usage["gigachat"]["users"][user_id] = 0
        save_usage(usage)
        return {"status": "success", "message": "Пользователи обновлены", "count": len(data)}
    except Exception as e:
        logger.error(f"Ошибка при обработке users.yml: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при чтении файла")

@admin_api.post("/reset-usage")
async def reset_usage_counters():
    usage = load_usage()
    usage["gigachat"]["total"] = 0
    usage["gigachat"]["users"] = {uid: 0 for uid in usage["gigachat"]["users"]}
    usage["last_reset"] = str(datetime.now())
    save_usage(usage)
    logger.info("Счётчики GigaChat сброшены администратором")
    return {"status": "success", "message": "Счётчики GigaChat сброшены"}

@admin_api.post("/overuse")
async def toggle_overuse():
    logger.info("Режим перегрузки GigaChat активирован")
    return {"status": "success", "message": "Режим перегрузки включён"}

# ✅ Исправлено: Путь к статике теперь относительный
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
print(f"✅ Статика доступна из: {static_dir}")

# --- Роуты ---
app.include_router(admin_api)

# ✅ Подключаем основные роуты
from .routes import router as web_router
app.include_router(web_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    logger.info("🟢 Веб-сервер запущен")
    logger.info("✨ Доступные роуты: /, /cabinet, /finance, /admin, /api/admin/stats")
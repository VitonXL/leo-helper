import sys
import os
import yaml
import json
from datetime import datetime
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Request, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

# Добавляем путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"🚀 ENV PORT: {os.getenv('PORT', '8080')}")
print(f"🚀 ARGS: {' '.join(sys.argv)}")
print("🔍 sys.path обновлён для импортов")

app = FastAPI(title="Лео Помощник — UI")

# --- Папки ---
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_YML = "users.yml"
USAGE_JSON = os.path.join(DATA_DIR, "usage.json")

if not os.path.exists(USAGE_JSON):
    with open(USAGE_JSON, "w", encoding="utf-8") as f:
        json.dump({"gigachat": {"total": 0, "limit": 100, "users": {}}, "last_reset": str(datetime.now())}, f, ensure_ascii=False, indent=2)

# --- Загрузка данных ---
def load_usage():
    if os.path.exists(USAGE_JSON):
        with open(USAGE_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"gigachat": {"total": 0, "limit": 100, "users": {}}, "last_reset": str(datetime.now())}

def save_usage(data):
    with open(USAGE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users_yml():
    if not os.path.exists(USERS_YML):
        return []
    with open(USERS_YML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []

def save_users_yml(users):
    with open(USERS_YML, "w", encoding="utf-8") as f:
        yaml.dump(users, f, ensure_ascii=False, default_flow_style=False)

# --- Админ API ---
admin_api = APIRouter(prefix="/api/admin", tags=["admin"])

# Статистика
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
        ],
        "api_usage": usage["gigachat"]
    }

# Использование API
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

# Обновить лимит API
@admin_api.post("/update-api-limit")
async def update_api_limit(data: dict):
    new_limit = data.get("limit", 100)
    if new_limit < 1:
        raise HTTPException(status_code=400, detail="Лимит должен быть > 0")
    usage = load_usage()
    usage["gigachat"]["limit"] = new_limit
    save_usage(usage)
    logger.info(f"Лимит GigaChat обновлён: {new_limit}")
    return {"status": "ok", "limit": new_limit}

# Поиск пользователя
@admin_api.get("/user")
async def get_user(query: str):
    users = load_users_yml()
    for u in users:
        if str(query) in str(u.get("id")) or query.lower() in u.get("username", "").lower():
            return u
    return None

# Выдать премиум
@admin_api.post("/grant-premium")
async def grant_premium(data: dict):
    user_id = str(data.get("user_id"))
    users = load_users_yml()
    for u in users:
        if str(u.get("id")) == user_id:
            u["premium"] = True
            u["premium_expires"] = (datetime.now().timestamp() + 30 * 86400)
            save_users_yml(users)
            logger.info(f"Премиум выдан: {user_id}")
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Пользователь не найден")

# Снять премиум
@admin_api.post("/revoke-premium")
async def revoke_premium(data: dict):
    user_id = str(data.get("user_id"))
    users = load_users_yml()
    for u in users:
        if str(u.get("id")) == user_id:
            u.pop("premium", None)
            u.pop("premium_expires", None)
            save_users_yml(users)
            logger.info(f"Премиум снят: {user_id}")
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Пользователь не найден")

# Заблокировать
@admin_api.post("/block-user")
async def block_user(data: dict):
    user_id = str(data.get("user_id"))
    users = load_users_yml()
    for u in users:
        if str(u.get("id")) == user_id:
            u["blocked"] = True
            save_users_yml(users)
            logger.info(f"Пользователь заблокирован: {user_id}")
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Пользователь не найден")

# Сброс статистики пользователя
@admin_api.post("/reset-user")
async def reset_user(data: dict):
    user_id = str(data.get("user_id"))
    usage = load_usage()
    if user_id in usage["gigachat"]["users"]:
        usage["gigachat"]["users"][user_id] = 0
        usage["gigachat"]["total"] = sum(usage["gigachat"]["users"].values())
        save_usage(usage)
        logger.info(f"Статистика сброшена: {user_id}")
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Пользователь не найден")

# Обновить users.yml из админки
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
        logger.info(f"users.yml загружен: {len(data)} пользователей")
        return {"status": "success", "message": "Пользователи обновлены", "count": len(data)}
    except Exception as e:
        logger.error(f"Ошибка при обработке users.yml: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при чтении файла")

# Сброс всех счётчиков
@admin_api.post("/reset-usage")
async def reset_usage_counters():
    usage = load_usage()
    usage["gigachat"]["total"] = 0
    usage["gigachat"]["users"] = {uid: 0 for uid in usage["gigachat"]["users"]}
    usage["last_reset"] = str(datetime.now())
    save_usage(usage)
    logger.info("Счётчики GigaChat сброшены администратором")
    return {"status": "success", "message": "Счётчики GigaChat сброшены"}

# Режим перегрузки
@admin_api.post("/overuse")
async def toggle_overuse():
    logger.info("Режим перегрузки GigaChat активирован")
    return {"status": "success", "message": "Режим перегрузки включён"}

# --- Статика и шаблоны ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
print(f"✅ Статика доступна из: {static_dir}")

# --- Jinja2 для HTML-шаблонов ---
templates = Jinja2Templates(directory=templates_dir)

# --- Маршрут для админки ---
ADMIN_ID = 1799560429

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if int(request.query_params.get("user_id", 0)) != ADMIN_ID:
        return HTMLResponse("❌ Доступ запрещён", status_code=403)

    usage = load_usage()
    users = load_users_yml()
    support_requests = [
        {"user_id": 1799560429, "message": "Не работает GigaChat", "status": "new"},
        {"user_id": 123456, "message": "Ошибка оплаты", "status": "processing"}
    ]

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "page_title": "Админ-панель",
            "stats": await get_admin_stats(),
            "api_usage": await get_api_usage(),
            "user_list": [
                {
                    "id": u.get("id"),
                    "first_name": u.get("first_name", "Пользователь"),
                    "username": u.get("username", ""),
                    "role": "admin" if u.get("id") == ADMIN_ID else "premium" if u.get("premium") else "user",
                    "language": u.get("language", "ru"),
                    "premium_expires": u.get("premium_expires"),
                    "last_seen": u.get("last_seen", datetime.now().isoformat())
                }
                for u in users
            ],
            "support_requests": support_requests
        }
    )

# --- Подключаем остальные роуты ---
app.include_router(admin_api)

try:
    from .routes import router as web_router
    app.include_router(web_router)
except Exception as e:
    logger.error(f"Ошибка импорта routes: {e}")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(static_dir, "favicon.ico"))

@app.on_event("startup")
async def startup_event():
    logger.info("🟢 Веб-сервер запущен")
    logger.info("✨ Доступные роуты: /, /cabinet, /finance, /admin, /api/admin/stats")
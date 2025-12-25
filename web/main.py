import sys
import os
import yaml
import json
from datetime import datetime
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter
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

# --- Статика и шаблоны ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
print(f"✅ Статика доступна из: {static_dir}")

# --- Jinja2 для HTML-шаблонов ---
templates = Jinja2Templates(directory=templates_dir)

# --- Маршрут для админки ---
ADMIN_ID = 1799560429  # ← Твой ID

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if int(request.query_params.get("user_id", 0)) != 1799560429:
        return HTMLResponse("❌ Доступ запрещён", status_code=403)

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "page_title": "Админка",
            "stats": {"total_users": 128, "active_today": 89, "premium_users": 24, "new_last_week": 17, "top_features": [{"feature": "GigaChat", "requests": 1200}, {"feature": "Финансы", "requests": 843}]},
            "api_usage": {"gigachat": {"used": 45, "limit": 100, "remaining": 55}},
            "user_list": [
                {"id": 1, "username": "vitron", "role": "admin", "is_premium": True},
                {"id": 2, "username": "user_123", "role": "user", "is_premium": False}
            ],
            "support_requests": [
                {"user_id": 1799560429, "message": "Не работает GigaChat", "status": "new"},
                {"user_id": 123456, "message": "Ошибка оплаты", "status": "processing"}
            ]
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
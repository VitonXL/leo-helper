from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import urllib.parse
import os
from .utils import verify_webapp_data, verify_cabinet_link
from .api import get_user_data
from database import get_db_pool, get_user_stats, get_referral_stats

# ✅ Исправлено: Путь к шаблонам теперь правильно указывает на web/templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

router = APIRouter()

# Для отладки — можно временно оставить
print(f"✅ Шаблоны загружаются из: {templates.env.loader.searchpath}")

# === ✅ ОБНОВЛЁННЫЙ МАРШРУТ / ===
@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user_id = request.query_params.get("user_id")
    hash_param = request.query_params.get("hash")

    # Попробуем загрузить пользователя, если есть user_id и hash
    if user_id and hash_param:
        try:
            user_id = int(user_id)
            if verify_cabinet_link(user_id, hash_param):
                user_data = await get_user_data(user_id)
                if user_data:
                    theme = request.cookies.get("theme", user_data.get("theme", "light"))
                    return templates.TemplateResponse(
                        "index.html",
                        {"request": request, "user": user_data, "theme": theme}
                    )
            # Если hash не прошёл проверку — игнорируем и показываем гостевую версию
        except (ValueError, Exception):
            pass  # Считаем гостем

    # ⚠️ Гостевой режим — минимальный user
    user_data = {
        "id": None,
        "first_name": "Гость",
        "avatar_url": "/static/img/avatar-placeholder.png",
        "role": "guest",
        "is_premium": False,
        "theme": "light",
        "hash": ""
    }
    theme = request.cookies.get("theme", "light")

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": user_data, "theme": theme}
    )

# Остальные маршруты — без изменений
@router.get("/premium", response_class=HTMLResponse)
async def premium_page(request: Request):
    user_id = request.query_params.get("user_id", "123456")
    user_data = {
        "id": user_id,
        "avatar_url": f"https://ui-avatars.com/api/?name={user_id}&background=4CAF50&color=fff",
        "theme": request.cookies.get("theme", "light")
    }
    return templates.TemplateResponse(
        "premium.html",
        {"request": request, "user": user_data}
    )

@router.post("/webapp", response_class=HTMLResponse)
async def handle_webapp(
    request: Request,
    user: str = Form(...),
    hash: str = Form(...)
):
    parsed_user = urllib.parse.parse_qs(user)
    data_check_string = "&".join([f"{k}={v[0]}" for k, v in parsed_user.items()])

    if not verify_webapp_data(os.getenv("BOT_TOKEN"), data_check_string, hash):
        return HTMLResponse("❌ Подпись неверна!", status_code=401)

    user_data = eval(parsed_user["user"][0])
    theme_str = parsed_user.get("theme_params", ["{}"])[0]
    try:
        theme_params = eval(theme_str)
    except:
        theme_params = {}

    theme = "dark" if theme_params.get("bg_color", "#ffffff").lower() in ["#000000", "#1a1a1a"] else "light"

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user_data,
            "theme": theme,
            "is_premium": False,
            "premium_expires": None
        }
    )

@router.get("/cabinet", response_class=HTMLResponse)
async def cabinet(request: Request):
    user_id = request.query_params.get("user_id")
    hash_param = request.query_params.get("hash")

    if not user_id or not hash_param:
        raise HTTPException(status_code=400, detail="Missing user_id or hash")

    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    if not verify_cabinet_link(user_id, hash_param):
        raise HTTPException(status_code=403, detail="Invalid signature")

    user_data = await get_user_data(user_id)
    if not user_data:
        user_data = {
            "id": user_id,
            "first_name": "Пользователь",
            "username": "unknown",
            "role": "user",
            "premium_expires": None,
            "is_premium": False,
            "language": "ru",
            "theme": "light"
        }

    pool = await get_db_pool()
    stats = await get_user_stats(pool, user_id)
    referrals_count = await get_referral_stats(pool, user_id)
    user_data["referrals"] = referrals_count

    theme = request.cookies.get("theme", user_data.get("theme", "light"))

    return templates.TemplateResponse(
        "cabinet.html",
        {
            "request": request,
            "user": user_data,
            "stats": stats,
            "news_list": [
                {"date": "21.12", "text": "Добавлен <b>AI-помощник</b> 🧠 — попробуйте в разделе 'Быстрые действия'"},
                {"date": "20.12", "text": "Обновлён дизайн кабинета — стал ещё удобнее! ✨"},
            ],
            "title": "Личный кабинет",
            "theme": theme
        }
    )

@router.get("/finance", response_class=HTMLResponse)
async def finance_page(request: Request):
    user_id = request.query_params.get("user_id")
    hash_param = request.query_params.get("hash")

    if not user_id or not hash_param:
        raise HTTPException(status_code=400, detail="Missing user_id or hash")

    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    if not verify_cabinet_link(user_id, hash_param):
        raise HTTPException(status_code=403, detail="Invalid signature")

    user_data = await get_user_data(user_id)
    if not user_data:
        user_data = {
            "id": user_id,
            "first_name": "Пользователь",
            "username": "unknown",
            "referrals": 0,
            "is_premium": False,
            "theme": "light"
        }

    theme = request.cookies.get("theme", user_data.get("theme", "light"))

    return templates.TemplateResponse(
        "finance.html",
        {
            "request": request,
            "user": user_data,
            "title": "Финансы",
            "theme": theme
        }
    )

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    user_id = request.query_params.get("user_id")
    hash_param = request.query_params.get("hash")

    if not user_id or not hash_param:
        raise HTTPException(status_code=400, detail="Missing user_id or hash")

    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    if not verify_cabinet_link(user_id, hash_param):
        raise HTTPException(status_code=403, detail="Invalid signature")

    user_data = await get_user_data(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admins only.")

    theme = request.cookies.get("theme", user_data.get("theme", "light"))

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": user_data,
            "title": "Админ-панель",
            "theme": theme
        }
    )
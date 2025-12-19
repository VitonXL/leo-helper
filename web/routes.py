from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import urllib.parse
import os
from .utils import verify_webapp_data, verify_cabinet_link
from .api import get_user_data

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    theme = request.cookies.get("theme", "light")
    return templates.TemplateResponse("index.html", {"request": request, "theme": theme})


@router.get("/premium", response_class=HTMLResponse)
async def premium_page(request: Request):
    user_id = request.query_params.get("user_id", "123456")
    return templates.TemplateResponse(
        "premium.html",
        {"request": request, "user": {"id": user_id}}
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
    theme = parsed_user.get("theme_params", ["{}"])[0]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user_data,
            "theme": "dark" if theme.get("bg_color", "#ffffff").lower() in ["#000000", "#1a1a1a"] else "light",
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
            "theme": "light",
            "referrals": 0
        }

    theme = request.cookies.get("theme", user_data.get("theme", "light"))

    return templates.TemplateResponse(
        "cabinet.html",
        {
            "request": request,
            "user": user_data,
            "title": "Личный кабинет",
            "theme": theme
        }
    )


# ✅ НОВЫЙ РОУТ: /finance
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
# web/routes.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import urllib.parse
import os

from .utils import verify_webapp_data

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    theme = request.cookies.get("theme", "light")
    return templates.TemplateResponse("index.html", {"request": request, "theme": theme})

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
            "theme": "dark" if theme.get("bg_color", "#ffffff").lower() in ["#000000", "#1a1a1a"] else "light"
        }
    )

# web/routes.py

from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/", response_class=HTMLResponse)
async def ui_home(request: Request):
    # Определяем тему: из куки или по умолчанию
    theme = request.cookies.get("theme", "light")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "theme": theme}
    )


@router.get("/toggle-theme")
async def toggle_theme(response: Response):
    # Переключаем тему
    theme = "dark" if response.cookies.get("theme") == "light" else "light"
    resp = HTMLResponse(content=f'<script>document.location="/"</script>')
    resp.set_cookie(key="theme", value=theme, max_age=3600*24*30)  # 30 дней
    return resp

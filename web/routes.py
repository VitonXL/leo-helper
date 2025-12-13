# web/routes.py

from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/", response_class=HTMLResponse)
async def ui_home(request: Request):
    theme = request.cookies.get("theme", "light")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "theme": theme}
    )


@router.get("/toggle-theme")
async def toggle_theme(response: Response):
    current_theme = response.cookies.get("theme")
    new_theme = "dark" if current_theme == "light" else "light"
    resp = HTMLResponse(content=f'<script>document.location="/"</script>')
    resp.set_cookie(key="theme", value=new_theme, max_age=3600*24*30)
    return resp

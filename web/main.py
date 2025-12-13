# web/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routes import router  # ← импорт

app = FastAPI(title="Лео Помощник — UI")

# Подключение статики
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Подключение маршрутов
app.include_router(router)  # ← вот это важно!

@app.get("/health")
async def health():
    return {"status": "ok"}

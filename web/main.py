# web/main.py
import os
print(f"🚀 ENV PORT: {os.getenv('PORT')}")
print(f"🚀 ARGS: {' '.join(os.sys.argv)}")

from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from .routes import router
from .api import router as api_router

app = FastAPI(title="Лео Помощник — UI")

# 🔼 Сначала — статика (чтобы /static/script.js отдавался напрямую)
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# 🔽 Потом — API и роуты
app.include_router(api_router, prefix="/api")
app.include_router(router)  # твои страницы (например, /cabinet)

@app.get("/health")
async def health():
    return {"status": "ok"}

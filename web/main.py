# web/main.py
import os
print(f"🚀 ENV PORT: {os.getenv('PORT')}")
print(f"🚀 ARGS: {' '.join(os.sys.argv)}")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routes import router
from .api import router as api_router

app = FastAPI(title="Лео Помощник — UI")

app.mount("/static", StaticFiles(directory="web/static"), name="static")
app.include_router(router)
app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def home():
    return {"message": "🌐 Веб работает!", "status": "ok"}

@router.get("/health")
async def health():
    return {"status": "ok"}

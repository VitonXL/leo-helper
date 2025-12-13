from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def home():
    return {"message": "🌐 Веб работает!"}

@router.get("/health")
async def health():
    return {"status": "ok"}

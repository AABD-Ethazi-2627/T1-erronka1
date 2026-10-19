from fastapi import APIRouter

from app.services.model import model_service

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "model_loaded": model_service.loaded, "model_path": model_service.path}

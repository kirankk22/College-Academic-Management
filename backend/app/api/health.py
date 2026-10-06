from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "college-management-api"}


@router.get("/ready")
def ready() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ready",
        "environment": settings.environment,
    }

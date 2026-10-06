from fastapi import APIRouter

from app.db.session import check_database_connection


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


@router.get("/ready")
def ready() -> dict[str, str]:
    database_ready = check_database_connection()

    if not database_ready:
        return {
            "status": "not_ready",
            "database": "unavailable",
        }

    return {
        "status": "ready",
        "database": "ok",
    }
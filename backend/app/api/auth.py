from typing import Any

from fastapi import APIRouter, Depends

from app.core.security import decode_supabase_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me")
def me(claims: dict[str, Any] = Depends(decode_supabase_access_token)) -> dict[str, Any]:
    return {
        "user_id": claims["sub"],
        "email": claims.get("email"),
        "role": claims.get("role"),
    }

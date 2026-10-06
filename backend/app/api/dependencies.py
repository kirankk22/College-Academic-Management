from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import decode_supabase_access_token
from app.db.session import get_db
from app.models.authenticated_user import AuthenticatedUser


def get_current_user(
    claims: dict = Depends(decode_supabase_access_token),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    try:
        user_id = UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity",
        ) from exc

    result = db.execute(
        text(
            """
            select
                id,
                email,
                role,
                organization_id,
                institution_id,
                department_id,
                is_active
            from public.user_profiles
            where id = :user_id
            limit 1
            """
        ),
        {"user_id": user_id},
    ).mappings().first()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Application profile not found",
        )

    if not result["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return AuthenticatedUser(
        user_id=result["id"],
        email=result["email"],
        role=result["role"],
        organization_id=result["organization_id"],
        institution_id=result["institution_id"],
        department_id=result["department_id"],
        is_active=result["is_active"],
    )
from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.models.authenticated_user import AuthenticatedUser


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


@router.get("/me")
def me(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    return {
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "role": current_user.role,
        "organization_id": (
            str(current_user.organization_id)
            if current_user.organization_id
            else None
        ),
        "institution_id": (
            str(current_user.institution_id)
            if current_user.institution_id
            else None
        ),
        "department_id": (
            str(current_user.department_id)
            if current_user.department_id
            else None
        ),
        "is_active": current_user.is_active,
    }
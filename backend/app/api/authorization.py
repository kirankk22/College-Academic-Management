from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.models.authenticated_user import AuthenticatedUser


def require_roles(*allowed_roles: str) -> Callable:
    """
    Create a FastAPI dependency that requires the authenticated
    application user to have one of the specified roles.
    """

    allowed = set(allowed_roles)

    def dependency(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return dependency
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.models.authenticated_user import AuthenticatedUser
from app.db.session import get_db


router = APIRouter(
    prefix="/api/v1/institutions",
    tags=["institutions"],
)


@router.get("")
def list_institutions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Return only institutions that belong to the authenticated
    user's authorized organization/institution scope.
    """

    if current_user.organization_id is None:
        return []

    query = """
        select
            id,
            organization_id,
            code,
            name,
            city,
            state,
            is_active
        from public.institutions
        where organization_id = :organization_id
          and is_active = true
    """

    params: dict[str, UUID] = {
        "organization_id": current_user.organization_id,
    }

    if current_user.institution_id is not None:
        query += """
            and id = :institution_id
        """
        params["institution_id"] = current_user.institution_id

    query += """
        order by name
    """

    result = db.execute(
        text(query),
        params,
    ).mappings().all()

    return [
        {
            "id": str(row["id"]),
            "organization_id": str(row["organization_id"]),
            "code": row["code"],
            "name": row["name"],
            "city": row["city"],
            "state": row["state"],
            "is_active": row["is_active"],
        }
        for row in result
    ]
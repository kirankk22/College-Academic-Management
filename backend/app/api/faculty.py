from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.authorization import require_roles
from app.db.session import get_db
from app.models.authenticated_user import AuthenticatedUser
from app.models.faculty import (
    FacultyCreate,
    FacultyResponse,
    FacultyUpdate,
)
from app.services.faculty_service import (
    FacultyConflictError,
    create_faculty,
    get_faculty,
    list_faculty,
    update_faculty,
)


router = APIRouter(
    prefix="/api/v1/faculty",
    tags=["faculty"],
)


MANAGEMENT_ROLES = (
    "organization_admin",
    "principal",
    "hod",
)


def require_institution_scope(
    current_user: AuthenticatedUser,
) -> AuthenticatedUser:
    if current_user.institution_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to an institution",
        )

    return current_user


@router.get(
    "",
    response_model=list[FacultyResponse],
)
def get_faculty_members(
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    return list_faculty(
        db=db,
        institution_id=current_user.institution_id,
    )


@router.get(
    "/{faculty_id}",
    response_model=FacultyResponse,
)
def get_faculty_by_id(
    faculty_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    faculty = get_faculty(
        db=db,
        institution_id=current_user.institution_id,
        faculty_id=faculty_id,
    )

    if faculty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found",
        )

    return faculty


@router.post(
    "",
    response_model=FacultyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_faculty(
    payload: FacultyCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return create_faculty(
            db=db,
            institution_id=current_user.institution_id,
            payload=payload,
        )
    except FacultyConflictError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Faculty conflicts with an existing record",
        ) from exc


@router.patch(
    "/{faculty_id}",
    response_model=FacultyResponse,
)
def update_existing_faculty(
    faculty_id: UUID,
    payload: FacultyUpdate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        faculty = update_faculty(
            db=db,
            institution_id=current_user.institution_id,
            faculty_id=faculty_id,
            payload=payload,
        )
    except FacultyConflictError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Faculty conflicts with an existing record",
        ) from exc

    if faculty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found",
        )

    return faculty
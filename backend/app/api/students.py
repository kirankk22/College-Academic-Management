from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.authorization import require_roles
from app.db.session import get_db
from app.models.authenticated_user import AuthenticatedUser
from app.models.student import (
    StudentCreate,
    StudentResponse,
    StudentUpdate,
)
from app.services.student_service import (
    create_student,
    get_student,
    list_students,
    update_student,
)


router = APIRouter(
    prefix="/api/v1/students",
    tags=["students"],
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
    response_model=list[StudentResponse],
)
def get_students(
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    return list_students(
        db=db,
        institution_id=current_user.institution_id,
    )


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
)
def get_student_by_id(
    student_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    student = get_student(
        db=db,
        institution_id=current_user.institution_id,
        student_id=student_id,
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    return student


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_student(
    payload: StudentCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return create_student(
            db=db,
            institution_id=current_user.institution_id,
            payload=payload,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student conflicts with an existing record",
        ) from exc


@router.patch(
    "/{student_id}",
    response_model=StudentResponse,
)
def update_existing_student(
    student_id: UUID,
    payload: StudentUpdate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        student = update_student(
            db=db,
            institution_id=current_user.institution_id,
            student_id=student_id,
            payload=payload,
        )
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
            detail="Student conflicts with an existing record",
        ) from exc

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    return student
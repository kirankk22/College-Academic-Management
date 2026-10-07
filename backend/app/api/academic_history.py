from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.authorization import require_roles
from app.db.session import get_db
from app.models.academic_history import (
    AcademicHistoryCreate,
    AcademicHistoryResponse,
    SemesterResultCreate,
    SemesterResultResponse,
)
from app.models.authenticated_user import AuthenticatedUser
from app.services.academic_history_service import (
    AcademicHistoryError,
    SemesterResultError,
    create_academic_history,
    create_semester_result,
    list_academic_history,
    list_semester_results,
)


router = APIRouter(
    prefix="/api/v1/students",
    tags=["academic-history"],
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
    "/{student_id}/academic-history",
    response_model=list[AcademicHistoryResponse],
)
def get_academic_history(
    student_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return list_academic_history(
            db=db,
            institution_id=current_user.institution_id,
            student_id=student_id,
        )
    except AcademicHistoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{student_id}/academic-history",
    response_model=AcademicHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_academic_history(
    student_id: UUID,
    payload: AcademicHistoryCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return create_academic_history(
            db=db,
            institution_id=current_user.institution_id,
            student_id=student_id,
            payload=payload,
        )
    except AcademicHistoryError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Academic history conflicts with an existing record",
        ) from exc


@router.get(
    "/{student_id}/semester-results",
    response_model=list[SemesterResultResponse],
)
def get_semester_results(
    student_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return list_semester_results(
            db=db,
            institution_id=current_user.institution_id,
            student_id=student_id,
        )
    except SemesterResultError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{student_id}/semester-results",
    response_model=SemesterResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_semester_result(
    student_id: UUID,
    payload: SemesterResultCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return create_semester_result(
            db=db,
            institution_id=current_user.institution_id,
            student_id=student_id,
            payload=payload,
        )
    except SemesterResultError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Semester result conflicts with an existing record",
        ) from exc
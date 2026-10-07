from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.authorization import require_roles
from app.db.session import get_db
from app.models.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodResponse,
    AcademicPeriodUpdate,
)
from app.models.authenticated_user import AuthenticatedUser
from app.services.academic_period_service import (
    AcademicPeriodError,
    create_academic_period,
    deactivate_academic_period,
    get_academic_period,
    list_academic_periods,
    update_academic_period,
)


router = APIRouter(
    prefix="/api/v1/academic-periods",
    tags=["academic-periods"],
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
    response_model=list[AcademicPeriodResponse],
)
def get_academic_periods(
    academic_year_id: UUID | None = None,
    program_id: UUID | None = None,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    return list_academic_periods(
        db=db,
        institution_id=current_user.institution_id,
        academic_year_id=academic_year_id,
        program_id=program_id,
    )


@router.get(
    "/{academic_period_id}",
    response_model=AcademicPeriodResponse,
)
def get_academic_period_by_id(
    academic_period_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    period = get_academic_period(
        db=db,
        institution_id=current_user.institution_id,
        academic_period_id=academic_period_id,
    )

    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic period not found",
        )

    return period


@router.post(
    "",
    response_model=AcademicPeriodResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_academic_period(
    payload: AcademicPeriodCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return create_academic_period(
            db=db,
            institution_id=current_user.institution_id,
            payload=payload,
        )
    except AcademicPeriodError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Academic period conflicts with an existing record",
        ) from exc


@router.patch(
    "/{academic_period_id}",
    response_model=AcademicPeriodResponse,
)
def update_existing_academic_period(
    academic_period_id: UUID,
    payload: AcademicPeriodUpdate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        period = update_academic_period(
            db=db,
            institution_id=current_user.institution_id,
            academic_period_id=academic_period_id,
            payload=payload,
        )
    except AcademicPeriodError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic period not found",
        )

    return period


@router.delete(
    "/{academic_period_id}",
    response_model=AcademicPeriodResponse,
)
def deactivate_existing_academic_period(
    academic_period_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    period = deactivate_academic_period(
        db=db,
        institution_id=current_user.institution_id,
        academic_period_id=academic_period_id,
    )

    if period is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic period not found",
        )

    return period
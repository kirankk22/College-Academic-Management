from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.authorization import require_roles
from app.db.session import get_db
from app.models.academic_catalog import (
    AcademicYearResponse,
    ProgramResponse,
    SectionResponse,
    SubjectResponse,
)
from app.models.authenticated_user import AuthenticatedUser
from app.services.academic_catalog_service import (
    list_academic_years,
    list_programs,
    list_sections,
    list_subjects,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["academic-catalog"],
)


READ_ROLES = (
    "organization_admin",
    "principal",
    "hod",
    "faculty",
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
    "/academic-years",
    response_model=list[AcademicYearResponse],
)
def get_academic_years(
    current_user: AuthenticatedUser = Depends(
        require_roles(*READ_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    return list_academic_years(
        db=db,
        institution_id=current_user.institution_id,
    )


@router.get(
    "/programs",
    response_model=list[ProgramResponse],
)
def get_programs(
    academic_year_id: UUID | None = None,
    current_user: AuthenticatedUser = Depends(
        require_roles(*READ_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    return list_programs(
        db=db,
        institution_id=current_user.institution_id,
        academic_year_id=academic_year_id,
    )


@router.get(
    "/sections",
    response_model=list[SectionResponse],
)
def get_sections(
    academic_period_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*READ_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    return list_sections(
        db=db,
        institution_id=current_user.institution_id,
        academic_period_id=academic_period_id,
    )


@router.get(
    "/subjects",
    response_model=list[SubjectResponse],
)
def get_subjects(
    academic_period_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*READ_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    return list_subjects(
        db=db,
        institution_id=current_user.institution_id,
        academic_period_id=academic_period_id,
    )
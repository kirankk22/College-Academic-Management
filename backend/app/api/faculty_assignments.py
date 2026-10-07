from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.authorization import require_roles

from app.db.session import get_db
from app.models.authenticated_user import AuthenticatedUser
from app.models.faculty_assignment import (
    FacultyAssignmentCreate,
    FacultyAssignmentResponse,
    FacultyAssignmentUpdate,
)
from app.services.faculty_assignment_service import (
    FacultyAssignmentConflictError,
    FacultyAssignmentNotFoundError,
    create_assignment,
    deactivate_assignment,
    get_assignment,
    list_assignments,
    update_assignment,
)


router = APIRouter(
    prefix="/api/v1/faculty-assignments",
    tags=["Faculty Assignments"],
)


MANAGEMENT_ROLES = (
    "organization_admin",
    "principal",
    "hod",
)


def require_institution_scope(
    current_user: AuthenticatedUser,
):
    if current_user.institution_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institution scope is required",
        )

    return current_user


@router.get(
    "",
    response_model=list[FacultyAssignmentResponse],
)
def get_faculty_assignments(
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    user = require_institution_scope(current_user)

    return list_assignments(
        db=db,
        institution_id=user.institution_id,
    )


@router.get(
    "/{assignment_id}",
    response_model=FacultyAssignmentResponse,
)
def get_faculty_assignment(
    assignment_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    user = require_institution_scope(current_user)

    try:
        return get_assignment(
            db=db,
            institution_id=user.institution_id,
            assignment_id=assignment_id,
        )
    except FacultyAssignmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=FacultyAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_faculty_assignment(
    payload: FacultyAssignmentCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    user = require_institution_scope(current_user)

    try:
        return create_assignment(
            db=db,
            institution_id=user.institution_id,
            faculty_id=payload.faculty_id,
            subject_id=payload.subject_id,
            section_id=payload.section_id,
            academic_year_id=payload.academic_year_id,
            assignment_type=payload.assignment_type,
        )
    except FacultyAssignmentConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{assignment_id}",
    response_model=FacultyAssignmentResponse,
)
def update_faculty_assignment(
    assignment_id: UUID,
    payload: FacultyAssignmentUpdate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    user = require_institution_scope(current_user)

    try:
        return update_assignment(
            db=db,
            institution_id=user.institution_id,
            assignment_id=assignment_id,
            faculty_id=payload.faculty_id,
            assignment_type=payload.assignment_type,
            is_active=payload.is_active,
        )
    except FacultyAssignmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except FacultyAssignmentConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{assignment_id}",
    response_model=FacultyAssignmentResponse,
)
def delete_faculty_assignment(
    assignment_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    user = require_institution_scope(current_user)

    try:
        return deactivate_assignment(
            db=db,
            institution_id=user.institution_id,
            assignment_id=assignment_id,
        )
    except FacultyAssignmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
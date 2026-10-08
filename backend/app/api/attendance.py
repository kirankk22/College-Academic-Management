from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.authorization import require_roles
from app.db.session import get_db
from app.models.attendance import (
    AttendanceBulkCreate,
    AttendanceBulkResponse,
    AttendanceCorrectionResponse,
    AttendanceCreate,
    AttendanceResponse,
    AttendanceUpdate,
)
from app.models.authenticated_user import AuthenticatedUser
from app.services.attendance_service import (
    AttendanceConflictError,
    AttendanceError,
    AttendanceNotFoundError,
    create_attendance,
    create_bulk_attendance,
    get_attendance,
    list_attendance,
    list_corrections,
    update_attendance,
)


router = APIRouter(
    prefix="/api/v1/attendance",
    tags=["attendance"],
)


MANAGEMENT_ROLES = (
    "organization_admin",
    "principal",
    "hod",
)

WRITE_ROLES = (
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
    "",
    response_model=list[AttendanceResponse],
)
def get_attendance_records(
    student_id: UUID | None = Query(default=None),
    subject_id: UUID | None = Query(default=None),
    section_id: UUID | None = Query(default=None),
    academic_period_id: UUID | None = Query(default=None),
    attendance_date: date | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "organization_admin",
            "principal",
            "hod",
            "faculty",
        )
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    return list_attendance(
        db=db,
        institution_id=current_user.institution_id,
        student_id=student_id,
        subject_id=subject_id,
        section_id=section_id,
        academic_period_id=academic_period_id,
        attendance_date=attendance_date,
    )


@router.post(
    "",
    response_model=AttendanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attendance_record(
    payload: AttendanceCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*WRITE_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return create_attendance(
            db=db,
            institution_id=current_user.institution_id,
            user_id=current_user.user_id,
            user_role=current_user.role,
            payload=payload,
        )

    except AttendanceConflictError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except AttendanceError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/bulk",
    response_model=AttendanceBulkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bulk_attendance_records(
    payload: AttendanceBulkCreate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*WRITE_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        records = create_bulk_attendance(
            db=db,
            institution_id=current_user.institution_id,
            user_id=current_user.user_id,
            user_role=current_user.role,
            payload=payload,
        )

        return AttendanceBulkResponse(
            saved_count=len(records),
            records=records,
        )

    except AttendanceConflictError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except AttendanceError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{attendance_id}",
    response_model=AttendanceResponse,
)
def get_attendance_record(
    attendance_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(
            "organization_admin",
            "principal",
            "hod",
            "faculty",
        )
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    attendance = get_attendance(
        db=db,
        institution_id=current_user.institution_id,
        attendance_id=attendance_id,
    )

    if attendance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance not found",
        )

    return attendance


@router.patch(
    "/{attendance_id}",
    response_model=AttendanceResponse,
)
def correct_attendance_record(
    attendance_id: UUID,
    payload: AttendanceUpdate,
    current_user: AuthenticatedUser = Depends(
        require_roles(*WRITE_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return update_attendance(
            db=db,
            institution_id=current_user.institution_id,
            user_id=current_user.user_id,
            user_role=current_user.role,
            attendance_id=attendance_id,
            payload=payload,
        )

    except AttendanceNotFoundError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except AttendanceError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{attendance_id}/corrections",
    response_model=list[AttendanceCorrectionResponse],
)
def get_attendance_corrections(
    attendance_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return list_corrections(
            db=db,
            institution_id=current_user.institution_id,
            attendance_id=attendance_id,
        )

    except AttendanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
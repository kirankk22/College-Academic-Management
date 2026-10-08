from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.authorization import require_roles
from app.db.session import get_db
from app.models.attendance_students import AttendanceStudentResponse
from app.models.authenticated_user import AuthenticatedUser
from app.services.attendance_student_service import (
    AttendanceStudentContextError,
    list_attendance_students,
)


router = APIRouter(
    prefix="/api/v1/attendance",
    tags=["attendance-students"],
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
    "/students",
    response_model=list[AttendanceStudentResponse],
)
def get_attendance_students(
    academic_year_id: UUID,
    program_id: UUID,
    academic_period_id: UUID,
    section_id: UUID,
    current_user: AuthenticatedUser = Depends(
        require_roles(*READ_ROLES)
    ),
    db: Session = Depends(get_db),
):
    current_user = require_institution_scope(current_user)

    try:
        return list_attendance_students(
            db=db,
            institution_id=current_user.institution_id,
            academic_year_id=academic_year_id,
            program_id=program_id,
            academic_period_id=academic_period_id,
            section_id=section_id,
        )
    except AttendanceStudentContextError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
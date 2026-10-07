from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ATTENDANCE_STATUSES = (
    "PRESENT",
    "ABSENT",
    "LEAVE",
    "OD",
    "LATE",
    "CANCELLED",
    "SPECIAL",
)

ATTENDANCE_SOURCES = (
    "DIRECT",
    "GOOGLE_SHEETS",
)


class AttendanceCreate(BaseModel):
    student_id: UUID
    subject_id: UUID
    section_id: UUID
    academic_period_id: UUID
    attendance_date: date
    status: str
    source: str = "DIRECT"
    correction_reason: str | None = None


class AttendanceUpdate(BaseModel):
    status: str
    correction_reason: str = Field(
        min_length=1,
        description="Reason required whenever an existing attendance "
        "record is corrected.",
    )


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    student_id: UUID
    subject_id: UUID
    section_id: UUID
    academic_period_id: UUID
    attendance_date: date
    status: str
    source: str
    source_import_id: UUID | None = None
    marked_by_user_id: UUID | None = None
    marked_by_faculty_id: UUID | None = None
    correction_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AttendanceCorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    attendance_id: UUID
    old_status: str
    new_status: str
    reason: str
    changed_by_user_id: UUID | None = None
    changed_by_faculty_id: UUID | None = None
    source: str
    changed_at: datetime
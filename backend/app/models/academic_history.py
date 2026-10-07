from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ACADEMIC_HISTORY_STATUSES = {
    "active",
    "completed",
    "promoted",
    "detained",
    "withdrawn",
    "transferred",
}

RESULT_STATUSES = {
    "pending",
    "pass",
    "fail",
}

PROGRESSION_STATUSES = {
    "eligible",
    "blocked",
    "conditional",
}


class AcademicHistoryCreate(BaseModel):
    academic_year_id: UUID
    program_id: UUID
    semester_id: UUID
    section_id: UUID
    roll_number: str | None = Field(
        default=None,
        max_length=50,
    )
    status: str = "active"


class AcademicHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    academic_year_id: UUID
    program_id: UUID
    semester_id: UUID
    section_id: UUID
    roll_number: str | None
    status: str
    start_date: date | None
    end_date: date | None


class SemesterResultCreate(BaseModel):
    academic_year_id: UUID
    program_id: UUID
    semester_id: UUID
    result_status: str
    result_date: date | None = None
    remarks: str | None = Field(
        default=None,
        max_length=1000,
    )


class SemesterResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    academic_year_id: UUID
    program_id: UUID
    semester_id: UUID
    result_status: str
    progression_status: str
    result_date: date | None
    remarks: str | None
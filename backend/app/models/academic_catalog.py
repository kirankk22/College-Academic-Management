from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AcademicYearResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    name: str
    start_date: date
    end_date: date
    is_current: bool


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department_id: UUID
    name: str
    code: str
    academic_structure_type: str
    duration_units: int
    is_active: bool


class SectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    academic_period_id: UUID
    semester_id: UUID
    name: str
    is_active: bool


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    semester_id: UUID
    code: str
    name: str
    credits: float | None
    is_active: bool
    has_lab: bool
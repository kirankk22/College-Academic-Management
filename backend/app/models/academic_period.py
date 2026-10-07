from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AcademicPeriodCreate(BaseModel):
    academic_year_id: UUID
    program_id: UUID
    period_type: str
    period_number: int = Field(gt=0)
    semester_id: UUID | None = None
    period_name: str
    semester_cycle: str | None = None
    is_active: bool = True


class AcademicPeriodUpdate(BaseModel):
    period_name: str | None = None
    is_active: bool | None = None


class AcademicPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    academic_year_id: UUID
    program_id: UUID
    period_type: str
    period_number: int
    semester_id: UUID | None
    period_name: str
    semester_cycle: str | None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
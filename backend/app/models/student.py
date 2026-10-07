from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentCreate(BaseModel):
    permanent_student_id: str = Field(
        min_length=1,
        max_length=100,
    )
    admission_number: str | None = Field(
        default=None,
        max_length=100,
    )
    first_name: str = Field(
        min_length=1,
        max_length=100,
    )
    middle_name: str | None = Field(
        default=None,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        max_length=100,
    )
    date_of_birth: date | None = None
    gender: str | None = Field(
        default=None,
        max_length=50,
    )
    email: str | None = Field(
        default=None,
        max_length=255,
    )
    phone: str | None = Field(
        default=None,
        max_length=30,
    )
    admission_date: date | None = None
    status: str = "active"


class StudentUpdate(BaseModel):
    admission_number: str | None = Field(
        default=None,
        max_length=100,
    )
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    middle_name: str | None = Field(
        default=None,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        max_length=100,
    )
    date_of_birth: date | None = None
    gender: str | None = Field(
        default=None,
        max_length=50,
    )
    email: str | None = Field(
        default=None,
        max_length=255,
    )
    phone: str | None = Field(
        default=None,
        max_length=30,
    )
    admission_date: date | None = None
    status: str | None = None


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    permanent_student_id: str
    admission_number: str | None
    first_name: str
    middle_name: str | None
    last_name: str | None
    date_of_birth: date | None
    gender: str | None
    email: str | None
    phone: str | None
    admission_date: date | None
    status: str
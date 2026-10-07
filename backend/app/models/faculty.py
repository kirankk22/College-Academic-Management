from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


FACULTY_DESIGNATIONS = {
    "professor",
    "associate_professor",
    "assistant_professor",
    "lecturer",
    "visiting_faculty",
    "other",
}


class FacultyCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    designation: str | None = Field(default=None, max_length=100)
    department_id: UUID | None = None
    user_profile_id: UUID | None = None
    is_active: bool = True


class FacultyUpdate(BaseModel):
    employee_id: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    designation: str | None = Field(default=None, max_length=100)
    department_id: UUID | None = None
    user_profile_id: UUID | None = None
    is_active: bool | None = None


class FacultyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    institution_id: UUID
    user_profile_id: UUID | None
    employee_id: str
    name: str
    email: str | None
    phone: str | None
    designation: str | None
    department_id: UUID | None
    is_active: bool
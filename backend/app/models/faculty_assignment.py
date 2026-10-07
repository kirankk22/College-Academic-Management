from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ASSIGNMENT_TYPES = {
    "SUBJECT",
    "LAB_PRIMARY",
    "LAB_SECONDARY",
}


class FacultyAssignmentCreate(BaseModel):
    faculty_id: UUID
    subject_id: UUID
    section_id: UUID
    academic_year_id: UUID
    assignment_type: str = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_assignment_type(self):
        if self.assignment_type not in ASSIGNMENT_TYPES:
            raise ValueError(
                "assignment_type must be one of: "
                "SUBJECT, LAB_PRIMARY, LAB_SECONDARY"
            )
        return self


class FacultyAssignmentUpdate(BaseModel):
    faculty_id: UUID | None = None
    assignment_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_assignment_type(self):
        if (
            self.assignment_type is not None
            and self.assignment_type not in ASSIGNMENT_TYPES
        ):
            raise ValueError(
                "assignment_type must be one of: "
                "SUBJECT, LAB_PRIMARY, LAB_SECONDARY"
            )
        return self


class FacultyAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    faculty_id: UUID
    subject_id: UUID
    section_id: UUID
    academic_year_id: UUID
    assignment_type: str
    is_primary: bool
    is_active: bool
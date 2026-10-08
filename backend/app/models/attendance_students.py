from uuid import UUID

from pydantic import BaseModel


class AttendanceStudentResponse(BaseModel):
    student_id: UUID
    permanent_student_id: str
    student_name: str
    roll_number: str | None
    student_status: str
    academic_history_id: UUID
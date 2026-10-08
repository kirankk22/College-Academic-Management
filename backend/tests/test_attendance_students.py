from uuid import UUID

from app.models.attendance_students import AttendanceStudentResponse
from app.services.attendance_student_service import (
    AttendanceStudentContextError,
)


def test_attendance_student_response_accepts_expected_fields():
    student_id = UUID("11111111-1111-1111-1111-111111111111")
    history_id = UUID("22222222-2222-2222-2222-222222222222")

    response = AttendanceStudentResponse(
        student_id=student_id,
        permanent_student_id="MCA26-001",
        student_name="Arjun Sharma",
        roll_number="MCA-S1-001",
        student_status="active",
        academic_history_id=history_id,
    )

    assert response.student_id == student_id
    assert response.permanent_student_id == "MCA26-001"
    assert response.student_name == "Arjun Sharma"
    assert response.roll_number == "MCA-S1-001"
    assert response.student_status == "active"
    assert response.academic_history_id == history_id


def test_attendance_student_response_allows_missing_roll_number():
    response = AttendanceStudentResponse(
        student_id=UUID("11111111-1111-1111-1111-111111111111"),
        permanent_student_id="MCA26-001",
        student_name="Arjun Sharma",
        roll_number=None,
        student_status="active",
        academic_history_id=UUID(
            "22222222-2222-2222-2222-222222222222"
        ),
    )

    assert response.roll_number is None


def test_attendance_student_context_error_is_domain_error():
    error = AttendanceStudentContextError(
        "Invalid academic attendance context"
    )

    assert str(error) == "Invalid academic attendance context"
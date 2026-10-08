import os
from datetime import date
from uuid import UUID

from test_attendance_smoke import (
    authenticate,
    backend_headers,
    expect_status,
    fail,
    get_real_academic_periods,
    get_real_institutions,
    get_real_students,
    request_json,
)


BASE_URL = os.getenv(
    "SMOKE_TEST_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

TEST_ATTENDANCE_DATE = date(2099, 12, 31)


def get_json(
    access_token: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
):
    query_string = ""

    if params:
        query_string = "?" + "&".join(
            f"{key}={value}"
            for key, value in params.items()
        )

    return request_json(
        "GET",
        f"{BASE_URL}{path}{query_string}",
        headers=backend_headers(access_token),
    )


def post_json(
    access_token: str,
    path: str,
    body: dict,
):
    return request_json(
        "POST",
        f"{BASE_URL}{path}",
        headers=backend_headers(access_token),
        body=body,
    )


def choose_active_students(
    students: list[dict],
    institution_ids: set[str],
) -> list[dict]:
    selected = []

    for student in students:
        if (
            student.get("id")
            and str(student.get("institution_id"))
            in institution_ids
            and student.get("status") == "active"
        ):
            selected.append(student)

        if len(selected) == 2:
            return selected

    fail(
        "Could not find two active students belonging to "
        "an institution visible to the authenticated user"
    )

    raise RuntimeError("unreachable")


def choose_matching_period(
    periods: list[dict],
    student_history: dict,
) -> dict:
    for period in periods:
        if not period.get("is_active"):
            continue

        if period.get("period_type") != "SEMESTER":
            continue

        if str(period.get("academic_year_id")) != str(
            student_history["academic_year_id"]
        ):
            continue

        if str(period.get("program_id")) != str(
            student_history["program_id"]
        ):
            continue

        if str(period.get("semester_id")) != str(
            student_history["semester_id"]
        ):
            continue

        return period

    fail(
        "Could not find an active SEMESTER academic period "
        "matching the selected student's academic history"
    )

    raise RuntimeError("unreachable")


def get_student_history(
    access_token: str,
    student_id: str,
) -> list[dict]:
    status_code, payload = get_json(
        access_token,
        f"/api/v1/students/{student_id}/academic-history",
    )

    expect_status(
        status_code,
        200,
        "Get student academic history",
        payload,
    )

    if not isinstance(payload, list):
        fail("Academic history response is not a list")

    active_history = [
        row
        for row in payload
        if row.get("status") == "active"
    ]

    if not active_history:
        fail(
            "Selected student has no active academic history"
        )

    return active_history


def main() -> None:
    print()
    print("Phase 3A.4B real Supabase Bulk Attendance smoke test")
    print(f"Backend: {BASE_URL}")
    print(
        f"Test attendance date: "
        f"{TEST_ATTENDANCE_DATE.isoformat()}"
    )
    print()

    access_token = authenticate()

    institutions = get_real_institutions(access_token)

    institution_ids = {
        str(institution["id"])
        for institution in institutions
        if institution.get("id")
    }

    if not institution_ids:
        fail(
            "No valid institution IDs were returned "
            "for the authenticated user"
        )

    students = get_real_students(access_token)

    selected_students = choose_active_students(
        students,
        institution_ids,
    )

    print(
        "PASS: Selected two active students "
        f"({selected_students[0].get('permanent_student_id')}, "
        f"{selected_students[1].get('permanent_student_id')})"
    )

    first_student_id = str(selected_students[0]["id"])

    history_rows = get_student_history(
        access_token,
        first_student_id,
    )

    student_history = history_rows[0]

    academic_year_id = str(
        student_history["academic_year_id"]
    )
    program_id = str(
        student_history["program_id"]
    )
    semester_id = str(
        student_history["semester_id"]
    )
    section_id = str(
        student_history["section_id"]
    )

    print(
        "PASS: Selected academic context from "
        f"student history "
        f"(academic_year_id={academic_year_id}, "
        f"program_id={program_id}, "
        f"semester_id={semester_id}, "
        f"section_id={section_id})"
    )

    periods = get_real_academic_periods(access_token)

    academic_period = choose_matching_period(
        periods,
        student_history,
    )

    academic_period_id = str(
        academic_period["id"]
    )

    if str(
        academic_period["academic_year_id"]
    ) != academic_year_id:
        fail(
            "Academic period academic_year_id does not "
            "match student academic history"
        )

    if str(
        academic_period["program_id"]
    ) != program_id:
        fail(
            "Academic period program_id does not "
            "match student academic history"
        )

    if str(
        academic_period["semester_id"]
    ) != semester_id:
        fail(
            "Academic period semester_id does not "
            "match student academic history"
        )

    print(
        "PASS: Academic period matches student "
        "academic history"
    )

    status_code, sections = get_json(
        access_token,
        "/api/v1/sections",
        params={
            "academic_period_id": academic_period_id,
        },
    )

    expect_status(
        status_code,
        200,
        "List sections",
        sections,
    )

    if not isinstance(sections, list):
        fail("Section response is not a list")

    matching_section = next(
        (
            section
            for section in sections
            if str(section.get("id")) == section_id
        ),
        None,
    )

    if matching_section is None:
        fail(
            "Student academic history section was not "
            "returned for the selected academic period"
        )

    print(
        "PASS: Student section matches "
        f"academic period ({matching_section['name']})"
    )

    status_code, subjects = get_json(
        access_token,
        "/api/v1/subjects",
        params={
            "academic_period_id": academic_period_id,
        },
    )

    expect_status(
        status_code,
        200,
        "List subjects",
        subjects,
    )

    if not isinstance(subjects, list):
        fail("Subject response is not a list")

    if not subjects:
        fail(
            "No subjects returned for the selected "
            "academic period"
        )

    subject = subjects[0]
    subject_id = str(subject["id"])

    print(
        "PASS: Selected subject "
        f"({subject['code']} - {subject['name']})"
    )

    student_context_status, attendance_students = get_json(
        access_token,
        "/api/v1/attendance/students",
        params={
            "academic_year_id": academic_year_id,
            "program_id": program_id,
            "academic_period_id": academic_period_id,
            "section_id": section_id,
        },
    )

    expect_status(
        student_context_status,
        200,
        "List attendance-context students",
        attendance_students,
    )

    if not isinstance(attendance_students, list):
        fail(
            "Attendance student response is not a list"
        )

    attendance_student_ids = {
        str(student["student_id"])
        for student in attendance_students
    }

    for selected_student in selected_students:
        if str(selected_student["id"]) not in attendance_student_ids:
            fail(
                "Selected student is not present in the "
                "attendance academic context"
            )

    print(
        "PASS: Both selected students belong to "
        "the attendance academic context"
    )

    payload = {
        "subject_id": subject_id,
        "section_id": section_id,
        "academic_period_id": academic_period_id,
        "attendance_date": TEST_ATTENDANCE_DATE.isoformat(),
        "source": "DIRECT",
        "records": [
            {
                "student_id": str(selected_students[0]["id"]),
                "status": "PRESENT",
            },
            {
                "student_id": str(selected_students[1]["id"]),
                "status": "ABSENT",
            },
        ],
    }

    status_code, created = post_json(
        access_token,
        "/api/v1/attendance/bulk",
        payload,
    )

    expect_status(
        status_code,
        201,
        "Create bulk attendance",
        created,
    )

    if not isinstance(created, dict):
        fail(
            "Bulk attendance response is not an object"
        )

    if created.get("saved_count") != 2:
        fail(
            "Expected saved_count=2, got "
            f"{created.get('saved_count')}"
        )

    records = created.get("records")

    if not isinstance(records, list):
        fail(
            "Bulk attendance records response is not a list"
        )

    if len(records) != 2:
        fail(
            "Expected exactly two created attendance "
            f"records, got {len(records)}"
        )

    created_by_student = {
        str(record["student_id"]): record
        for record in records
    }

    first_record = created_by_student.get(
        str(selected_students[0]["id"])
    )
    second_record = created_by_student.get(
        str(selected_students[1]["id"])
    )

    if first_record is None:
        fail(
            "First selected student was not returned "
            "in bulk response"
        )

    if second_record is None:
        fail(
            "Second selected student was not returned "
            "in bulk response"
        )

    if first_record["status"] != "PRESENT":
        fail(
            "First student's status was expected to "
            "be PRESENT"
        )

    if second_record["status"] != "ABSENT":
        fail(
            "Second student's status was expected to "
            "be ABSENT"
        )

    print(
        "PASS: Bulk attendance created "
        "(2 records)"
    )

    duplicate_status, duplicate_payload = post_json(
        access_token,
        "/api/v1/attendance/bulk",
        payload,
    )

    expect_status(
        duplicate_status,
        409,
        "Duplicate bulk attendance rejected",
        duplicate_payload,
    )

    invalid_payload = {
        **payload,
        "attendance_date": date(
            2099,
            12,
            30,
        ).isoformat(),
        "records": [
            {
                "student_id": str(
                    selected_students[0]["id"]
                ),
                "status": "PRESENT",
            },
            {
                "student_id": str(
                    UUID(
                        "99999999-9999-9999-9999-999999999999"
                    )
                ),
                "status": "ABSENT",
            },
        ],
    }

    invalid_status, invalid_payload_response = post_json(
        access_token,
        "/api/v1/attendance/bulk",
        invalid_payload,
    )

    expect_status(
        invalid_status,
        400,
        "Invalid student bulk submission rejected",
        invalid_payload_response,
    )

    verification_status, attendance_rows = get_json(
        access_token,
        "/api/v1/attendance",
        params={
            "subject_id": subject_id,
            "section_id": section_id,
            "academic_period_id": academic_period_id,
            "attendance_date": (
                TEST_ATTENDANCE_DATE.isoformat()
            ),
        },
    )

    expect_status(
        verification_status,
        200,
        "Verify real Supabase bulk attendance",
        attendance_rows,
    )

    if not isinstance(attendance_rows, list):
        fail(
            "Attendance verification response "
            "is not a list"
        )

    test_rows = [
        row
        for row in attendance_rows
        if row.get("attendance_date")
        == TEST_ATTENDANCE_DATE.isoformat()
    ]

    if len(test_rows) != 2:
        fail(
            "Expected exactly two test attendance "
            f"records, got {len(test_rows)}"
        )

    verified_student_ids = {
        str(row["student_id"])
        for row in test_rows
    }

    expected_student_ids = {
        str(selected_students[0]["id"]),
        str(selected_students[1]["id"]),
    }

    if verified_student_ids != expected_student_ids:
        fail(
            "Verified attendance records do not belong "
            "to the submitted students"
        )

    print(
        "PASS: Real Supabase bulk attendance records verified"
    )

    print()
    print("==============================================")
    print(
        "PASS: Phase 3A.4B real Supabase "
        "Bulk Attendance smoke test"
    )
    print("==============================================")
    print()
    print(
        "IMPORTANT: Two test records were created with "
        f"attendance_date={TEST_ATTENDANCE_DATE.isoformat()}."
    )
    print(
        "They must be removed through the controlled "
        "Supabase SQL cleanup before Phase 3A.4B is closed."
    )


if __name__ == "__main__":
    main()
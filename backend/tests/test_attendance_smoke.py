import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv(
    "SMOKE_TEST_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
TEST_AUTH_EMAIL = os.environ["TEST_AUTH_EMAIL"]
TEST_AUTH_PASSWORD = os.environ["TEST_AUTH_PASSWORD"]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
) -> tuple[int, dict | list | None]:
    request_headers = dict(headers or {})
    data = None

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=request_headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")

            if not response_body:
                return response.status, None

            return response.status, json.loads(response_body)

    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")

        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError:
            payload = response_body

        return exc.code, payload

    except urllib.error.URLError as exc:
        fail(f"Request failed: {exc}")

    raise RuntimeError("unreachable")


def expect_status(
    actual_status: int,
    expected_status: int,
    operation: str,
    payload: dict | list | None,
) -> None:
    if actual_status != expected_status:
        fail(
            f"{operation}: expected HTTP {expected_status}, "
            f"got HTTP {actual_status}: {payload}"
        )

    print(f"PASS: {operation}")


def authenticate() -> str:
    url = (
        f"{SUPABASE_URL}/auth/v1/token"
        "?grant_type=password"
    )

    status_code, payload = request_json(
        "POST",
        url,
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
        },
        body={
            "email": TEST_AUTH_EMAIL,
            "password": TEST_AUTH_PASSWORD,
        },
    )

    if status_code != 200:
        fail(
            "Supabase Auth login failed: "
            f"HTTP {status_code}: {payload}"
        )

    if not isinstance(payload, dict):
        fail("Supabase Auth login returned an unexpected response")

    access_token = payload.get("access_token")

    if not access_token:
        fail("Supabase Auth login did not return an access token")

    print("PASS: Supabase Auth login")

    return access_token


def backend_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
    }


def get_real_institutions(
    access_token: str,
) -> list[dict]:
    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}/api/v1/institutions",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "List institutions",
        payload,
    )

    if not isinstance(payload, list):
        fail("Institution response is not a list")

    if not payload:
        fail("No institutions were returned")

    print(
        f"PASS: List institutions "
        f"({len(payload)} records returned)"
    )

    return payload


def get_real_academic_periods(
    access_token: str,
) -> list[dict]:
    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}/api/v1/academic-periods",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "List academic periods",
        payload,
    )

    if not isinstance(payload, list):
        fail("Academic period response is not a list")

    if not payload:
        fail("No academic periods were returned")

    print(
        f"PASS: List academic periods "
        f"({len(payload)} records returned)"
    )

    return payload


def get_real_students(
    access_token: str,
) -> list[dict]:
    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}/api/v1/students",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "List students",
        payload,
    )

    if not isinstance(payload, list):
        fail("Student response is not a list")

    if not payload:
        fail("No students were returned from Supabase")

    print(
        f"PASS: List students "
        f"({len(payload)} records returned)"
    )

    return payload


def get_student_academic_history(
    access_token: str,
    student_id: str,
) -> list[dict]:
    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}/api/v1/students/{student_id}/academic-history",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "Get student academic history",
        payload,
    )

    if not isinstance(payload, list):
        fail("Academic history response is not a list")

    if not payload:
        fail(
            "Selected student has no academic history records"
        )

    print(
        f"PASS: Student academic history "
        f"({len(payload)} records returned)"
    )

    return payload


def choose_active_student(
    students: list[dict],
    institution_ids: set[str],
) -> dict:
    for student in students:
        if (
            student.get("id")
            and str(student.get("institution_id")) in institution_ids
            and student.get("status") == "active"
        ):
            return student

    fail(
        "Could not find an active student belonging to "
        "an institution visible to the authenticated user"
    )

    raise RuntimeError("unreachable")


def choose_student_history(
    history_rows: list[dict],
) -> dict:
    for history in history_rows:
        if history.get("status") == "active":
            required_fields = {
                "id",
                "student_id",
                "academic_year_id",
                "program_id",
                "semester_id",
                "section_id",
            }

            if required_fields.issubset(history.keys()):
                return history

    fail(
        "Could not find an active academic-history record "
        "with the required academic context"
    )

    raise RuntimeError("unreachable")


def choose_matching_period(
    periods: list[dict],
    history: dict,
) -> dict:
    required_fields = {
        "id",
        "academic_year_id",
        "program_id",
        "period_type",
        "period_number",
        "semester_id",
        "period_name",
        "is_active",
    }

    for period in periods:
        if not required_fields.issubset(period.keys()):
            continue

        if period.get("is_active") is not True:
            continue

        if period.get("period_type") != "SEMESTER":
            continue

        if str(period.get("academic_year_id")) != str(
            history["academic_year_id"]
        ):
            continue

        if str(period.get("program_id")) != str(
            history["program_id"]
        ):
            continue

        if str(period.get("semester_id")) != str(
            history["semester_id"]
        ):
            continue

        return period

    fail(
        "Could not find an active SEMESTER academic period "
        "matching the student's academic history"
    )

    raise RuntimeError("unreachable")


def list_attendance(
    access_token: str,
    *,
    student_id: str | None = None,
    subject_id: str | None = None,
    section_id: str | None = None,
    academic_period_id: str | None = None,
) -> list[dict]:
    query_parts = []

    if student_id:
        query_parts.append(f"student_id={student_id}")

    if subject_id:
        query_parts.append(f"subject_id={subject_id}")

    if section_id:
        query_parts.append(f"section_id={section_id}")

    if academic_period_id:
        query_parts.append(
            f"academic_period_id={academic_period_id}"
        )

    query_string = ""

    if query_parts:
        query_string = "?" + "&".join(query_parts)

    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}/api/v1/attendance{query_string}",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "List attendance",
        payload,
    )

    if not isinstance(payload, list):
        fail("Attendance list response is not a list")

    print(
        f"PASS: List attendance "
        f"({len(payload)} records returned)"
    )

    return payload


def get_attendance(
    access_token: str,
    attendance_id: str,
) -> dict:
    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}/api/v1/attendance/{attendance_id}",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "Get attendance",
        payload,
    )

    if not isinstance(payload, dict):
        fail("Get attendance returned an unexpected response")

    return payload


def update_attendance(
    access_token: str,
    attendance_id: str,
    *,
    status: str,
    reason: str,
) -> dict:
    status_code, payload = request_json(
        "PATCH",
        f"{BASE_URL}/api/v1/attendance/{attendance_id}",
        headers=backend_headers(access_token),
        body={
            "status": status,
            "correction_reason": reason,
        },
    )

    expect_status(
        status_code,
        200,
        "Correct attendance",
        payload,
    )

    if not isinstance(payload, dict):
        fail(
            "Attendance correction returned "
            "an unexpected response"
        )

    return payload


def get_corrections(
    access_token: str,
    attendance_id: str,
) -> list[dict]:
    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}/api/v1/attendance/{attendance_id}/corrections",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "Get attendance correction audit",
        payload,
    )

    if not isinstance(payload, list):
        fail("Correction audit response is not a list")

    return payload


def restore_attendance(
    access_token: str,
    attendance_id: str,
    original_status: str,
) -> None:
    restored = update_attendance(
        access_token,
        attendance_id,
        status=original_status,
        reason="Smoke test restoration",
    )

    if restored.get("status") != original_status:
        fail(
            "Attendance restoration failed: "
            f"expected {original_status}, "
            f"got {restored.get('status')}"
        )

    print("PASS: Attendance restored to original status")


def verify_noop_correction_rejected(
    access_token: str,
    attendance_id: str,
    current_status: str,
) -> None:
    status_code, payload = request_json(
        "PATCH",
        f"{BASE_URL}/api/v1/attendance/{attendance_id}",
        headers=backend_headers(access_token),
        body={
            "status": current_status,
            "correction_reason": "No-op correction smoke test",
        },
    )

    expect_status(
        status_code,
        400,
        "Reject no-op attendance correction",
        payload,
    )


def verify_invalid_status_rejected(
    access_token: str,
    attendance_id: str,
) -> None:
    status_code, payload = request_json(
        "PATCH",
        f"{BASE_URL}/api/v1/attendance/{attendance_id}",
        headers=backend_headers(access_token),
        body={
            "status": "INVALID_STATUS",
            "correction_reason": "Invalid status smoke test",
        },
    )

    expect_status(
        status_code,
        400,
        "Reject invalid attendance status",
        payload,
    )


def choose_existing_attendance(
    attendance_rows: list[dict],
    academic_period_id: str,
    student_id: str,
    section_id: str,
) -> dict:
    for row in attendance_rows:
        if (
            row.get("id")
            and str(row.get("academic_period_id"))
            == academic_period_id
            and str(row.get("student_id")) == student_id
            and str(row.get("section_id")) == section_id
            and row.get("attendance_date")
            and row.get("status")
        ):
            return row

    fail(
        "No existing attendance record was found for the "
        "student's academic period and section. "
        "Smoke test will not create test data."
    )

    raise RuntimeError("unreachable")


def main() -> None:
    print()
    print("Phase 3A.2 real Supabase Attendance smoke test")
    print(f"Backend: {BASE_URL}")
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

    active_student = choose_active_student(
        students,
        institution_ids,
    )

    student_id = str(active_student["id"])

    print(
        "PASS: Selected active student "
        f"(permanent_student_id="
        f"{active_student.get('permanent_student_id')}, "
        f"student_id={student_id})"
    )

    history_rows = get_student_academic_history(
        access_token,
        student_id,
    )

    student_history = choose_student_history(
        history_rows,
    )

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
        "PASS: Selected active academic history "
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

    print(
        "PASS: Matched academic period to student history "
        f"(id={academic_period_id}, "
        f"period_name={academic_period['period_name']}, "
        f"period_number={academic_period['period_number']})"
    )

    if str(
        academic_period["academic_year_id"]
    ) != academic_year_id:
        fail(
            "Academic period academic_year_id does not match "
            "student academic history"
        )

    if str(
        academic_period["program_id"]
    ) != program_id:
        fail(
            "Academic period program_id does not match "
            "student academic history"
        )

    if str(
        academic_period["semester_id"]
    ) != semester_id:
        fail(
            "Academic period semester_id does not match "
            "student academic history"
        )

    print(
        "PASS: Academic period context matches "
        "student academic history"
    )

    attendance_rows = list_attendance(
        access_token,
        student_id=student_id,
        section_id=section_id,
        academic_period_id=academic_period_id,
    )

    if not attendance_rows:
        fail(
            "No existing attendance records were found for "
            "the selected student, section and academic period. "
            "Smoke test will not create test data."
        )

    existing_row = choose_existing_attendance(
        attendance_rows,
        academic_period_id,
        student_id,
        section_id,
    )

    attendance_id = str(existing_row["id"])
    original_status = str(existing_row["status"])
    existing_subject_id = str(existing_row["subject_id"])

    print(
        "PASS: Discovered existing real attendance record "
        f"(id={attendance_id}, "
        f"student_id={student_id}, "
        f"subject_id={existing_subject_id}, "
        f"section_id={section_id}, "
        f"status={original_status}, "
        f"date={existing_row.get('attendance_date')})"
    )

    fetched = get_attendance(
        access_token,
        attendance_id,
    )

    if fetched.get("id") != attendance_id:
        fail(
            "Attendance GET returned a different "
            "attendance record"
        )

    print("PASS: Existing attendance record verified")

    verify_invalid_status_rejected(
        access_token,
        attendance_id,
    )

    verify_noop_correction_rejected(
        access_token,
        attendance_id,
        original_status,
    )

    alternate_status = (
        "ABSENT"
        if original_status != "ABSENT"
        else "PRESENT"
    )

    corrected = update_attendance(
        access_token,
        attendance_id,
        status=alternate_status,
        reason="Smoke test correction",
    )

    if corrected.get("status") != alternate_status:
        fail(
            "Attendance correction returned "
            f"unexpected status: {corrected.get('status')}"
        )

    corrections = get_corrections(
        access_token,
        attendance_id,
    )

    if not corrections:
        fail(
            "Attendance correction audit returned "
            "no records after correction"
        )

    matching_correction = None

    for correction in corrections:
        if (
            correction.get("old_status") == original_status
            and correction.get("new_status") == alternate_status
            and correction.get("reason")
            == "Smoke test correction"
        ):
            matching_correction = correction
            break

    if not matching_correction:
        fail(
            "Expected attendance correction was not found "
            "in the correction audit"
        )

    print(
        "PASS: Attendance correction audit contains "
        "the expected old/new status and reason"
    )

    verify_noop_correction_rejected(
        access_token,
        attendance_id,
        alternate_status,
    )

    restore_attendance(
        access_token,
        attendance_id,
        original_status,
    )

    restored = get_attendance(
        access_token,
        attendance_id,
    )

    if restored.get("status") != original_status:
        fail(
            "Final attendance verification failed: "
            f"expected {original_status}, "
            f"got {restored.get('status')}"
        )

    print("PASS: Final attendance status verified")

    print()
    print("==============================================")
    print("PASS: Phase 3A.2 real Supabase Attendance smoke test")
    print("==============================================")


if __name__ == "__main__":
    main()
import os
import sys
from uuid import UUID

import httpx


BASE_URL = os.getenv(
    "SMOKE_TEST_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.environ[
    "SUPABASE_PUBLISHABLE_KEY"
]
TEST_AUTH_EMAIL = os.environ["TEST_AUTH_EMAIL"]
TEST_AUTH_PASSWORD = os.environ["TEST_AUTH_PASSWORD"]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def expect(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    with httpx.Client(timeout=30.0) as client:
        # ---------------------------------------------------------
        # 1. Authenticate against Supabase
        # ---------------------------------------------------------
        login_response = client.post(
            f"{SUPABASE_URL}/auth/v1/token",
            params={"grant_type": "password"},
            headers={
                "apikey": SUPABASE_PUBLISHABLE_KEY,
                "Content-Type": "application/json",
            },
            json={
                "email": TEST_AUTH_EMAIL,
                "password": TEST_AUTH_PASSWORD,
            },
        )

        expect(
            login_response.status_code == 200,
            (
                "Supabase Auth login failed: "
                f"{login_response.status_code} "
                f"{login_response.text}"
            ),
        )
        print("PASS: Supabase Auth login")

        access_token = login_response.json().get(
            "access_token"
        )

        expect(
            bool(access_token),
            "Supabase access token was not returned",
        )
        print("PASS: Supabase access token returned")

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        # ---------------------------------------------------------
        # 2. Get academic years
        # ---------------------------------------------------------
        academic_year_response = client.get(
            f"{BASE_URL}/api/v1/academic-years",
            headers=headers,
        )

        expect(
            academic_year_response.status_code == 200,
            (
                "List academic years failed: "
                f"{academic_year_response.status_code} "
                f"{academic_year_response.text}"
            ),
        )
        print("PASS: List academic years")

        academic_years = academic_year_response.json()

        expect(
            len(academic_years) > 0,
            "No academic years returned",
        )
        print(
            "PASS: Academic years returned "
            f"({len(academic_years)} records)"
        )

        academic_year = next(
            (
                item
                for item in academic_years
                if item.get("is_current")
            ),
            academic_years[0],
        )

        academic_year_id = UUID(
            academic_year["id"]
        )

        # ---------------------------------------------------------
        # 3. Find a real academic context containing students
        #
        # Do not hard-code MCA, semester, section, etc.
        # Continue searching until the attendance-student API
        # actually returns at least one student.
        # ---------------------------------------------------------
        programs_response = client.get(
            f"{BASE_URL}/api/v1/programs",
            params={
                "academic_year_id": str(
                    academic_year_id
                )
            },
            headers=headers,
        )

        expect(
            programs_response.status_code == 200,
            (
                "List programs failed: "
                f"{programs_response.status_code} "
                f"{programs_response.text}"
            ),
        )
        print("PASS: List programs")

        programs = programs_response.json()

        expect(
            len(programs) > 0,
            "No programs returned",
        )
        print(
            "PASS: Programs returned "
            f"({len(programs)} records)"
        )

        selected_context = None

        for program in programs:
            program_id = UUID(program["id"])

            periods_response = client.get(
                f"{BASE_URL}/api/v1/academic-periods",
                params={
                    "academic_year_id": str(
                        academic_year_id
                    ),
                    "program_id": str(program_id),
                },
                headers=headers,
            )

            expect(
                periods_response.status_code == 200,
                (
                    "List academic periods failed for "
                    f"program {program_id}: "
                    f"{periods_response.status_code} "
                    f"{periods_response.text}"
                ),
            )

            periods = periods_response.json()

            for period in periods:
                if not period.get("is_active"):
                    continue

                if period.get("period_type") != "SEMESTER":
                    continue

                academic_period_id = UUID(
                    period["id"]
                )

                sections_response = client.get(
                    f"{BASE_URL}/api/v1/sections",
                    params={
                        "academic_period_id": str(
                            academic_period_id
                        )
                    },
                    headers=headers,
                )

                expect(
                    sections_response.status_code == 200,
                    (
                        "List sections failed for "
                        f"academic period "
                        f"{academic_period_id}: "
                        f"{sections_response.status_code} "
                        f"{sections_response.text}"
                    ),
                )

                sections = sections_response.json()

                for section in sections:
                    if not section.get("is_active"):
                        continue

                    section_id = UUID(section["id"])

                    students_response = client.get(
                        f"{BASE_URL}/api/v1/attendance/students",
                        params={
                            "academic_year_id": str(
                                academic_year_id
                            ),
                            "program_id": str(
                                program_id
                            ),
                            "academic_period_id": str(
                                academic_period_id
                            ),
                            "section_id": str(
                                section_id
                            ),
                        },
                        headers=headers,
                    )

                    expect(
                        students_response.status_code == 200,
                        (
                            "List attendance-context "
                            "students failed: "
                            f"{students_response.status_code} "
                            f"{students_response.text}"
                        ),
                    )

                    students = students_response.json()

                    print(
                        "INFO: Checked context "
                        f"program={program.get('name')} "
                        f"period={period.get('period_name')} "
                        f"section={section.get('name')} "
                        f"students={len(students)}"
                    )

                    if students:
                        selected_context = {
                            "program": program,
                            "period": period,
                            "section": section,
                            "students": students,
                        }
                        break

                if selected_context is not None:
                    break

            if selected_context is not None:
                break

        # ---------------------------------------------------------
        # 4. Ensure an actual student context was found
        # ---------------------------------------------------------
        expect(
            selected_context is not None,
            (
                "No active semester/section context "
                "with attendance students was found"
            ),
        )

        program = selected_context["program"]
        period = selected_context["period"]
        section = selected_context["section"]
        students = selected_context["students"]

        print(
            "PASS: Found academic context with students "
            f"(program={program['name']}, "
            f"period={period['period_name']}, "
            f"section={section['name']})"
        )

        print(
            "PASS: Attendance-context students returned "
            f"({len(students)} records)"
        )

        # ---------------------------------------------------------
        # 5. Validate every returned student
        # ---------------------------------------------------------
        required_fields = {
            "student_id",
            "permanent_student_id",
            "student_name",
            "roll_number",
            "student_status",
            "academic_history_id",
        }

        permanent_student_ids = set()

        for index, student in enumerate(students, start=1):
            missing_fields = required_fields.difference(
                student.keys()
            )

            expect(
                not missing_fields,
                (
                    f"Student #{index} is missing fields: "
                    f"{sorted(missing_fields)}"
                ),
            )

            expect(
                bool(student["student_id"]),
                f"Student #{index} has no student_id",
            )

            expect(
                bool(student["permanent_student_id"]),
                (
                    f"Student #{index} has no "
                    "permanent_student_id"
                ),
            )

            expect(
                bool(student["student_name"]),
                f"Student #{index} has no student_name",
            )

            expect(
                student["student_status"] == "active",
                (
                    f"Student #{index} is not active: "
                    f"{student['student_status']}"
                ),
            )

            UUID(student["student_id"])
            UUID(student["academic_history_id"])

            expect(
                student["permanent_student_id"]
                not in permanent_student_ids,
                (
                    "Duplicate permanent_student_id "
                    f"returned: "
                    f"{student['permanent_student_id']}"
                ),
            )

            permanent_student_ids.add(
                student["permanent_student_id"]
            )

        print(
            "PASS: All attendance-context student "
            "response fields validated"
        )

        # ---------------------------------------------------------
        # 6. Verify invalid section/context is rejected
        # ---------------------------------------------------------
        invalid_section_id = UUID(int=0)

        mismatch_response = client.get(
            f"{BASE_URL}/api/v1/attendance/students",
            params={
                "academic_year_id": str(
                    academic_year_id
                ),
                "program_id": program["id"],
                "academic_period_id": period["id"],
                "section_id": str(
                    invalid_section_id
                ),
            },
            headers=headers,
        )

        expect(
            mismatch_response.status_code == 400,
            (
                "Invalid section context was not rejected: "
                f"{mismatch_response.status_code} "
                f"{mismatch_response.text}"
            ),
        )

        print(
            "PASS: Invalid section context rejected"
        )

        print(
            "PASS: Phase 3A.3B real Supabase "
            "Attendance Student Context smoke test"
        )


if __name__ == "__main__":
    main()
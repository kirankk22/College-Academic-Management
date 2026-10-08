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


def get_list(
    access_token: str,
    path: str,
    operation: str,
) -> list[dict]:
    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}{path}",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        operation,
        payload,
    )

    if not isinstance(payload, list):
        fail(f"{operation}: response is not a list")

    return payload


def get_academic_years(
    access_token: str,
) -> list[dict]:
    rows = get_list(
        access_token,
        "/api/v1/academic-years",
        "List academic years",
    )

    if not rows:
        fail("No academic years were returned")

    print(
        f"PASS: Academic years returned "
        f"({len(rows)} records)"
    )

    return rows


def get_programs(
    access_token: str,
    academic_year_id: str,
) -> list[dict]:
    rows = get_list(
        access_token,
        f"/api/v1/programs?academic_year_id={academic_year_id}",
        "List programs for academic year",
    )

    if not rows:
        fail(
            "No programs were returned for the selected "
            "academic year"
        )

    print(
        f"PASS: Programs returned for academic year "
        f"({len(rows)} records)"
    )

    return rows


def get_academic_periods(
    access_token: str,
) -> list[dict]:
    rows = get_list(
        access_token,
        "/api/v1/academic-periods",
        "List academic periods",
    )

    if not rows:
        fail("No academic periods were returned")

    print(
        f"PASS: Academic periods returned "
        f"({len(rows)} records)"
    )

    return rows


def get_sections(
    access_token: str,
    academic_period_id: str,
) -> list[dict]:
    rows = get_list(
        access_token,
        (
            "/api/v1/sections"
            f"?academic_period_id={academic_period_id}"
        ),
        "List sections for academic period",
    )

    return rows


def get_subjects(
    access_token: str,
    academic_period_id: str,
) -> list[dict]:
    rows = get_list(
        access_token,
        (
            "/api/v1/subjects"
            f"?academic_period_id={academic_period_id}"
        ),
        "List subjects for academic period",
    )

    return rows


def choose_current_academic_year(
    academic_years: list[dict],
) -> dict:
    for academic_year in academic_years:
        if (
            academic_year.get("id")
            and academic_year.get("is_current") is True
        ):
            return academic_year

    fail("No current academic year was returned")
    raise RuntimeError("unreachable")


def get_current_year_program_ids(
    programs: list[dict],
) -> set[str]:
    program_ids = {
        str(program["id"])
        for program in programs
        if program.get("id")
    }

    if not program_ids:
        fail(
            "No valid program IDs were returned for the "
            "current academic year"
        )

    return program_ids


def choose_period_with_subjects(
    access_token: str,
    academic_periods: list[dict],
    program_ids: set[str],
    academic_year_id: str,
) -> tuple[dict, list[dict]]:
    candidate_periods = [
        period
        for period in academic_periods
        if (
            period.get("id")
            and period.get("is_active") is True
            and period.get("period_type") == "SEMESTER"
            and period.get("semester_id")
            and str(period.get("academic_year_id"))
            == academic_year_id
            and str(period.get("program_id")) in program_ids
        )
    ]

    candidate_periods.sort(
        key=lambda period: (
            str(period.get("program_id")),
            int(period.get("period_number", 0)),
        )
    )

    if not candidate_periods:
        fail(
            "No active SEMESTER academic periods were found "
            "for the current academic year"
        )

    for period in candidate_periods:
        academic_period_id = str(period["id"])

        subjects = get_subjects(
            access_token,
            academic_period_id,
        )

        if subjects:
            return period, subjects

        print(
            "INFO: Academic period has no subjects; "
            f"trying next period "
            f"(period_name={period.get('period_name')}, "
            f"program_id={period.get('program_id')})"
        )

    fail(
        "No active semester academic period for the current "
        "academic year has any subjects"
    )

    raise RuntimeError("unreachable")


def verify_program_context(
    programs: list[dict],
    academic_year_id: str,
    academic_periods: list[dict],
) -> None:
    program_ids = get_current_year_program_ids(programs)

    for period in academic_periods:
        if str(period.get("academic_year_id")) != academic_year_id:
            continue

        if not period.get("is_active"):
            continue

        if str(period.get("program_id")) not in program_ids:
            fail(
                "Academic period returned for the selected "
                "academic year belongs to a program outside "
                "the returned program list"
            )

    print(
        "PASS: Program and academic-year context is consistent"
    )


def verify_section_context(
    sections: list[dict],
    academic_period_id: str,
) -> None:
    if not sections:
        fail(
            "No sections were returned for the selected "
            "academic period"
        )

    for section in sections:
        if str(section.get("academic_period_id")) != academic_period_id:
            fail(
                "Section returned for academic period has "
                "a different academic_period_id"
            )

    print(
        f"PASS: Sections returned for selected academic period "
        f"({len(sections)} records)"
    )

    print(
        "PASS: Section academic-period context is consistent"
    )


def verify_subject_context(
    subjects: list[dict],
    academic_period: dict,
) -> None:
    semester_id = academic_period.get("semester_id")

    if not semester_id:
        fail(
            "Selected semester academic period does not "
            "contain semester_id"
        )

    if not subjects:
        fail(
            "Selected academic period returned no subjects"
        )

    for subject in subjects:
        if str(subject.get("semester_id")) != str(semester_id):
            fail(
                "Subject returned for academic period belongs "
                "to a different semester"
            )

    print(
        f"PASS: Subjects returned for selected academic period "
        f"({len(subjects)} records)"
    )

    print(
        "PASS: Subject academic-period context is consistent"
    )


def main() -> None:
    print()
    print(
        "Phase 3A.3A real Supabase Academic Catalog smoke test"
    )
    print(f"Backend: {BASE_URL}")
    print()

    access_token = authenticate()

    academic_years = get_academic_years(
        access_token
    )

    current_academic_year = choose_current_academic_year(
        academic_years
    )

    academic_year_id = str(
        current_academic_year["id"]
    )

    print(
        "PASS: Selected current academic year "
        f"(name={current_academic_year.get('name')}, "
        f"id={academic_year_id})"
    )

    programs = get_programs(
        access_token,
        academic_year_id,
    )

    academic_periods = get_academic_periods(
        access_token
    )

    verify_program_context(
        programs,
        academic_year_id,
        academic_periods,
    )

    program_ids = get_current_year_program_ids(
        programs
    )

    academic_period, subjects = choose_period_with_subjects(
        access_token,
        academic_periods,
        program_ids,
        academic_year_id,
    )

    program_id = str(
        academic_period["program_id"]
    )

    selected_program = next(
        (
            program
            for program in programs
            if str(program.get("id")) == program_id
        ),
        None,
    )

    if selected_program is None:
        fail(
            "Selected academic period references a program "
            "that was not returned for the current academic year"
        )

    print(
        "PASS: Selected program "
        f"(name={selected_program.get('name')}, "
        f"code={selected_program.get('code')}, "
        f"id={program_id})"
    )

    academic_period_id = str(
        academic_period["id"]
    )

    print(
        "PASS: Selected academic period "
        f"(name={academic_period.get('period_name')}, "
        f"type={academic_period.get('period_type')}, "
        f"number={academic_period.get('period_number')}, "
        f"id={academic_period_id})"
    )

    sections = get_sections(
        access_token,
        academic_period_id,
    )

    verify_section_context(
        sections,
        academic_period_id,
    )

    verify_subject_context(
        subjects,
        academic_period,
    )

    print()
    print("==============================================")
    print(
        "PASS: Phase 3A.3A real Supabase "
        "Academic Catalog smoke test"
    )
    print("==============================================")


if __name__ == "__main__":
    main()
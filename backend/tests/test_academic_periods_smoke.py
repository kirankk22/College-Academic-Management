import json
import os
import sys
import urllib.error
import urllib.request
from uuid import UUID


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
        fail("List academic periods returned a non-list response")

    if not payload:
        fail("No academic periods were returned from Supabase")

    print(
        f"PASS: List academic periods "
        f"({len(payload)} records returned)"
    )

    return payload


def choose_real_period(periods: list[dict]) -> dict:
    required_fields = {
        "id",
        "academic_year_id",
        "program_id",
        "period_type",
        "period_number",
        "period_name",
        "is_active",
    }

    for period in periods:
        if required_fields.issubset(period.keys()):
            return period

    fail(
        "Could not find a usable academic period "
        "from the real Supabase response"
    )

    raise RuntimeError("unreachable")


def get_period(
    access_token: str,
    academic_period_id: UUID,
) -> dict:
    status_code, payload = request_json(
        "GET",
        f"{BASE_URL}/api/v1/academic-periods/{academic_period_id}",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "Get academic period",
        payload,
    )

    if not isinstance(payload, dict):
        fail("Get academic period returned an unexpected response")

    return payload


def update_period(
    access_token: str,
    academic_period_id: UUID,
    period_name: str,
    is_active: bool | None = None,
) -> dict:
    body = {
        "period_name": period_name,
    }

    if is_active is not None:
        body["is_active"] = is_active

    status_code, payload = request_json(
        "PATCH",
        f"{BASE_URL}/api/v1/academic-periods/{academic_period_id}",
        headers=backend_headers(access_token),
        body=body,
    )

    expect_status(
        status_code,
        200,
        "Update academic period",
        payload,
    )

    if not isinstance(payload, dict):
        fail("Update academic period returned an unexpected response")

    return payload


def deactivate_period(
    access_token: str,
    academic_period_id: UUID,
) -> dict:
    status_code, payload = request_json(
        "DELETE",
        f"{BASE_URL}/api/v1/academic-periods/{academic_period_id}",
        headers=backend_headers(access_token),
    )

    expect_status(
        status_code,
        200,
        "Deactivate academic period",
        payload,
    )

    if not isinstance(payload, dict):
        fail(
            "Deactivate academic period returned "
            "an unexpected response"
        )

    return payload


def verify_period_inactive(
    access_token: str,
    academic_period_id: UUID,
) -> None:
    period = get_period(
        access_token,
        academic_period_id,
    )

    if period.get("is_active") is not False:
        fail(
            "Verify deactivation: expected is_active=false, "
            f"got {period.get('is_active')}"
        )

    print("PASS: Verify logical deactivation")


def restore_period(
    access_token: str,
    academic_period_id: UUID,
    original_name: str,
) -> None:
    restored = update_period(
        access_token,
        academic_period_id,
        original_name,
        is_active=True,
    )

    if restored.get("is_active") is not True:
        fail(
            "Restore academic period: "
            f"expected is_active=true, got "
            f"{restored.get('is_active')}"
        )

    print("PASS: Restore academic period")


def verify_create_business_rule(
    access_token: str,
    real_period: dict,
) -> None:
    """
    Validate the real Supabase CREATE path without modifying data.

    We intentionally use the real semester configuration but an invalid
    period number. The production service must reject it because a
    SEMESTER academic period must match the semester_number.
    """

    if real_period.get("period_type") != "SEMESTER":
        print(
            "SKIP: CREATE validation requires an existing "
            "SEMESTER academic period"
        )
        return

    semester_id = real_period.get("semester_id")

    if not semester_id:
        fail(
            "Real SEMESTER academic period does not contain "
            "semester_id"
        )

    actual_period_number = real_period.get("period_number")

    if not isinstance(actual_period_number, int):
        fail(
            "Real academic period has an invalid "
            "period_number"
        )

    invalid_period_number = actual_period_number + 100

    payload = {
        "academic_year_id": real_period["academic_year_id"],
        "program_id": real_period["program_id"],
        "period_type": "SEMESTER",
        "period_number": invalid_period_number,
        "semester_id": semester_id,
        "period_name": "Smoke Test Invalid Period",
        "semester_cycle": "ODD"
        if actual_period_number % 2 == 1
        else "EVEN",
        "is_active": True,
    }

    status_code, response = request_json(
        "POST",
        f"{BASE_URL}/api/v1/academic-periods",
        headers=backend_headers(access_token),
        body=payload,
    )

    expect_status(
        status_code,
        400,
        "Reject invalid semester period creation",
        response,
    )

    if not isinstance(response, dict):
        fail(
            "Invalid CREATE validation returned "
            "an unexpected response"
        )

    detail = str(response.get("detail", ""))

    if "Period number must match the semester number" not in detail:
        fail(
            "Invalid CREATE validation returned an unexpected "
            f"error: {detail}"
        )

    print(
        "PASS: CREATE business rule validated against "
        "real Supabase data"
    )


def main() -> None:
    print()
    print("Phase 2C.3B real Supabase smoke test")
    print(f"Backend: {BASE_URL}")
    print()

    access_token = authenticate()

    periods = get_real_academic_periods(access_token)

    real_period = choose_real_period(periods)

    academic_period_id = UUID(str(real_period["id"]))

    print(
        "PASS: Discovered real academic period "
        f"(id={academic_period_id}, "
        f"program_id={real_period['program_id']}, "
        f"academic_year_id={real_period['academic_year_id']}, "
        f"period_number={real_period['period_number']})"
    )

    fetched_period = get_period(
        access_token,
        academic_period_id,
    )

    if fetched_period.get("id") != str(academic_period_id):
        fail(
            "Get academic period returned a different "
            "academic period"
        )

    original_name = str(real_period["period_name"])

    smoke_name = (
        f"{original_name} - Smoke Test"
    )

    updated_period = update_period(
        access_token,
        academic_period_id,
        smoke_name,
    )

    if updated_period.get("period_name") != smoke_name:
        fail(
            "Update academic period: "
            f"expected period_name={smoke_name!r}, "
            f"got {updated_period.get('period_name')!r}"
        )

    print("PASS: Update response contains new period name")

    verify_updated = get_period(
        access_token,
        academic_period_id,
    )

    if verify_updated.get("period_name") != smoke_name:
        fail(
            "Verify update: database did not retain "
            "the updated period name"
        )

    print("PASS: Verify update persisted")

    deactivated_period = deactivate_period(
        access_token,
        academic_period_id,
    )

    if deactivated_period.get("is_active") is not False:
        fail(
            "Deactivate academic period: expected "
            "is_active=false"
        )

    verify_period_inactive(
        access_token,
        academic_period_id,
    )

    restore_period(
        access_token,
        academic_period_id,
        original_name,
    )

    restored_period = get_period(
        access_token,
        academic_period_id,
    )

    if restored_period.get("period_name") != original_name:
        fail(
            "Restore verification: original period name "
            "was not restored"
        )

    if restored_period.get("is_active") is not True:
        fail(
            "Restore verification: academic period "
            "was not reactivated"
        )

    print("PASS: Verify academic period restored")

    verify_create_business_rule(
        access_token,
        real_period,
    )

    print()
    print("==============================================")
    print("PASS: Phase 2C.3B real Supabase smoke test")
    print("==============================================")


if __name__ == "__main__":
    main()

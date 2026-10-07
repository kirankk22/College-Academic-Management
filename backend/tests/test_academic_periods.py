from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.authenticated_user import AuthenticatedUser


INSTITUTION_ID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_INSTITUTION_ID = UUID("99999999-9999-4999-8999-999999999999")

ORGANIZATION_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

ACADEMIC_YEAR_ID = UUID("33333333-3333-4333-8333-333333333333")
OTHER_ACADEMIC_YEAR_ID = UUID("88888888-8888-4888-8888-888888888888")

PROGRAM_ID = UUID("22222222-2222-4222-8222-222222222222")
ANNUAL_PROGRAM_ID = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")

SEMESTER_ID = UUID("44444444-4444-4444-8444-444444444444")
OTHER_PROGRAM_SEMESTER_ID = UUID("55555555-5555-4555-8555-555555555555")

USER_ID = UUID("66666666-6666-4666-8666-666666666666")


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        if not self.rows:
            return None

        row = self.rows[0]

        if isinstance(row, dict):
            return next(iter(row.values()))

        return row


class FakeAcademicPeriodDatabase:
    def __init__(self):
        self.academic_years = {
            ACADEMIC_YEAR_ID: {
                "id": ACADEMIC_YEAR_ID,
                "institution_id": INSTITUTION_ID,
                "name": "2026-27",
            },
            OTHER_ACADEMIC_YEAR_ID: {
                "id": OTHER_ACADEMIC_YEAR_ID,
                "institution_id": OTHER_INSTITUTION_ID,
                "name": "2026-27",
            },
        }

        self.programs = {
            PROGRAM_ID: {
                "id": PROGRAM_ID,
                "institution_id": INSTITUTION_ID,
                "academic_structure_type": "SEMESTER",
                "duration_units": 4,
            },
            ANNUAL_PROGRAM_ID: {
                "id": ANNUAL_PROGRAM_ID,
                "institution_id": INSTITUTION_ID,
                "academic_structure_type": "ANNUAL",
                "duration_units": 2,
            },
            OTHER_PROGRAM_SEMESTER_ID: {
                "id": OTHER_PROGRAM_SEMESTER_ID,
                "institution_id": OTHER_INSTITUTION_ID,
                "academic_structure_type": "SEMESTER",
                "duration_units": 4,
            },
        }

        self.departments = {
            UUID("77777777-7777-4777-8777-777777777777"): {
                "id": UUID("77777777-7777-4777-8777-777777777777"),
                "institution_id": INSTITUTION_ID,
            }
        }

        self.semesters = {
            SEMESTER_ID: {
                "id": SEMESTER_ID,
                "program_id": PROGRAM_ID,
                "semester_number": 1,
            },
            OTHER_PROGRAM_SEMESTER_ID: {
                "id": OTHER_PROGRAM_SEMESTER_ID,
                "program_id": OTHER_PROGRAM_SEMESTER_ID,
                "semester_number": 1,
            },
        }

        self.periods = {}

    def _institution_for_program(self, program_id):
        program = self.programs.get(program_id)

        if program is None:
            return None

        return program["institution_id"]

    def _period_row(self, period):
        return {
            "id": period["id"],
            "academic_year_id": period["academic_year_id"],
            "program_id": period["program_id"],
            "period_type": period["period_type"],
            "period_number": period["period_number"],
            "semester_id": period["semester_id"],
            "period_name": period["period_name"],
            "semester_cycle": period["semester_cycle"],
            "is_active": period["is_active"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

    def execute(self, query, params=None):
        params = params or {}
        sql = str(query).lower().strip()

        # ---------------------------------------------------------
        # Get one academic period
        # ---------------------------------------------------------
        if (
            "from public.academic_periods ap" in sql
            and "where ap.id = :academic_period_id" in sql
        ):
            period = self.periods.get(params["academic_period_id"])

            if period is None:
                return FakeResult()

            academic_year = self.academic_years.get(
                period["academic_year_id"]
            )

            program_institution = self._institution_for_program(
                period["program_id"]
            )

            if (
                academic_year is None
                or academic_year["institution_id"]
                != params["institution_id"]
                or program_institution != params["institution_id"]
            ):
                return FakeResult()

            return FakeResult([self._period_row(period)])

        # ---------------------------------------------------------
        # List academic periods
        # ---------------------------------------------------------
        if (
            "from public.academic_periods ap" in sql
            and "order by" in sql
            and "ap.id = :academic_period_id" not in sql
        ):
            rows = []

            for period in self.periods.values():
                academic_year = self.academic_years.get(
                    period["academic_year_id"]
                )

                program_institution = self._institution_for_program(
                    period["program_id"]
                )

                if (
                    academic_year is None
                    or academic_year["institution_id"]
                    != params["institution_id"]
                    or program_institution != params["institution_id"]
                ):
                    continue

                if (
                    "academic_year_id" in params
                    and period["academic_year_id"]
                    != params["academic_year_id"]
                ):
                    continue

                if (
                    "program_id" in params
                    and period["program_id"] != params["program_id"]
                ):
                    continue

                rows.append(self._period_row(period))

            rows.sort(
                key=lambda row: (
                    str(row["program_id"]),
                    row["period_number"],
                )
            )

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Validate academic year + program institution context
        # Also return academic structure type.
        # ---------------------------------------------------------
        if (
            "from public.academic_years ay" in sql
            and "join public.programs p" in sql
            and "join public.departments d" in sql
            and "ay.id = :academic_year_id" in sql
        ):
            academic_year = self.academic_years.get(
                params["academic_year_id"]
            )

            program = self.programs.get(params["program_id"])

            if academic_year is None or program is None:
                return FakeResult()

            if (
                academic_year["institution_id"]
                != params["institution_id"]
                or program["institution_id"]
                != params["institution_id"]
            ):
                return FakeResult()

            return FakeResult(
                [
                    {
                        "academic_year_id": academic_year["id"],
                        "academic_year_institution_id": (
                            academic_year["institution_id"]
                        ),
                        "program_id": program["id"],
                        "program_institution_id": (
                            program["institution_id"]
                        ),
                        "academic_structure_type": program[
                            "academic_structure_type"
                        ],
                    }
                ]
            )

        # ---------------------------------------------------------
        # Validate semester + program
        #
        # Important:
        # Match the exact SQL generated by the service:
        #
        # from public.semesters
        # where id = :semester_id
        #   and program_id = :program_id
        # ---------------------------------------------------------
        if (
            "from public.semesters" in sql
            and "semester_number" in sql
            and "where id = :semester_id" in sql
            and "and program_id = :program_id" in sql
        ):
            semester = self.semesters.get(params["semester_id"])

            if (
                semester is None
                or semester["program_id"] != params["program_id"]
            ):
                return FakeResult()

            return FakeResult(
                [
                    {
                        "id": semester["id"],
                        "program_id": semester["program_id"],
                        "semester_number": semester["semester_number"],
                    }
                ]
            )

        # ---------------------------------------------------------
        # Check duplicate academic period
        # ---------------------------------------------------------
        if (
            "from public.academic_periods" in sql
            and "academic_year_id = :academic_year_id" in sql
            and "program_id = :program_id" in sql
            and "period_number = :period_number" in sql
        ):
            for period in self.periods.values():
                if (
                    period["academic_year_id"]
                    == params["academic_year_id"]
                    and period["program_id"]
                    == params["program_id"]
                    and period["period_number"]
                    == params["period_number"]
                ):
                    return FakeResult([{"id": period["id"]}])

            return FakeResult()

        # ---------------------------------------------------------
        # Insert academic period
        # ---------------------------------------------------------
        if "insert into public.academic_periods" in sql:
            period_id = uuid4()

            period = {
                "id": period_id,
                "academic_year_id": params["academic_year_id"],
                "program_id": params["program_id"],
                "period_type": params["period_type"],
                "period_number": params["period_number"],
                "semester_id": params["semester_id"],
                "period_name": params["period_name"],
                "semester_cycle": params["semester_cycle"],
                "is_active": params["is_active"],
            }

            self.periods[period_id] = period

            return FakeResult([self._period_row(period)])

        # ---------------------------------------------------------
        # Update academic period
        # ---------------------------------------------------------
        if "update public.academic_periods ap" in sql:
            period_id = params["academic_period_id"]

            period = self.periods.get(period_id)

            if period is None:
                return FakeResult()

            academic_year = self.academic_years.get(
                period["academic_year_id"]
            )

            program_institution = self._institution_for_program(
                period["program_id"]
            )

            if (
                academic_year is None
                or academic_year["institution_id"]
                != params["institution_id"]
                or program_institution != params["institution_id"]
            ):
                return FakeResult()

            if "period_name" in params:
                period["period_name"] = params["period_name"]

            if "is_active" in params:
                period["is_active"] = params["is_active"]

            return FakeResult([self._period_row(period)])

        # ---------------------------------------------------------
        # Logical deactivation
        # ---------------------------------------------------------
        if (
            "update public.academic_periods" in sql
            and "set is_active = false" in sql
        ):
            period = self.periods.get(params["academic_period_id"])

            if period is None:
                return FakeResult()

            period["is_active"] = False

            return FakeResult([self._period_row(period)])

        raise AssertionError(
            f"Unhandled SQL in fake database:\n{sql}"
        )

    def commit(self):
        return None

    def rollback(self):
        return None


def management_user(
    role="principal",
    institution_id=INSTITUTION_ID,
):
    return AuthenticatedUser(
        user_id=USER_ID,
        email="principal.demo@college-demo.local",
        role=role,
        organization_id=ORGANIZATION_ID,
        institution_id=institution_id,
        department_id=None,
        is_active=True,
    )


def setup_overrides(
    role="principal",
    institution_id=INSTITUTION_ID,
):
    database = FakeAcademicPeriodDatabase()

    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_current_user] = lambda: management_user(
        role=role,
        institution_id=institution_id,
    )

    return database


@pytest.fixture
def client():
    return TestClient(app)


def semester_payload(
    *,
    academic_year_id=ACADEMIC_YEAR_ID,
    program_id=PROGRAM_ID,
    semester_id=SEMESTER_ID,
    period_number=1,
    period_name="Semester 1",
    semester_cycle="ODD",
):
    return {
        "academic_year_id": str(academic_year_id),
        "program_id": str(program_id),
        "period_type": "SEMESTER",
        "period_number": period_number,
        "semester_id": str(semester_id),
        "period_name": period_name,
        "semester_cycle": semester_cycle,
        "is_active": True,
    }


def annual_payload(
    *,
    academic_year_id=ACADEMIC_YEAR_ID,
    program_id=ANNUAL_PROGRAM_ID,
    period_number=1,
    period_name="Year 1",
):
    return {
        "academic_year_id": str(academic_year_id),
        "program_id": str(program_id),
        "period_type": "ANNUAL_YEAR",
        "period_number": period_number,
        "semester_id": None,
        "period_name": period_name,
        "semester_cycle": None,
        "is_active": True,
    }


# ================================================================
# LIST
# ================================================================


def test_management_user_can_list_academic_periods():
    database = setup_overrides()

    try:
        period_id = uuid4()

        database.periods[period_id] = {
            "id": period_id,
            "academic_year_id": ACADEMIC_YEAR_ID,
            "program_id": PROGRAM_ID,
            "period_type": "SEMESTER",
            "period_number": 1,
            "semester_id": SEMESTER_ID,
            "period_name": "Semester 1",
            "semester_cycle": "ODD",
            "is_active": True,
        }

        response = TestClient(app).get(
            "/api/v1/academic-periods"
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert body[0]["period_name"] == "Semester 1"
        assert body[0]["period_type"] == "SEMESTER"

    finally:
        app.dependency_overrides.clear()


# ================================================================
# CREATE — SEMESTER
# ================================================================


def test_management_user_can_create_semester_period():
    setup_overrides()

    try:
        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=semester_payload(),
        )

        assert response.status_code == 201

        body = response.json()

        assert body["period_type"] == "SEMESTER"
        assert body["period_number"] == 1
        assert body["semester_id"] == str(SEMESTER_ID)
        assert body["semester_cycle"] == "ODD"

    finally:
        app.dependency_overrides.clear()


def test_duplicate_period_is_rejected():
    setup_overrides()

    try:
        first = TestClient(app).post(
            "/api/v1/academic-periods",
            json=semester_payload(),
        )

        assert first.status_code == 201

        second = TestClient(app).post(
            "/api/v1/academic-periods",
            json=semester_payload(),
        )

        assert second.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_semester_must_belong_to_program():
    setup_overrides()

    try:
        payload = semester_payload(
            semester_id=OTHER_PROGRAM_SEMESTER_ID,
        )

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_period_number_must_match_semester_number():
    setup_overrides()

    try:
        payload = semester_payload(
            period_number=2,
        )

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_semester_period_requires_semester_id():
    setup_overrides()

    try:
        payload = semester_payload(
            semester_id=SEMESTER_ID,
        )
        payload["semester_id"] = None

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_semester_period_requires_valid_cycle():
    setup_overrides()

    try:
        payload = semester_payload(
            semester_cycle="INVALID",
        )

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


# ================================================================
# CREATE — ANNUAL
# ================================================================


def test_management_user_can_create_annual_period():
    setup_overrides()

    try:
        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=annual_payload(),
        )

        assert response.status_code == 201

        body = response.json()

        assert body["period_type"] == "ANNUAL_YEAR"
        assert body["period_number"] == 1
        assert body["semester_id"] is None
        assert body["semester_cycle"] is None

    finally:
        app.dependency_overrides.clear()


def test_annual_period_cannot_have_semester():
    setup_overrides()

    try:
        payload = annual_payload()
        payload["semester_id"] = str(SEMESTER_ID)

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_annual_period_cannot_have_semester_cycle():
    setup_overrides()

    try:
        payload = annual_payload()
        payload["semester_cycle"] = "ODD"

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_semester_period_cannot_be_created_for_annual_program():
    setup_overrides()

    try:
        payload = semester_payload(
            program_id=ANNUAL_PROGRAM_ID,
        )

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_annual_period_cannot_be_created_for_semester_program():
    setup_overrides()

    try:
        payload = annual_payload(
            program_id=PROGRAM_ID,
        )

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


# ================================================================
# TENANT / AUTHORIZATION
# ================================================================


def test_user_cannot_choose_another_institution():
    setup_overrides()

    try:
        payload = semester_payload(
            academic_year_id=OTHER_ACADEMIC_YEAR_ID,
            program_id=OTHER_PROGRAM_SEMESTER_ID,
            semester_id=OTHER_PROGRAM_SEMESTER_ID,
        )

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_user_cannot_use_another_institution_program():
    setup_overrides()

    try:
        payload = semester_payload(
            program_id=OTHER_PROGRAM_SEMESTER_ID,
            semester_id=OTHER_PROGRAM_SEMESTER_ID,
        )

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_student_role_cannot_create_academic_period():
    setup_overrides(role="student")

    try:
        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=semester_payload(),
        )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()


def test_client_cannot_override_institution_scope():
    setup_overrides()

    try:
        payload = semester_payload()

        payload["institution_id"] = str(OTHER_INSTITUTION_ID)

        response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=payload,
        )

        assert response.status_code == 201

        body = response.json()

        assert body["program_id"] == str(PROGRAM_ID)

    finally:
        app.dependency_overrides.clear()


# ================================================================
# GET
# ================================================================


def test_management_user_can_get_academic_period():
    setup_overrides()

    try:
        create_response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=semester_payload(),
        )

        assert create_response.status_code == 201

        period_id = create_response.json()["id"]

        response = TestClient(app).get(
            f"/api/v1/academic-periods/{period_id}"
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == period_id
        assert body["period_name"] == "Semester 1"

    finally:
        app.dependency_overrides.clear()


def test_user_cannot_get_period_from_another_institution():
    database = setup_overrides()

    try:
        period_id = uuid4()

        database.periods[period_id] = {
            "id": period_id,
            "academic_year_id": OTHER_ACADEMIC_YEAR_ID,
            "program_id": OTHER_PROGRAM_SEMESTER_ID,
            "period_type": "SEMESTER",
            "period_number": 1,
            "semester_id": OTHER_PROGRAM_SEMESTER_ID,
            "period_name": "Other Institution Semester 1",
            "semester_cycle": "ODD",
            "is_active": True,
        }

        response = TestClient(app).get(
            f"/api/v1/academic-periods/{period_id}"
        )

        assert response.status_code == 404

    finally:
        app.dependency_overrides.clear()


# ================================================================
# UPDATE
# ================================================================


def test_management_user_can_update_period_name():
    setup_overrides()

    try:
        create_response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=semester_payload(),
        )

        assert create_response.status_code == 201

        period_id = create_response.json()["id"]

        response = TestClient(app).patch(
            f"/api/v1/academic-periods/{period_id}",
            json={
                "period_name": "Semester 1 Updated",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == period_id
        assert body["period_name"] == "Semester 1 Updated"

    finally:
        app.dependency_overrides.clear()


# ================================================================
# LOGICAL DELETE
# ================================================================


def test_delete_logically_deactivates_period():
    setup_overrides()

    try:
        create_response = TestClient(app).post(
            "/api/v1/academic-periods",
            json=semester_payload(),
        )

        assert create_response.status_code == 201

        period_id = create_response.json()["id"]

        response = TestClient(app).delete(
            f"/api/v1/academic-periods/{period_id}"
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == period_id
        assert body["is_active"] is False

    finally:
        app.dependency_overrides.clear()
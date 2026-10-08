from datetime import date
from uuid import UUID

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
OTHER_PROGRAM_ID = UUID("99999999-8888-4777-8666-555555555555")
ANNUAL_PROGRAM_ID = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")

SEMESTER_ID = UUID("44444444-4444-4444-8444-444444444444")
OTHER_SEMESTER_ID = UUID("55555555-5555-4555-8555-555555555555")

ACADEMIC_PERIOD_ID = UUID("aaaaaaaa-1111-4222-8333-444444444444")
OTHER_ACADEMIC_PERIOD_ID = UUID("bbbbbbbb-1111-4222-8333-444444444444")
ANNUAL_ACADEMIC_PERIOD_ID = UUID("cccccccc-1111-4222-8333-444444444444")

SECTION_ID = UUID("66666666-6666-4666-8666-666666666666")
OTHER_SECTION_ID = UUID("77777777-6666-4666-8666-666666666666")

SUBJECT_ID = UUID("aaaaaaaa-2222-4333-8444-555555555555")
OTHER_SUBJECT_ID = UUID("bbbbbbbb-2222-4333-8444-555555555555")

USER_ID = UUID("66666666-6666-4666-8666-666666666666")


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeAcademicCatalogDatabase:
    def __init__(self):
        self.academic_years = [
            {
                "id": ACADEMIC_YEAR_ID,
                "institution_id": INSTITUTION_ID,
                "name": "2026-27",
                "start_date": date(2026, 6, 1),
                "end_date": date(2027, 5, 31),
                "is_current": True,
            },
            {
                "id": OTHER_ACADEMIC_YEAR_ID,
                "institution_id": OTHER_INSTITUTION_ID,
                "name": "2026-27",
                "start_date": date(2026, 6, 1),
                "end_date": date(2027, 5, 31),
                "is_current": True,
            },
        ]

        self.programs = [
            {
                "id": PROGRAM_ID,
                "department_id": UUID(
                    "77777777-7777-4777-8777-777777777777"
                ),
                "institution_id": INSTITUTION_ID,
                "name": "MCA",
                "code": "MCA",
                "academic_structure_type": "SEMESTER",
                "duration_units": 4,
                "is_active": True,
            },
            {
                "id": ANNUAL_PROGRAM_ID,
                "department_id": UUID(
                    "77777777-7777-4777-8777-777777777777"
                ),
                "institution_id": INSTITUTION_ID,
                "name": "Annual Program",
                "code": "ANNUAL",
                "academic_structure_type": "ANNUAL",
                "duration_units": 2,
                "is_active": True,
            },
            {
                "id": OTHER_PROGRAM_ID,
                "department_id": UUID(
                    "88888888-8888-4888-8888-888888888888"
                ),
                "institution_id": OTHER_INSTITUTION_ID,
                "name": "Other MCA",
                "code": "MCA-OTHER",
                "academic_structure_type": "SEMESTER",
                "duration_units": 4,
                "is_active": True,
            },
        ]

        self.semesters = [
            {
                "id": SEMESTER_ID,
                "program_id": PROGRAM_ID,
                "semester_number": 1,
            },
            {
                "id": OTHER_SEMESTER_ID,
                "program_id": OTHER_PROGRAM_ID,
                "semester_number": 1,
            },
        ]

        self.periods = [
            {
                "id": ACADEMIC_PERIOD_ID,
                "academic_year_id": ACADEMIC_YEAR_ID,
                "program_id": PROGRAM_ID,
                "period_type": "SEMESTER",
                "period_number": 1,
                "semester_id": SEMESTER_ID,
                "period_name": "Semester 1",
                "semester_cycle": "ODD",
                "is_active": True,
            },
            {
                "id": OTHER_ACADEMIC_PERIOD_ID,
                "academic_year_id": OTHER_ACADEMIC_YEAR_ID,
                "program_id": OTHER_PROGRAM_ID,
                "period_type": "SEMESTER",
                "period_number": 1,
                "semester_id": OTHER_SEMESTER_ID,
                "period_name": "Semester 1",
                "semester_cycle": "ODD",
                "is_active": True,
            },
            {
                "id": ANNUAL_ACADEMIC_PERIOD_ID,
                "academic_year_id": ACADEMIC_YEAR_ID,
                "program_id": ANNUAL_PROGRAM_ID,
                "period_type": "ANNUAL_YEAR",
                "period_number": 1,
                "semester_id": None,
                "period_name": "Year 1",
                "semester_cycle": None,
                "is_active": True,
            },
        ]

        self.sections = [
            {
                "id": SECTION_ID,
                "academic_period_id": ACADEMIC_PERIOD_ID,
                "semester_id": SEMESTER_ID,
                "program_id": PROGRAM_ID,
                "institution_id": INSTITUTION_ID,
                "name": "Section A",
                "is_active": True,
            },
            {
                "id": OTHER_SECTION_ID,
                "academic_period_id": OTHER_ACADEMIC_PERIOD_ID,
                "semester_id": OTHER_SEMESTER_ID,
                "program_id": OTHER_PROGRAM_ID,
                "institution_id": OTHER_INSTITUTION_ID,
                "name": "Section A",
                "is_active": True,
            },
        ]

        self.subjects = [
            {
                "id": SUBJECT_ID,
                "semester_id": SEMESTER_ID,
                "program_id": PROGRAM_ID,
                "institution_id": INSTITUTION_ID,
                "code": "MCA101",
                "name": "Data Structures",
                "credits": 4.0,
                "is_active": True,
                "has_lab": False,
            },
            {
                "id": OTHER_SUBJECT_ID,
                "semester_id": OTHER_SEMESTER_ID,
                "program_id": OTHER_PROGRAM_ID,
                "institution_id": OTHER_INSTITUTION_ID,
                "code": "MCA-OTHER-101",
                "name": "Other Institution Subject",
                "credits": 4.0,
                "is_active": True,
                "has_lab": False,
            },
        ]

    def execute(self, query, params=None):
        params = params or {}
        sql = str(query).lower().strip()

        # ---------------------------------------------------------
        # Academic years
        # ---------------------------------------------------------
        if "from public.academic_years ay" in sql:
            rows = [
                row
                for row in self.academic_years
                if row["institution_id"] == params["institution_id"]
                and row["is_current"] is True
            ]

            rows.sort(
                key=lambda row: (
                    row["start_date"],
                    row["name"],
                ),
                reverse=True,
            )

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Programs filtered by academic year
        # ---------------------------------------------------------
        if (
            "from public.programs p" in sql
            and "join public.academic_periods ap" in sql
            and "academic_year_id" in params
        ):
            program_ids = {
                period["program_id"]
                for period in self.periods
                if period["academic_year_id"]
                == params["academic_year_id"]
                and period["is_active"] is True
            }

            rows = [
                row
                for row in self.programs
                if row["institution_id"] == params["institution_id"]
                and row["is_active"] is True
                and row["id"] in program_ids
            ]

            rows.sort(key=lambda row: (row["name"], row["code"]))

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Programs without academic-year filter
        # ---------------------------------------------------------
        if "from public.programs p" in sql:
            rows = [
                row
                for row in self.programs
                if row["institution_id"] == params["institution_id"]
                and row["is_active"] is True
            ]

            rows.sort(key=lambda row: (row["name"], row["code"]))

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Sections
        # ---------------------------------------------------------
        if "from public.sections sec" in sql:
            rows = [
                row
                for row in self.sections
                if row["academic_period_id"]
                == params["academic_period_id"]
                and row["institution_id"] == params["institution_id"]
                and row["is_active"] is True
                and any(
                    period["id"] == row["academic_period_id"]
                    and period["is_active"] is True
                    for period in self.periods
                )
            ]

            rows.sort(key=lambda row: row["name"])

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Subjects
        # ---------------------------------------------------------
        if "from public.subjects sub" in sql:
            matching_periods = [
                period
                for period in self.periods
                if period["id"] == params["academic_period_id"]
                and period["is_active"] is True
            ]

            if not matching_periods:
                return FakeResult()

            period = matching_periods[0]

            if period["semester_id"] is None:
                return FakeResult()

            matching_semesters = [
                semester
                for semester in self.semesters
                if semester["id"] == period["semester_id"]
                and semester["program_id"] == period["program_id"]
            ]

            if not matching_semesters:
                return FakeResult()

            rows = [
                row
                for row in self.subjects
                if row["semester_id"] == period["semester_id"]
                and row["program_id"] == period["program_id"]
                and row["institution_id"] == params["institution_id"]
                and row["is_active"] is True
            ]

            rows.sort(key=lambda row: (row["code"], row["name"]))

            return FakeResult(rows)

        raise AssertionError(
            f"Unhandled SQL in fake database:\n{sql}"
        )


def catalog_user(
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
    database = FakeAcademicCatalogDatabase()

    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_current_user] = lambda: catalog_user(
        role=role,
        institution_id=institution_id,
    )

    return database


@pytest.fixture
def client():
    return TestClient(app)


def test_user_can_list_only_current_institution_academic_years():
    setup_overrides()

    try:
        response = TestClient(app).get(
            "/api/v1/academic-years"
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert body[0]["id"] == str(ACADEMIC_YEAR_ID)
        assert body[0]["name"] == "2026-27"

    finally:
        app.dependency_overrides.clear()


def test_user_can_list_only_current_institution_programs():
    setup_overrides()

    try:
        response = TestClient(app).get(
            "/api/v1/programs"
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 2

        returned_ids = {
            UUID(item["id"])
            for item in body
        }

        assert PROGRAM_ID in returned_ids
        assert ANNUAL_PROGRAM_ID in returned_ids
        assert OTHER_PROGRAM_ID not in returned_ids

    finally:
        app.dependency_overrides.clear()


def test_programs_can_be_filtered_by_academic_year():
    setup_overrides()

    try:
        response = TestClient(app).get(
            "/api/v1/programs",
            params={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
            },
        )

        assert response.status_code == 200

        body = response.json()

        returned_ids = {
            UUID(item["id"])
            for item in body
        }

        assert PROGRAM_ID in returned_ids
        assert ANNUAL_PROGRAM_ID in returned_ids
        assert OTHER_PROGRAM_ID not in returned_ids

    finally:
        app.dependency_overrides.clear()


def test_user_can_list_sections_for_academic_period():
    setup_overrides()

    try:
        response = TestClient(app).get(
            "/api/v1/sections",
            params={
                "academic_period_id": str(
                    ACADEMIC_PERIOD_ID
                ),
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert body[0]["id"] == str(SECTION_ID)
        assert body[0]["name"] == "Section A"

    finally:
        app.dependency_overrides.clear()


def test_user_cannot_receive_section_from_another_institution():
    setup_overrides()

    try:
        response = TestClient(app).get(
            "/api/v1/sections",
            params={
                "academic_period_id": str(
                    OTHER_ACADEMIC_PERIOD_ID
                ),
            },
        )

        assert response.status_code == 200
        assert response.json() == []

    finally:
        app.dependency_overrides.clear()


def test_user_can_list_subjects_for_academic_period():
    setup_overrides()

    try:
        response = TestClient(app).get(
            "/api/v1/subjects",
            params={
                "academic_period_id": str(
                    ACADEMIC_PERIOD_ID
                ),
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1
        assert body[0]["id"] == str(SUBJECT_ID)
        assert body[0]["code"] == "MCA101"
        assert body[0]["name"] == "Data Structures"
        assert body[0]["has_lab"] is False

    finally:
        app.dependency_overrides.clear()


def test_annual_academic_period_does_not_return_semester_subjects():
    setup_overrides()

    try:
        response = TestClient(app).get(
            "/api/v1/subjects",
            params={
                "academic_period_id": str(
                    ANNUAL_ACADEMIC_PERIOD_ID
                ),
            },
        )

        assert response.status_code == 200
        assert response.json() == []

    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "role",
    [
        "student",
        "parent",
        "accounts",
    ],
)
def test_non_academic_roles_cannot_access_catalog(role):
    setup_overrides(role=role)

    try:
        response = TestClient(app).get(
            "/api/v1/academic-years"
        )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()


def test_faculty_can_access_catalog():
    setup_overrides(role="faculty")

    try:
        response = TestClient(app).get(
            "/api/v1/academic-years"
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1

    finally:
        app.dependency_overrides.clear()


def test_user_without_institution_scope_is_forbidden():
    setup_overrides(
        role="principal",
        institution_id=None,
    )

    try:
        response = TestClient(app).get(
            "/api/v1/academic-years"
        )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()
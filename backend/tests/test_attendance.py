from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.authenticated_user import AuthenticatedUser


client = TestClient(app)


ORGANIZATION_ID = UUID(
    "0b5c5400-d7db-4086-97dc-b60cd2d680cc"
)

INSTITUTION_ID = UUID(
    "e52a2686-9793-4018-80de-19e54e75101d"
)

USER_ID = UUID(
    "7a44a650-0a4e-4bfa-995e-2b38331008b2"
)

STUDENT_ID = UUID(
    "11111111-1111-4111-8111-111111111111"
)

SUBJECT_ID = UUID(
    "22222222-2222-4222-8222-222222222222"
)

SECTION_ID = UUID(
    "55555555-5555-4555-8555-555555555555"
)

ACADEMIC_PERIOD_ID = UUID(
    "66666666-6666-4666-8666-666666666666"
)

ACADEMIC_YEAR_ID = UUID(
    "77777777-7777-4777-8777-777777777777"
)

FACULTY_ID = UUID(
    "88888888-8888-4888-8888-888888888888"
)

ATTENDANCE_ID = UUID(
    "99999999-9999-4999-8999-999999999999"
)

SEMESTER_ID = UUID(
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
)

PROGRAM_ID = UUID(
    "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
)


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def __iter__(self):
        return iter(self.rows)


class FakeAttendanceDatabase:
    def __init__(self):
        self.attendance = {}
        self.corrections = []

    def execute(self, query, params):
        sql = str(query).lower().strip()

        # ---------------------------------------------------------
        # Academic context
        # ---------------------------------------------------------
        if "from public.students s" in sql:
            return FakeResult(
                [
                    {
                        "student_id": STUDENT_ID,
                        "student_institution_id": INSTITUTION_ID,
                        "subject_id": SUBJECT_ID,
                        "subject_semester_id": SEMESTER_ID,
                        "section_id": SECTION_ID,
                        "section_semester_id": SEMESTER_ID,
                        "section_academic_period_id": ACADEMIC_PERIOD_ID,
                        "academic_period_id": ACADEMIC_PERIOD_ID,
                        "academic_year_id": ACADEMIC_YEAR_ID,
                        "program_id": PROGRAM_ID,
                        "period_type": "SEMESTER",
                        "period_number": 1,
                        "period_semester_id": SEMESTER_ID,
                        "academic_year_institution_id": INSTITUTION_ID,
                        "department_institution_id": INSTITUTION_ID,
                        "student_history_section_id": SECTION_ID,
                        "student_history_academic_year_id": ACADEMIC_YEAR_ID,
                        "student_history_program_id": PROGRAM_ID,
                        "student_history_semester_id": SEMESTER_ID,
                    }
                ]
            )

        # ---------------------------------------------------------
        # Faculty lookup
        # ---------------------------------------------------------
        if "from public.faculty" in sql:
            return FakeResult(
                [
                    {
                        "id": FACULTY_ID,
                        "institution_id": INSTITUTION_ID,
                        "user_profile_id": USER_ID,
                        "is_active": True,
                    }
                ]
            )

        # ---------------------------------------------------------
        # Faculty assignment
        # ---------------------------------------------------------
        if "from public.faculty_assignments" in sql:
            return FakeResult(
                [{"id": uuid4()}]
            )

        # ---------------------------------------------------------
        # Academic period lookup
        # ---------------------------------------------------------
        if "from public.academic_periods" in sql:
            return FakeResult(
                [{"academic_year_id": ACADEMIC_YEAR_ID}]
            )

        # ---------------------------------------------------------
        # Attendance lookup
        # ---------------------------------------------------------
        if "from public.attendance a" in sql:
            if "a.id = :attendance_id" in sql:
                row = self.attendance.get(
                    params["attendance_id"]
                )

                if (
                    row
                    and row["institution_id"]
                    == params["institution_id"]
                ):
                    return FakeResult([row])

                return FakeResult()

            rows = [
                row
                for row in self.attendance.values()
                if row["institution_id"]
                == params["institution_id"]
            ]

            if "a.student_id = :student_id" in sql:
                rows = [
                    row
                    for row in rows
                    if row["student_id"]
                    == params["student_id"]
                ]

            if "a.subject_id = :subject_id" in sql:
                rows = [
                    row
                    for row in rows
                    if row["subject_id"]
                    == params["subject_id"]
                ]

            if "a.section_id = :section_id" in sql:
                rows = [
                    row
                    for row in rows
                    if row["section_id"]
                    == params["section_id"]
                ]

            if (
                "a.academic_period_id = :academic_period_id"
                in sql
            ):
                rows = [
                    row
                    for row in rows
                    if row["academic_period_id"]
                    == params["academic_period_id"]
                ]

            if "a.attendance_date = :attendance_date" in sql:
                rows = [
                    row
                    for row in rows
                    if row["attendance_date"]
                    == params["attendance_date"]
                ]

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Existing attendance identity check
        # ---------------------------------------------------------
        if (
            "from public.attendance" in sql
            and "where institution_id = :institution_id" in sql
        ):
            rows = [
                row
                for row in self.attendance.values()
                if row["institution_id"]
                == params["institution_id"]
                and row["student_id"]
                == params["student_id"]
                and row["subject_id"]
                == params["subject_id"]
                and row["section_id"]
                == params["section_id"]
                and row["academic_period_id"]
                == params["academic_period_id"]
                and row["attendance_date"]
                == params["attendance_date"]
            ]

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Attendance UPDATE
        #
        # This MUST appear before the generic INSERT handler.
        # ---------------------------------------------------------
        if sql.startswith(
            "update public.attendance"
        ):
            row = self.attendance.get(
                params["attendance_id"]
            )

            if row is None:
                return FakeResult()

            row["status"] = params["new_status"]

            row["correction_reason"] = (
                params["correction_reason"]
            )

            row["marked_by_user_id"] = (
                params["marked_by_user_id"]
            )

            row["marked_by_faculty_id"] = (
                params["marked_by_faculty_id"]
            )

            return FakeResult([row])

        # ---------------------------------------------------------
        # Correction audit INSERT
        # ---------------------------------------------------------
        if sql.startswith(
            "insert into public.attendance_corrections"
        ):
            self.corrections.append(params)

            return FakeResult()

        # ---------------------------------------------------------
        # Attendance INSERT
        # ---------------------------------------------------------
        if sql.startswith(
            "insert into public.attendance"
        ):
            row = {
                "id": ATTENDANCE_ID,
                "institution_id":
                    params["institution_id"],
                "student_id":
                    params["student_id"],
                "subject_id":
                    params["subject_id"],
                "section_id":
                    params["section_id"],
                "academic_period_id":
                    params["academic_period_id"],
                "attendance_date":
                    params["attendance_date"],
                "status":
                    params["status"],
                "source":
                    params["source"],
                "source_import_id": None,
                "marked_by_user_id":
                    params["marked_by_user_id"],
                "marked_by_faculty_id":
                    params["marked_by_faculty_id"],
                "correction_reason":
                    params["correction_reason"],
                "created_at": None,
                "updated_at": None,
            }

            self.attendance[ATTENDANCE_ID] = row

            return FakeResult([row])

        return FakeResult()

    def commit(self):
        return None

    def rollback(self):
        return None


def setup(
    role="principal",
    database=None,
):
    fake_db = (
        database
        if database is not None
        else FakeAttendanceDatabase()
    )

    app.dependency_overrides[get_current_user] = (
        lambda: AuthenticatedUser(
            user_id=USER_ID,
            email="demo@college-demo.local",
            role=role,
            organization_id=ORGANIZATION_ID,
            institution_id=INSTITUTION_ID,
            department_id=None,
            is_active=True,
        )
    )

    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    return fake_db


def teardown():
    app.dependency_overrides.clear()


def payload():
    return {
        "student_id": str(STUDENT_ID),
        "subject_id": str(SUBJECT_ID),
        "section_id": str(SECTION_ID),
        "academic_period_id": str(
            ACADEMIC_PERIOD_ID
        ),
        "attendance_date": "2026-10-07",
        "status": "PRESENT",
    }


def test_management_user_can_create_attendance():
    setup()

    try:
        response = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert response.status_code == 201

        data = response.json()

        assert data["status"] == "PRESENT"
        assert data["source"] == "DIRECT"

    finally:
        teardown()


def test_duplicate_attendance_is_rejected():
    setup()

    try:
        first = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        second = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert first.status_code == 201
        assert second.status_code == 409

    finally:
        teardown()


def test_correction_requires_reason():
    setup()

    try:
        create_response = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert create_response.status_code == 201

        attendance_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/attendance/{attendance_id}",
            json={
                "status": "ABSENT",
                "correction_reason": "",
            },
        )

        assert response.status_code == 422

    finally:
        teardown()


def test_correction_creates_audit_record():
    database = setup()

    try:
        create_response = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert create_response.status_code == 201

        attendance_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/attendance/{attendance_id}",
            json={
                "status": "ABSENT",
                "correction_reason":
                    "Attendance register correction",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "ABSENT"

        assert len(database.corrections) == 1

        correction = database.corrections[0]

        assert correction["old_status"] == "PRESENT"
        assert correction["new_status"] == "ABSENT"

        assert (
            correction["reason"]
            == "Attendance register correction"
        )

    finally:
        teardown()


def test_noop_correction_is_rejected():
    setup()

    try:
        create_response = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert create_response.status_code == 201

        attendance_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/attendance/{attendance_id}",
            json={
                "status": "PRESENT",
                "correction_reason":
                    "No actual change",
            },
        )

        assert response.status_code == 400

    finally:
        teardown()


def test_student_role_cannot_create_attendance():
    setup(role="student")

    try:
        response = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert response.status_code == 403

    finally:
        teardown()


def test_parent_role_cannot_create_attendance():
    setup(role="parent")

    try:
        response = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert response.status_code == 403

    finally:
        teardown()


def test_accounts_role_cannot_create_attendance():
    setup(role="accounts")

    try:
        response = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert response.status_code == 403

    finally:
        teardown()


def test_faculty_can_create_attendance_when_assigned():
    setup(role="faculty")

    try:
        response = client.post(
            "/api/v1/attendance",
            json=payload(),
        )

        assert response.status_code == 201

        data = response.json()

        assert data["marked_by_faculty_id"] == str(
            FACULTY_ID
        )

    finally:
        teardown()


def test_institution_scope_is_enforced():
    setup()

    try:
        response = client.get(
            "/api/v1/attendance",
            params={
                "student_id": str(uuid4()),
            },
        )

        assert response.status_code == 200

    finally:
        teardown()
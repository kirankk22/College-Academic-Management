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

BANGALORE_INSTITUTION_ID = UUID(
    "e52a2686-9793-4018-80de-19e54e75101d"
)

MYSORE_INSTITUTION_ID = UUID(
    "6c8590ff-f19d-4365-8a2c-26147ad3a48b"
)

USER_ID = UUID(
    "7a44a650-0a4e-4bfa-995e-2b38331008b2"
)

ACADEMIC_YEAR_ID = UUID(
    "11111111-1111-4111-8111-111111111111"
)

SUBJECT_ID = UUID(
    "22222222-2222-4222-8222-222222222222"
)

LAB_SUBJECT_ID = UUID(
    "33333333-3333-4333-8333-333333333333"
)

NON_LAB_SUBJECT_ID = UUID(
    "44444444-4444-4444-8444-444444444444"
)

SECTION_ID = UUID(
    "55555555-5555-4555-8555-555555555555"
)

SECOND_SECTION_ID = UUID(
    "66666666-6666-4666-8666-666666666666"
)

FACULTY_ONE_ID = UUID(
    "77777777-7777-4777-8777-777777777777"
)

FACULTY_TWO_ID = UUID(
    "88888888-8888-4888-8888-888888888888"
)

FACULTY_THREE_ID = UUID(
    "99999999-9999-4999-8999-999999999999"
)

INACTIVE_FACULTY_ID = UUID(
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
)

FOREIGN_FACULTY_ID = UUID(
    "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
)


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []
        self._first = self.rows[0] if self.rows else None

    def mappings(self):
        return self

    def first(self):
        return self._first

    def all(self):
        return self.rows

    def one(self):
        if len(self.rows) != 1:
            raise AssertionError(
                f"Expected exactly one row, got {len(self.rows)}"
            )

        return self.rows[0]


class FakeFacultyAssignmentDatabase:
    def __init__(self):
        self.assignments = {}

        self.faculty = {
            FACULTY_ONE_ID: {
                "id": FACULTY_ONE_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
                "is_active": True,
            },
            FACULTY_TWO_ID: {
                "id": FACULTY_TWO_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
                "is_active": True,
            },
            FACULTY_THREE_ID: {
                "id": FACULTY_THREE_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
                "is_active": True,
            },
            INACTIVE_FACULTY_ID: {
                "id": INACTIVE_FACULTY_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
                "is_active": False,
            },
            FOREIGN_FACULTY_ID: {
                "id": FOREIGN_FACULTY_ID,
                "institution_id": MYSORE_INSTITUTION_ID,
                "is_active": True,
            },
        }

        self.subjects = {
            SUBJECT_ID: {
                "id": SUBJECT_ID,
                "semester_id": UUID(
                    "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
                ),
                "has_lab": False,
                "is_active": True,
                "institution_id": BANGALORE_INSTITUTION_ID,
            },
            LAB_SUBJECT_ID: {
                "id": LAB_SUBJECT_ID,
                "semester_id": UUID(
                    "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
                ),
                "has_lab": True,
                "is_active": True,
                "institution_id": BANGALORE_INSTITUTION_ID,
            },
            NON_LAB_SUBJECT_ID: {
                "id": NON_LAB_SUBJECT_ID,
                "semester_id": UUID(
                    "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
                ),
                "has_lab": False,
                "is_active": True,
                "institution_id": BANGALORE_INSTITUTION_ID,
            },
        }

        self.sections = {
            SECTION_ID: {
                "id": SECTION_ID,
                "semester_id": UUID(
                    "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
                ),
                "is_active": True,
                "institution_id": BANGALORE_INSTITUTION_ID,
            },
            SECOND_SECTION_ID: {
                "id": SECOND_SECTION_ID,
                "semester_id": UUID(
                    "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
                ),
                "is_active": True,
                "institution_id": BANGALORE_INSTITUTION_ID,
            },
        }

        self.academic_years = {
            ACADEMIC_YEAR_ID: {
                "id": ACADEMIC_YEAR_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
            }
        }

    def _assignment_row(self, assignment):
        return {
            "id": assignment["id"],
            "faculty_id": assignment["faculty_id"],
            "subject_id": assignment["subject_id"],
            "section_id": assignment["section_id"],
            "academic_year_id": assignment["academic_year_id"],
            "assignment_type": assignment["assignment_type"],
            "is_primary": assignment["is_primary"],
            "is_active": assignment["is_active"],
        }

    def _active_assignments(self):
        return [
            assignment
            for assignment in self.assignments.values()
            if assignment["is_active"]
        ]

    def execute(self, query, params):
        sql = str(query).lower().strip()

        # ---------------------------------------------------------
        # Academic context validation
        # ---------------------------------------------------------
        if (
            "from public.faculty f" in sql
            and "join public.subjects s" in sql
            and "join public.sections sec" in sql
        ):
            faculty = self.faculty.get(params["faculty_id"])
            subject = self.subjects.get(params["subject_id"])
            section = self.sections.get(params["section_id"])
            academic_year = self.academic_years.get(
                params["academic_year_id"]
            )

            if not faculty:
                return FakeResult()

            if faculty["institution_id"] != params["institution_id"]:
                return FakeResult()

            if not subject:
                return FakeResult()

            if subject["institution_id"] != params["institution_id"]:
                return FakeResult()

            if not section:
                return FakeResult()

            if section["institution_id"] != params["institution_id"]:
                return FakeResult()

            if not academic_year:
                return FakeResult()

            if (
                academic_year["institution_id"]
                != params["institution_id"]
            ):
                return FakeResult()

            row = {
                "faculty_id": faculty["id"],
                "faculty_institution_id": faculty["institution_id"],
                "faculty_is_active": faculty["is_active"],
                "subject_id": subject["id"],
                "subject_semester_id": subject["semester_id"],
                "subject_has_lab": subject["has_lab"],
                "subject_is_active": subject["is_active"],
                "section_id": section["id"],
                "section_semester_id": section["semester_id"],
                "section_is_active": section["is_active"],
                "academic_year_id": academic_year["id"],
                "academic_year_institution_id": (
                    academic_year["institution_id"]
                ),
                "subject_institution_id": subject["institution_id"],
                "section_institution_id": section["institution_id"],
            }

            return FakeResult([row])

        # ---------------------------------------------------------
        # Get one assignment
        # ---------------------------------------------------------
        if (
            "from public.faculty_assignments fa" in sql
            and "where fa.id = :assignment_id" in sql
        ):
            assignment = self.assignments.get(
                params["assignment_id"]
            )

            if assignment is None:
                return FakeResult()

            faculty = self.faculty.get(assignment["faculty_id"])

            if (
                faculty is None
                or faculty["institution_id"]
                != params["institution_id"]
            ):
                return FakeResult()

            return FakeResult([
                self._assignment_row(assignment)
            ])

        # ---------------------------------------------------------
        # List assignments
        # ---------------------------------------------------------
        if (
            "from public.faculty_assignments fa" in sql
            and "order by fa.created_at" in sql
        ):
            rows = []

            for assignment in self.assignments.values():
                faculty = self.faculty.get(
                    assignment["faculty_id"]
                )

                if (
                    faculty
                    and faculty["institution_id"]
                    == params["institution_id"]
                ):
                    rows.append(
                        self._assignment_row(assignment)
                    )

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Check duplicate faculty + role
        # ---------------------------------------------------------
        if (
            "from public.faculty_assignments fa" in sql
            and "fa.faculty_id = :faculty_id" in sql
            and "fa.assignment_type = :assignment_type" in sql
            and "fa.is_active = true" in sql
        ):
            for assignment in self._active_assignments():
                if (
                    assignment["faculty_id"]
                    == params["faculty_id"]
                    and assignment["subject_id"]
                    == params["subject_id"]
                    and assignment["section_id"]
                    == params["section_id"]
                    and assignment["academic_year_id"]
                    == params["academic_year_id"]
                    and assignment["assignment_type"]
                    == params["assignment_type"]
                ):
                    excluded_id = params.get(
                        "exclude_assignment_id"
                    )

                    if (
                        excluded_id is None
                        or assignment["id"] != excluded_id
                    ):
                        return FakeResult(
                            [{"id": assignment["id"]}]
                        )

            return FakeResult()

        # ---------------------------------------------------------
        # Check primary lab faculty when assigning secondary
        # ---------------------------------------------------------
        if (
            "assignment_type = 'lab_primary'" in sql
            and "fa.faculty_id = :faculty_id" in sql
        ):
            for assignment in self._active_assignments():
                if (
                    assignment["faculty_id"]
                    == params["faculty_id"]
                    and assignment["subject_id"]
                    == params["subject_id"]
                    and assignment["section_id"]
                    == params["section_id"]
                    and assignment["academic_year_id"]
                    == params["academic_year_id"]
                    and assignment["assignment_type"]
                    == "LAB_PRIMARY"
                ):
                    excluded_id = params.get(
                        "exclude_assignment_id"
                    )

                    if (
                        excluded_id is None
                        or assignment["id"] != excluded_id
                    ):
                        return FakeResult(
                            [{"id": assignment["id"]}]
                        )

            return FakeResult()

        # ---------------------------------------------------------
        # Check one active role
        # ---------------------------------------------------------
        if (
            "from public.faculty_assignments fa" in sql
            and "fa.assignment_type = :assignment_type" in sql
            and "fa.is_active = true" in sql
        ):
            for assignment in self._active_assignments():
                if (
                    assignment["subject_id"]
                    == params["subject_id"]
                    and assignment["section_id"]
                    == params["section_id"]
                    and assignment["academic_year_id"]
                    == params["academic_year_id"]
                    and assignment["assignment_type"]
                    == params["assignment_type"]
                ):
                    excluded_id = params.get(
                        "exclude_assignment_id"
                    )

                    if (
                        excluded_id is None
                        or assignment["id"] != excluded_id
                    ):
                        return FakeResult(
                            [{"id": assignment["id"]}]
                        )

            return FakeResult()

        # ---------------------------------------------------------
        # Insert assignment
        # ---------------------------------------------------------
        if "insert into public.faculty_assignments" in sql:
            assignment_id = uuid4()

            assignment = {
                "id": assignment_id,
                "faculty_id": params["faculty_id"],
                "subject_id": params["subject_id"],
                "section_id": params["section_id"],
                "academic_year_id": params["academic_year_id"],
                "assignment_type": params["assignment_type"],
                "is_primary": params["is_primary"],
                "is_active": True,
            }

            self.assignments[assignment_id] = assignment

            return FakeResult([
                self._assignment_row(assignment)
            ])

        # ---------------------------------------------------------
        # Update assignment
        # ---------------------------------------------------------
        if "update public.faculty_assignments" in sql:
            assignment_id = params["assignment_id"]

            assignment = self.assignments.get(assignment_id)

            if assignment is None:
                return FakeResult()

            assignment["faculty_id"] = params["faculty_id"]
            assignment["assignment_type"] = (
                params["assignment_type"]
            )
            assignment["is_primary"] = params["is_primary"]
            assignment["is_active"] = params["is_active"]

            return FakeResult([
                self._assignment_row(assignment)
            ])

        raise AssertionError(
            f"Unhandled SQL in fake database:\n{sql}"
        )

    def commit(self):
        pass

    def rollback(self):
        pass


def principal_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        email="principal.demo@college-demo.local",
        role="principal",
        organization_id=ORGANIZATION_ID,
        institution_id=BANGALORE_INSTITUTION_ID,
        department_id=None,
        is_active=True,
    )


def faculty_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        email="faculty.demo@college-demo.local",
        role="faculty",
        organization_id=ORGANIZATION_ID,
        institution_id=BANGALORE_INSTITUTION_ID,
        department_id=None,
        is_active=True,
    )


def setup_overrides(
    user: AuthenticatedUser | None = None,
    database: FakeFacultyAssignmentDatabase | None = None,
):
    fake_db = database or FakeFacultyAssignmentDatabase()

    app.dependency_overrides[get_current_user] = (
        lambda: user or principal_user()
    )
    app.dependency_overrides[get_db] = lambda: fake_db

    return fake_db


def teardown_overrides():
    app.dependency_overrides.clear()


def assignment_payload(
    faculty_id: UUID,
    subject_id: UUID = SUBJECT_ID,
    assignment_type: str = "SUBJECT",
    section_id: UUID = SECTION_ID,
):
    return {
        "faculty_id": str(faculty_id),
        "subject_id": str(subject_id),
        "section_id": str(section_id),
        "academic_year_id": str(ACADEMIC_YEAR_ID),
        "assignment_type": assignment_type,
    }


def test_management_user_can_create_subject_faculty():
    database = setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FACULTY_ONE_ID),
        )

        assert response.status_code == 201

        data = response.json()

        assert data["faculty_id"] == str(FACULTY_ONE_ID)
        assert data["assignment_type"] == "SUBJECT"
        assert data["is_primary"] is True
        assert data["is_active"] is True

        assert len(database.assignments) == 1

    finally:
        teardown_overrides()


def test_only_one_active_subject_faculty_is_allowed():
    setup_overrides()

    try:
        first = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FACULTY_ONE_ID),
        )

        second = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FACULTY_TWO_ID),
        )

        assert first.status_code == 201
        assert second.status_code == 409

        assert (
            "active SUBJECT assignment already exists"
            in second.json()["detail"]
        )

    finally:
        teardown_overrides()


def test_lab_primary_faculty_requires_lab_enabled_subject():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_ONE_ID,
                subject_id=NON_LAB_SUBJECT_ID,
                assignment_type="LAB_PRIMARY",
                section_id=SECOND_SECTION_ID,
            ),
        )

        assert response.status_code == 400
        assert (
            "Lab faculty can only be assigned"
            in response.json()["detail"]
        )

    finally:
        teardown_overrides()


def test_lab_primary_faculty_can_be_different_from_subject_faculty():
    database = setup_overrides()

    try:
        subject_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_ONE_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="SUBJECT",
            ),
        )

        primary_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_TWO_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="LAB_PRIMARY",
            ),
        )

        assert subject_response.status_code == 201
        assert primary_response.status_code == 201

        assert (
            subject_response.json()["faculty_id"]
            != primary_response.json()["faculty_id"]
        )

        assert len(database.assignments) == 2

    finally:
        teardown_overrides()


def test_subject_faculty_can_also_be_primary_lab_faculty():
    setup_overrides()

    try:
        subject_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_ONE_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="SUBJECT",
            ),
        )

        primary_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_ONE_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="LAB_PRIMARY",
            ),
        )

        assert subject_response.status_code == 201
        assert primary_response.status_code == 201

        assert (
            subject_response.json()["faculty_id"]
            == primary_response.json()["faculty_id"]
        )

    finally:
        teardown_overrides()


def test_multiple_secondary_faculty_are_allowed():
    database = setup_overrides()

    try:
        primary_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_ONE_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="LAB_PRIMARY",
            ),
        )

        secondary_one = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_TWO_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="LAB_SECONDARY",
            ),
        )

        secondary_two = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_THREE_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="LAB_SECONDARY",
            ),
        )

        assert primary_response.status_code == 201
        assert secondary_one.status_code == 201
        assert secondary_two.status_code == 201

        assert (
            secondary_one.json()["is_primary"] is False
        )
        assert (
            secondary_two.json()["is_primary"] is False
        )

        assert len(database.assignments) == 3

    finally:
        teardown_overrides()


def test_secondary_faculty_cannot_be_same_as_primary_lab_faculty():
    setup_overrides()

    try:
        primary_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_ONE_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="LAB_PRIMARY",
            ),
        )

        secondary_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(
                FACULTY_ONE_ID,
                subject_id=LAB_SUBJECT_ID,
                assignment_type="LAB_SECONDARY",
            ),
        )

        assert primary_response.status_code == 201
        assert secondary_response.status_code == 409

        assert (
            "Primary Lab Faculty cannot also be Secondary"
            in secondary_response.json()["detail"]
        )

    finally:
        teardown_overrides()


def test_inactive_faculty_cannot_be_assigned():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(INACTIVE_FACULTY_ID),
        )

        assert response.status_code == 400
        assert (
            "Inactive faculty cannot be newly assigned"
            in response.json()["detail"]
        )

    finally:
        teardown_overrides()


def test_foreign_institution_faculty_cannot_be_assigned():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FOREIGN_FACULTY_ID),
        )

        assert response.status_code == 400
        assert (
            "not valid for the authenticated institution"
            in response.json()["detail"]
        )

    finally:
        teardown_overrides()


def test_student_role_cannot_manage_faculty_assignments():
    setup_overrides(
        user=AuthenticatedUser(
            user_id=USER_ID,
            email="student.demo@college-demo.local",
            role="student",
            organization_id=ORGANIZATION_ID,
            institution_id=BANGALORE_INSTITUTION_ID,
            department_id=None,
            is_active=True,
        )
    )

    try:
        response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FACULTY_ONE_ID),
        )

        assert response.status_code == 403

    finally:
        teardown_overrides()


def test_client_cannot_choose_another_institution():
    database = setup_overrides()

    try:
        payload = assignment_payload(FACULTY_ONE_ID)

        payload["institution_id"] = str(MYSORE_INSTITUTION_ID)

        response = client.post(
            "/api/v1/faculty-assignments",
            json=payload,
        )

        assert response.status_code == 201

        data = response.json()

        assert data["faculty_id"] == str(FACULTY_ONE_ID)

        stored = next(iter(database.assignments.values()))

        assert stored["faculty_id"] == FACULTY_ONE_ID

    finally:
        teardown_overrides()


def test_management_user_can_list_assignments():
    setup_overrides()

    try:
        create_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FACULTY_ONE_ID),
        )

        assert create_response.status_code == 201

        response = client.get(
            "/api/v1/faculty-assignments"
        )

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["faculty_id"] == str(FACULTY_ONE_ID)

    finally:
        teardown_overrides()


def test_management_user_can_get_assignment():
    setup_overrides()

    try:
        create_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FACULTY_ONE_ID),
        )

        assert create_response.status_code == 201

        assignment_id = create_response.json()["id"]

        response = client.get(
            f"/api/v1/faculty-assignments/{assignment_id}"
        )

        assert response.status_code == 200
        assert response.json()["id"] == assignment_id

    finally:
        teardown_overrides()


def test_management_user_can_update_assignment():
    database = setup_overrides()

    try:
        create_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FACULTY_ONE_ID),
        )

        assert create_response.status_code == 201

        assignment_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/faculty-assignments/{assignment_id}",
            json={
                "faculty_id": str(FACULTY_TWO_ID),
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["faculty_id"] == str(FACULTY_TWO_ID)
        assert data["assignment_type"] == "SUBJECT"
        assert data["is_primary"] is True

        assert len(database.assignments) == 1

    finally:
        teardown_overrides()


def test_delete_logically_deactivates_assignment():
    database = setup_overrides()

    try:
        create_response = client.post(
            "/api/v1/faculty-assignments",
            json=assignment_payload(FACULTY_ONE_ID),
        )

        assert create_response.status_code == 201

        assignment_id = create_response.json()["id"]

        response = client.delete(
            f"/api/v1/faculty-assignments/{assignment_id}"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["id"] == assignment_id
        assert data["is_active"] is False

        stored = database.assignments[
            UUID(assignment_id)
        ]

        assert stored["is_active"] is False

    finally:
        teardown_overrides()
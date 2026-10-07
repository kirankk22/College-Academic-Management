from datetime import date
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

MYSORE_INSTITUTION_ID = uuid4()

USER_ID = UUID(
    "7a44a650-0a4e-4bfa-995e-2b38331008b2"
)

STUDENT_ID = UUID(
    "11111111-1111-4111-8111-111111111111"
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


class FakeStudentDatabase:
    def __init__(self):
        self.students = {
            STUDENT_ID: {
                "id": STUDENT_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
                "permanent_student_id": "MCA2026001",
                "admission_number": "ADM001",
                "first_name": "Ananya",
                "middle_name": None,
                "last_name": "Sharma",
                "date_of_birth": date(2004, 5, 10),
                "gender": "Female",
                "email": "ananya@example.com",
                "phone": "9876543210",
                "admission_date": date(2026, 7, 1),
                "status": "active",
            }
        }

    def execute(self, query, params):
        sql = str(query).lower().strip()

        # ---------------------------------------------------------
        # SELECT one student by ID
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.students" in sql
            and "where id = :student_id" in sql
        ):
            student_id = params["student_id"]
            institution_id = params["institution_id"]

            student = self.students.get(student_id)

            if (
                student
                and student["institution_id"] == institution_id
            ):
                return FakeResult([student])

            return FakeResult()

        # ---------------------------------------------------------
        # Duplicate permanent student ID lookup
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.students" in sql
            and "and permanent_student_id = :permanent_student_id"
            in sql
        ):
            institution_id = params["institution_id"]
            permanent_student_id = params["permanent_student_id"]

            rows = [
                student
                for student in self.students.values()
                if (
                    student["institution_id"] == institution_id
                    and student["permanent_student_id"]
                    == permanent_student_id
                )
            ]

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Duplicate admission number lookup
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.students" in sql
            and "and admission_number = :admission_number"
            in sql
        ):
            institution_id = params["institution_id"]
            admission_number = params["admission_number"]

            rows = [
                student
                for student in self.students.values()
                if (
                    student["institution_id"] == institution_id
                    and student["admission_number"]
                    == admission_number
                )
            ]

            return FakeResult(rows)

        # ---------------------------------------------------------
        # List students for authenticated institution
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.students" in sql
        ):
            institution_id = params["institution_id"]

            rows = [
                student
                for student in self.students.values()
                if student["institution_id"] == institution_id
            ]

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Create student
        # ---------------------------------------------------------
        if (
            sql.startswith("insert")
            and "into public.students" in sql
        ):
            student_id = uuid4()

            student = {
                "id": student_id,
                "institution_id": params["institution_id"],
                "permanent_student_id": params[
                    "permanent_student_id"
                ],
                "admission_number": params["admission_number"],
                "first_name": params["first_name"],
                "middle_name": params["middle_name"],
                "last_name": params["last_name"],
                "date_of_birth": params["date_of_birth"],
                "gender": params["gender"],
                "email": params["email"],
                "phone": params["phone"],
                "admission_date": params["admission_date"],
                "status": params["status"],
            }

            self.students[student_id] = student

            return FakeResult([student])

        # ---------------------------------------------------------
        # Update student
        # ---------------------------------------------------------
        if (
            sql.startswith("update")
            and "public.students" in sql
        ):
            student_id = params["student_id"]
            institution_id = params["institution_id"]

            student = self.students.get(student_id)

            if (
                student is None
                or student["institution_id"] != institution_id
            ):
                return FakeResult()

            for key in (
                "admission_number",
                "first_name",
                "middle_name",
                "last_name",
                "date_of_birth",
                "gender",
                "email",
                "phone",
                "admission_date",
                "status",
            ):
                if key in params:
                    student[key] = params[key]

            return FakeResult([student])

        return FakeResult()

    def commit(self):
        pass

    def rollback(self):
        pass


def override_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        email="principal.demo@college-demo.local",
        role="principal",
        organization_id=ORGANIZATION_ID,
        institution_id=BANGALORE_INSTITUTION_ID,
        department_id=None,
        is_active=True,
    )


def override_unauthorized_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=USER_ID,
        email="student.demo@college-demo.local",
        role="student",
        organization_id=ORGANIZATION_ID,
        institution_id=BANGALORE_INSTITUTION_ID,
        department_id=None,
        is_active=True,
    )


def override_db():
    yield FakeStudentDatabase()


def setup_overrides(
    user_dependency=override_current_user,
) -> None:
    app.dependency_overrides[get_current_user] = user_dependency
    app.dependency_overrides[get_db] = override_db


def teardown_overrides() -> None:
    app.dependency_overrides.clear()


def test_management_user_can_list_students():
    setup_overrides()

    try:
        response = client.get("/api/v1/students")

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["permanent_student_id"] == "MCA2026001"
        assert data[0]["first_name"] == "Ananya"

    finally:
        teardown_overrides()


def test_management_user_can_get_student():
    setup_overrides()

    try:
        response = client.get(
            f"/api/v1/students/{STUDENT_ID}"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["id"] == str(STUDENT_ID)
        assert data["institution_id"] == str(
            BANGALORE_INSTITUTION_ID
        )
        assert data["permanent_student_id"] == "MCA2026001"

    finally:
        teardown_overrides()


def test_management_user_cannot_get_student_from_another_institution():
    setup_overrides()

    try:
        response = client.get(
            f"/api/v1/students/{uuid4()}"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Student not found"

    finally:
        teardown_overrides()


def test_management_user_can_create_student():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/students",
            json={
                "permanent_student_id": "MCA2026002",
                "admission_number": "ADM002",
                "first_name": "Rahul",
                "last_name": "Kumar",
                "date_of_birth": "2004-06-15",
                "gender": "Male",
                "email": "rahul@example.com",
                "phone": "9876500000",
                "admission_date": "2026-07-01",
                "status": "active",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["permanent_student_id"] == "MCA2026002"
        assert data["first_name"] == "Rahul"
        assert data["institution_id"] == str(
            BANGALORE_INSTITUTION_ID
        )

    finally:
        teardown_overrides()


def test_duplicate_permanent_student_id_is_rejected():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/students",
            json={
                "permanent_student_id": "MCA2026001",
                "admission_number": "ADM999",
                "first_name": "Duplicate",
                "last_name": "Student",
                "status": "active",
            },
        )

        assert response.status_code == 409

        assert (
            response.json()["detail"]
            == "A student with this permanent student ID already exists"
        )

    finally:
        teardown_overrides()


def test_management_user_can_update_student():
    setup_overrides()

    try:
        response = client.patch(
            f"/api/v1/students/{STUDENT_ID}",
            json={
                "phone": "9999999999",
                "email": "updated@example.com",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["phone"] == "9999999999"
        assert data["email"] == "updated@example.com"

    finally:
        teardown_overrides()


def test_student_role_cannot_manage_students():
    setup_overrides(override_unauthorized_user)

    try:
        response = client.get("/api/v1/students")

        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"

    finally:
        teardown_overrides()


def test_client_cannot_choose_another_institution():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/students",
            json={
                "institution_id": str(MYSORE_INSTITUTION_ID),
                "permanent_student_id": "MCA2026003",
                "admission_number": "ADM003",
                "first_name": "Unauthorized",
                "last_name": "Institution",
                "status": "active",
            },
        )

        assert response.status_code == 201

        data = response.json()

        # The request attempted to supply another institution.
        # The API must ignore it and use the authenticated
        # user's institution.
        assert data["institution_id"] == str(
            BANGALORE_INSTITUTION_ID
        )

    finally:
        teardown_overrides()
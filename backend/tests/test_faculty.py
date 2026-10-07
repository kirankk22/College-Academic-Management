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

DEPARTMENT_ID = UUID(
    "22222222-2222-4222-8222-222222222222"
)

FOREIGN_DEPARTMENT_ID = UUID(
    "33333333-3333-4333-8333-333333333333"
)

USER_PROFILE_ID = USER_ID

FOREIGN_USER_PROFILE_ID = UUID(
    "44444444-4444-4444-8444-444444444444"
)

FACULTY_ID = UUID(
    "55555555-5555-4555-8555-555555555555"
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


class FakeFacultyDatabase:
    def __init__(self):
        self.departments = {
            DEPARTMENT_ID: {
                "id": DEPARTMENT_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
            },
            FOREIGN_DEPARTMENT_ID: {
                "id": FOREIGN_DEPARTMENT_ID,
                "institution_id": MYSORE_INSTITUTION_ID,
            },
        }

        self.user_profiles = {
            USER_PROFILE_ID: {
                "id": USER_PROFILE_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
            },
            FOREIGN_USER_PROFILE_ID: {
                "id": FOREIGN_USER_PROFILE_ID,
                "institution_id": MYSORE_INSTITUTION_ID,
            },
        }

        self.faculty = {
            FACULTY_ID: {
                "id": FACULTY_ID,
                "institution_id": BANGALORE_INSTITUTION_ID,
                "user_profile_id": USER_PROFILE_ID,
                "employee_id": "EMP001",
                "name": "Dr. Ananya Sharma",
                "email": "ananya@example.com",
                "phone": "9876543210",
                "designation": "Assistant Professor",
                "department_id": DEPARTMENT_ID,
                "is_active": True,
            }
        }

    def execute(self, query, params):
        sql = str(query).lower().strip()

        # ---------------------------------------------------------
        # Faculty by ID
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.faculty" in sql
            and "where id = :faculty_id" in sql
        ):
            faculty_id = params["faculty_id"]
            institution_id = params["institution_id"]

            faculty = self.faculty.get(faculty_id)

            if (
                faculty
                and faculty["institution_id"] == institution_id
            ):
                return FakeResult([faculty])

            return FakeResult()

        # ---------------------------------------------------------
        # Department validation
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.departments" in sql
        ):
            department_id = params["department_id"]
            institution_id = params["institution_id"]

            department = self.departments.get(department_id)

            if (
                department
                and department["institution_id"] == institution_id
            ):
                return FakeResult([department])

            return FakeResult()

        # ---------------------------------------------------------
        # User profile validation
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.user_profiles" in sql
        ):
            user_profile_id = params["user_profile_id"]
            institution_id = params["institution_id"]

            profile = self.user_profiles.get(user_profile_id)

            if (
                profile
                and profile["institution_id"] == institution_id
            ):
                return FakeResult([profile])

            return FakeResult()

        # ---------------------------------------------------------
        # Duplicate employee ID
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.faculty" in sql
            and "employee_id = :employee_id" in sql
        ):
            institution_id = params["institution_id"]
            employee_id = params["employee_id"]

            rows = [
                faculty
                for faculty in self.faculty.values()
                if (
                    faculty["institution_id"] == institution_id
                    and faculty["employee_id"] == employee_id
                )
            ]

            return FakeResult(rows)

        # ---------------------------------------------------------
        # List faculty
        # ---------------------------------------------------------
        if (
            sql.startswith("select")
            and "from public.faculty" in sql
        ):
            institution_id = params["institution_id"]

            rows = [
                faculty
                for faculty in self.faculty.values()
                if faculty["institution_id"] == institution_id
            ]

            return FakeResult(rows)

        # ---------------------------------------------------------
        # Create faculty
        # ---------------------------------------------------------
        if (
            sql.startswith("insert")
            and "into public.faculty" in sql
        ):
            faculty_id = uuid4()

            faculty = {
                "id": faculty_id,
                "institution_id": params["institution_id"],
                "user_profile_id": params["user_profile_id"],
                "employee_id": params["employee_id"],
                "name": params["name"],
                "email": params["email"],
                "phone": params["phone"],
                "designation": params["designation"],
                "department_id": params["department_id"],
                "is_active": params["is_active"],
            }

            self.faculty[faculty_id] = faculty

            return FakeResult([faculty])

        # ---------------------------------------------------------
        # Update faculty
        # ---------------------------------------------------------
        if (
            sql.startswith("update")
            and "public.faculty" in sql
        ):
            faculty_id = params["faculty_id"]
            institution_id = params["institution_id"]

            faculty = self.faculty.get(faculty_id)

            if (
                faculty is None
                or faculty["institution_id"] != institution_id
            ):
                return FakeResult()

            for key in (
                "employee_id",
                "name",
                "email",
                "phone",
                "designation",
                "department_id",
                "user_profile_id",
                "is_active",
            ):
                if key in params:
                    faculty[key] = params[key]

            return FakeResult([faculty])

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
    yield FakeFacultyDatabase()


def setup_overrides(
    user_dependency=override_current_user,
) -> None:
    app.dependency_overrides[get_current_user] = user_dependency
    app.dependency_overrides[get_db] = override_db


def teardown_overrides() -> None:
    app.dependency_overrides.clear()


def test_management_user_can_list_faculty():
    setup_overrides()

    try:
        response = client.get("/api/v1/faculty")

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["employee_id"] == "EMP001"
        assert data[0]["name"] == "Dr. Ananya Sharma"
    finally:
        teardown_overrides()


def test_management_user_can_get_faculty():
    setup_overrides()

    try:
        response = client.get(
            f"/api/v1/faculty/{FACULTY_ID}"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["id"] == str(FACULTY_ID)
        assert data["institution_id"] == str(
            BANGALORE_INSTITUTION_ID
        )
        assert data["employee_id"] == "EMP001"
    finally:
        teardown_overrides()


def test_management_user_cannot_get_faculty_from_another_institution():
    setup_overrides()

    try:
        response = client.get(
            f"/api/v1/faculty/{uuid4()}"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Faculty not found"
    finally:
        teardown_overrides()


def test_management_user_can_create_faculty():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty",
            json={
                "employee_id": "EMP002",
                "name": "Dr. Rahul Kumar",
                "email": "rahul@example.com",
                "phone": "9876500000",
                "designation": "Professor",
                "department_id": str(DEPARTMENT_ID),
                "user_profile_id": str(USER_PROFILE_ID),
                "is_active": True,
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["employee_id"] == "EMP002"
        assert data["name"] == "Dr. Rahul Kumar"
        assert data["institution_id"] == str(
            BANGALORE_INSTITUTION_ID
        )
    finally:
        teardown_overrides()


def test_duplicate_employee_id_is_rejected():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty",
            json={
                "employee_id": "EMP001",
                "name": "Duplicate Faculty",
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "A faculty member with this employee ID already exists"
        )
    finally:
        teardown_overrides()


def test_foreign_department_is_rejected():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty",
            json={
                "employee_id": "EMP003",
                "name": "Foreign Department Faculty",
                "department_id": str(
                    FOREIGN_DEPARTMENT_ID
                ),
            },
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Department does not belong to the authenticated institution"
        )
    finally:
        teardown_overrides()


def test_foreign_user_profile_is_rejected():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty",
            json={
                "employee_id": "EMP004",
                "name": "Foreign Profile Faculty",
                "user_profile_id": str(
                    FOREIGN_USER_PROFILE_ID
                ),
            },
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "User profile does not belong to the authenticated institution"
        )
    finally:
        teardown_overrides()


def test_management_user_can_update_faculty():
    setup_overrides()

    try:
        response = client.patch(
            f"/api/v1/faculty/{FACULTY_ID}",
            json={
                "phone": "9999999999",
                "email": "updated@example.com",
                "designation": "Professor",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["phone"] == "9999999999"
        assert data["email"] == "updated@example.com"
        assert data["designation"] == "Professor"
    finally:
        teardown_overrides()


def test_management_user_cannot_change_faculty_to_foreign_department():
    setup_overrides()

    try:
        response = client.patch(
            f"/api/v1/faculty/{FACULTY_ID}",
            json={
                "department_id": str(
                    FOREIGN_DEPARTMENT_ID
                )
            },
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Department does not belong to the authenticated institution"
        )
    finally:
        teardown_overrides()


def test_student_role_cannot_manage_faculty():
    setup_overrides(override_unauthorized_user)

    try:
        response = client.get("/api/v1/faculty")

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Insufficient permissions"
        )
    finally:
        teardown_overrides()


def test_client_cannot_choose_another_institution():
    setup_overrides()

    try:
        response = client.post(
            "/api/v1/faculty",
            json={
                "institution_id": str(MYSORE_INSTITUTION_ID),
                "employee_id": "EMP005",
                "name": "Unauthorized Institution Faculty",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["institution_id"] == str(
            BANGALORE_INSTITUTION_ID
        )
    finally:
        teardown_overrides()
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

STUDENT_ID = uuid4()
ACADEMIC_YEAR_ID = uuid4()
PROGRAM_ID = uuid4()
SEMESTER_1_ID = uuid4()
SEMESTER_2_ID = uuid4()
SECTION_1_ID = uuid4()
SECTION_2_ID = uuid4()


class FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self._row

    def all(self):
        return self._rows


class FakeDatabase:
    def __init__(self):
        self.history = []
        self.results = []

    def execute(self, query, params):
        sql = str(query).lower()

        if (
            "from public.student_semester_results" in sql
            and "select id" in sql
        ):
            for item in self.results:
                if (
                    item["student_id"] == params["student_id"]
                    and item["academic_year_id"]
                    == params["academic_year_id"]
                    and item["semester_id"]
                    == params["semester_id"]
                ):
                    return FakeResult(row={"id": item["id"]})

            return FakeResult()

        if (
            "from public.student_semester_results" in sql
            and "select" in sql
        ):
            previous_semester_number = params.get(
                "previous_semester_number"
            )

            if previous_semester_number is not None:
                for item in self.results:
                    if (
                        item["student_id"]
                        == params["student_id"]
                        and item["program_id"]
                        == params["program_id"]
                        and item["semester_number"]
                        == previous_semester_number
                    ):
                        return FakeResult(row=item)

                return FakeResult()

            return FakeResult(rows=self.results)

        if "from public.students" in sql:
            return FakeResult(
                row={"id": STUDENT_ID}
            )

        if (
            "from public.academic_years ay" in sql
            and "join public.semesters s" in sql
        ):
            semester_id = params["semester_id"]

            semester_number = (
                1
                if semester_id == SEMESTER_1_ID
                else 2
            )

            return FakeResult(
                row={
                    "academic_year_id": ACADEMIC_YEAR_ID,
                    "program_id": PROGRAM_ID,
                    "semester_id": semester_id,
                    "section_id": params["section_id"],
                    "semester_number": semester_number,
                    "duration_semesters": 4,
                }
            )

        if (
            "from public.student_academic_history" in sql
            and "select section_id" in sql
        ):
            for item in self.history:
                if (
                    item["student_id"] == params["student_id"]
                    and item["academic_year_id"]
                    == params["academic_year_id"]
                    and item["semester_id"]
                    == params["semester_id"]
                ):
                    return FakeResult(
                        row=(item["section_id"],)
                    )

            return FakeResult()

        if (
            "from public.student_academic_history" in sql
            and "select id" in sql
        ):
            for item in self.history:
                if (
                    item["student_id"] == params["student_id"]
                    and item["academic_year_id"]
                    == params["academic_year_id"]
                    and item["semester_id"]
                    == params["semester_id"]
                ):
                    return FakeResult(
                        row={"id": item["id"]}
                    )

            return FakeResult()

        if (
            "from public.student_academic_history" in sql
            and "order by" in sql
        ):
            return FakeResult(rows=self.history)

        if (
            "insert into public.student_academic_history"
            in sql
        ):
            row = {
                "id": uuid4(),
                "student_id": params["student_id"],
                "academic_year_id": params["academic_year_id"],
                "program_id": params["program_id"],
                "semester_id": params["semester_id"],
                "section_id": params["section_id"],
                "roll_number": params["roll_number"],
                "status": params["status"],
                "start_date": None,
                "end_date": None,
            }

            self.history.append(row)

            return FakeResult(row=row)

        if (
            "insert into public.student_semester_results"
            in sql
        ):
            semester_number = (
                1
                if params["semester_id"] == SEMESTER_1_ID
                else 2
            )

            row = {
                "id": uuid4(),
                "student_id": params["student_id"],
                "academic_year_id": params["academic_year_id"],
                "program_id": params["program_id"],
                "semester_id": params["semester_id"],
                "result_status": params["result_status"],
                "progression_status": params[
                    "progression_status"
                ],
                "result_date": params["result_date"],
                "remarks": params["remarks"],
                "semester_number": semester_number,
            }

            self.results.append(row)

            return FakeResult(row=row)

        if (
            "update public.student_academic_history"
            in sql
        ):
            return FakeResult()

        return FakeResult()

    def commit(self):
        pass

    def rollback(self):
        pass


CURRENT_DATABASE = None


def override_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        email="principal.demo@college-demo.local",
        role="principal",
        organization_id=ORGANIZATION_ID,
        institution_id=INSTITUTION_ID,
        department_id=None,
        is_active=True,
    )


def override_db():
    yield CURRENT_DATABASE


def setup_overrides() -> None:
    global CURRENT_DATABASE

    CURRENT_DATABASE = FakeDatabase()

    app.dependency_overrides[get_current_user] = (
        override_current_user
    )
    app.dependency_overrides[get_db] = override_db


def teardown_overrides() -> None:
    global CURRENT_DATABASE

    CURRENT_DATABASE = None
    app.dependency_overrides.clear()


def seed_semester_1_history() -> None:
    CURRENT_DATABASE.history.append(
        {
            "id": uuid4(),
            "student_id": STUDENT_ID,
            "academic_year_id": ACADEMIC_YEAR_ID,
            "program_id": PROGRAM_ID,
            "semester_id": SEMESTER_1_ID,
            "section_id": SECTION_1_ID,
            "roll_number": "MCA001",
            "status": "active",
            "start_date": None,
            "end_date": None,
        }
    )


def seed_semester_1_result(result_status: str) -> None:
    CURRENT_DATABASE.results.append(
        {
            "id": uuid4(),
            "student_id": STUDENT_ID,
            "academic_year_id": ACADEMIC_YEAR_ID,
            "program_id": PROGRAM_ID,
            "semester_id": SEMESTER_1_ID,
            "result_status": result_status,
            "progression_status": (
                "eligible"
                if result_status == "pass"
                else "blocked"
            ),
            "result_date": None,
            "remarks": None,
            "semester_number": 1,
        }
    )


def test_semester_1_history_can_be_created():
    setup_overrides()

    try:
        response = client.post(
            f"/api/v1/students/{STUDENT_ID}/academic-history",
            json={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
                "program_id": str(PROGRAM_ID),
                "semester_id": str(SEMESTER_1_ID),
                "section_id": str(SECTION_1_ID),
                "roll_number": "MCA001",
                "status": "active",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["student_id"] == str(STUDENT_ID)
        assert data["semester_id"] == str(SEMESTER_1_ID)
        assert data["status"] == "active"

    finally:
        teardown_overrides()


def test_duplicate_semester_history_is_rejected():
    setup_overrides()

    try:
        seed_semester_1_history()

        response = client.post(
            f"/api/v1/students/{STUDENT_ID}/academic-history",
            json={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
                "program_id": str(PROGRAM_ID),
                "semester_id": str(SEMESTER_1_ID),
                "section_id": str(SECTION_1_ID),
                "roll_number": "MCA001",
                "status": "active",
            },
        )

        assert response.status_code == 409

        assert (
            response.json()["detail"]
            == "Student already has academic history for this semester"
        )

    finally:
        teardown_overrides()


def test_fail_result_is_blocked():
    setup_overrides()

    try:
        seed_semester_1_history()

        response = client.post(
            f"/api/v1/students/{STUDENT_ID}/semester-results",
            json={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
                "program_id": str(PROGRAM_ID),
                "semester_id": str(SEMESTER_1_ID),
                "result_status": "fail",
                "remarks": "Failed semester",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["result_status"] == "fail"
        assert data["progression_status"] == "blocked"

    finally:
        teardown_overrides()


def test_pending_result_is_blocked():
    setup_overrides()

    try:
        seed_semester_1_history()

        response = client.post(
            f"/api/v1/students/{STUDENT_ID}/semester-results",
            json={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
                "program_id": str(PROGRAM_ID),
                "semester_id": str(SEMESTER_1_ID),
                "result_status": "pending",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["result_status"] == "pending"
        assert data["progression_status"] == "blocked"

    finally:
        teardown_overrides()


def test_semester_2_allowed_after_pass():
    setup_overrides()

    try:
        seed_semester_1_result("pass")

        response = client.post(
            f"/api/v1/students/{STUDENT_ID}/academic-history",
            json={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
                "program_id": str(PROGRAM_ID),
                "semester_id": str(SEMESTER_2_ID),
                "section_id": str(SECTION_2_ID),
                "roll_number": "MCA001",
                "status": "active",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["semester_id"] == str(SEMESTER_2_ID)

    finally:
        teardown_overrides()


def test_semester_2_blocked_after_fail():
    setup_overrides()

    try:
        seed_semester_1_result("fail")

        response = client.post(
            f"/api/v1/students/{STUDENT_ID}/academic-history",
            json={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
                "program_id": str(PROGRAM_ID),
                "semester_id": str(SEMESTER_2_ID),
                "section_id": str(SECTION_2_ID),
                "roll_number": "MCA001",
                "status": "active",
            },
        )

        assert response.status_code == 409

        assert (
            response.json()["detail"]
            == "Student cannot progress because the previous "
            "semester result is not PASS"
        )

    finally:
        teardown_overrides()


def test_semester_2_blocked_after_pending():
    setup_overrides()

    try:
        seed_semester_1_result("pending")

        response = client.post(
            f"/api/v1/students/{STUDENT_ID}/academic-history",
            json={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
                "program_id": str(PROGRAM_ID),
                "semester_id": str(SEMESTER_2_ID),
                "section_id": str(SECTION_2_ID),
                "roll_number": "MCA001",
                "status": "active",
            },
        )

        assert response.status_code == 409

        assert (
            response.json()["detail"]
            == "Student cannot progress because the previous "
            "semester result is not PASS"
        )

    finally:
        teardown_overrides()


def test_semester_2_blocked_without_previous_result():
    setup_overrides()

    try:
        response = client.post(
            f"/api/v1/students/{STUDENT_ID}/academic-history",
            json={
                "academic_year_id": str(ACADEMIC_YEAR_ID),
                "program_id": str(PROGRAM_ID),
                "semester_id": str(SEMESTER_2_ID),
                "section_id": str(SECTION_2_ID),
                "roll_number": "MCA001",
                "status": "active",
            },
        )

        assert response.status_code == 409

        assert (
            response.json()["detail"]
            == "Student cannot progress because the previous "
            "semester result is not available"
        )

    finally:
        teardown_overrides()


def test_unauthorized_role_cannot_manage_academic_history():
    def override_student_user():
        return AuthenticatedUser(
            user_id=uuid4(),
            email="student@example.com",
            role="student",
            organization_id=ORGANIZATION_ID,
            institution_id=INSTITUTION_ID,
            department_id=None,
            is_active=True,
        )

    app.dependency_overrides[
        get_current_user
    ] = override_student_user

    try:
        response = client.get(
            f"/api/v1/students/{STUDENT_ID}/academic-history"
        )

        assert response.status_code == 403

    finally:
        teardown_overrides()
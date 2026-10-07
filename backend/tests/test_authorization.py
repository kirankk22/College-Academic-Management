from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.authenticated_user import AuthenticatedUser


client = TestClient(app)


ORGANIZATION_ID = UUID("0b5c5400-d7db-4086-97dc-b60cd2d680cc")
BANGALORE_INSTITUTION_ID = UUID(
    "e52a2686-9793-4018-80de-19e54e75101d"
)
MYSORE_INSTITUTION_ID = uuid4()
USER_ID = UUID("7a44a650-0a4e-4bfa-995e-2b38331008b2")


class FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class FakeDatabase:
    def __init__(self):
        self.bangalore_institution = {
            "id": BANGALORE_INSTITUTION_ID,
            "organization_id": ORGANIZATION_ID,
            "code": "BLR-DEMO",
            "name": "Bangalore Demo College",
            "city": "Bangalore",
            "state": "Karnataka",
            "is_active": True,
        }

    def execute(self, query, params):
        institution_id = params["institution_id"]
        organization_id = params["organization_id"]

        if (
            institution_id == BANGALORE_INSTITUTION_ID
            and organization_id == ORGANIZATION_ID
        ):
            authorized_institution_id = params.get(
                "authorized_institution_id"
            )

            if (
                authorized_institution_id is None
                or authorized_institution_id == BANGALORE_INSTITUTION_ID
            ):
                return FakeResult(self.bangalore_institution)

        return FakeResult(None)


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


def override_db():
    yield FakeDatabase()


def setup_overrides() -> None:
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db] = override_db


def teardown_overrides() -> None:
    app.dependency_overrides.clear()


def test_user_can_access_authorized_institution():
    setup_overrides()

    try:
        response = client.get(
            f"/api/v1/institutions/{BANGALORE_INSTITUTION_ID}"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["code"] == "BLR-DEMO"
        assert data["name"] == "Bangalore Demo College"
        assert data["city"] == "Bangalore"

    finally:
        teardown_overrides()


def test_user_cannot_access_another_institution():
    setup_overrides()

    try:
        response = client.get(
            f"/api/v1/institutions/{MYSORE_INSTITUTION_ID}"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Institution not found"

    finally:
        teardown_overrides()


def test_unauthenticated_user_is_rejected():
    response = client.get(
        f"/api/v1/institutions/{BANGALORE_INSTITUTION_ID}"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"

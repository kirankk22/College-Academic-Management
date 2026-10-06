import os

import httpx


SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
TEST_AUTH_EMAIL = os.environ["TEST_AUTH_EMAIL"]
TEST_AUTH_PASSWORD = os.environ["TEST_AUTH_PASSWORD"]

FASTAPI_URL = "http://127.0.0.1:8000"


def main() -> None:
    print("1. Authenticating with Supabase...")

    login_response = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Content-Type": "application/json",
        },
        json={
            "email": TEST_AUTH_EMAIL,
            "password": TEST_AUTH_PASSWORD,
        },
        timeout=20,
    )

    print("Supabase login HTTP:", login_response.status_code)

    if not login_response.is_success:
        print("Supabase login failed:")
        print(login_response.text)
        raise SystemExit(1)

    login_data = login_response.json()

    access_token = login_data.get("access_token")

    if not access_token:
        print("Login succeeded but no access token was returned.")
        raise SystemExit(1)

    print("Supabase login: PASS")
    print("Access token received: True")
    print("Token type:", login_data.get("token_type"))
    print("Expires in:", login_data.get("expires_in"))

    print()
    print("2. Calling FastAPI /api/v1/auth/me...")

    api_response = httpx.get(
        f"{FASTAPI_URL}/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=20,
    )

    print("FastAPI HTTP:", api_response.status_code)

    if not api_response.is_success:
        print("FastAPI authentication failed:")
        print(api_response.text)
        raise SystemExit(1)

    user = api_response.json()

    print("FastAPI authentication: PASS")
    print()
    print("Authenticated application user:")
    print("User ID:", user.get("user_id"))
    print("Email:", user.get("email"))
    print("Role:", user.get("role"))
    print("Organization ID:", user.get("organization_id"))
    print("Institution ID:", user.get("institution_id"))
    print("Department ID:", user.get("department_id"))
    print("Active:", user.get("is_active"))

    print()
    print("3. Calling FastAPI /api/v1/institutions...")

    institutions_response = httpx.get(
        f"{FASTAPI_URL}/api/v1/institutions",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        timeout=20,
    )

    print("Institutions HTTP:", institutions_response.status_code)

    if not institutions_response.is_success:
        print("Institution API failed:")
        print(institutions_response.text)
        raise SystemExit(1)

    institutions = institutions_response.json()

    print("Institution authorization: PASS")
    print("Visible institutions:", len(institutions))

    for institution in institutions:
        print(
            "-",
            institution["code"],
            "|",
            institution["name"],
            "|",
            institution["city"],
        )

    print()
    print("AUTHENTICATION FLOW: PASS")


if __name__ == "__main__":
    main()
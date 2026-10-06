import os

import httpx


SUPABASE_URL = os.environ["SUPABASE_URL"]
EMAIL = os.environ["TEST_AUTH_EMAIL"]
PASSWORD = os.environ["TEST_AUTH_PASSWORD"]


response = httpx.post(
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    headers={
        "apikey": os.environ["SUPABASE_ANON_KEY"],
        "Content-Type": "application/json",
    },
    json={
        "email": EMAIL,
        "password": PASSWORD,
    },
    timeout=20,
)

print("HTTP:", response.status_code)

if response.is_success:
    data = response.json()

    print("Login successful")
    print("Access token received:", bool(data.get("access_token")))
    print("Token type:", data.get("token_type"))
    print("Expires in:", data.get("expires_in"))

    # Deliberately do NOT print the access token.
else:
    print(response.text)
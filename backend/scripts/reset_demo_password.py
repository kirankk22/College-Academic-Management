import os

import httpx


SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]

USER_ID = "7a44a650-0a4e-4bfa-995e-2b38331008b2"
NEW_PASSWORD = os.environ["TEST_AUTH_PASSWORD"]


response = httpx.put(
    f"{SUPABASE_URL}/auth/v1/admin/users/{USER_ID}",
    headers={
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "password": NEW_PASSWORD,
        "email_confirm": True,
    },
    timeout=20,
)

print("HTTP:", response.status_code)

if response.is_success:
    data = response.json()

    print("Demo user password updated successfully.")
    print("User ID:", data.get("id"))
    print("Email:", data.get("email"))
    print("Email confirmed:", bool(data.get("email_confirmed_at")))
else:
    print(response.text)
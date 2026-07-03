import httpx
import uuid
import sys

BASE = "https://pad-plus-ai.onrender.com"
email = f"trainer-{uuid.uuid4().hex[:8]}@pad.ai"
pw = "Test1234!"

with httpx.Client(base_url=BASE, timeout=60) as c:
    # 1. Register
    r1 = c.post("/api/v1/auth/register", json={"email": email, "password": pw})
    print(f"Register: {r1.status_code}")
    if r1.status_code != 200:
        print(r1.text[:200])
        sys.exit(1)

    # 2. Login
    r2 = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
    print(f"Login: {r2.status_code}")
    if r2.status_code != 200:
        print(r2.text[:200])
        sys.exit(1)
    jwt = r2.json().get("access_token", "")
    print(f"JWT: {jwt[:48]}...")

    # 3. Upload doc
    doc = b"# Test\n\nTest document for PAD+."
    r3 = c.post(
        "/api/v1/documents/upload",
        files={"file": ("test.md", doc, "text/markdown")},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    print(f"Upload: {r3.status_code}")
    if r3.status_code in (200, 201):
        print(f"  Doc ID: {r3.json().get('id','?')}")
    else:
        print(f"  {r3.text[:150]}")

    # 4. Chat
    r4 = c.post(
        "/api/v1/chat",
        json={"message": "Привет! Как дела?"},
        headers={"Authorization": f"Bearer {jwt}"},
    )
    print(f"Chat: {r4.status_code}")
    if r4.status_code == 200:
        data = r4.json()
        print(f"  Strategy: {data.get('strategy','?')}")
        print(f"  Reply: {data.get('reply','')[:100]}")
    else:
        print(f"  {r4.text[:200]}")

print("\nDone!")

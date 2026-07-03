import httpx, uuid, time

BASE = "https://pad-plus-ai.onrender.com"
email = f"test-{uuid.uuid4().hex[:6]}@pad.ai"
pw = "Test1234!"
GIGA_KEY = "9925731e-1267-4e2c-8552-65e8f09610a1:59026945-6544-4f8e-84a6-d71c29aaf2cd"

with httpx.Client(base_url=BASE, timeout=60) as c:
    c.post("/api/v1/auth/register", json={"email": email, "password": pw})
    r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
    jwt = r.json()["access_token"]

    c.post("/api/v1/keys", json={"provider": "gigachat", "api_key": GIGA_KEY, "name": "test", "is_default": True},
           headers={"Authorization": f"Bearer {jwt}"})

    before = c.get("/api/v1/xray/brain/strategies").json()
    print(f"Before: total_decisions={before['total_decisions']}")

    r2 = c.post("/api/v1/chat", json={"message": "Привет!"},
                headers={"Authorization": f"Bearer {jwt}"})
    print(f"Chat: {r2.status_code}", r2.json().get("text","")[:60] if r2.status_code==200 else r2.text[:100])

    time.sleep(2)

    after = c.get("/api/v1/xray/brain/strategies").json()
    print(f"After: total_decisions={after['total_decisions']}")
    for s, d in after.get("strategies", {}).items():
        if d["count"] > 0:
            print(f"  {s}: count={d['count']}")

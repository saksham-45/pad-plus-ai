import httpx, uuid, json

BASE = "https://pad-plus-ai.onrender.com"
email = f"trainer-{uuid.uuid4().hex[:8]}@pad.ai"
pw = "TrainMeNow_42!"
GIGA_KEY = "9925731e-1267-4e2c-8552-65e8f09610a1:59026945-6544-4f8e-84a6-d71c29aaf2cd"

with httpx.Client(base_url=BASE, timeout=120) as c:
    c.post("/api/v1/auth/register", json={"email": email, "password": pw})
    r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
    jwt = r.json().get("access_token", "")
    c.post("/api/v1/keys", json={
        "provider": "gigachat",
        "api_key": GIGA_KEY,
        "name": "GigaChat test",
        "is_default": True,
    }, headers={"Authorization": f"Bearer {jwt}"})

    # Chat with more detail
    r2 = c.post("/api/v1/chat", json={"message": "Привет! Как тебя зовут?"},
                headers={"Authorization": f"Bearer {jwt}"})
    data = r2.json()
    print(f"Status: {r2.status_code}")
    print(f"Full response: {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")

import sys, time, uuid, httpx
from pathlib import Path

PAD_API = "https://pad-plus-ai.onrender.com"
GIGA_KEY = "9925731e-1267-4e2c-8552-65e8f09610a1:59026945-6544-4f8e-84a6-d71c29aaf2cd"
PW = "TrainMeNow_42!"

# 50 разнообразных сообщений для всех стратегий
MESSAGES = [
    # simple — приветствия, короткие фразы
    "Привет!",
    "Как дела?",
    "Хорошего дня!",
    "Спасибо!",
    "Пока!",
    "Ок",
    "Круто!",
    "Отлично",
    "Что делаешь?",
    "Спокойной ночи",

    # retrieval — запросы фактов/инфо
    "Что такое искусственный интеллект?",
    "Расскажи про базы данных",
    "Что такое REST API?",
    "Объясни Docker простыми словами",
    "Что такое нейронная сеть?",
    "Чем отличается SQL от NoSQL?",
    "Что такое Git?",
    "Расскажи про Python",
    "Что такое облачные вычисления?",
    "Как работает HTTP?",

    # reasoning — анализ, сравнение, объяснение
    "Сравни Python и JavaScript",
    "Почему нейросети лучше классических алгоритмов?",
    "Проанализируй плюсы и минусы микросервисов",
    "Объясни, как работает машинное обучение",
    "Почему важно тестировать код?",
    "Как работает шифрование данных?",
    "Сравни SQLite и PostgreSQL",
    "Детально разбери архитектуру REST",
    "Почему Linux лучше Windows для серверов?",
    "Объясни принципы SOLID",

    # creative — креативные запросы
    "Придумай название для стартапа",
    "Напиши стих про программирование",
    "Сочини тост для айтишников",
    "Придумай идею для мобильного приложения",
    "Напиши короткий рассказ про хакера",
    "Сгенерируй слоган для AI компании",
    "Придумай необычный рецепт пиццы",
    "Напиши загадку про компьютер",
    "Сочини диалог между CPU и GPU",
    "Придумай креативный способ изучить Python",

    # reflective — саморефлексия
    "Что ты думаешь о себе?",
    "Как ты принимаешь решения?",
    "Расскажи о своих возможностях",
    "В чём твоя главная цель?",
    "Как ты понимаешь, что ответ правильный?",
    "Что бы ты хотел улучшить в себе?",
    "Как ты обрабатываешь эмоции?",
    "Почему ты так отвечаешь?",
    "Что ты чувствуешь прямо сейчас?",
    "Как ты учишься на ошибках?",

    # learning — запоминание
    "Запомни: мой любимый язык — Python",
    "Запомни: я работаю программистом",
    "Новый факт: я живу в Москве",
    "Запомни: меня зовут Александр",
    "Добавь в память: я учу JavaScript",
]

with httpx.Client(base_url=PAD_API, timeout=120) as c:
    email = f"train-{uuid.uuid4().hex[:8]}@pad.ai"
    c.post("/api/v1/auth/register", json={"email": email, "password": PW})
    r = c.post("/api/v1/auth/login", json={"email": email, "password": PW})
    jwt = r.json()["access_token"]
    print(f"User: {email}")

    c.post("/api/v1/keys", json={"provider": "gigachat", "api_key": GIGA_KEY, "name": "GigaChat", "is_default": True},
           headers={"Authorization": f"Bearer {jwt}"})

    print(f"\n=== TRAINING: {len(MESSAGES)} MESSAGES ===")
    start = time.time()

    strategies_used = {}
    ok = 0
    fail = 0

    for i, msg in enumerate(MESSAGES):
        print(f"  [{i+1:02d}/{len(MESSAGES)}] << {msg[:55]}  ", end="")
        try:
            r = c.post("/api/v1/chat", json={"message": msg}, headers={"Authorization": f"Bearer {jwt}"})
            if r.status_code == 200:
                d = r.json()
                txt = d.get("text", "")[:60]
                ok += 1
                print(f"[OK] {txt}")
            elif r.status_code == 429:
                print("[RATE-LIMIT] жду 12с...")
                time.sleep(12)
                r = c.post("/api/v1/chat", json={"message": msg}, headers={"Authorization": f"Bearer {jwt}"})
                if r.status_code == 200:
                    ok += 1
                    print(f"  [OK] {r.json().get('text','')[:60]}")
                else:
                    fail += 1
                    print(f"  [FAIL] {r.status_code}")
            else:
                fail += 1
                print(f"[FAIL] {r.status_code}")
        except Exception as e:
            fail += 1
            print(f"[ERROR] {e}")

        if (i + 1) % 5 == 0:
            time.sleep(0.5)  # пауза каждые 5 запросов
        else:
            time.sleep(0.2)

    elapsed = time.time() - start
    print(f"\n=== DONE in {elapsed:.0f}s ===")
    print(f"  Success: {ok}/{len(MESSAGES)}, Failed: {fail}")

    print(f"\n=== META-LEARNER STATS ===")
    r = c.get("/api/v1/xray/brain/strategies")
    s = r.json()
    print(f"  Total decisions: {s.get('total_decisions', 0)}")
    print(f"  Overall success: {s.get('overall_success_rate', 0)*100:.0f}%")
    for name, st in sorted(s.get("strategies", {}).items()):
        if st["count"] > 0:
            pct = st["success_rate"] * 100
            print(f"    {name}: {st['count']} calls, {pct:.0f}% success")

    print(f"\n=== BRAIN STATUS ===")
    r = c.get("/api/v1/xray/brain/status")
    s = r.json()
    ms = s.get("meta_learner", {})
    print(f"  Best strategy: {ms.get('best_strategy')}")
    print(f"  Worst strategy: {ms.get('worst_strategy')}")
    print(f"  Reflection count: {s.get('reflection',{}).get('reflection_count',0)}")

    print(f"\nUser credentials for future use:")
    print(f"  Email: {email}")
    print(f"  Password: {PW}")

    import json as _json
    with open("train_result.json", "w") as f:
        _json.dump(s, f, ensure_ascii=False, indent=2)
    print(f"\nStats saved to train_result.json")

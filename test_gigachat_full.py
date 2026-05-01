"""Тест GigaChat подключения"""
import sys, os, time, requests, subprocess, threading, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

BASE = "http://127.0.0.1:8080"

def start_server():
    """Запускает сервер в фоне"""
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8080"],
        cwd=os.path.join(os.path.dirname(__file__), 'backend'),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return proc

def wait_for_server(timeout=60):
    """Ждёт пока сервер запустится"""
    for i in range(timeout):
        try:
            r = requests.get(f"{BASE}/health", timeout=2)
            if r.status_code == 200:
                print("✅ Сервер запущен")
                return True
        except:
            pass
        if i % 10 == 0:
            print(f"  Ожидание... {i}с")
        time.sleep(1)
    print("❌ Сервер не запустился")
    return False

def register_and_login():
    """Регистрация и получение токена"""
    email = f"test_gigachat_{int(time.time())}@test.com"
    password = "TestPass123!"
    
    # Регистрация
    r = requests.post(f"{BASE}/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": "Test"
    })
    print(f"Register: {r.status_code}")
    
    # Вход
    r = requests.post(f"{BASE}/api/v1/auth/login", json={
        "email": email, "password": password
    })
    print(f"Login: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        return data.get("access_token")
    return None

def test_gigachat(token):
    """Тест GigaChat"""
    # Сначала добавим ключ GigaChat
    gigachat_key = "OTkyNTczMWUtMTI2Ny00ZTJjLTg1NTItNjVlOGYwOTYxMGExOjliZWQ1Y2I3LTQ1MDctNDJiYS1iZTdjLTJlZTQzMTU1MTZlNw=="
    
    r = requests.post(f"{BASE}/api/v1/keys", json={
        "provider": "gigachat",
        "api_key": gigachat_key,
        "name": "GigaChat Test",
        "model_preference": "GigaChat",
        "is_default": True
    }, headers={"Authorization": f"Bearer {token}"})
    print(f"Add key: {r.status_code}")
    if r.status_code != 200:
        print(f"  Response: {r.text[:300]}")
        return
    
    key_data = r.json()
    key_id = key_data.get("id")
    print(f"  Key ID: {key_id}")
    
    # Тест чата
    r = requests.post(f"{BASE}/api/v1/chat/stream", json={
        "message": "Привет! Ответь кратко.",
        "key_id": key_id,
        "model": "GigaChat",
        "provider": "gigachat",
        "stream": True
    }, headers={"Authorization": f"Bearer {token}"}, stream=True)
    
    print(f"Chat: {r.status_code}")
    if r.status_code == 200:
        for line in r.iter_lines():
            if line:
                text = line.decode('utf-8')
                if text.startswith('data: '):
                    data = json.loads(text[6:])
                    if 'chunk' in data:
                        print(f"  Response: {data['chunk']}")
                    elif 'error' in data:
                        print(f"  Error: {data['error']}")
                    elif 'done' in data:
                        print("  Done!")
                        break
    else:
        print(f"  Response: {r.text[:500]}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Тест GigaChat подключения")
    print("=" * 60)
    
    # Запускаем сервер
    print("\n🚀 Запуск сервера...")
    proc = start_server()
    
    if wait_for_server():
        # Регистрируемся
        print("\n📝 Регистрация...")
        token = register_and_login()
        
        if token:
            print(f"\n✅ Токен получен: {token[:20]}...")
            # Тестируем GigaChat
            print("\n🔌 Тест GigaChat...")
            test_gigachat(token)
        else:
            print("❌ Не удалось получить токен")
    
    # Останавливаем сервер
    print("\n🛑 Остановка сервера...")
    proc.terminate()
    proc.wait()
    print("✅ Готово")

import requests, json, time, sys

BASE = 'http://127.0.0.1:8080'
out = open('test_gc_result.txt', 'w', encoding='utf-8')

def log(msg):
    print(msg, file=out, flush=True)
    print(msg)

try:
    # 1. Регистрация
    email = f'test_gc_{int(time.time())}@test.com'
    r = requests.post(f'{BASE}/api/v1/auth/register', json={'email': email, 'password': 'Test1234!', 'full_name': 'Test'}, timeout=10)
    log(f'Register: {r.status_code}')

    # 2. Вход
    r = requests.post(f'{BASE}/api/v1/auth/login', json={'email': email, 'password': 'Test1234!'}, timeout=10)
    log(f'Login: {r.status_code}')
    token = r.json().get('access_token')
    log(f'Token: {token[:20]}...')

    # 3. Добавляем ключ GigaChat
    gigachat_key = 'OTkyNTczMWUtMTI2Ny00ZTJjLTg1NTItNjVlOGYwOTYxMGExOjliZWQ1Y2I3LTQ1MDctNDJiYS1iZTdjLTJlZTQzMTU1MTZlNw=='
    r = requests.post(f'{BASE}/api/v1/keys', json={
        'provider': 'gigachat',
        'api_key': gigachat_key,
        'name': 'GigaChat Test',
        'model_preference': 'GigaChat',
        'is_default': True
    }, headers={'Authorization': f'Bearer {token}'}, timeout=10)
    log(f'Add key: {r.status_code}')
    if r.status_code == 200:
        key_id = r.json()['id']
        log(f'Key ID: {key_id}')
        
        # 4. Тест чата (без stream)
        r = requests.post(f'{BASE}/api/v1/chat', json={
            'message': 'Привет! Ответь кратко.',
            'key_id': key_id,
            'model': 'GigaChat',
            'provider': 'gigachat'
        }, headers={'Authorization': f'Bearer {token}'}, timeout=30)
        
        log(f'Chat: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            log(f'Response: {data.get("text", "")[:300]}')
        else:
            log(f'Response: {r.text[:500]}')
    else:
        log(f'Response: {r.text[:300]}')
except Exception as e:
    log(f'Error: {e}')
    import traceback
    log(traceback.format_exc())

out.close()

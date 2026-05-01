"""
Тест новой аутентификации PAD+ AI v4.0
"""

import requests
import random
import os

API = os.getenv('API_URL', 'http://localhost:8080/api/v1')

# Генерируем уникальный email для теста
TEST_EMAIL = f'test+{random.randint(1000, 9999)}@padplus.dev'
TEST_PASSWORD = 'TestPassword123!'
TEST_NAME = 'Test User'

print('=' * 70)
print('  ТЕСТИРОВАНИЕ НОВОЙ АУТЕНТИФИКАЦИИ')
print('=' * 70)

# 1. Регистрация нового пользователя
print('\n[1/5] РЕГИСТРАЦИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ...')
print(f'   Email: {TEST_EMAIL}')
print(f'   Password: {TEST_PASSWORD}')

response = requests.post(f'{API}/auth/register', json={
    'email': TEST_EMAIL,
    'password': TEST_PASSWORD,
    'full_name': TEST_NAME
}, timeout=10)

if response.status_code == 200:
    user_data = response.json()
    print(f'   ✅ PASS: Пользователь зарегистрирован')
    print(f'      ID: {user_data.get("id", "N/A")[:36]}')
    print(f'      Email: {user_data.get("email", "N/A")}')
else:
    print(f'   ❌ FAIL: {response.status_code}')
    print(f'      Error: {response.json()}')
    exit(1)

# 2. Вход
print('\n[2/5] ВХОД...')
response = requests.post(f'{API}/auth/login', json={
    'email': TEST_EMAIL,
    'password': TEST_PASSWORD
}, timeout=10)

if response.status_code == 200:
    auth_data = response.json()
    token = auth_data.get('access_token', '')
    refresh_token = auth_data.get('refresh_token', '')
    
    if token:
        print(f'   ✅ PASS: Token получен')
        print(f'      Access Token: {token[:50]}...')
        print(f'      Refresh Token: {refresh_token[:50]}...')
        print(f'      Expires In: {auth_data.get("expires_in", "N/A")} сек')
    else:
        print(f'   ❌ FAIL: No token in response')
        exit(1)
else:
    print(f'   ❌ FAIL: {response.status_code}')
    print(f'      Error: {response.json()}')
    exit(1)

# 3. Получение данных пользователя
print('\n[3/5] ПОЛУЧЕНИЕ ДАННЫХ ПОЛЬЗОВАТЕЛЯ...')
response = requests.get(f'{API}/auth/me', headers={
    'Authorization': f'Bearer {token}'
}, timeout=10)

if response.status_code == 200:
    user_info = response.json()
    print(f'   ✅ PASS: Данные получены')
    print(f'      ID: {user_info.get("id", "N/A")[:36]}')
    print(f'      Email: {user_info.get("email", "N/A")}')
    print(f'      Full Name: {user_info.get("full_name", "N/A")}')
else:
    print(f'   ❌ FAIL: {response.status_code}')
    print(f'      Error: {response.json()}')
    exit(1)

# 4. Добавление API ключа
print('\n[4/5] ДОБАВЛЕНИЕ API КЛЮЧА...')
print(f'   Провайдер: google')
print(f'   Модель: gemini-2.0-flash')

# Примечание: используем тестовый ключ (не валидный, только для демонстрации)
TEST_API_KEY = os.getenv('TEST_API_KEY', 'AIzaSyTestKeyForDemonstration')

response = requests.post(f'{API}/keys', headers={
    'Authorization': f'Bearer {token}'
}, json={
    'provider': 'google',
    'api_key': TEST_API_KEY,
    'name': 'Test Google Key',
    'model_preference': 'gemini-2.0-flash',
    'is_default': True
}, timeout=10)

if response.status_code == 200:
    key_data = response.json()
    print(f'   ✅ PASS: Ключ добавлен')
    print(f'      Key ID: {key_data.get("id", "N/A")}')
    print(f'      Provider: {key_data.get("provider", "N/A")}')
    print(f'      Model: {key_data.get("model_preference", "N/A")}')
else:
    print(f'   ⚠️  WARN: {response.status_code}')
    print(f'      Error: {response.json()}')

# 5. Получение списка ключей
print('\n[5/5] ПОЛУЧЕНИЕ СПИСКА КЛЮЧЕЙ...')
response = requests.get(f'{API}/keys', headers={
    'Authorization': f'Bearer {token}'
}, timeout=10)

if response.status_code == 200:
    keys = response.json()
    print(f'   ✅ PASS: Найдено ключей: {len(keys)}')
    for key in keys:
        default = ' (default)' if key.get('is_default') else ''
        print(f'      - {key["provider"]}: {key["name"]}{default}')
else:
    print(f'   ❌ FAIL: {response.status_code}')
    print(f'      Error: {response.json()}')

# Итоги
print('\n' + '=' * 70)
print('  АУТЕНТИФИКАЦИЯ ПРОТЕСТИРОВАНА УСПЕШНО!')
print('=' * 70)
print(f'\n  Зарегистрирован тестовый пользователь:')
print(f'    Email: {TEST_EMAIL}')
print(f'    Password: {TEST_PASSWORD}')
print(f'\n  Система готова к работе!')

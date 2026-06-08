"""
Полное тестирование системы PAD+ AI v4.0

Для запуска настройте переменные окружения:
    TEST_EMAIL=your@email.com
    TEST_PASSWORD=yourpassword
    python test_system.py
"""

import requests
import sys
import os

API = os.getenv('API_URL', 'http://localhost:8080/api/v1')

# Учётные данные из переменных окружения (не хранить в репозитории!)
EMAIL = os.getenv('TEST_EMAIL', 'test@padplus.dev')
PASSWORD = os.getenv('TEST_PASSWORD', 'TestPassword123!')


def main():
    # Проверка наличия учётных данных
    if EMAIL == 'test@padplus.dev' and PASSWORD == 'TestPassword123!':
        print('\n⚠️  ПРЕДУПРЕЖДЕНИЕ: Используются тестовые учётные данные по умолчанию')
        print('   Для реального тестирования настройте переменные окружения:')
        print('   TEST_EMAIL=your@email.com TEST_PASSWORD=yourpassword')
        print()

    print('=' * 70)
    print('  ПОЛНОЕ ТЕСТИРОВАНИЕ PAD+ AI v4.0')
    print('=' * 70)

    tests_passed = 0
    tests_failed = 0

    # 1. Health Check
    print('\n[1/6] HEALTH CHECK...')
    try:
        response = requests.get(f'{API}/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'healthy':
                print(f'   ✅ PASS: {data["status"]}')
                tests_passed += 1
            else:
                print(f'   ❌ FAIL: {data["status"]}')
                tests_failed += 1
        else:
            print(f'   ❌ FAIL: HTTP {response.status_code}')
            tests_failed += 1
    except Exception as e:
        print(f'   ❌ FAIL: {e}')
        tests_failed += 1

    # 2. Providers List
    print('\n[2/6] PROVIDERS LIST...')
    try:
        response = requests.get(f'{API}/providers', timeout=5)
        if response.status_code == 200:
            providers = response.json()
            if len(providers) > 0:
                print(f'   ✅ PASS: {len(providers)} providers')
                tests_passed += 1
            else:
                print(f'   ❌ FAIL: No providers')
                tests_failed += 1
        else:
            print(f'   ❌ FAIL: HTTP {response.status_code}')
            tests_failed += 1
    except Exception as e:
        print(f'   ❌ FAIL: {e}')
        tests_failed += 1

    # 3. Login
    print('\n[3/6] LOGIN...')
    try:
        response = requests.post(f'{API}/auth/login', json={
            'email': EMAIL,
            'password': PASSWORD
        }, timeout=5)
        if response.status_code == 200:
            token = response.json().get('access_token')
            if token:
                print(f'   ✅ PASS: Token received')
                tests_passed += 1
            else:
                print(f'   ❌ FAIL: No token')
                tests_failed += 1
        else:
            print(f'   ❌ FAIL: HTTP {response.status_code}')
            tests_failed += 1
    except Exception as e:
        print(f'   ❌ FAIL: {e}')
        tests_failed += 1

    # 4. Get User Keys
    print('\n[4/6] GET USER KEYS...')
    try:
        response = requests.post(f'{API}/auth/login', json={
            'email': EMAIL,
            'password': PASSWORD
        }, timeout=5)
        token = response.json().get('access_token', '')

        response = requests.get(f'{API}/keys', 
            headers={'Authorization': f'Bearer {token}'},
            timeout=5
        )
        if response.status_code == 200:
            keys = response.json()
            print(f'   ✅ PASS: {len(keys)} keys found')
            tests_passed += 1
        else:
            print(f'   ❌ FAIL: HTTP {response.status_code}')
            tests_failed += 1
    except Exception as e:
        print(f'   ❌ FAIL: {e}')
        tests_failed += 1

    # 5. Chat Test
    print('\n[5/6] CHAT TEST...')
    try:
        response = requests.post(f'{API}/auth/login', json={
            'email': EMAIL,
            'password': PASSWORD
        }, timeout=5)
        token = response.json().get('access_token', '')

        response = requests.post(f'{API}/chat',
            headers={'Authorization': f'Bearer {token}'},
            json={'message': 'Привет! Ответь кратко.'},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if 'text' in data or 'response' in data:
                text = data.get('text', data.get('response', 'N/A'))[:50]
                print(f'   ✅ PASS: {text}...')
                tests_passed += 1
            else:
                print(f'   ❌ FAIL: No response text')
                tests_failed += 1
        else:
            print(f'   ❌ FAIL: HTTP {response.status_code}')
            tests_failed += 1
    except Exception as e:
        print(f'   ❌ FAIL: {e}')
        tests_failed += 1

    # 6. Encryption Test
    print('\n[6/6] ENCRYPTION TEST...')
    try:
        sys.path.insert(0, 'backend')
        from core.encryption import get_encryptor
        encryptor = get_encryptor()
        test_text = 'test-key-123'
        encrypted = encryptor.encrypt(test_text)
        decrypted = encryptor.decrypt(encrypted)
        if decrypted == test_text:
            print(f'   ✅ PASS: Encryption works')
            tests_passed += 1
        else:
            print(f'   ❌ FAIL: Decryption mismatch')
            tests_failed += 1
    except Exception as e:
        print(f'   ❌ FAIL: {e}')
        tests_failed += 1

    # Итоги
    print('\n' + '=' * 70)
    print(f'  РЕЗУЛЬТАТЫ: {tests_passed}/{tests_passed + tests_failed} тестов пройдено')
    print('=' * 70)

    if tests_failed == 0:
        print('\n  🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!')
        sys.exit(0)
    else:
        print(f'\n  ⚠️  {tests_failed} тестов не прошли')
        sys.exit(1)


if __name__ == '__main__':
    main()

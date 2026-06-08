import os
import random
import requests

API = os.getenv('API_URL', 'http://localhost:8080/api/v1')

# Генерируем уникальный email для теста
TEST_EMAIL = f'test+{random.randint(1000, 9999)}@padplus.dev'
TEST_PASSWORD = 'TestPassword123!'
TEST_NAME = 'Test User'


def test_auth_clean_flow():
    response = requests.post(
        f'{API}/auth/register',
        json={
            'email': TEST_EMAIL,
            'password': TEST_PASSWORD,
            'full_name': TEST_NAME,
        },
        timeout=10,
    )
    assert response.status_code == 200, f'Registration failed: {response.status_code} {response.text}'

    user_data = response.json()
    assert user_data.get('email') == TEST_EMAIL

    response = requests.post(
        f'{API}/auth/login',
        json={
            'email': TEST_EMAIL,
            'password': TEST_PASSWORD,
        },
        timeout=10,
    )
    assert response.status_code == 200, f'Login failed: {response.status_code} {response.text}'

    auth_data = response.json()
    token = auth_data.get('access_token')
    assert token, f'Missing access token: {response.text}'

    response = requests.get(
        f'{API}/auth/me',
        headers={'Authorization': f'Bearer {token}'},
        timeout=10,
    )
    assert response.status_code == 200, f'Auth /me failed: {response.status_code} {response.text}'
    profile = response.json()
    assert profile.get('email') == TEST_EMAIL

    test_api_key = os.getenv('TEST_API_KEY', 'AIzaSyTestKeyForDemonstration')
    response = requests.post(
        f'{API}/keys',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'provider': 'google',
            'api_key': test_api_key,
            'name': 'Test Google Key',
            'model_preference': 'gemini-2.0-flash',
            'is_default': True,
        },
        timeout=10,
    )

    assert response.status_code in (200, 201), f'Add key failed: {response.status_code} {response.text}'

    response = requests.get(
        f'{API}/keys',
        headers={'Authorization': f'Bearer {token}'},
        timeout=10,
    )
    assert response.status_code == 200, f'Fetch keys failed: {response.status_code} {response.text}'
    keys = response.json()
    assert isinstance(keys, list), f'Unexpected keys response: {keys}'

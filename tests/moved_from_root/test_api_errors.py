"""
Тест API для диагностики ошибок 500
"""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_endpoint(endpoint, method="GET", data=None, auth_token=None):
    """Тест эндпоинта"""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Origin": "http://localhost:5174"
    }
    
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"\n{'='*60}")
        print(f"ENDPOINT: {method} {endpoint}")
        print(f"STATUS: {response.status_code}")
        
        try:
            print(f"RESPONSE: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except:
            print(f"RESPONSE: {response.text[:500]}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ENDPOINT: {method} {endpoint}")
        print(f"ERROR: {e}")
        return False

def main():
    """Тест основных endpoints"""
    print("🔍 Тестирование API endpoints...")
    
    # Тест без auth
    endpoints_no_auth = [
        "/health",
        "/api/v1/providers",
    ]
    
    # Тест с auth (нужно будет добавить токен)
    endpoints_with_auth = [
        "/api/v1/keys?offset=0&limit=100",
        "/api/v1/mind-state",
        "/api/v1/metrics/activity",
        "/api/v1/metrics/system",
    ]
    
    print("\n=== Без авторизации ===")
    for endpoint in endpoints_no_auth:
        test_endpoint(endpoint)
    
    print("\n=== С авторизацией (требуется токен) ===")
    # Здесь нужно добавить реальный токен
    # auth_token = "your_token_here"
    # for endpoint in endpoints_with_auth:
    #     test_endpoint(endpoint, auth_token=auth_token)

if __name__ == "__main__":
    main()

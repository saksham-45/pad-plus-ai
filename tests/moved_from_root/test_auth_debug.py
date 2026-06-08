#!/usr/bin/env python3
"""
🔐 ТЕСТ АВТОРИЗАЦИИ - ДИАГНОСТИКА ПРОБЛЕМ

Проверяет:
✅ Эндпоинт регистрации
✅ Эндпоинт входа
✅ Эндпоинт refresh
✅ Эндпоинт me (профиль)
"""

import requests
import json
from datetime import datetime

# Конфигурация
BACKEND_URL = "http://localhost:8080"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_green(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_red(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_yellow(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_blue(text):
    print(f"{Colors.BLUE}🔍 {text}{Colors.END}")

def test_auth_endpoints():
    print(f"\n{Colors.BOLD}🔐 ТЕСТ АВТОРИЗАЦИИ - ДИАГНОСТИКА{Colors.END}")
    print("=" * 60)
    
    # Тестовые данные
    test_email = "test@padplus.ai"
    test_password = "test123456"
    
    # Тест 1: Регистрация нового пользователя
    print_blue("Тест 1: Регистрация нового пользователя")
    try:
        register_data = {
            "email": test_email,
            "password": test_password,
            "name": "Test User"
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/register",
            json=register_data,
            timeout=10
        )
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print_green(f"Регистрация успешна: {result.get('message', 'Success')}")
            print_green(f"User ID: {result.get('user', {}).get('id', 'N/A')}")
        elif response.status_code == 400:
            error = response.json()
            if "already exists" in str(error):
                print_yellow("Пользователь уже существует - это нормально")
            else:
                print_red(f"Ошибка регистрации: {error}")
        else:
            print_red(f"Ошибка регистрации: {response.status_code} - {response.text}")
            
    except Exception as e:
        print_red(f"Ошибка подключения: {e}")
    
    # Тест 2: Вход в систему
    print_blue("\nТест 2: Вход в систему")
    try:
        login_data = {
            "email": test_email,
            "password": test_password
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json=login_data,
            timeout=10
        )
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print_green("Вход успешный!")
            
            access_token = result.get('access_token')
            refresh_token = result.get('refresh_token')
            user_info = result.get('user', {})
            
            print(f"Access Token: {access_token[:20]}..." if access_token else "❌ Нет токена")
            print(f"Refresh Token: {refresh_token[:20]}..." if refresh_token else "❌ Нет refresh токена")
            print(f"User ID: {user_info.get('id', 'N/A')}")
            print(f"User Email: {user_info.get('email', 'N/A')}")
            
            # Тест 3: Проверка профиля с токеном
            print_blue("\nТест 3: Проверка профиля с токеном")
            try:
                headers = {"Authorization": f"Bearer {access_token}"}
                
                profile_response = requests.get(
                    f"{BACKEND_URL}/api/v1/auth/me",
                    headers=headers,
                    timeout=10
                )
                
                print(f"Статус: {profile_response.status_code}")
                
                if profile_response.status_code == 200:
                    profile = profile_response.json()
                    print_green("Профиль получен успешно!")
                    print(f"ID: {profile.get('id', 'N/A')}")
                    print(f"Email: {profile.get('email', 'N/A')}")
                    print(f"Name: {profile.get('name', 'N/A')}")
                else:
                    print_red(f"Ошибка профиля: {profile_response.status_code} - {profile_response.text}")
                    
            except Exception as e:
                print_red(f"Ошибка проверки профиля: {e}")
            
            # Тест 4: Проверка API ключей с токеном
            print_blue("\nТест 4: Проверка API ключей с токеном")
            try:
                headers = {"Authorization": f"Bearer {access_token}"}
                
                keys_response = requests.get(
                    f"{BACKEND_URL}/api/v1/keys",
                    headers=headers,
                    timeout=10
                )
                
                print(f"Статус: {keys_response.status_code}")
                
                if keys_response.status_code == 200:
                    keys = keys_response.json()
                    print_green(f"Ключи получены: {len(keys)} шт.")
                else:
                    error = keys_response.json()
                    print_red(f"Ошибка ключей: {keys_response.status_code} - {error}")
                    
            except Exception as e:
                print_red(f"Ошибка проверки ключей: {e}")
            
        else:
            error = response.json()
            print_red(f"Ошибка входа: {response.status_code} - {error}")
            
    except Exception as e:
        print_red(f"Ошибка входа: {e}")
    
    # Тест 5: Проверка доступности эндпоинтов
    print_blue("\nТест 5: Проверка доступности эндпоинтов")
    endpoints = [
        "/api/v1/auth/register",
        "/api/v1/auth/login", 
        "/api/v1/auth/refresh",
        "/api/v1/auth/me",
        "/api/v1/auth/logout"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            method = "GET" if response.status_code != 405 else "POST"
            print(f"{endpoint}: {response.status_code} (метод: {method})")
        except Exception as e:
            print(f"{endpoint}: Ошибка - {e}")
    
    print("\n" + "=" * 60)
    print(f"{Colors.BOLD}📊 ЗАКЛЮЧЕНИЕ{Colors.END}")
    print("1. Если регистрация работает - создай нового пользователя")
    print("2. Если вход работает - используй правильные email/пароль")
    print("3. Если профиль работает - токены работают корректно")
    print("4. Если ключи работают - RLS настроен правильно")
    print("\nЕсли что-то не работает - проверь SQL миграции в Supabase!")

if __name__ == "__main__":
    test_auth_endpoints()

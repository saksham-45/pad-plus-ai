@echo off
chcp 65001 >nul
title PAD+ AI - Проверка системы

echo ============================================
echo   PAD+ AI v4.0 - Проверка системы...
echo ============================================
echo.

:: Проверяем наличие Python
echo [1/5] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ Python не найден! Установите Python 3.10+
) else (
    python --version
    echo   ✓ Python установлен
)

:: Проверяем наличие Node.js
echo.
echo [2/5] Проверка Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ Node.js не найден! Установите Node.js 18+
) else (
    node --version
    echo   ✓ Node.js установлен
)

:: Проверяем наличие pip пакетов
echo.
echo [3/5] Проверка Python пакетов...
pip show supabase >nul 2>&1
if errorlevel 1 (
    echo   ✗ Пакет supabase не установлен!
    echo     Установите: pip install supabase
) else (
    echo   ✓ Пакет supabase установлен
)

pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo   ✗ Пакет fastapi не установлен!
    echo     Установите: pip install fastapi uvicorn
) else (
    echo   ✓ Пакет fastapi установлен
)

pip show python-dotenv >nul 2>&1
if errorlevel 1 (
    echo   ✗ Пакет python-dotenv не установлен!
    echo     Установите: pip install python-dotenv
) else (
    echo   ✓ Пакет python-dotenv установлен
)

:: Проверяем наличие npm пакетов
echo.
echo [4/5] Проверка Frontend зависимостей...
if exist "frontend\node_modules" (
    echo   ✓ Node modules установлены
) else (
    echo   ✗ Node modules не установлены!
    echo     Выполните: cd frontend ^&^& npm install
)

:: Проверяем .env файл
echo.
echo [5/5] Проверка .env файла...
if exist ".env" (
    echo   ✓ .env файл найден
    findstr /C:"SUPABASE_URL=" .env >nul 2>&1
    if errorlevel 1 (
        echo   ✗ SUPABASE_URL не настроен в .env!
    ) else (
        echo   ✓ SUPABASE_URL настроен
    )
    findstr /C:"SUPABASE_KEY=" .env >nul 2>&1
    if errorlevel 1 (
        echo   ✗ SUPABASE_KEY не настроен в .env!
    ) else (
        echo   ✓ SUPABASE_KEY настроен
    )
    findstr /C:"ENCRYPTION_KEY=" .env >nul 2>&1
    if errorlevel 1 (
        echo   ✗ ENCRYPTION_KEY не настроен в .env!
    ) else (
        echo   ✓ ENCRYPTION_KEY настроен
    )
) else (
    echo   ✗ .env файл не найден!
    echo     Скопируйте .env.example в .env и настройте
)

:: Проверяем порты
echo.
echo ============================================
echo   Проверка состояния портов:
echo ============================================

set BACKEND_RUNNING=0
set FRONTEND_RUNNING=0

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080 ^| findstr LISTENING') do (
    echo   - Порт 8080 занят (PID %%a) - Backend работает
    set BACKEND_RUNNING=1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5174 ^| findstr LISTENING') do (
    echo   - Порт 5174 занят (PID %%a) - Frontend работает
    set FRONTEND_RUNNING=1
)

if "%BACKEND_RUNNING%"=="0" (
    echo   - Порт 8080 свободен - Backend не запущен
)

if "%FRONTEND_RUNNING%"=="0" (
    echo   - Порт 5174 свободен - Frontend не запущен
)

echo.
echo ============================================
echo   Итоги проверки:
echo ============================================

if "%BACKEND_RUNNING%"=="1" if "%FRONTEND_RUNNING%"=="1" (
    echo   ✓ Система работает!
    echo.
    echo   Frontend: http://localhost:5174
    echo   Backend:  http://localhost:8080
    echo.
) else (
    echo   ⚠ Система не запущена
    echo.
    echo   Для запуска выполните: start.bat
    echo.
)

pause
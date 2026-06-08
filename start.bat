@echo off
chcp 65001 >nul
title PAD+ AI - Запуск системы

echo ============================================
echo   PAD+ AI v4.0 - Система запускается...
echo ============================================
echo.

:: Активация venv если существует
if exist "venv\Scripts\activate.bat" (
    echo [0/5] Активация виртуального окружения...
    call venv\Scripts\activate
    echo   ✓ venv активирован
    echo.
) else (
    echo ⚠ venv не найден! Запуск без виртуального окружения.
    echo   Для создания: python -m venv venv
    echo.
)

:: Освобождаем порты если они заняты
echo [1/5] Проверка и освобождение портов...

:: Проверяем порт 8080 (backend)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080 ^| findstr LISTENING') do (
    echo   - Порт 8080 занят PID %%a, освобождаем...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 1 >nul
)

:: Проверяем порт 5174 (frontend)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5174 ^| findstr LISTENING') do (
    echo   - Порт 5174 занят PID %%a, освобождаем...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 1 >nul
)

echo   ✓ Порты освобождены
echo.

:: Запускаем backend
echo [2/5] Запуск Backend (порт 8080)...
cd /d "%~dp0backend"
set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" (
    start "PAD+ AI Backend" cmd /k "echo Backend запускается... && set PORT=8080 && "%PYTHON_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
) else (
    start "PAD+ AI Backend" cmd /k "echo Backend запускается... && set PORT=8080 && uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
)
cd /d "%~dp0"

:: Ждём пока backend загрузится
echo   ⏳ Ожидание запуска backend...
timeout /t 5 >nul

:: Проверяем что backend действительно готов
echo   🔄 Проверка доступности backend...
for /l %%i in (1,1,10) do (
    curl -s http://127.0.0.1:8080/health >nul 2>&1 && (
        echo   ✓ Backend готов!
        goto :backend_ready
    )
    echo   ⏳ Попытка %%i/10...
    timeout /t 2 >nul
)

echo   ⚠ Backend не ответил за 25 секунд, продолжаем...
:backend_ready

:: Запускаем frontend
echo [3/5] Запуск Frontend (порт 5174)...
cd /d "%~dp0frontend"
start "PAD+ AI Frontend" cmd /k "echo Frontend запускается... && npm run dev"
cd /d "%~dp0"

timeout /t 2 >nul

:: Открываем браузер
echo [4/5] Открытие браузера...
start http://localhost:5174

echo.
echo ============================================
echo   ✓ Система PAD+ AI запущена!
echo ============================================
echo.
echo   Frontend: http://localhost:5174
echo   Backend:  http://localhost:8080
echo.
echo   Для остановки запустите: stop.bat
echo.
pause
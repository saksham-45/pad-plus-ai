@echo off
chcp 65001 >nul
title 🧠 PAD+ AI - Запуск

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║             🧠 PAD+ AI v3.5 - Запуск системы               ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

:: Переход в директорию проекта
cd /d "%~dp0"

:: Проверка Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не найден! Установите Python 3.10+
    pause
    exit /b 1
)

:: Проверка Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js не найден! Установите Node.js 18+
    pause
    exit /b 1
)

echo ✅ Python найден
echo ✅ Node.js найден
echo.

:: Создание директории для данных
if not exist "data" mkdir data
echo ✅ Директория данных готова
echo.

:: Запуск Backend
echo ─────────────────────────────────────────────────────────────
echo 🚀 Запуск Backend (порт 8000)...
echo ─────────────────────────────────────────────────────────────
start "PAD+ Backend" cmd /k "cd /d "%~dp0" && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: Ожидание запуска backend
timeout /t 3 /nobreak >nul

:: Запуск Frontend
echo.
echo ─────────────────────────────────────────────────────────────
echo 🚀 Запуск Frontend (порт 5173)...
echo ─────────────────────────────────────────────────────────────
start "PAD+ Frontend" cmd /k "cd /d "%~dp0\frontend" && npm run dev"

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║                  ✅ Система запущена!                      ║
echo  ╠═══════════════════════════════════════════════════════════╣
echo  ║  Frontend:  http://localhost:5173                         ║
echo  ║  Backend:   http://localhost:8000                         ║
echo  ║  API Docs:  http://localhost:8000/docs                    ║
echo  ╠═══════════════════════════════════════════════════════════╣
echo  ║  Для остановки запустите: stop.bat                        ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

:: Открытие браузера
timeout /t 5 /nobreak >nul
echo 🌐 Открытие браузера...
start http://localhost:5173

echo.
echo Нажмите любую клавишу для закрытия этого окна...
pause >nul
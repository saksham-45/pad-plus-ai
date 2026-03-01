@echo off
chcp 65001 >nul
title 🧠 PAD+ AI - Остановка

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║           🧠 PAD+ AI v3.5 - Остановка системы              ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

echo 🛑 Остановка Backend (uvicorn)...
taskkill /f /im python.exe /fi "WINDOWTITLE eq PAD+ Backend*" >nul 2>&1

echo 🛑 Остановка Frontend (node)...
taskkill /f /im node.exe /fi "WINDOWTITLE eq PAD+ Frontend*" >nul 2>&1

:: Дополнительная очистка портов
echo.
echo 🧹 Освобождение портов...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║                  ✅ Система остановлена!                   ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

timeout /t 2 /nobreak >nul
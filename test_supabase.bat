@echo off
chcp 65001 >nul
title 🧪 Тест Supabase

echo.
echo ╔═════════════════════════════════════════════════════════╗
echo ║           🧪 Тест подключения к Supabase PostgreSQL        ║
echo ╚═══════════════════════════════════════════════════════╝
echo.

echo 🔧 Установка переменных окружения...
set DATABASE_URL=postgresql://postgres:TiMuPom13Q5OfKBi@db.hgjbjccpeirwrabbcjhr.supabase.co:5432/postgres
echo ✅ DATABASE_URL установлена
echo.

echo 🧪 Запуск теста...
python test_supabase.py

echo.
echo ╔═════════════════════════════════════════════════════╗
echo ║                   Тест завершен!                     ║
echo ╚═════════════════════════════════════════════════════╝
echo.

echo Нажмите любую клавишу для закрытия...
pause >nul

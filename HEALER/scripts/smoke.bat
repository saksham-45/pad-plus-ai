@echo off
chcp 65001 >nul
title HEALER Smoke Test
cd /d "%~dp0.."
echo ==============================================
echo   HEALER Smoke Test
echo ==============================================
python scripts/smoke_test.py
if %errorlevel% equ 0 (
    echo.
    echo [OK] Smoke test passed
) else (
    echo.
    echo [FAIL] Smoke test failed
)
pause

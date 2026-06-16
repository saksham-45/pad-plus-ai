@echo off
chcp 65001 >nul
title HEALER Deploy
cd /d "%~dp0.."
echo ==============================================
echo   HEALER Deploy
echo ==============================================
echo.
echo [1/3] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Python not found. Install Python 3.12+ from python.org
    pause
    exit /b 1
)
python --version
echo [OK]

echo [2/3] Installing pytest (optional)...
pip install pytest 2>nul
echo [OK]

echo [3/3] Running smoke test...
python scripts/smoke_test.py
if %errorlevel% neq 0 (
    echo [FAIL] Smoke test failed
    pause
    exit /b 1
)

echo.
echo ==============================================
echo   HEALER ready
echo ==============================================
echo.
echo Commands:
echo   python main.py                             - demo
echo   python -m healer.diagnostics.runner        - CLI diagnostics
echo   python -m healer.diagnostics.runner --watch - monitoring
echo   python -m pytest tests/                    - unit tests
echo   python -m healer.diagnostics.integration_test - integration tests
echo   cd ../healer-viewer ^&^& start.bat         - viewer
echo.
pause

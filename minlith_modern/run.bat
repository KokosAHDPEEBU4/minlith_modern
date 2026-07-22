@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==============================
echo  MINLITH Modern — Install ^& Run
echo ==============================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.12+ and add to PATH.
    pause
    exit /b 1
)

:: Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo       Done.
echo.

:: Launch
echo [2/2] Launching MINLITH Modern...
echo.
python src\main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error.
    pause
)

@echo off
setlocal enabledelayedexpansion
rem ============================================================
rem  Автосборка MINLITH Modern (PyInstaller, onedir, windowed).
rem  Результат:  ..\minlith_exe\MINLITH\MINLITH.exe
rem  onedir (папка) — быстрый запуск, т.к. НЕ распаковывает 100+ МБ
rem  во временную папку при каждом старте (в отличие от --onefile).
rem  Для переноса на другое устройство копируйте папку MINLITH целиком.
rem  Запуск: build_exe.bat [--onefile]   (по умолчанию onedir)
rem ============================================================

cd /d "%~dp0"
set "PROJ=%~dp0"
set "OUT=%~dp0..\minlith_exe"
set "ONEFILE="
if /i "%~1"=="--onefile" set "ONEFILE=--onefile"

echo [1/4] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден в PATH.
    goto :err
)

echo [2/4] Проверка PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller не найден — устанавливаю...
    python -m pip install --upgrade pyinstaller || goto :err
)

echo [3/4] Очистка прошлой сборки...
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"

echo [4/4] Сборка MINLITH.exe (onedir%ONEFILE%)...
python -m PyInstaller --noconfirm --clean --windowed %ONEFILE% ^
    --name MINLITH ^
    --distpath "%OUT%" ^
    --workpath "%OUT%\_work" ^
    --specpath "%OUT%" ^
    --add-data "%PROJ%src\gui\styles;src/gui/styles" ^
    --add-data "%PROJ%src\core\excel_port\data;src/core/excel_port/data" ^
    --collect-submodules src ^
    "%PROJ%src\main.py"
if errorlevel 1 goto :err

echo.
if defined ONEFILE (
    echo ГОТОВО: "%OUT%\MINLITH.exe"  ^(одним файлом^)
) else (
    echo ГОТОВО: "%OUT%\MINLITH\MINLITH.exe"  ^(папка — для переноса копируйте её целиком^)
)
goto :eof

:err
echo.
echo ОШИБКА сборки. Смотрите вывод выше.
exit /b 1

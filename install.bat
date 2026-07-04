@echo off
title GreatOCR Installer

echo ============================================
echo   GreatOCR V2.3 - Windows Installer
echo ============================================
echo.

REM ---------- 1. Python check ----------
echo [1/4] Checking Python ...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found.
    echo Please install Python 3.11+ from:
    echo   https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo     Python: %PY_VER%
echo.

REM ---------- 2. Create venv ----------
echo [2/4] Creating virtual environment ...
if exist ".venv\Scripts\python.exe" (
    echo     Virtual environment already exists, skipping.
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo     Virtual environment created.
)
echo.

REM ---------- 3. Install Python deps ----------
echo [3/4] Installing Python dependencies (Tsinghua mirror) ...
.venv\Scripts\python.exe -m pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo.
    echo [ERROR] Python dependency installation failed.
    pause
    exit /b 1
)
echo     Python dependencies installed.
echo.

REM ---------- 4. Node.js check ----------
echo [4/4] Checking Node.js ...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================
    echo   Node.js not found!
    echo ============================================
    echo.
    echo GreatOCR requires Node.js 20 or later.
    echo Download from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)
echo     Node.js: OK
echo.

REM ---------- 5. Frontend deps ----------
echo [5/5] Installing frontend dependencies (npmmirror) ...
if exist "frontend\node_modules" (
    echo     Already installed, skipping.
) else (
    cd frontend
    node ..\scripts\install_frontend.mjs
    if errorlevel 1 (
        cd ..
        echo.
        echo [ERROR] Frontend dependency installation failed.
        pause
        exit /b 1
    )
    cd ..
    echo     Frontend dependencies installed.
)
echo.

echo ============================================
echo   GreatOCR V2.3 Installation Complete!
echo ============================================
echo.
echo To start: double-click start.bat
echo.
pause

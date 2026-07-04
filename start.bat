@echo off
title GreatOCR Launcher

echo ============================================
echo   GreatOCR V2.3 - Windows Launcher
echo ============================================
echo.

REM ---------- Check venv ----------
echo [1/3] Checking backend dependencies ...
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] Virtual environment not found.
    echo Please run install.bat first.
    pause
    exit /b 1
)
echo     OK
echo.

REM ---------- Check frontend deps ----------
echo [2/3] Checking frontend dependencies ...
if not exist "frontend\node_modules" (
    echo.
    echo [ERROR] Frontend dependencies not found.
    echo Please run install.bat first.
    pause
    exit /b 1
)
echo     OK
echo.

REM ---------- Start services ----------
echo [3/3] Starting services ...
echo.
echo     Starting backend (port 8399) ...
start "GreatOCR Backend" /min cmd /c ".venv\Scripts\python.exe scripts\serve.py"
echo     Waiting for backend to start ...
timeout /t 3 /nobreak >nul
echo.

echo     Starting frontend (port 5173) ...
echo.
echo    - - - - - - - - - - - - - - - - - - - - - -
echo    Browser will open automatically.
echo    If not, visit:
echo    http://127.0.0.1:5173
echo    - - - - - - - - - - - - - - - - - - - - - -
echo.
cd frontend
call npx pnpm dev --open
cd ..

echo.
echo ============================================
echo   Services stopped.
echo ============================================
echo.
echo If the backend window did not close automatically,
echo please close the "GreatOCR Backend" window manually.
echo.
pause

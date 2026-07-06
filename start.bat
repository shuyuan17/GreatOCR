@echo off
setlocal
cd /d "%~dp0"
title GreatOCR Launcher

set "INSTALL_MARKER=.greatocr-installed"

echo ============================================
echo   GreatOCR V2.3 - Windows Launcher
echo ============================================
echo.

if not exist "%INSTALL_MARKER%" (
    echo [ERROR] GreatOCR is not installed yet.
    echo Please run install.bat first.
    pause
    exit /b 1
)

echo [1/4] Checking Python ...
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python environment not found.
    echo Please run install.bat again.
    pause
    exit /b 1
)
echo     OK
echo.

echo [2/4] Preparing local session ...
for /f "delims=" %%I in ('.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"') do set "GREATOCR_SESSION_TOKEN=%%I"
set "GREATOCR_ALLOWED_ORIGIN=http://localhost:5173"
set "VITE_GREAT_OCR_TOKEN=%GREATOCR_SESSION_TOKEN%"
echo     Session prepared
echo.

echo [3/4] Checking Node.js ...
set "NODE_EXE="
for /f "delims=" %%I in ('where node 2^>nul') do (
    if not defined NODE_EXE set "NODE_EXE=%%I"
)

if not defined NODE_EXE (
    echo [ERROR] Node.js not found.
    echo Please install Node.js LTS and make sure it is added to PATH.
    pause
    exit /b 1
)

"%NODE_EXE%" --version
echo.

echo [4/4] Checking frontend dependencies ...
if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies not found.
    echo Please run install.bat again.
    pause
    exit /b 1
)
echo     OK
echo.

echo Starting backend ...
start "GreatOCR Backend" cmd /k "cd /d "%~dp0" && ".venv\Scripts\python.exe" "scripts\serve.py""

timeout /t 3 /nobreak >nul

echo Starting frontend ...
start "GreatOCR Frontend" cmd /k "cd /d "%~dp0frontend" && "%NODE_EXE%" "node_modules\vite\bin\vite.js" --host localhost --open"

echo.
echo GreatOCR is starting.
echo Close the Backend and Frontend windows to stop GreatOCR.
echo.
pause
exit /b 0
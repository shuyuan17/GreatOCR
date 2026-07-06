@echo off
setlocal
cd /d "%~dp0"
title GreatOCR Installer

set "INSTALL_MARKER=.greatocr-installed"

echo ============================================
echo   GreatOCR V2.3 - Windows Installer
echo ============================================
echo.

if not exist "pyproject.toml" (
    echo [ERROR] Project files not found.
    echo Please run this file inside the GreatOCR folder.
    echo.
    pause
    exit /b 1
)

echo [1/6] Checking Python ...
python --version
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found.
    echo Please install Python 3.11+ and enable "Add Python to PATH".
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo.

echo [2/6] Checking Node.js ...
call :resolve_node
if errorlevel 1 (
    echo.
    echo [ERROR] Node.js not found.
    echo Please install Node.js LTS and enable "Add to PATH".
    echo Download: https://nodejs.org/
    echo.
    pause
    exit /b 1
)
"%NODE_EXE%" --version
echo.

echo [3/6] Checking npm ...
if not exist "%NPM_CLI%" (
    echo.
    echo [ERROR] npm not found.
    echo Please reinstall Node.js LTS with npm included.
    echo.
    pause
    exit /b 1
)
"%NODE_EXE%" "%NPM_CLI%" --version
echo.

echo [4/6] Creating virtual environment ...
if exist ".venv\Scripts\python.exe" (
    echo     Already exists, skipping.
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )
    echo     Created.
)
echo.

echo [5/6] Installing Python dependencies ...
.venv\Scripts\python.exe -m pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo.
    echo [ERROR] Python dependency installation failed.
    echo.
    pause
    exit /b 1
)
echo     Python dependencies installed.
echo.

echo [6/6] Installing frontend dependencies ...
"%NODE_EXE%" scripts\install_frontend.mjs
if errorlevel 1 (
    echo.
    echo [ERROR] Frontend dependency installation failed.
    echo.
    pause
    exit /b 1
)
echo.

(
    echo installed_at=%date% %time%
    echo python=.venv\Scripts\python.exe
    echo frontend=frontend\node_modules
) > "%INSTALL_MARKER%"

echo ============================================
echo   GreatOCR V2.3 Installation Complete
echo ============================================
echo.
echo Next step:
echo   Double-click start.bat
echo.
pause
exit /b 0

:resolve_node
set "NODE_EXE="
set "NPM_CLI="

for /f "delims=" %%I in ('where node 2^>nul') do (
    if not defined NODE_EXE set "NODE_EXE=%%I"
)

if not defined NODE_EXE if exist "C:\Program Files\nodejs\node.exe" set "NODE_EXE=C:\Program Files\nodejs\node.exe"
if not defined NODE_EXE if exist "C:\Program Files (x86)\nodejs\node.exe" set "NODE_EXE=C:\Program Files (x86)\nodejs\node.exe"
if not defined NODE_EXE if exist "%LOCALAPPDATA%\Programs\nodejs\node.exe" set "NODE_EXE=%LOCALAPPDATA%\Programs\nodejs\node.exe"

if not defined NODE_EXE exit /b 1

for %%I in ("%NODE_EXE%") do set "NODE_DIR=%%~dpI"
set "PATH=%NODE_DIR%;%PATH%"
set "NPM_CLI=%NODE_DIR%node_modules\npm\bin\npm-cli.js"
exit /b 0

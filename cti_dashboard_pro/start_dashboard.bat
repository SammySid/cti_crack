@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "BACKEND_SCRIPT=%ROOT_DIR%app\backend\dashboard_server.py"
set "DEFAULT_URL=http://localhost:8000"

title SS Cooling Tower LTD - Dashboard Launcher
echo =============================================================
echo   SS COOLING TOWER LTD ^| Thermal Analysis Dashboard
echo =============================================================
echo.

call :ensure_python
if errorlevel 1 goto :fatal

call :ensure_node
if errorlevel 1 goto :fatal

echo [0/4] Checking for existing server on port 8000...
powershell -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [1/4] Installing/validating Python dependencies...
"%PYTHON_EXE%" -m pip install --disable-pip-version-check --quiet --user xlsxwriter pandas openpyxl python-dateutil
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    goto :fatal
)

echo [2/4] Verifying Node.js runtime...
node --version
if errorlevel 1 (
    echo [ERROR] Node.js is still unavailable after installation attempt.
    goto :fatal
)

echo [3/4] Launching dashboard URL...
start "" "%DEFAULT_URL%"

echo [4/4] Starting local dashboard server...
echo.
echo Project Root: %ROOT_DIR%
echo URL: %DEFAULT_URL%
echo.
echo Keep this window open while using the dashboard.
echo.

"%PYTHON_EXE%" "%BACKEND_SCRIPT%"
if errorlevel 1 (
    echo.
    echo [ERROR] Dashboard server terminated unexpectedly.
    goto :fatal
)

echo.
echo Server stopped.
pause
exit /b 0

:ensure_python
set "PYTHON_EXE="
where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto :python_ready
)
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py -3"
    goto :python_ready
)

echo [INFO] Python not found. Attempting automatic install via winget...
where winget >nul 2>&1
if errorlevel 1 (
    echo [ERROR] winget is not available. Install Python 3.10+ manually and re-run.
    exit /b 1
)
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements >nul

where python >nul 2>&1
if not errorlevel 1 set "PYTHON_EXE=python"
if not defined PYTHON_EXE (
    where py >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=py -3"
)
if not defined PYTHON_EXE (
    echo [ERROR] Python installation failed.
    exit /b 1
)

:python_ready
echo [INFO] Using Python command: %PYTHON_EXE%
%PYTHON_EXE% --version
if errorlevel 1 (
    echo [ERROR] Python command failed.
    exit /b 1
)
%PYTHON_EXE% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Bootstrapping pip...
    %PYTHON_EXE% -m ensurepip --upgrade >nul 2>&1
)
exit /b 0

:ensure_node
where node >nul 2>&1
if not errorlevel 1 (
    node --version
    exit /b 0
)

echo [INFO] Node.js not found. Attempting automatic install via winget...
where winget >nul 2>&1
if errorlevel 1 (
    echo [ERROR] winget is not available. Install Node.js LTS manually and re-run.
    exit /b 1
)
winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements >nul
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js installation failed.
    exit /b 1
)
node --version
exit /b 0

:fatal
echo.
echo Setup/startup failed.
pause
exit /b 1

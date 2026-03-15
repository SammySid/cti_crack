@echo off
setlocal
cd /d "%~dp0\.."
echo ===================================================
echo   SS COOLING TOWER - PROFESSIONAL EXCEL GENERATOR  
echo ===================================================
echo.

:: 1. Check for thermal_data.json (Check root first, then reports folder)
if exist "reports\thermal_data.json" (
    set "JSFILE=reports\thermal_data.json"
) else if exist "web\reports\thermal_data.json" (
    copy "web\reports\thermal_data.json" "reports\thermal_data.json" >nul
    set "JSFILE=reports\thermal_data.json"
) else if exist "thermal_data.json" (
    set "JSFILE=thermal_data.json"
) else (
    echo [ERROR] thermal_data.json not found!
    echo Please open the dashboard and click "Export Data & Curves" first.
    echo.
    pause
    exit /b
)

:: 2. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python from python.org to use this feature.
    echo.
    pause
    exit /b
)

:: 3. Install dependencies quietly
echo Checking dependencies (xlsxwriter)...
python -m pip install xlsxwriter --quiet --user

:: 4. Run the generator
echo.
echo Generating specialized report...
python backend\excel_gen.py "%JSFILE%" "reports"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The report generation failed. 
) else (
    echo.
    echo ===================================================
    echo   SUCCESS: Your professional report is ready!
    echo   Check the "reports" folder for your files.
    echo ===================================================
)

echo.
pause

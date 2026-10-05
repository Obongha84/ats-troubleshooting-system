@echo off
title ATS - Automated Troubleshooting System
color 0A

cls
echo.
echo  ============================================================
echo    ATS - AUTOMATED TROUBLESHOOTING SYSTEM
echo  ============================================================
echo.
echo    Starting server, please wait...
echo.

cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Open browser after 3 seconds (in background)
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"

REM Start the Flask app
python web_app.py

pause
@echo off
title ATS Database Viewer
color 0A
cls

echo ============================================================
echo   ATS - DATABASE VIEWER
echo ============================================================
echo.

cd /d "%~dp0"
call venv\Scripts\activate.bat

python view_db.py

pause
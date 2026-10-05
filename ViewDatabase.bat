@echo off
title ATS Database Viewer
color 0A

echo ============================================================
echo   ATS - DATABASE VIEWER
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if DB Browser is installed
if exist "C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe" (
    start "" "C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe" "%~dp0instance\diagnoses.db"
    exit
)

if exist "C:\Program Files (x86)\DB Browser for SQLite\DB Browser for SQLite.exe" (
    start "" "C:\Program Files (x86)\DB Browser for SQLite\DB Browser for SQLite.exe" "%~dp0instance\diagnoses.db"
    exit
)

echo DB Browser for SQLite not found.
echo Please install it from: https://sqlitebrowser.org/dl/
echo.
pause
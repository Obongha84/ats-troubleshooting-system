@echo off
echo ============================================================
echo Installing PyInstaller and Building Application
echo ============================================================
echo.

echo Current directory: %cd%
echo.

echo Step 1: Installing PyInstaller...
echo Using: python -m pip install pyinstaller
python -m pip install pyinstaller

if errorlevel 1 (
    echo.
    echo Trying with py launcher...
    py -m pip install pyinstaller
)

if errorlevel 1 (
    echo.
    echo ❌ Failed to install PyInstaller!
    echo Please check that Python is installed correctly.
    echo.
    echo To check Python installation, run:
    echo   python --version
    echo   py --version
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ PyInstaller installed successfully!
echo.

echo Step 2: Building the application...
py -m PyInstaller --onefile --add-data "templates;templates" --add-data "static;static" --add-data "diagnostics.db;." --hidden-import flask --hidden-import flask_sqlalchemy --hidden-import sqlalchemy --hidden-import jinja2 --name "TroubleshootingSystem" launcher.py

if errorlevel 1 (
    echo.
    echo ❌ Build failed!
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ BUILD COMPLETE!
echo ============================================================
echo.
echo 📁 Executable location:
echo    %cd%\dist\TroubleshootingSystem.exe
echo.
echo 📝 To run the application:
echo    Double-click TroubleshootingSystem.exe
echo.
echo ============================================================
pause
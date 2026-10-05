# build.ps1
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Building Troubleshooting System Desktop Application" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Cleaning old builds..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue }
if (Test-Path "*.spec") { Remove-Item -Force "*.spec" -ErrorAction SilentlyContinue }

Write-Host ""
Write-Host "Building executable..." -ForegroundColor Yellow

python -m PyInstaller --onefile `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --add-data "diagnostics.db;." `
    --hidden-import flask `
    --hidden-import flask_sqlalchemy `
    --hidden-import sqlalchemy `
    --hidden-import jinja2 `
    --hidden-import markupsafe `
    --hidden-import reportlab `
    --hidden-import pandas `
    --hidden-import psutil `
    --name "ATSTroubleshootingSystem" `
    launcher.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "✅ BUILD COMPLETE!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "📁 Executable location:" -ForegroundColor Cyan
    Write-Host "    $PWD\dist\ATSTroubleshootingSystem.exe" -ForegroundColor White
    Write-Host ""
    Write-Host "📝 To run: Double-click ATSTroubleshootingSystem.exe" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Build failed!" -ForegroundColor Red
}

Read-Host "Press Enter to exit"
$ErrorActionPreference = 'Stop'
Write-Host "=== HMRA Live System Startup ===" -ForegroundColor Cyan

if (-not (Test-Path '.venv')) {
    Write-Host "Creating Python virtual environment (.venv)..." -ForegroundColor Yellow
    py -m venv .venv
}

Write-Host "Installing / verifying backend dependencies..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

if (-not (Test-Path '.env')) {
    Write-Host "Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item '.env.example' '.env'
    Write-Host "Please edit .env and configure your LLM_API_KEY (and optional BRAVE_API_KEY), then press Enter." -ForegroundColor Yellow
    Read-Host
}

Write-Host "Starting HMRA FastAPI server on http://127.0.0.1:8000 ..." -ForegroundColor Green
.\.venv\Scripts\python.exe run.py

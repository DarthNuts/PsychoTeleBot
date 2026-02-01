Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  PsychoTeleBot - Telegram Mode" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Checking configuration..." -ForegroundColor Yellow

if (-not (Test-Path -Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create .env file with your Telegram bot token:" -ForegroundColor Yellow
    Write-Host "TELEGRAM_BOT_TOKEN=your_token_here" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "See .env.example for reference." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Configuration found." -ForegroundColor Green
Write-Host "Starting Telegram bot..." -ForegroundColor Green
Write-Host ""

python -m adapters.telegram.run

if ($LASTEXITCODE -ne 0) {
    Write-Host "" 
    Write-Host "ERROR: Bot failed to start!" -ForegroundColor Red
    Write-Host "" 
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "1. Check if TELEGRAM_BOT_TOKEN is set in .env" -ForegroundColor Yellow
    Write-Host "2. Install dependencies: pip install -r requirements-telegram.txt" -ForegroundColor Yellow
    Write-Host "3. Check your internet connection" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
}

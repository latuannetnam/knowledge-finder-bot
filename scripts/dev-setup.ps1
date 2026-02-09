# Development setup script for Windows

Write-Host "Setting up nlm-chatbot development environment..." -ForegroundColor Green

# Check Python version
$pythonVersion = python --version 2>&1
if ($pythonVersion -notmatch "Python 3\.1[1-9]") {
    Write-Host "Error: Python 3.11+ required. Found: $pythonVersion" -ForegroundColor Red
    exit 1
}
Write-Host "Python version: $pythonVersion" -ForegroundColor Cyan

# Create virtual environment if not exists
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -e ".[dev]"

# Copy .env.example if .env doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Please edit .env with your Azure credentials" -ForegroundColor Cyan
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env with your Azure Bot credentials"
Write-Host "  2. Run: python -m knowledge_finder_bot.main"
Write-Host "  3. Use Bot Framework Emulator to test"

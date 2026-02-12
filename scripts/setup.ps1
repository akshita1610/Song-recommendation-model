# Song Recommendation System - Setup Script (PowerShell)
# This script sets up the development environment on Windows

Write-Host "🎵 Setting up Song Recommendation System..." -ForegroundColor Green

# Check Python version
try {
    $pythonVersion = python --version 2>&1
    $versionNumber = [regex]::Match($pythonVersion, '\d+\.\d+').Value
    $requiredVersion = "3.9"
    
    if ([version]$versionNumber -lt [version]$requiredVersion) {
        Write-Host "❌ Python $requiredVersion or higher is required. Found: $versionNumber" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Python version check passed: $versionNumber" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.9 or higher." -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "⬆️ Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install the package in development mode
Write-Host "📥 Installing package and dependencies..." -ForegroundColor Yellow
pip install -e .[dev]

# Setup pre-commit hooks
Write-Host "🪝 Setting up pre-commit hooks..." -ForegroundColor Yellow
pre-commit install

# Create necessary directories
Write-Host "📁 Creating necessary directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path logs, cache, data | Out-Null

# Copy environment file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "⚙️ Creating environment file..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "📝 Please edit .env file with your Spotify credentials" -ForegroundColor Cyan
}

# Run initial type check
Write-Host "🔍 Running initial type check..." -ForegroundColor Yellow
try {
    mypy src/
} catch {
    Write-Host "⚠️ Type check found issues - please fix them" -ForegroundColor Yellow
}

# Run tests
Write-Host "🧪 Running tests..." -ForegroundColor Yellow
try {
    pytest tests/
} catch {
    Write-Host "⚠️ Some tests failed - please check them" -ForegroundColor Yellow
}

Write-Host "🎉 Setup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file with your Spotify credentials"
Write-Host "2. Activate the environment: venv\Scripts\Activate.ps1"
Write-Host "3. Run the application: streamlit run main.py"
Write-Host ""
Write-Host "🛠️ Development commands:" -ForegroundColor Cyan
Write-Host "- Format code: black src/ main.py"
Write-Host "- Sort imports: isort src/ main.py"
Write-Host "- Type check: mypy src/"
Write-Host "- Run tests: pytest tests/"
Write-Host "- Run all checks: pre-commit run --all-files"

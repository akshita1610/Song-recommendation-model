#!/bin/bash

# Song Recommendation System - Setup Script
# This script sets up the development environment

set -e

echo "🎵 Setting up Song Recommendation System..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install the package in development mode
echo "📥 Installing package and dependencies..."
pip install -e .[dev]

# Setup pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs cache data

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your Spotify credentials"
fi

# Run initial type check
echo "🔍 Running initial type check..."
mypy src/ || echo "⚠️ Type check found issues - please fix them"

# Run tests
echo "🧪 Running tests..."
pytest tests/ || echo "⚠️ Some tests failed - please check them"

echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your Spotify credentials"
echo "2. Activate the environment: source venv/bin/activate"
echo "3. Run the application: streamlit run main.py"
echo ""
echo "🛠️ Development commands:"
echo "- Format code: black src/ main.py"
echo "- Sort imports: isort src/ main.py"
echo "- Type check: mypy src/"
echo "- Run tests: pytest tests/"
echo "- Run all checks: pre-commit run --all-files"

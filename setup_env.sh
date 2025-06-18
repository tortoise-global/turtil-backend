#!/bin/bash

# Turtil Backend - Virtual Environment Setup Script
# This script creates and activates a Python virtual environment

set -e  # Exit on any error

echo "🚀 Setting up Turtil Backend development environment..."

# Check if Python 3.8+ is available
if ! python3 --version >/dev/null 2>&1; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $PYTHON_VERSION found, but Python $REQUIRED_VERSION or higher is required."
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"

# Virtual environment directory
VENV_DIR="venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv $VENV_DIR
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source $VENV_DIR/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "📚 Installing Python dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "❌ requirements.txt not found"
    exit 1
fi

# Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📄 Creating .env file from .env.example..."
        cp .env.example .env
        echo "✅ .env file created. Please update it with your actual values."
    else
        echo "⚠️  .env.example not found. You'll need to create .env manually."
    fi
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To get started:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Update your .env file with actual values"
echo ""
echo "  3. Start the database services:"
echo "     cd db && docker-compose up -d"
echo ""
echo "  4. Run the application:"
echo "     python run.py"
echo ""
echo "  5. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "🔧 Development commands:"
echo "  - Format code: ruff format ."
echo "  - Lint code: ruff check ."
echo "  - Type check: mypy app/"
echo "  - Run with Docker: docker-compose up"
echo ""

# Check if we're being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "⚠️  To activate the virtual environment in your current shell, run:"
    echo "     source setup_env.sh"
    echo ""
    echo "   Or manually activate with:"
    echo "     source venv/bin/activate"
else
    echo "✅ Virtual environment is now active in your current shell!"
    echo "   Your prompt should show (venv) indicating the active environment."
fi
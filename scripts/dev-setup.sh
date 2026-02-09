#!/bin/bash
# Development setup script for Unix

set -e

echo -e "\033[32mSetting up nlm-chatbot development environment...\033[0m"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
if [[ ! $PYTHON_VERSION =~ "Python 3.1"[1-9] ]]; then
    echo -e "\033[31mError: Python 3.11+ required. Found: $PYTHON_VERSION\033[0m"
    exit 1
fi
echo -e "\033[36mPython version: $PYTHON_VERSION\033[0m"

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo -e "\033[33mCreating virtual environment...\033[0m"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "\033[33mActivating virtual environment...\033[0m"
source .venv/bin/activate

# Install dependencies
echo -e "\033[33mInstalling dependencies...\033[0m"
pip install -e ".[dev]"

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo -e "\033[33mCreating .env from .env.example...\033[0m"
    cp .env.example .env
    echo -e "\033[36mPlease edit .env with your Azure credentials\033[0m"
fi

echo -e "\n\033[32mSetup complete!\033[0m"
echo -e "\033[36mNext steps:\033[0m"
echo "  1. Edit .env with your Azure Bot credentials"
echo "  2. Run: python -m knowledge_finder_bot.main"
echo "  3. Use Bot Framework Emulator to test"

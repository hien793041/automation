#!/usr/bin/env bash
set -e

echo "Setting up ROK Bot Engine v2 environment..."

# Python version check
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Created virtual environment"
fi

source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install main dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-asyncio black ruff

# Optional: install training dependencies
if [ "$1" == "--with-training" ]; then
    pip install jupyter matplotlib seaborn plotly
    echo "Installed training dependencies"
fi

echo "Environment setup complete. Activate with: source .venv/bin/activate"

#!/bin/bash

# Exit on error
set -e

# Load environment variables if they exist
if [ -f .env ]; then
    source .env
fi

# Check if pyenv is installed
if ! command -v pyenv &> /dev/null; then
    echo "pyenv is not installed. Please install pyenv first."
    exit 1
fi

# Install Python 3.9.18 if not already installed
if ! pyenv versions | grep -q "3.9.18"; then
    echo "Installing Python 3.9.18..."
    pyenv install 3.9.18
fi

# Set local Python version
pyenv local 3.9.18

# Create and activate venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
    
    # Install pip in the virtual environment
    echo "Installing pip..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    .venv/bin/python get-pip.py
    rm get-pip.py
fi

# Ensure dependencies are installed
echo "Installing dependencies..."
. .venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Check if we're on Apple Silicon
if [ "$(uname -m)" = "arm64" ]; then
    echo "Apple Silicon detected, installing pywhispercpp with CoreML support..."
    # Clone and install pywhispercpp with CoreML support
    rm -rf tmp/pywhispercpp || true
    mkdir -p tmp
    cd tmp
    git clone --recursive https://github.com/abdeladim-s/pywhispercpp
    cd pywhispercpp
    WHISPER_COREML=1 pip install .
    cd ../..
    rm -rf tmp/pywhispercpp
    
    # Install other dependencies
    grep -v "pywhispercpp" requirements.txt | pip install -r /dev/stdin
else
    # Install all dependencies normally
    pip install -r requirements.txt
fi

# Start the application
echo "Starting Dicta..."
PYTHONPATH=$PYTHONPATH:. python -m app.desktop_ui.main 
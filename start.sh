#!/bin/bash

# Exit on error
set -e

# Load environment variables if they exist
if [ -f .env ]; then
    source .env
fi

# Check if running on Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo "Warning: This application is optimized for Apple Silicon (M1/M2/M3) Macs."
    echo "Some features like MLX acceleration may not work on your system."
fi

# Check if Homebrew is installed (needed for FFmpeg)
if ! command -v brew &> /dev/null; then
    echo "Homebrew is not installed. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install FFmpeg if not installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg (required for audio processing)..."
    brew install ffmpeg
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
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
    echo "Creating virtual environment with uv..."
    uv venv
fi

# Create mlx_models directory if it doesn't exist
mkdir -p mlx_models

# Ensure dependencies are installed
echo "Installing dependencies with uv..."
. .venv/bin/activate

# Install all dependencies using uv
uv pip install -r requirements.txt

# Start the application
echo "Starting Dicta..."
python -m app.desktop_ui.main "$@" 
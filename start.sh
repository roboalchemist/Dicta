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

# Check if Homebrew is installed (needed for FFmpeg and PortAudio)
if ! command -v brew &> /dev/null; then
    echo "Homebrew is not installed. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for current session
    if [[ $(uname -m) == "arm64" ]]; then
        export PATH="/opt/homebrew/bin:$PATH"
    else
        export PATH="/usr/local/bin:$PATH"
    fi
fi

# Install FFmpeg if not installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg (required for audio processing)..."
    brew install ffmpeg
fi

# Install PortAudio (required for PyAudio)
if ! brew list portaudio &> /dev/null; then
    echo "Installing PortAudio (required for PyAudio)..."
    brew install portaudio
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add uv to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
    
    # Source the env file if it exists
    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    fi
fi

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Remove any existing virtual environment to ensure clean state
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf .venv
fi

# Create fresh virtual environment with uv
echo "Creating fresh virtual environment with uv..."
uv venv --python 3.11

# Create mlx_models directory if it doesn't exist
mkdir -p mlx_models

# Install dependencies using uv with explicit virtual environment activation
echo "Installing dependencies with uv..."
source .venv/bin/activate
uv pip install -r requirements.txt

# Install parakeet-mlx separately (requires specific installation method)
echo "Installing parakeet-mlx..."
uv pip install parakeet-mlx -U

deactivate

# Verify the installation worked
echo "Verifying installation..."
source .venv/bin/activate
if python -c "import numpy, parakeet_mlx; print('✓ Dependencies installed successfully')" 2>/dev/null; then
    echo "✓ All dependencies are properly installed"
    deactivate
else
    echo "✗ Dependency installation failed"
    deactivate
    exit 1
fi

# Start the application
echo "Starting Dicta..."
source .venv/bin/activate
python -m app.desktop_ui.main "$@" 
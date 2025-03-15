#!/bin/bash

# Exit on error
set -e

# Load environment variables if they exist
if [ -f .env ]; then
    source .env
fi

# Activate virtual environment if it exists
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Start the application
echo "Starting PyQt6 application..."
python app/desktop_ui/main.py 
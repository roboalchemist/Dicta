#!/bin/bash

# Exit on error
set -e

# Load test environment variables if they exist
if [ -f app/tests/.env.test ]; then
    source app/tests/.env.test
fi

# Activate virtual environment if it exists
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Run tests with pytest
echo "Running PyQt6 application tests..."
python -m pytest app/tests -v 
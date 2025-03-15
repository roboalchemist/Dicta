#!/bin/bash

# Exit on error
set -e

# Activate virtual environment if it exists
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Determine OS and set package type
case "$(uname -s)" in
    Darwin*)
        echo "Creating macOS .dmg package..."
        pyinstaller --clean --windowed --name app \
            --add-data "app/desktop_ui:app/desktop_ui" \
            app/desktop_ui/main.py
        # Additional commands for DMG creation would go here
        ;;
    Linux*)
        echo "Creating Linux AppImage..."
        pyinstaller --clean --windowed --name app \
            --add-data "app/desktop_ui:app/desktop_ui" \
            app/desktop_ui/main.py
        # Additional commands for AppImage creation would go here
        ;;
    MINGW*|CYGWIN*|MSYS*)
        echo "Creating Windows .exe package..."
        pyinstaller --clean --windowed --name app \
            --add-data "app/desktop_ui;app/desktop_ui" \
            app/desktop_ui/main.py
        ;;
    *)
        echo "Unsupported operating system"
        exit 1
        ;;
esac

echo "Package created in dist/ directory" 
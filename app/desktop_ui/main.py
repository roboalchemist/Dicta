#!/usr/bin/env python3
import sys
import logging
import os
from PyQt6.QtWidgets import QApplication
from .menu_bar_app import MenuBarApp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Dicta application."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when windows are closed
    
    # Create the menu bar app
    menu_bar = MenuBarApp()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 
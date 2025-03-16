#!/usr/bin/env python3
import sys
import logging
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QPen, QColor, QBrush, QAction, QActionGroup
from PyQt6.QtCore import Qt, QSize, QObject, pyqtSignal, QThread, QTimer
import platform

from app.speech import SpeechToText, GroqWhisperService, WhisperCppService
from app.audio import AudioCapture
from .command_mapper import CommandMapper
from .command_overlay import CommandOverlay
from app.speech_manager import SpeechManager
from app.desktop_ui.command_list import CommandListWindow
from app.config import config, Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DictaSystemTrayIcon(QSystemTrayIcon):
    """System tray icon for the Dicta application."""
    
    def __init__(self):
        super().__init__()
        self.current_status = "Stopped"
        self.command_mapper = CommandMapper()
        self.command_overlay = CommandOverlay(self.command_mapper)
        
        # Get project root directory
        self.project_root = Path(__file__).parent.parent.parent
        self.icon_path = self.project_root / "app" / "assets" / "icons" / "app.png"
        
        # Available model sizes for Whisper.cpp
        self.whisper_model_sizes = ["tiny", "base", "small", "medium", "large-v3"]
        
        # Initialize available backends
        self.speech_services = {
            "Whisper.cpp": WhisperCppService,
            "Groq": GroqWhisperService
        }
        self.current_service = "Whisper.cpp"
        
        # Initialize speech manager with default service
        self.speech_manager = SpeechManager(self.speech_services[self.current_service](), parent=self)
        
        # Set up UI
        self.setup_ui()
        self.setup_connections()
        self.show()
        
    def setup_ui(self):
        """Set up the system tray icon and menu."""
        # Create base icon from file if it exists, otherwise draw one
        if self.icon_path.exists():
            base_icon = QIcon(str(self.icon_path))
        else:
            logger.error(f"Icon not found at {self.icon_path}")
            return
            
        self.setIcon(base_icon)
        
        # Create menu
        menu = QMenu()
        
        # Add backend selection submenu
        backend_menu = menu.addMenu("Transcription Backend")
        backend_group = QActionGroup(menu)
        backend_group.setExclusive(True)
        
        # Add Whisper.cpp with model size submenu
        whisper_menu = backend_menu.addMenu("Whisper.cpp")
        whisper_action = QAction("Whisper.cpp", menu, checkable=True)
        whisper_action.setChecked(self.current_service == "Whisper.cpp")
        whisper_action.triggered.connect(lambda checked: self.change_backend("Whisper.cpp"))
        backend_group.addAction(whisper_action)
        
        # Add model size submenu
        model_menu = whisper_menu.addMenu("Model Size")
        model_group = QActionGroup(menu)
        model_group.setExclusive(True)
        
        # Get current model size
        current_model = config.get("whisper", "model_size")
        
        for size in self.whisper_model_sizes:
            action = QAction(size, menu, checkable=True)
            action.setChecked(size == current_model)
            action.triggered.connect(lambda checked, s=size: self.change_model_size(s))
            model_group.addAction(action)
            model_menu.addAction(action)
            
        # Add CoreML toggle if on Apple Silicon
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            whisper_menu.addSeparator()
            use_coreml = config.get("whisper", "use_coreml", True)
            coreml_action = QAction("Use Metal GPU", menu, checkable=True)
            coreml_action.setChecked(use_coreml)
            coreml_action.triggered.connect(self.toggle_coreml)
            whisper_menu.addAction(coreml_action)
            
        # Add other backends
        for backend in [b for b in self.speech_services.keys() if b != "Whisper.cpp"]:
            action = QAction(backend, menu, checkable=True)
            action.setChecked(backend == self.current_service)
            action.triggered.connect(lambda checked, b=backend: self.change_backend(b))
            backend_group.addAction(action)
            backend_menu.addAction(action)
        
        # Add auto-listen toggle
        self.auto_listen_action = menu.addAction("Auto Listen")
        self.auto_listen_action.setCheckable(True)
        self.auto_listen_action.triggered.connect(self.toggle_auto_listen)
        
        # Add commands action
        commands_action = menu.addAction("Commands")
        commands_action.triggered.connect(self.show_commands)
        
        menu.addSeparator()
        
        # Add quit action
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_application)
        
        self.setContextMenu(menu)
        
    def setup_connections(self):
        """Set up signal/slot connections."""
        self.speech_manager.transcription_ready.connect(self.handle_transcription)
        self.speech_manager.status_changed.connect(self.update_status)
        
    def update_status(self, status):
        """Update the current status and icon."""
        self.current_status = status
        self.update_icon()
        
    def update_icon(self):
        """Update the icon based on current status."""
        if not self.icon_path.exists():
            logger.error(f"Icon not found at {self.icon_path}")
            return
            
        # Load the base icon
        base_pixmap = QPixmap(str(self.icon_path))
        icon_size = base_pixmap.size()
        
        # Create a new pixmap for the colored overlay
        result_pixmap = QPixmap(icon_size)
        result_pixmap.fill(Qt.GlobalColor.transparent)
        
        # Draw the base icon
        painter = QPainter(result_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, base_pixmap)
        
        # Create color overlay based on status
        if self.current_status == "Stopped":
            color = QColor(255, 0, 0, 100)  # Semi-transparent red
        elif self.current_status == "Listening":
            color = QColor(255, 255, 0, 100)  # Semi-transparent yellow
        elif self.current_status == "Speech detected":
            color = QColor(0, 255, 0, 100)  # Semi-transparent green
        elif self.current_status == "Processing":
            color = QColor(0, 0, 255, 100)  # Semi-transparent blue
        else:
            color = QColor(255, 255, 255, 0)  # Transparent
            
        # Apply color overlay
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        painter.fillRect(result_pixmap.rect(), color)
        painter.end()
        
        # Set the icon
        self.setIcon(QIcon(result_pixmap))
        self.setToolTip(f"Dicta Voice Commands - {self.current_status}")
        
    def toggle_auto_listen(self, enabled):
        """Toggle auto-listen mode."""
        if enabled:
            self.speech_manager.start_listening()
        else:
            self.speech_manager.stop_listening()
        
    def show_commands(self):
        """Show the command list window."""
        command_list = CommandListWindow(self.command_mapper)
        command_list.show()
        
    def handle_transcription(self, text):
        """Handle transcribed text."""
        logger.info(f"Transcribed text: {text}")
        if not self.command_mapper.process_text(text):
            # If not a command, show the text in the overlay
            self.command_overlay.show_command(text)

    def change_backend(self, backend: str):
        """Change the transcription backend."""
        try:
            # Stop current service if running
            if hasattr(self, 'speech_manager'):
                self.speech_manager.stop_listening()
            
            # Create new service
            service = self.speech_services[backend]()
            self.speech_manager = SpeechManager(service, parent=self)
            self.current_service = backend
            
            # Reconnect signals
            self.speech_manager.transcription_ready.connect(self.handle_transcription)
            self.speech_manager.status_changed.connect(self.update_status)
            
            logger.info(f"Switched to {backend} backend")
            
        except Exception as e:
            logger.error(f"Error changing backend to {backend}: {e}")
            QMessageBox.critical(None, "Error", f"Failed to initialize {backend} backend")
            
            # Revert to Whisper.cpp if there's an error
            if backend != "Whisper.cpp":
                self.change_backend("Whisper.cpp")
    
    def quit_application(self):
        """Quit the application."""
        if hasattr(self, 'speech_manager'):
            self.speech_manager.stop_listening()
        QApplication.quit()

    def change_model_size(self, size: str):
        """Change the Whisper.cpp model size.
        
        Args:
            size: The model size to use
        """
        try:
            # Update config
            config.set("whisper", "model_size", size)
            logger.info(f"Changed model size to {size}")
            
            # Reinitialize service if currently using Whisper.cpp
            if self.current_service == "Whisper.cpp":
                self.change_backend("Whisper.cpp")
                
        except Exception as e:
            logger.error(f"Error changing model size: {e}")
            QMessageBox.critical(None, "Error", f"Failed to change model size: {e}")

    def toggle_coreml(self, enabled: bool):
        """Toggle CoreML support.
        
        Args:
            enabled: Whether to enable CoreML
        """
        try:
            # Update config
            config.set("whisper", "use_coreml", enabled)
            logger.info(f"{'Enabled' if enabled else 'Disabled'} CoreML support")
            
            # Reinitialize service if currently using Whisper.cpp
            if self.current_service == "Whisper.cpp":
                self.change_backend("Whisper.cpp")
                
        except Exception as e:
            logger.error(f"Error toggling CoreML: {e}")
            QMessageBox.critical(None, "Error", f"Failed to toggle CoreML: {e}")

def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Create and show system tray icon
    tray_icon = DictaSystemTrayIcon()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 
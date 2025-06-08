"""Menu bar application for Dicta."""

import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction, QActionGroup, QPixmap, QPainter, QFont, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
import numpy as np
import sys
import os

from app.speech import GroqWhisperService
from app.transcription.whisper_service import WhisperService, WhisperModel
from app.speech_manager import SpeechManager  # Re-enabled - Core Foundation crash fixed
from app.config import config
from .settings_window import SettingsWindow
from .command_list import CommandListWindow  # Re-enabled - Core Foundation crash fixed
from app.config import Config
from app.settings.settings_dialog import SettingsDialog
from app.audio import AudioService
from app.audio.vad import VADManager
from .signal_icon import SignalIcon

logger = logging.getLogger(__name__)

class ModelLoaderThread(QThread):
    """Thread for loading the Whisper model."""
    finished = pyqtSignal(object)  # Emits the loaded model
    error = pyqtSignal(str)  # Emits error message if loading fails
    
    def __init__(self, model_type):
        super().__init__()
        self.model_type = model_type
    
    def run(self):
        """Load the model in a background thread."""
        try:
            logger.info(f"Loading {self.model_type} model in background...")
            whisper_service = WhisperService(self.model_type)
            self.finished.emit(whisper_service)
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.error.emit(str(e))

class MenuBarApp(QObject):
    """Menu bar application for Dicta."""
    
    def __init__(self):
        """Initialize the application."""
        super().__init__()
        
        # Set up icon paths
        self.icon_path = os.path.join(os.path.dirname(__file__), "icons")
        self.mic_icon = os.path.join(self.icon_path, "microphone.png")
        logger.info(f"Icon path: {self.icon_path}")
        logger.info(f"Microphone icon path: {self.mic_icon}")
        logger.info(f"Icon exists: {os.path.exists(self.mic_icon)}")
        
        # Initialize signal icon first
        self.signal_icon = SignalIcon()  # Re-enabled - Core Foundation crash fixed
        
        # Initialize services
        self.initialize_services()
        
        # Set up UI elements after services are ready
        self.setup_settings_dialog()
        self.setup_tray_icon()  # Move this after settings dialog setup
        
        # Let the speech manager handle auto-listen
        # Don't start listening here - it will be handled after model loads
        logger.info("MenuBarApp initialized")
    
    def initialize_services(self):
        """Initialize required services."""
        try:
            # Get model size from config
            model_size = config.get("model_size", "large-v3")
            
            # Initialize speech manager (handles its own threading)
            self.speech_manager = SpeechManager(model_size)
            
            # Connect signals
            self.speech_manager.level_changed.connect(self.update_icon_level)
            self.speech_manager.status_changed.connect(self.update_status)
            self.speech_manager.model_loaded.connect(self.on_model_loaded)
            self.speech_manager.error_occurred.connect(self.show_error)
            
            logger.info("Services initialized")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            QMessageBox.critical(None, "Error", f"Failed to initialize services: {e}")
            sys.exit(1)
    
    def create_loading_icon(self):
        """Create a loading icon to show while the model is loading."""
        pixmap = QPixmap(44, 44)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a simple loading indicator (spinning dots or clock symbol)
        painter.setFont(QFont("Arial", 32))
        painter.setPen(QColor(128, 128, 128))  # Grey color for loading
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "⏳")
        
        painter.end()
        return QIcon(pixmap)

    def setup_tray_icon(self):
        """Set up the system tray icon and menu."""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set loading icon immediately
        self.tray_icon.setIcon(self.create_loading_icon())
        self.tray_icon.setToolTip("Dicta - Loading model...")
        self.tray_icon.show()  # Show immediately with loading icon
        
        # Create context menu
        menu = QMenu()
        
        # Add listening toggle
        self.listen_action = QAction("Start Listening", self)
        self.listen_action.setCheckable(True)
        self.listen_action.setChecked(False)  # Always start unchecked until model loads
        self.listen_action.setEnabled(False)  # Disabled until model loads
        self.listen_action.triggered.connect(self.toggle_listening)
        menu.addAction(self.listen_action)
        
        # Add auto-listen setting
        self.auto_listen_action = QAction("Listen on Startup", self)
        self.auto_listen_action.setCheckable(True)
        self.auto_listen_action.setChecked(config.get("auto_listen", True))
        self.auto_listen_action.triggered.connect(self.toggle_auto_listen)
        menu.addAction(self.auto_listen_action)
        menu.addSeparator()
        
        # Add model selection submenu
        model_menu = menu.addMenu("Model")
        self.setup_model_menu(model_menu)
        
        # Add settings and quit options
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.cleanup)
        menu.addAction(quit_action)
        
        # Set up tray icon
        self.tray_icon.setContextMenu(menu)
    
    def setup_model_menu(self, model_menu):
        """Set up the model selection submenu."""
        try:
            # Get current model type
            current_model = config.get("model_size", "large-v3")
            
            # Create model list from WhisperModel enum
            available_models = [
                ("tiny", "Tiny"),
                ("base", "Base"),
                ("distil-small.en", "Small English"),
                ("small", "Small"),
                ("distil-medium.en", "Medium English"),
                ("medium", "Medium"),
                ("distil-large-v3", "Large v3 English"),
                ("large-v3", "Large v3"),
                ("whisper-1", "GROQ Whisper")
            ]
            
            # Add model actions
            for model_id, display_name in available_models:
                action = QAction(display_name, self)
                action.setCheckable(True)
                action.setChecked(model_id == current_model)
                action.triggered.connect(lambda checked, m=model_id: self.select_model(m))
                model_menu.addAction(action)
                
        except Exception as e:
            logger.error(f"Error setting up model menu: {e}")
            # Add disabled action to show error
            action = QAction("Error loading models", self)
            action.setEnabled(False)
            model_menu.addAction(action)

    def select_model(self, model):
        """Select a new model."""
        try:
            # Save model selection to config
            config.set("model_size", model)
            config.save()
            
            # Show loading message
            self.tray_icon.showMessage(
                "Loading Model",
                f"Switching to {model} model...",
                QSystemTrayIcon.Information,
                2000
            )
            
            # Create new service in background
            self.model_loader = ModelLoaderThread(model)
            self.model_loader.finished.connect(self.on_model_loaded)
            self.model_loader.error.connect(self.show_error)
            self.model_loader.start()
            
            # Update tooltip
            self.update_tooltip()
            
            logger.info(f"Started loading model: {model}")
            
        except Exception as e:
            logger.error(f"Error selecting model: {e}")
            self.tray_icon.showMessage(
                "Error",
                f"Failed to switch model: {e}",
                QSystemTrayIcon.Critical,
                2000
            )

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(config)  # Remove parent since we're not a QWidget
        dialog.exec()
    
    def toggle_listening(self, checked):
        """Toggle current listening state."""
        if checked:
            if not self.speech_manager.speech_thread.is_listening:
                self.speech_manager.start_listening()
        else:
            if self.speech_manager.speech_thread.is_listening:
                self.speech_manager.stop_listening()
        
        # Update UI to reflect actual state
        self.update_listening_state()
    
    def update_tooltip(self):
        """Update the tray icon tooltip with current status."""
        status = "Listening" if self.speech_manager.speech_thread.is_listening else "Not Listening"
        model = config.get("model_size", "large-v3")
        auto_start = "Will listen on startup" if config.get("auto_listen", True) else "Manual start only"
        self.tray_icon.setToolTip(f"Dicta - {status}\nModel: {model}\n{auto_start}")
    
    def update_status(self, status: str):
        """Update the application status."""
        logger.debug(f"Status changed to: {status}")
        self.update_listening_state()
    
    def show_error(self, message: str):
        """Show error message."""
        QMessageBox.critical(None, "Error", message)
    
    def update_icon_state(self):
        """Update the tray icon based on current speech manager state."""
        try:
            if hasattr(self, 'speech_manager') and self.speech_manager.speech_thread.is_listening:
                self.update_icon_level(0)  # Start with level 0
            else:
                # Check if icon file exists and is valid
                if not os.path.exists(self.mic_icon):
                    logger.error(f"Icon not found: {self.mic_icon}")
                    # Create a fallback icon with text
                    pixmap = QPixmap(44, 44)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setFont(QFont("Arial", 24))
                    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🎤")
                    painter.end()
                    self.tray_icon.setIcon(QIcon(pixmap))
                    return
                    
                if os.path.getsize(self.mic_icon) == 0:
                    logger.error(f"Icon file is empty: {self.mic_icon}")
                    # Use text fallback
                    pixmap = QPixmap(44, 44)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setFont(QFont("Arial", 24))
                    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🎤")
                    painter.end()
                    self.tray_icon.setIcon(QIcon(pixmap))
                    return
                    
                # Load the icon
                icon = QIcon(self.mic_icon)
                if icon.isNull():
                    logger.error(f"Failed to load icon: {self.mic_icon}")
                    # Use text fallback
                    pixmap = QPixmap(44, 44)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setFont(QFont("Arial", 24))
                    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🎤")
                    painter.end()
                    self.tray_icon.setIcon(QIcon(pixmap))
                else:
                    self.tray_icon.setIcon(icon)
                    logger.debug("Successfully set microphone icon")
                    
        except Exception as e:
            logger.error(f"Error updating icon state: {e}")
            # Final fallback - try to show something
            try:
                pixmap = QPixmap(44, 44)
                pixmap.fill(Qt.GlobalColor.red)
                self.tray_icon.setIcon(QIcon(pixmap))
            except:
                pass
    
    def cleanup(self):
        """Clean up resources before quitting."""
        if hasattr(self, 'speech_manager'):
            self.speech_manager.cleanup()
        QApplication.quit()

    def update_icon_level(self, level: int):
        """Update the tray icon based on current voice level."""
        if self.speech_manager.speech_thread.is_listening:
            self.tray_icon.setIcon(self.signal_icon.generate(level))
    
    def setup_settings_dialog(self):
        """Set up the settings dialog."""
        # This method is now empty as the settings dialog is handled by the SettingsDialog class
        pass

    def toggle_auto_listen(self, checked):
        """Toggle whether listening starts automatically on launch."""
        config.set("auto_listen", checked)
        config.save()
        logger.info(f"Listen on startup {'enabled' if checked else 'disabled'}")
        self.update_tooltip()

    def update_listening_state(self):
        """Update UI elements to reflect current listening state."""
        is_listening = self.speech_manager.speech_thread.is_listening
        self.listen_action.setChecked(is_listening)
        self.listen_action.setText("Stop Listening" if is_listening else "Start Listening")
        self.update_icon_state()
        self.update_tooltip()

    def on_model_loaded(self):
        """Handle model loaded event."""
        logger.info("Model loaded successfully")
        
        # Enable listening controls
        self.listen_action.setEnabled(True)
        
        # Start listening if auto-listen is enabled
        if config.get("auto_listen", True):
            self.speech_manager.start_listening()
            
        # Update UI state
        self.update_listening_state() 
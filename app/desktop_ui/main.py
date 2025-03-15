#!/usr/bin/env python3
import sys
import logging
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QPen, QColor, QBrush, QAction
from PyQt6.QtCore import Qt, QSize, QObject, pyqtSignal, QThread

from app.speech import SpeechToText, GroqWhisperService
from app.audio import AudioCapture
from .command_mapper import CommandMapper
from .command_overlay import CommandOverlay
from app.speech_manager import SpeechManager
from app.desktop_ui.command_list import CommandListWindow

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranscriptionWorker(QObject):
    """Worker for handling transcription in a separate thread."""
    finished = pyqtSignal()
    result = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, speech_to_text, audio_data):
        super().__init__()
        self.speech_to_text = speech_to_text
        self.audio_data = audio_data
        
    def run(self):
        try:
            text = self.speech_to_text.transcribe_stream(self.audio_data)
            self.result.emit(text)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

class DictaSystemTrayIcon(QSystemTrayIcon):
    """System tray icon for the Dicta application."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.command_mapper = CommandMapper()
        self.command_overlay = CommandOverlay(self.command_mapper)
        self.speech_manager = SpeechManager()
        self.current_status = "Stopped"
        self.setup_ui()
        self.setup_connections()
        self.show()
        
    def setup_ui(self):
        """Set up the system tray icon and menu."""
        self.update_icon()
        self.setToolTip("Dicta Voice Commands")
        
        # Create menu
        menu = QMenu()
        
        # Add actions
        self.auto_listen_action = QAction("Auto Listen", menu)
        self.auto_listen_action.setCheckable(True)
        self.auto_listen_action.triggered.connect(self.toggle_auto_listen)
        menu.addAction(self.auto_listen_action)
        
        commands_action = QAction("Commands", menu)
        commands_action.triggered.connect(self.show_command_list)
        menu.addAction(commands_action)
        
        menu.addSeparator()
        
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        
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
        icon_size = QSize(32, 32)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw circle with color based on status
        pen = QPen(QColor("#333333"))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Choose color based on status
        if self.current_status == "Stopped":
            color = QColor("#ff0000")  # Red
        elif self.current_status == "Listening":
            color = QColor("#ffff00")  # Yellow
        elif self.current_status == "Speech detected":
            color = QColor("#00ff00")  # Green
        elif self.current_status == "Processing":
            color = QColor("#0000ff")  # Blue
        else:
            color = QColor("#ffffff")  # White
            
        painter.setBrush(QBrush(color))
        painter.drawEllipse(2, 2, 28, 28)
        
        # Draw microphone icon
        painter.setPen(QPen(QColor("#333333")))
        painter.drawRect(13, 8, 6, 12)  # Microphone body
        painter.drawArc(11, 20, 10, 6, 0, 180 * 16)  # Microphone stand
        painter.drawLine(16, 26, 16, 28)  # Microphone pole
        
        painter.end()
        
        self.setIcon(QIcon(pixmap))
        self.setToolTip(f"Dicta Voice Commands - {self.current_status}")
        
    def toggle_auto_listen(self, enabled):
        """Toggle auto-listen mode."""
        self.speech_manager.toggle_auto_listen(enabled)
        
    def show_command_list(self):
        """Show the command list window."""
        command_list = CommandListWindow(self.command_mapper)
        command_list.show()
        
    def handle_transcription(self, text):
        """Handle transcribed text."""
        logger.info(f"Transcribed text: {text}")
        if not self.command_mapper.process_text(text):
            # If not a command, show the text in the overlay
            self.command_overlay.show_command(text)

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
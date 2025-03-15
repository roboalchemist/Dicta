"""Overlay window for displaying available voice commands."""
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QDialog
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication
from .command_mapper import CommandMapper

logger = logging.getLogger(__name__)

class CommandOverlay(QDialog):
    """Overlay window that displays the recognized command."""
    
    def __init__(self, command_mapper, parent=None):
        super().__init__(parent)
        self.command_mapper = command_mapper
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()
        self.position_window()
        
    def setup_ui(self):
        """Set up the UI components."""
        self.setFixedSize(200, 50)
        
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create and style the command label
        self.command_label = QLabel()
        self.command_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.command_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 180);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.command_label)
        
        # Create timer for auto-hide
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        
    def show_command(self, command):
        """Show the command text in the overlay."""
        self.command_label.setText(command)
        self.show()
        self.hide_timer.start(2000)  # Hide after 2 seconds
        
    def show_commands(self, duration_ms=3000):
        """Show the overlay with current commands.
        
        Args:
            duration_ms: How long to show the overlay (in milliseconds)
        """
        commands = self.command_mapper.get_commands()
        if commands:
            command_text = "\n".join(f"{cmd} -> {key}" for cmd, key in commands.items())
            self.command_label.setText(command_text)
            self.show()
            self.hide_timer.start(duration_ms)
        else:
            # Show a message even if there are no commands
            self.command_label.setText("No commands available")
            self.show()
            self.hide_timer.start(duration_ms)
        
    def position_window(self):
        """Position the window at the bottom center of the screen."""
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 100  # 100 pixels from bottom
        self.move(x, y)  # Use move instead of setGeometry to avoid decoration issues
        
    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return):
            self.hide()
        else:
            super().keyPressEvent(event) 
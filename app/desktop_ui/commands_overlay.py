"""Overlay window for displaying commands."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor
import logging
from AppKit import (
    NSEvent,
    NSEventMaskKeyDown,
    NSEventMaskKeyUp,
    NSEventMaskFlagsChanged,
    NSEventTypeKeyDown,
    NSEventTypeKeyUp,
    NSEventTypeFlagsChanged,
    NSAlternateKeyMask,
    NSCommandKeyMask,
    NSShiftKeyMask,
    NSControlKeyMask,
    NSApplication,
)
import threading

from app.config import Config
from .commands_view import CommandsView

logger = logging.getLogger(__name__)

class CommandsOverlay(QWidget):
    """Overlay window showing available commands."""
    
    def __init__(self, config: Config, parent=None):
        """Initialize the overlay window."""
        super().__init__(parent)
        self.config = config
        
        # Set window flags - frameless but stays on top
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |  # No title bar
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        
        # Set window attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(0)
        
        # Create a container for the close button that floats in top-right
        close_container = QWidget()
        close_container.setStyleSheet("background: transparent;")
        close_layout = QHBoxLayout(close_container)
        close_layout.setContentsMargins(0, 0, 0, 0)
        close_layout.addStretch()
        
        # Add close button in top-right corner
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet("""
            QPushButton {
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                background: transparent;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 30);
            }
        """)
        close_button.clicked.connect(self.hide)
        close_layout.addWidget(close_button)
        
        # Add close button container
        self.main_layout.addWidget(close_container)
        
        # Add the commands view
        commands_view = CommandsView(self.config, self)
        commands_view.setStyleSheet("background: transparent;")
        self.main_layout.addWidget(commands_view)
        
        # Initialize keyboard monitoring
        self.setup_keyboard_monitoring()
    
    def setup_keyboard_monitoring(self):
        """Set up keyboard event monitoring using AppKit."""
        try:
            logger.info("Setting up keyboard monitoring...")
            
            # Set up global monitor for when our window doesn't have focus
            mask = NSEventMaskFlagsChanged
            self.global_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                mask,
                self.handle_keyboard_event
            )
            
            # Set up local monitor for when our window has focus
            self.local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                mask,
                self.handle_local_keyboard_event
            )
            
            if self.global_monitor and self.local_monitor:
                logger.info("Event monitors created successfully")
            else:
                logger.error("Failed to create event monitors - check accessibility permissions")
                
        except Exception as e:
            logger.error(f"Error setting up keyboard monitoring: {e}", exc_info=True)

    def handle_local_keyboard_event(self, event):
        """Handle keyboard events when window has focus."""
        self.handle_keyboard_event(event)
        return event  # Return the event so it continues propagation

    def show(self):
        """Override show to add logging."""
        logger.info("Show method called")
        if not self.isVisible():
            super().show()
            self.raise_()
            self.activateWindow()
            logger.info("Show method completed - window is now visible")
        else:
            logger.debug("Show called but window was already visible")

    def hide(self):
        """Override hide to ensure it only happens through our toggle."""
        logger.info("Hide method called")
        self._programmatic_close = True
        super().hide()
        self._programmatic_close = False

    def thread_safe_show(self):
        """Show the overlay in a thread-safe manner."""
        logger.info("Queueing show request on main thread")
        QTimer.singleShot(0, self._do_show)

    def thread_safe_hide(self):
        """Hide the overlay in a thread-safe manner."""
        logger.info("Queueing hide request on main thread")
        QTimer.singleShot(0, self._do_hide)

    def handle_keyboard_event(self, event):
        """Handle keyboard events from the monitoring thread."""
        try:
            event_type = event.type()
            flags = event.modifierFlags()
            key_code = event.keyCode() if hasattr(event, 'keyCode') else None
            
            logger.debug(f"Raw event - Type: {event_type}, Key code: {key_code}, Flags: {bin(flags)}")
            
            # Right Option key has keyCode 61 on macOS
            is_right_option = key_code == 61
            is_option_pressed = bool(flags & NSAlternateKeyMask)
            
            # Only proceed if this is the right option key being pressed
            if is_right_option and is_option_pressed:
                # Queue the toggle operation on the main Qt thread
                QTimer.singleShot(0, self._toggle_visibility)
                    
        except Exception as e:
            logger.error(f"Error handling keyboard event: {e}", exc_info=True)

    def _toggle_visibility(self):
        """Toggle window visibility on the main Qt thread."""
        try:
            if self.isVisible():
                logger.info("Hiding overlay (main thread)")
                self.hide()
            else:
                logger.info("Showing overlay (main thread)")
                self.show()
                self.raise_()
                self.activateWindow()
        except Exception as e:
            logger.error(f"Error toggling visibility: {e}", exc_info=True)
    
    def setup_ui(self):
        """Set up the UI elements."""
        pass  # UI setup is now handled in __init__

    def paintEvent(self, event):
        """Paint the semi-transparent background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw semi-transparent black background
        painter.setBrush(QColor(0, 0, 0, 128))  # 50% opacity black
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
    
    def mousePressEvent(self, event):
        """Handle mouse press events for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging."""
        if hasattr(self, 'drag_position'):
            if event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if hasattr(self, 'drag_position'):
            del self.drag_position
        event.accept()

    def focusOutEvent(self, event):
        """Prevent window from closing on focus loss."""
        event.accept()

    def leaveEvent(self, event):
        """Prevent window from closing when mouse leaves."""
        event.accept()

    def keyPressEvent(self, event):
        """Handle key press events."""
        # Don't close on key press anymore since we're using right-option
        pass
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'global_monitor') and self.global_monitor:
                NSEvent.removeMonitor_(self.global_monitor)
                self.global_monitor = None
            if hasattr(self, 'local_monitor') and self.local_monitor:
                NSEvent.removeMonitor_(self.local_monitor)
                self.local_monitor = None
            logger.info("Event monitors removed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    def closeEvent(self, event):
        """Only allow programmatic close events."""
        if hasattr(self, '_programmatic_close') and self._programmatic_close:
            super().closeEvent(event)
        else:
            event.ignore()

    def _do_show(self):
        """Internal method to show the overlay."""
        logger.info("Executing show request")
        self.show()
        logger.info("Overlay is now visible")

    def _do_hide(self):
        """Internal method to hide the overlay."""
        logger.info("Executing hide request")
        self.hide()
        logger.info("Overlay is now hidden") 
"""Shared commands view component."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from app.config import Config

class CommandsView(QWidget):
    """Widget that displays available commands."""
    
    def __init__(self, config: Config, parent=None):
        """Initialize the commands view."""
        super().__init__(parent)
        self.config = config
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI elements."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title
        title = QLabel("Available Commands")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)
        
        # Description
        description = QLabel("Click anywhere or press any key to dismiss")
        description.setWordWrap(True)
        description.setStyleSheet("color: #FFFFFF; font-style: italic;")
        layout.addWidget(description)
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Voice Commands Section
        voice_title = QLabel("Voice Commands")
        voice_title.setFont(QFont("", 12, QFont.Weight.Bold))
        voice_title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(voice_title)
        
        # Create a table-like layout for voice commands
        voice_commands = {
            "escape": "Press Escape key",
            "arrow up": "Press Up arrow key",
            "arrow down": "Press Down arrow key",
            "arrow left": "Press Left arrow key",
            "arrow right": "Press Right arrow key",
            "enter": "Press Enter key",
            "tab": "Press Tab key",
            "backspace": "Press Backspace key",
            "delete": "Press Delete key",
            "space": "Press Space key",
            "copy": "Copy selected text",
            "paste": "Paste from clipboard",
            "select all": "Select all text",
            "undo": "Undo last action",
            "redo": "Redo last action"
        }
        
        # Add voice commands to the form
        voice_layout = QFormLayout()
        for command, action in voice_commands.items():
            command_label = QLabel(f'"{command}"')
            command_label.setStyleSheet("font-family: monospace; color: #FFFFFF;")
            action_label = QLabel(action)
            action_label.setStyleSheet("color: #FFFFFF;")
            voice_layout.addRow(command_label, action_label)
        
        layout.addLayout(voice_layout)
        
        # Add spacing between sections
        layout.addSpacing(20)
        
        # Hotkeys Section
        hotkeys_title = QLabel("Hotkeys")
        hotkeys_title.setFont(QFont("", 12, QFont.Weight.Bold))
        hotkeys_title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(hotkeys_title)
        
        # Create a table-like layout for hotkeys
        hotkeys_layout = QFormLayout()
        
        # Get the current push-to-talk key
        ptt_key = self.config.get("push_to_talk_key", "`")
        
        # Add hotkey commands
        ptt_label = QLabel(ptt_key)
        ptt_label.setStyleSheet("font-family: monospace; color: #FFFFFF;")
        ptt_action = QLabel("Push-to-talk (hold to record)")
        ptt_action.setStyleSheet("color: #FFFFFF;")
        hotkeys_layout.addRow(ptt_label, ptt_action)
        
        layout.addLayout(hotkeys_layout)
        
        # Add a stretch at the end to push everything up
        layout.addStretch() 
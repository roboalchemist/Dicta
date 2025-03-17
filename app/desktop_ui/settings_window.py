"""Settings window for Dicta."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt
from app.config import config

class SettingsWindow(QDialog):
    """Settings window for Dicta."""
    
    def __init__(self, parent=None):
        """Initialize the settings window."""
        super().__init__(parent)
        self.setWindowTitle("Dicta Settings")
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        
        # Service selection
        service_layout = QHBoxLayout()
        service_label = QLabel("Default Service:")
        self.service_combo = QComboBox()
        self.service_combo.addItems(["MLX", "Groq"])
        self.service_combo.setCurrentText(config.get("service", "MLX"))
        service_layout.addWidget(service_label)
        service_layout.addWidget(self.service_combo)
        layout.addLayout(service_layout)
        
        # Model size selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Default Model Size:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText(config.get("model_size", "medium"))
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        # Hotkey configuration
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Push-to-Talk Hotkey:")
        self.hotkey_edit = QLineEdit(config.get("hotkey", "ctrl+shift+space"))
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_edit)
        layout.addLayout(hotkey_layout)
        
        # Auto-listen toggle
        self.auto_listen = QCheckBox("Auto-Listen Mode")
        self.auto_listen.setChecked(config.get("auto_listen", False))
        layout.addWidget(self.auto_listen)
        
        # Save and cancel buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_settings(self):
        """Save the settings and close the window."""
        config.set("service", self.service_combo.currentText())
        config.set("model_size", self.model_combo.currentText())
        config.set("hotkey", self.hotkey_edit.text())
        config.set("auto_listen", self.auto_listen.isChecked())
        config.save()
        self.accept() 
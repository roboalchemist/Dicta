"""Configuration management for the application."""

import os
import json
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "service": "MLX",  # MLX or Groq
    "model_size": "large-v3",  # tiny, small, medium, large-v3
    "hotkey": "ctrl+shift+space",
    "auto_listen": True,  # Enable auto-listening by default
    "vad_threshold": 0.5,  # VAD threshold (0-1)
    "vad_silence_threshold": 10,  # Number of silence frames to trigger silence
    "vad_speech_threshold": 3,  # Number of speech frames to trigger speech
    "vad_sampling_rate": 16000,  # Audio sampling rate for VAD
    "vad_pre_buffer": 0.5,  # Seconds of audio to keep before speech
    "vad_post_buffer": 0.2,  # Seconds of audio to keep after speech
    "notification_duration": 2000,  # Duration of notifications in milliseconds
    "typing_speed": 0.01,  # Seconds between typed characters
    "commands": {
        "escape": "escape",
        "enter": "enter",
        "tab": "tab",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "backspace": "backspace",
        "delete": "delete",
        "space": "space",
        "stop": "command+delete",  # Stop command
        "accept": "command+enter"   # Accept command
    }
}

class Config(QObject):
    """Configuration manager."""
    
    # Signal emitted when configuration changes
    config_changed = pyqtSignal()
    
    def __init__(self):
        """Initialize configuration with defaults."""
        super().__init__()
        self.config_dir = Path.home() / ".dicta"
        self.config_file = self.config_dir / "config.json"
        self.config = DEFAULT_CONFIG.copy()  # Use the defined defaults
        self.has_unsaved_changes = False
        
        # Load config from file
        self.load()
    
    def load(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    self.config_changed.emit()
                    logger.info("Configuration loaded successfully")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
    
    def save(self):
        """Save configuration to file."""
        if not self.has_unsaved_changes:
            return
            
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
            self.has_unsaved_changes = False
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set a configuration value."""
        if self.config.get(key) != value:
            self.config[key] = value
            self.has_unsaved_changes = True
            self.config_changed.emit()
            
            # Save after a short delay to batch multiple changes
            QTimer.singleShot(1000, self.save)

# Global configuration instance
config = Config()

__all__ = ['Config', 'config'] 
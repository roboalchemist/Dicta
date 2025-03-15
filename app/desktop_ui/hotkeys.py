import logging
import keyboard
import json
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class HotkeyManager(QObject):
    """Manages keyboard shortcuts for the application."""
    
    # Signals
    hotkey_pressed = pyqtSignal()  # Emitted when push-to-talk key is pressed
    hotkey_released = pyqtSignal()  # Emitted when push-to-talk key is released
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the hotkey manager.
        
        Args:
            config_path: Path to config file. Defaults to ~/.dicta/config.json
        """
        super().__init__()
        self.config_path = config_path or Path.home() / ".dicta" / "config.json"
        self.push_to_talk_key = self._load_config().get("push_to_talk_key", "\\")  # Default to backslash key
        self._setup_hotkeys()
        logger.info(f"Initialized hotkey manager with push-to-talk key: {self.push_to_talk_key}")
        
    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
        return {}
        
    def _save_config(self, config: dict) -> None:
        """Save configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            
    def _setup_hotkeys(self) -> None:
        """Set up keyboard hooks for hotkeys."""
        try:
            keyboard.on_press_key(self.push_to_talk_key, lambda _: self.hotkey_pressed.emit())
            keyboard.on_release_key(self.push_to_talk_key, lambda _: self.hotkey_released.emit())
            logger.info("Successfully set up keyboard hooks")
        except Exception as e:
            logger.error(f"Failed to set up keyboard hooks: {e}")
            
    def set_push_to_talk_key(self, key: str) -> None:
        """Set the push-to-talk hotkey.
        
        Args:
            key: The key to use for push-to-talk
        """
        try:
            # Remove old hotkey
            keyboard.unhook_key(self.push_to_talk_key)
            
            # Update config
            config = self._load_config()
            config["push_to_talk_key"] = key
            self._save_config(config)
            
            # Set new hotkey
            self.push_to_talk_key = key
            self._setup_hotkeys()
            logger.info(f"Updated push-to-talk key to: {key}")
        except Exception as e:
            logger.error(f"Failed to set push-to-talk key: {e}")
            
    def cleanup(self) -> None:
        """Clean up keyboard hooks."""
        try:
            keyboard.unhook_key(self.push_to_talk_key)
            logger.info("Cleaned up keyboard hooks")
        except Exception as e:
            logger.error(f"Failed to clean up keyboard hooks: {e}") 
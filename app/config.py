"""Configuration manager for Dicta application."""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "whisper": {
        "backend": "auto",  # auto, whisper.cpp, openai
        "model_size": "tiny",
        "device": "auto",  # auto, cpu, cuda, mps
        "use_coreml": True,  # Enable CoreML on Apple Silicon by default
    },
    "voice_commands": {
        "escape": "Escape",
        "arrow up": "Up",
        "arrow down": "Down",
        "arrow left": "Left",
        "arrow right": "Right",
        "enter": "Return",
        "tab": "Tab",
        "space": "Space"
    },
    "hotkeys": {
        "push_to_talk": "`",  # Key above Tab/backward slash
        "toggle_listening": "Alt+M",
    },
    "ui": {
        "overlay_duration": 3.0,  # seconds
        "typing_delay": 0.05,  # seconds between characters
    }
}

class Config:
    """Manages application configuration."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = Path.home() / ".dicta"
        self.config_file = self.config_dir / "config.json"
        self.config: Dict[str, Any] = {}
        self._ensure_config_exists()
        self.load_config()
    
    def _ensure_config_exists(self) -> None:
        """Ensure the configuration directory and file exist."""
        try:
            # Create config directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create config file with default values if it doesn't exist
            if not self.config_file.exists():
                self.config = DEFAULT_CONFIG.copy()
                self.save_config()
                logger.info(f"Created default configuration at {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error ensuring config exists: {e}")
            raise
    
    def load_config(self) -> None:
        """Load the configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_file}")
            
            # Update config with any new default values
            updated = False
            for section, values in DEFAULT_CONFIG.items():
                if section not in self.config:
                    self.config[section] = values
                    updated = True
                elif isinstance(values, dict):
                    for key, value in values.items():
                        if key not in self.config[section]:
                            self.config[section][key] = value
                            updated = True
            
            if updated:
                self.save_config()
                logger.info("Updated configuration with new default values")
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config = DEFAULT_CONFIG.copy()
            self.save_config()
    
    def save_config(self) -> None:
        """Save the current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            section: The configuration section
            key: The specific key in the section (optional)
            default: Default value if key doesn't exist (optional)
            
        Returns:
            The configuration value or section
        """
        try:
            if key is None:
                return self.config[section]
            return self.config[section][key]
        except KeyError:
            if key is None:
                if default is not None:
                    return default
                return DEFAULT_CONFIG[section]
            if default is not None:
                return default
            return DEFAULT_CONFIG[section][key]
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            section: The configuration section
            key: The key to set
            value: The value to set
            
        Raises:
            TypeError: If section or key is not a string
            ValueError: If section is not in DEFAULT_CONFIG
        """
        if not isinstance(section, str):
            raise TypeError(f"Section must be a string, got {type(section)}")
        if not isinstance(key, str):
            raise TypeError(f"Key must be a string, got {type(key)}")
        if section not in DEFAULT_CONFIG:
            raise ValueError(f"Invalid section: {section}")
            
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            self.save_config()
            logger.info(f"Updated config: {section}.{key} = {value}")
        except Exception as e:
            logger.error(f"Error setting config value: {e}")
            raise
    
    def remove(self, section: str, key: str) -> None:
        """Remove a configuration value.
        
        Args:
            section: The configuration section
            key: The key to remove
            
        Raises:
            TypeError: If section or key is not a string
            ValueError: If section is not in DEFAULT_CONFIG
        """
        if not isinstance(section, str):
            raise TypeError(f"Section must be a string, got {type(section)}")
        if not isinstance(key, str):
            raise TypeError(f"Key must be a string, got {type(key)}")
        if section not in DEFAULT_CONFIG:
            raise ValueError(f"Invalid section: {section}")
            
        try:
            if section in self.config and key in self.config[section]:
                del self.config[section][key]
                self.save_config()
                logger.info(f"Removed config: {section}.{key}")
        except Exception as e:
            logger.error(f"Error removing config value: {e}")
            raise

# Create a singleton instance
config = Config()
__all__ = ['Config', 'config'] 
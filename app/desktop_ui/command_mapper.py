"""Voice command to keyboard mapping functionality."""
import logging
import keyboard
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from app.config import ConfigManager
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class CommandMapper(QObject):
    """Maps voice commands to keyboard shortcuts."""
    
    # Signal emitted when a command is executed
    command_executed = pyqtSignal(str)  # Emits the command that was executed
    
    def __init__(self, parent=None):
        """Initialize the command mapper.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.commands = {}
        self.load_commands()
        logger.info(f"Initialized CommandMapper with {len(self.commands)} commands")
        
    def load_commands(self):
        """Load commands from config."""
        config_commands = self.config_manager.get("voice_commands")
        if isinstance(config_commands, dict):
            self.commands = {k.lower(): v for k, v in config_commands.items()}
        return self.commands
        
    def get_commands(self) -> Dict[str, str]:
        """Get all voice command mappings.
        
        Returns:
            Dict[str, str]: Dictionary of command -> key mappings
        """
        return dict(self.commands)  # Return a copy
        
    def add_command(self, command: str, key: str):
        """Add a voice command mapping.
        
        Args:
            command: The voice command
            key: The keyboard shortcut
        """
        try:
            # Validate key format
            keyboard.parse_hotkey(key)
            
            # Add to commands dict
            command = command.lower()
            self.commands[command] = key
            
            # Save to config
            self.config_manager.set("voice_commands", command, key)
            logger.info(f"Added command mapping: {command} -> {key}")
            return True
        except ValueError as e:
            logger.error(f"Invalid key format: {key}")
            return False
            
    def remove_command(self, command: str):
        """Remove a voice command mapping.
        
        Args:
            command: The voice command to remove
        """
        command = command.lower()
        if command in self.commands:
            del self.commands[command]
            self.config_manager.remove("voice_commands", command)
            
    def process_text(self, text: str) -> bool:
        """Process transcribed text and execute command if found.
        
        Args:
            text: The transcribed text
            
        Returns:
            bool: True if command was found and executed
        """
        text = text.lower()
        if text in self.commands:
            try:
                keyboard.press_and_release(self.commands[text])
                self.command_executed.emit(text)
                logger.info(f"Executed command: {text} -> {self.commands[text]}")
                return True
            except Exception as e:
                QMessageBox.warning(None, "Error", f"Failed to execute command: {e}")
                return False
        return False
    
    def _normalize_key(self, key: str) -> str:
        """Normalize a key name to the format expected by the keyboard library.
        
        Args:
            key: The key name to normalize
            
        Returns:
            The normalized key name
            
        Raises:
            ValueError: If the key name is invalid
        """
        # Convert to lowercase since keyboard library expects lowercase
        key = key.lower()
        
        # Split into parts for hotkey combinations
        parts = [part.strip() for part in key.split("+")]
        
        # Validate each part
        valid_modifiers = {"ctrl", "control", "alt", "shift", "meta", "win", "cmd"}
        for part in parts[:-1]:  # All parts except last should be modifiers
            if part not in valid_modifiers:
                raise ValueError(f"Invalid modifier key: {part}")
                
        # Try to parse with keyboard library to validate
        try:
            keyboard.parse_hotkey(key)
            return key
        except Exception as e:
            raise ValueError(f"Invalid key format: {key}") from e

    def add_command(self, command: str, key: str) -> bool:
        """Add a voice command mapping.
        
        Args:
            command: The voice command text
            key: The keyboard shortcut (e.g. 'ctrl+t')
            
        Raises:
            ValueError: If the key format is invalid
        """
        if not command or not key:
            raise ValueError("Command and key must not be empty")
            
        # Normalize and validate key
        key = self._normalize_key(key)
        
        # Add to commands dict
        self.commands[command.lower()] = key
        
        # Save to config
        self.config_manager.set("voice_commands", command.lower(), key)
        logger.info(f"Added command mapping: {command} -> {key}")
        return True
    
    def remove_command(self, command: str) -> bool:
        """Remove a voice command mapping.
        
        Args:
            command: The voice command to remove
            
        Returns:
            bool: True if command was removed successfully
        """
        command = command.lower()
        if command in self.commands:
            del self.commands[command]
            self.config_manager.remove("voice_commands", command)
            logger.info(f"Removed command: {command}")
            return True
        else:
            logger.warning(f"Command not found: {command}")
            return False
    
    def get_commands(self) -> Dict[str, str]:
        """Get all voice command mappings.
        
        Returns:
            Dict[str, str]: Dictionary of command -> key mappings
        """
        return dict(self.commands)  # Return a copy 
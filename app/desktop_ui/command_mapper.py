"""Voice command to keyboard mapping functionality."""
import logging
# import keyboard  # Causes Core Foundation crash on macOS - replaced with PyObjC  
import string
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from app.config import config
from PyQt6.QtWidgets import QMessageBox

# Use PyObjC for keyboard simulation on macOS
try:
    from Cocoa import NSEvent, NSEventTypeKeyDown, NSKeyDown
    from Foundation import NSString
    from AppKit import NSApplication, NSApp
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    logging.warning("PyObjC not available for keyboard simulation in CommandMapper")

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
        self.config = config
        self.commands = {}
        self.load_commands()
        logger.info(f"Initialized CommandMapper with {len(self.commands)} commands")
        
        if not KEYBOARD_AVAILABLE:
            logger.warning("Keyboard simulation not available in CommandMapper")
    
    def _simulate_key_press(self, key: str):
        """Simulate a key press using PyObjC.
        
        Args:
            key: Key to press (e.g., 'escape', 'enter', etc.)
        """
        if not KEYBOARD_AVAILABLE:
            logger.warning(f"Cannot press key '{key}' - keyboard simulation not available")
            return False
            
        try:
            # Map common keys to macOS key codes
            key_codes = {
                'escape': 53,
                'enter': 36,
                'return': 36,
                'tab': 48,
                'space': 49,
                'up': 126,
                'down': 125,
                'left': 123,
                'right': 124,
                'backspace': 51,
                'delete': 117,
            }
            
            key_code = key_codes.get(key.lower(), 0)
            if key_code:
                event = NSEvent.keyEventWithType_location_modifierFlags_timestamp_windowNumber_context_characters_charactersIgnoringModifiers_isARepeat_keyCode_(
                    NSKeyDown, (0, 0), 0, 0, 0, None, '', '', False, key_code
                )
                NSApp.sendEvent_(event)
                return True
            else:
                logger.warning(f"Unknown key: {key}")
                return False
                
        except Exception as e:
            logger.error(f"Error simulating key press '{key}': {e}")
            return False
        
    def load_commands(self):
        """Load commands from config."""
        config_commands = self.config.get("commands", {
            "escape": "escape",
            "enter": "enter",
            "tab": "tab",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "backspace": "backspace",
            "delete": "delete",
            "space": "space"
        })
        if isinstance(config_commands, dict):
            self.commands = {k.lower(): v for k, v in config_commands.items()}
        return self.commands
        
    def get_commands(self) -> Dict[str, str]:
        """Get all voice command mappings.
        
        Returns:
            Dict[str, str]: Dictionary of command -> key mappings
        """
        return dict(self.commands)  # Return a copy
        
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
        self.config.set("voice_commands", command.lower(), key)
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
            self.config.remove("voice_commands", command)
            logger.info(f"Removed command: {command}")
            return True
        else:
            logger.warning(f"Command not found: {command}")
            return False
    
    def _clean_text(self, text: str) -> str:
        """Clean text by converting to lowercase and removing punctuation/whitespace.
        
        Args:
            text: The text to clean
            
        Returns:
            str: The cleaned text
        """
        # Convert to lowercase
        text = text.lower()
        # Remove punctuation and whitespace from start/end
        text = text.strip(string.punctuation + string.whitespace)
        return text
        
    def process_text(self, text: str) -> bool:
        """Process transcribed text and execute command if found.
        
        Args:
            text: The transcribed text
            
        Returns:
            bool: True if command was found and executed
        """
        # Clean the input text
        text = self._clean_text(text)
        
        if text in self.commands:
            try:
                # keyboard.press_and_release(self.commands[text])  # Replaced with PyObjC
                success = self._simulate_key_press(self.commands[text])
                if success:
                    self.command_executed.emit(text)
                    logger.info(f"Executed command: {text} -> {self.commands[text]}")
                    return True
                else:
                    QMessageBox.warning(None, "Error", f"Failed to execute command: {text}")
                    return False
            except Exception as e:
                QMessageBox.warning(None, "Error", f"Failed to execute command: {e}")
                return False
        return False
    
    def _normalize_key(self, key: str) -> str:
        """Normalize a key name to a standard format.
        
        Args:
            key: The key name to normalize
            
        Returns:
            The normalized key name
            
        Raises:
            ValueError: If the key name is invalid
        """
        # Convert to lowercase 
        key = key.lower()
        
        # For now, just validate against known keys since we're not using keyboard library
        valid_keys = {
            'escape', 'enter', 'return', 'tab', 'space', 
            'up', 'down', 'left', 'right', 'backspace', 'delete'
        }
        
        if key not in valid_keys:
            logger.warning(f"Key '{key}' may not be supported")
            
        return key 
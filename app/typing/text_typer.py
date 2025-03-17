"""Text typing functionality for Dicta."""

import logging
import keyboard
import time
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from app.config import config
from app.desktop_ui.command_mapper import CommandMapper

logger = logging.getLogger(__name__)

class TextTyper(QObject):
    """Handles typing text and executing keyboard commands."""
    
    # Signals
    typing_started = pyqtSignal()
    typing_finished = pyqtSignal()
    command_executed = pyqtSignal(str)  # Emits the command that was executed
    
    def __init__(self, command_mapper: Optional[CommandMapper] = None, parent: Optional[QObject] = None):
        """Initialize the text typer.
        
        Args:
            command_mapper: Optional CommandMapper instance for handling special commands
            parent: Parent QObject
        """
        super().__init__(parent)
        self.command_mapper = command_mapper or CommandMapper()
        self.typing_speed = config.get("typing_speed", 0.01)  # seconds between characters
        self.commands = self.command_mapper.get_commands()
        logger.info(f"Initialized TextTyper with {len(self.commands)} commands")
    
    def type_text(self, text: str):
        """Type the given text.
        
        Args:
            text: The text to type
        """
        if not text:
            logger.warning("Received empty text to type")
            return
            
        try:
            logger.info(f"Starting to type text (raw): {text}")
            self.typing_started.emit()
            
            # Split text into words but preserve original case
            words = text.split()
            logger.debug(f"Split text into {len(words)} words (raw): {words}")
            
            import string
            
            # Only process as command if it's a single word
            if len(words) == 1:
                word = words[0]
                # Create cleaned copy for command checking (lowercase, no punctuation, stripped)
                cleaned_word = word.lower().strip().translate(str.maketrans("", "", string.punctuation))
                
                # Check if cleaned word is a command
                if cleaned_word in self.commands:
                    logger.info(f"Found single-word command: {cleaned_word} -> {self.commands[cleaned_word]}")
                    self._execute_command(cleaned_word)
                    self.typing_finished.emit()
                    return
            
            # If not a single-word command, type the entire text normally
            for word in words:
                logger.debug(f"Typing word (raw): {word}")
                # Type the original word character by character, preserving case and punctuation
                self._type_word(word)
                # Add space after word
                logger.debug("Adding space after word")
                keyboard.write(" ")
                time.sleep(self.typing_speed)
            
            self.typing_finished.emit()
            logger.info(f"Finished typing text (raw): {text}")
            
        except Exception as e:
            logger.error(f"Error typing text: {e}", exc_info=True)
            self.typing_finished.emit()
    
    def _type_word(self, word: str):
        """Type a single word character by character, preserving case.
        
        Args:
            word: The word to type
        """
        try:
            for char in word:
                logger.debug(f"Typing character (raw): {char}")
                keyboard.write(char)
                time.sleep(self.typing_speed)
        except Exception as e:
            logger.error(f"Error typing word '{word}': {e}", exc_info=True)
    
    def _execute_command(self, command: str):
        """Execute a keyboard command.
        
        Args:
            command: The command to execute
        """
        try:
            key = self.commands.get(command)
            if key:
                logger.info(f"Executing command: {command} -> {key}")
                keyboard.press_and_release(key)
                self.command_executed.emit(command)
                logger.debug(f"Successfully executed command: {command}")
                time.sleep(self.typing_speed * 2)  # Slightly longer pause after commands
            else:
                logger.warning(f"No key mapping found for command: {command}")
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}", exc_info=True)
    
    def set_typing_speed(self, speed: float):
        """Set the typing speed in seconds between characters.
        
        Args:
            speed: Time in seconds between characters
        """
        if speed > 0:
            self.typing_speed = speed
            config.set("typing_speed", speed)
            logger.info(f"Updated typing speed to {speed}s") 
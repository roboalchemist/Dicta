"""Text typing functionality for Dicta."""

import logging
import time
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QCoreApplication
from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import QApplication

from app.config import config
from app.desktop_ui.command_mapper import CommandMapper

logger = logging.getLogger(__name__)

class TextTyper(QObject):
    """Handles typing text and executing keyboard commands."""
    
    # Signals
    typing_started = pyqtSignal()
    typing_finished = pyqtSignal()
    command_executed = pyqtSignal(str)  # Emits the command that was executed
    
    # Internal signals for main thread execution
    _type_text_signal = pyqtSignal(str)
    _execute_command_signal = pyqtSignal(str)
    
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
        
        # Connect internal signals to main thread methods
        self._type_text_signal.connect(self._type_text_on_main_thread)
        self._execute_command_signal.connect(self._execute_command_on_main_thread)
        
        logger.info(f"Initialized TextTyper with {len(self.commands)} commands")
    
    def _type_text_on_main_thread(self, text: str):
        """Type text on the main thread using clipboard simulation.
        
        Args:
            text: Text to type
        """
        try:
            logger.info(f"Typing text on main thread: {text}")
            
            # Get the application clipboard
            app = QApplication.instance()
            if app is None:
                logger.error("No QApplication instance found")
                return
                
            clipboard = app.clipboard()
            
            # Save current clipboard content
            original_content = clipboard.text()
            
            # Set our text to clipboard
            clipboard.setText(text)
            
            # Simulate Cmd+V to paste the text
            # This is much more reliable than trying to simulate individual keystrokes
            import subprocess
            try:
                # Use osascript (AppleScript) to send Cmd+V 
                subprocess.run([
                    'osascript', '-e', 
                    'tell application "System Events" to keystroke "v" using command down'
                ], check=True, capture_output=True)
                
                logger.info(f"Successfully typed text via clipboard: {text}")
                
                # Restore original clipboard content after a short delay
                QTimer.singleShot(100, lambda: clipboard.setText(original_content))
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to execute paste command: {e}")
                # Restore clipboard immediately if paste failed
                clipboard.setText(original_content)
                
        except Exception as e:
            logger.error(f"Error typing text on main thread: {e}")
    
    def _execute_command_on_main_thread(self, command: str):
        """Execute a command on the main thread.
        
        Args:
            command: The command to execute
        """
        try:
            key = self.commands.get(command)
            if key:
                logger.info(f"Executing command on main thread: {command} -> {key}")
                
                # Use osascript to send the key press
                import subprocess
                
                # Map our key names to AppleScript key codes
                applescript_keys = {
                    'escape': 'key code 53',
                    'enter': 'key code 36', 
                    'return': 'key code 36',
                    'tab': 'key code 48',
                    'space': 'key code 49',
                    'up': 'key code 126',
                    'down': 'key code 125', 
                    'left': 'key code 123',
                    'right': 'key code 124',
                    'backspace': 'key code 51',
                    'delete': 'key code 117',
                }
                
                applescript_key = applescript_keys.get(key.lower())
                if applescript_key:
                    try:
                        subprocess.run([
                            'osascript', '-e',
                            f'tell application "System Events" to {applescript_key}'
                        ], check=True, capture_output=True)
                        
                        self.command_executed.emit(command)
                        logger.info(f"Successfully executed command: {command}")
                        
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to execute command: {e}")
                else:
                    logger.warning(f"Unknown key for command: {command} -> {key}")
            else:
                logger.warning(f"No key mapping found for command: {command}")
                
        except Exception as e:
            logger.error(f"Error executing command on main thread: {e}")
    
    def type_text(self, text: str):
        """Type the given text.
        
        Args:
            text: The text to type
        """
        if not text:
            logger.warning("Received empty text to type")
            return
            
        try:
            logger.info(f"Starting to type text: {text}")
            self.typing_started.emit()
            
            # Split text into words but preserve original case
            words = text.split()
            logger.debug(f"Split text into {len(words)} words: {words}")
            
            import string
            
            # Only process as command if it's a single word
            if len(words) == 1:
                word = words[0]
                # Create cleaned copy for command checking (lowercase, no punctuation, stripped)
                cleaned_word = word.lower().strip().translate(str.maketrans("", "", string.punctuation))
                
                # Check if cleaned word is a command
                if cleaned_word in self.commands:
                    logger.info(f"Found single-word command: {cleaned_word} -> {self.commands[cleaned_word]}")
                    # Execute command on main thread
                    self._execute_command_signal.emit(cleaned_word)
                    self.typing_finished.emit()
                    return
            
            # If not a single-word command, type the entire text normally
            full_text = " ".join(words)
            # Type text on main thread
            self._type_text_signal.emit(full_text)
            
            self.typing_finished.emit()
            logger.info(f"Finished typing text: {text}")
            
        except Exception as e:
            logger.error(f"Error typing text: {e}", exc_info=True)
            self.typing_finished.emit()
    
    def set_typing_speed(self, speed: float):
        """Set the typing speed in seconds between characters.
        
        Args:
            speed: Time in seconds between characters
        """
        if speed > 0:
            self.typing_speed = speed
            config.set("typing_speed", speed)
            logger.info(f"Updated typing speed to {speed}s") 
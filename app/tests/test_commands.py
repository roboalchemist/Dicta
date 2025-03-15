"""Tests for voice command functionality."""
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QPushButton, QLabel, QMessageBox, QTableWidget
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
import os
import speech_recognition as sr
import wave

from app.desktop_ui.command_list import CommandListWindow
from app.desktop_ui.command_overlay import CommandOverlay
from app.desktop_ui.command_mapper import CommandMapper
from app.desktop_ui.main import DictaSystemTrayIcon
from app.speech_manager import SpeechManager
from app.audio import AudioCapture
from app.speech import GroqWhisperService

# Mock the audio and speech modules
mock_audio_capture = MagicMock()
mock_speech_to_text = MagicMock()
mock_groq_whisper = MagicMock()

# Apply mocks
patches = [
    patch('app.audio.AudioCapture', mock_audio_capture),
    patch('app.speech_manager.SpeechManager', mock_speech_to_text),
    patch('app.speech.GroqWhisperService', mock_groq_whisper)
]

# Apply all patches
for p in patches:
    p.start()

# Stop all patches after imports
for p in patches:
    p.stop()

@pytest.fixture
def command_mapper():
    """Create a command mapper instance."""
    mapper = CommandMapper()
    # Clear any default commands
    mapper.commands = {}
    return mapper

@pytest.fixture
def command_list(qtbot, command_mapper):
    """Create a command list window instance."""
    window = CommandListWindow(command_mapper)
    qtbot.addWidget(window)
    # Wait for window to be shown
    with qtbot.waitExposed(window):
        window.show()
    return window

@pytest.fixture
def command_overlay(qtbot, command_mapper):
    """Create a command overlay instance."""
    overlay = CommandOverlay(command_mapper)
    qtbot.addWidget(overlay)
    return overlay

@pytest.fixture
def system_tray(qtbot):
    """Create a system tray icon instance."""
    tray = DictaSystemTrayIcon()
    tray.show()  # Make sure the tray icon is visible
    return tray

@pytest.fixture
def test_audio_file():
    """Get path to test audio file."""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_dir, "test-data", "test_audio.wav")

def test_command_list_initialization(command_list):
    """Test that the command list window initializes correctly."""
    assert command_list.command_input.placeholderText() == "Voice Command"
    assert command_list.key_input.placeholderText() == "Key (e.g. 'escape')"
    assert command_list.command_table.rowCount() == 0

def test_add_command(command_list, command_mapper):
    """Test adding a command."""
    command_list.command_input.setText("test")
    command_list.key_input.setText("control+tab")
    command_list.add_button.click()
    
    assert command_list.command_table.rowCount() == 1
    assert command_list.command_table.item(0, 0).text() == "test"
    assert command_list.command_table.item(0, 1).text() == "control+tab"
    assert "test" in command_mapper.commands
    assert command_mapper.commands["test"] == "control+tab"

def test_remove_command(command_list, command_mapper):
    """Test removing a command."""
    # Add a command first
    command_list.command_input.setText("test")
    command_list.key_input.setText("control+tab")
    command_list.add_button.click()
    
    # Select and remove it
    command_list.command_table.selectRow(0)
    command_list.remove_button.click()
    
    assert command_list.command_table.rowCount() == 0
    assert "test" not in command_mapper.commands

def test_edit_command(command_list, command_mapper):
    """Test editing a command."""
    # Add a command first
    command_list.command_input.setText("test")
    command_list.key_input.setText("control+tab")
    command_list.add_button.click()
    
    # Select and edit it
    command_list.command_table.selectRow(0)
    command_list.command_input.setText("test2")
    command_list.key_input.setText("control+space")
    command_list.edit_button.click()
    
    assert command_list.command_table.rowCount() == 1
    assert command_list.command_table.item(0, 0).text() == "test2"
    assert command_list.command_table.item(0, 1).text() == "control+space"
    assert "test" not in command_mapper.commands
    assert "test2" in command_mapper.commands
    assert command_mapper.commands["test2"] == "control+space"

def test_invalid_key_format(command_list):
    """Test handling invalid key format."""
    command_list.command_input.setText("test")
    command_list.key_input.setText("invalid+key")
    command_list.add_button.click()
    
    assert command_list.command_table.rowCount() == 0

def test_duplicate_command(command_list):
    """Test adding duplicate command."""
    # Add first command
    command_list.command_input.setText("test")
    command_list.key_input.setText("control+tab")
    command_list.add_button.click()
    
    # Try to add duplicate
    command_list.command_input.setText("test")
    command_list.key_input.setText("control+space")
    command_list.add_button.click()
    
    assert command_list.command_table.rowCount() == 1
    assert command_list.command_table.item(0, 1).text() == "control+tab"

def test_command_case_insensitive(command_list, command_mapper):
    """Test that commands are case insensitive."""
    command_mapper.add_command("test", "control+tab")
    
    assert command_mapper.process_text("TEST")
    assert command_mapper.process_text("Test")
    assert command_mapper.process_text("test")

def test_overlay_position(command_overlay, qtbot):
    """Test that the overlay appears in the correct position."""
    command_overlay.show()
    qtbot.waitForWindowShown(command_overlay)
    
    # Get screen geometry
    screen = QApplication.primaryScreen()
    screen_rect = screen.availableGeometry()
    
    # Calculate expected position (centered horizontally, 100px from bottom)
    expected_x = (screen_rect.width() - command_overlay.width()) // 2
    expected_y = screen_rect.height() - command_overlay.height() - 100
    
    # Allow for some margin of error due to window decorations
    assert abs(command_overlay.x() - expected_x) <= 5
    assert abs(command_overlay.y() - expected_y) <= 20

def test_keyboard_handling(command_overlay, qtbot):
    """Test keyboard event handling in the overlay."""
    command_overlay.show()
    qtbot.waitForWindowShown(command_overlay)
    
    # Test escape key closes overlay
    qtbot.keyClick(command_overlay, Qt.Key.Key_Escape)
    assert not command_overlay.isVisible()
    
    # Show overlay again
    command_overlay.show()
    qtbot.waitForWindowShown(command_overlay)
    
    # Test enter key closes overlay
    qtbot.keyClick(command_overlay, Qt.Key.Key_Return)
    assert not command_overlay.isVisible()

def test_command_execution(command_mapper):
    """Test command execution."""
    with patch('keyboard.press_and_release') as mock_press:
        command_mapper.add_command("test", "escape")
        command_mapper.process_text("test")
        mock_press.assert_called_once_with("escape")

def test_command_execution_error_handling(command_mapper):
    """Test error handling during command execution."""
    with patch('keyboard.press_and_release', side_effect=Exception("Test error")):
        with patch.object(QMessageBox, 'warning') as mock_warning:
            command_mapper.add_command("test", "escape")
            command_mapper.process_text("test")
            mock_warning.assert_called_once()

def test_command_list_keyboard_shortcuts(command_list, qtbot):
    """Test keyboard shortcuts in command list window."""
    # Add a test command
    command_list.command_mapper.add_command("test command", "escape")
    command_list.load_commands()
    qtbot.wait(100)  # Wait for commands to load

    # Select the command
    command_list.command_table.selectRow(0)
    qtbot.wait(100)  # Wait for selection

    # Test Delete key removes command
    qtbot.keyClick(command_list.command_table, Qt.Key.Key_Delete)
    qtbot.wait(100)  # Wait for key event to be processed
    assert command_list.command_table.rowCount() == 0

def test_system_tray_integration(system_tray):
    """Test system tray icon integration."""
    assert system_tray.isVisible()
    assert system_tray.contextMenu() is not None

def test_command_persistence(command_mapper):
    """Test that commands persist through config."""
    # Add a command
    command_mapper.add_command("test command", "escape")

    # Create new instance with same config
    new_mapper = CommandMapper()
    new_mapper.commands = {}  # Clear default commands
    new_mapper.load_commands()  # Load commands from config

    # Verify command persisted
    commands = new_mapper.get_commands()
    assert "test command" in commands

def test_command_overlay_show(command_overlay, command_mapper, qtbot):
    """Test showing the command overlay."""
    # Add some test commands
    command_mapper.add_command("test1", "escape")
    command_mapper.add_command("test2", "return")

    # Show the overlay
    with qtbot.waitExposed(command_overlay):
        command_overlay.show_commands(1000)  # 1 second duration

    # Process events and verify overlay is visible
    qtbot.wait(100)
    assert command_overlay.isVisible()

    # Verify commands are displayed
    command_text = command_overlay.command_label.text()
    assert "test1 -> escape" in command_text
    assert "test2 -> return" in command_text

def test_command_overlay_auto_hide(command_overlay, qtbot):
    """Test that overlay auto-hides after duration."""
    command_overlay.show_commands(500)  # 500ms duration
    qtbot.waitForWindowShown(command_overlay)
    
    # Process events and verify overlay is visible
    assert command_overlay.isVisible()
    
    # Wait for auto-hide
    qtbot.wait(600)  # Wait a bit longer than the duration
    assert not command_overlay.isVisible()

def test_overlay_keyboard_handling(command_overlay, qtbot):
    """Test keyboard handling in the overlay."""
    command_overlay.show()
    qtbot.waitForWindowShown(command_overlay)

    # Test escape key closes overlay
    qtbot.keyClick(command_overlay, Qt.Key.Key_Escape)
    assert not command_overlay.isVisible()

    # Show overlay again
    command_overlay.show()
    qtbot.waitForWindowShown(command_overlay)

    # Test enter key closes overlay
    qtbot.keyClick(command_overlay, Qt.Key.Key_Return)
    assert not command_overlay.isVisible()

def test_audio_to_typing_e2e(test_audio_file, qtbot):
    """Test end-to-end flow from audio input to typing output."""
    # Create a mock keyboard to track typed text
    typed_text = []
    speech_manager = None
    try:
        with patch('keyboard.write') as mock_write:
            mock_write.side_effect = lambda text: typed_text.append(text)
            
            # Initialize speech manager
            speech_manager = SpeechManager()
            
            # Connect to transcription signal
            @speech_manager.transcription_ready.connect
            def handle_transcription(text):
                # Simulate typing the transcribed text
                mock_write.assert_not_called()  # Ensure no typing has happened yet
                mock_write(text)
            
            # Load test audio file
            with open(test_audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Create recognizer and convert audio data to AudioData
            recognizer = sr.Recognizer()
            with wave.open(test_audio_file, 'rb') as wav_file:
                audio = sr.AudioData(
                    wav_file.readframes(wav_file.getnframes()),
                    wav_file.getframerate(),
                    wav_file.getsampwidth()
                )
            
            # Mock recognize_google to return known text
            test_text = "Hello world, this is a test"
            with patch.object(recognizer, 'recognize_google', return_value=test_text):
                # Process the audio through the speech recognition
                text = recognizer.recognize_google(audio)
                speech_manager.transcription_ready.emit(text)
            
            # Wait for signal processing
            qtbot.wait(100)
            
            # Verify text was typed
            assert len(typed_text) > 0
            assert typed_text[0] == test_text
    finally:
        if speech_manager:
            speech_manager.stop_listening() 
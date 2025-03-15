import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from PyQt6.QtCore import Qt
from app.desktop_ui.hotkeys import HotkeyManager

@pytest.fixture
def temp_config():
    """Create a temporary config file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        yield config_path

@pytest.fixture
def hotkey_manager(temp_config, qapp):
    """Create a hotkey manager instance with a temporary config."""
    manager = HotkeyManager(config_path=temp_config)
    yield manager
    manager.cleanup()

def test_hotkey_manager_initialization(hotkey_manager):
    """Test that the hotkey manager initializes with default settings."""
    assert hotkey_manager.push_to_talk_key == "\\"  # Default key is backslash
    assert isinstance(hotkey_manager.config_path, Path)

def test_load_config_nonexistent(hotkey_manager):
    """Test loading config when file doesn't exist."""
    config = hotkey_manager._load_config()
    assert isinstance(config, dict)
    assert len(config) == 0

def test_save_and_load_config(hotkey_manager, temp_config):
    """Test saving and loading configuration."""
    # Save config
    test_config = {"push_to_talk_key": "a"}
    hotkey_manager._save_config(test_config)
    
    # Verify file exists
    assert temp_config.exists()
    
    # Load and verify config
    loaded_config = hotkey_manager._load_config()
    assert loaded_config == test_config

@patch('keyboard.on_press_key')
@patch('keyboard.on_release_key')
def test_setup_hotkeys(mock_on_release, mock_on_press, hotkey_manager):
    """Test setting up keyboard hooks."""
    hotkey_manager._setup_hotkeys()
    mock_on_press.assert_called_once()
    mock_on_release.assert_called_once()

@patch('keyboard.unhook_key')
@patch('keyboard.on_press_key')
@patch('keyboard.on_release_key')
def test_set_push_to_talk_key(mock_on_release, mock_on_press, mock_unhook, hotkey_manager):
    """Test changing the push-to-talk key."""
    # Set new key
    hotkey_manager.set_push_to_talk_key("a")
    
    # Verify old key was unhooked
    mock_unhook.assert_called_once_with("\\")  # Verify unhooking backslash key
    
    # Verify new hooks were set up
    assert mock_on_press.called
    assert mock_on_release.called
    
    # Verify config was updated
    config = hotkey_manager._load_config()
    assert config["push_to_talk_key"] == "a"

@patch('keyboard.unhook_key')
def test_cleanup(mock_unhook, hotkey_manager):
    """Test cleanup of keyboard hooks."""
    hotkey_manager.cleanup()
    mock_unhook.assert_called_once_with(hotkey_manager.push_to_talk_key)

def test_hotkey_signals(hotkey_manager, qtbot):
    """Test that hotkey signals are emitted correctly."""
    # Set up signal tracking
    with qtbot.waitSignal(hotkey_manager.hotkey_pressed, timeout=1000) as pressed_signal:
        # Simulate key press
        hotkey_manager.hotkey_pressed.emit()
    assert pressed_signal.signal_triggered
    
    with qtbot.waitSignal(hotkey_manager.hotkey_released, timeout=1000) as released_signal:
        # Simulate key release
        hotkey_manager.hotkey_released.emit()
    assert released_signal.signal_triggered 
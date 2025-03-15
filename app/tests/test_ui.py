import pytest
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from app.desktop_ui.main import DictaSystemTrayIcon, SpeechManager
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="session")
def qapp():
    """Create a Qt application instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

@pytest.fixture
def mock_groq_service():
    """Create a mock Groq service."""
    mock = MagicMock()
    mock.transcribe_audio.return_value = "Test transcription"
    mock.transcribe_stream.return_value = "Test stream transcription"
    return mock

@pytest.fixture
def tray_icon(qapp, qtbot, mock_groq_service):
    """Create a system tray icon instance."""
    with patch('app.desktop_ui.main.GroqWhisperService', return_value=mock_groq_service):
        icon = DictaSystemTrayIcon()
        qtbot.addWidget(icon.contextMenu())  # Add menu to qtbot for event handling
        yield icon
        icon.hide()
        icon.deleteLater()

@pytest.fixture
def speech_manager(qapp, mock_groq_service):
    """Create a speech manager instance."""
    with patch('app.desktop_ui.main.GroqWhisperService', return_value=mock_groq_service):
        manager = SpeechManager()
        yield manager
        manager.deleteLater()

def test_tray_icon_initialization(tray_icon, qtbot):
    """Test that the tray icon initializes correctly."""
    assert tray_icon is not None
    assert tray_icon.isSystemTrayAvailable()
    assert tray_icon.toolTip() == "Dicta - Voice Control"

def test_menu_setup(tray_icon, qtbot):
    """Test that the menu is set up correctly."""
    menu = tray_icon.contextMenu()
    assert menu is not None
    
    # Check menu items
    actions = menu.actions()
    assert len(actions) == 3  # Auto Listen, Separator, Quit
    assert actions[0].text() == "Auto Listen"
    assert actions[0].isCheckable()
    assert not actions[0].isChecked()
    assert actions[2].text() == "Quit"

def test_speech_manager_initialization(speech_manager, qtbot):
    """Test that the speech manager initializes correctly."""
    assert speech_manager is not None
    assert not speech_manager.is_listening
    assert not speech_manager.auto_listen

@patch('app.audio.AudioCapture.start_recording')
@patch('app.audio.AudioCapture.stop_recording')
def test_auto_listen_toggle(mock_stop_recording, mock_start_recording, tray_icon, qtbot):
    """Test that auto-listen toggle works correctly."""
    # Mock audio recording
    mock_stop_recording.return_value = b'test_audio_data'
    
    # Get the auto-listen action
    auto_listen_action = tray_icon.contextMenu().actions()[0]
    
    # Toggle auto-listen on
    with qtbot.waitSignal(tray_icon.speech_manager.status_changed, timeout=1000):
        auto_listen_action.trigger()
    assert auto_listen_action.isChecked()
    assert tray_icon.speech_manager.auto_listen
    assert tray_icon.speech_manager.is_listening
    assert mock_start_recording.called
    
    # Toggle auto-listen off
    with qtbot.waitSignal(tray_icon.speech_manager.status_changed, timeout=1000):
        auto_listen_action.trigger()
    assert not auto_listen_action.isChecked()
    assert not tray_icon.speech_manager.auto_listen
    assert not tray_icon.speech_manager.is_listening
    assert mock_stop_recording.called

@patch('app.audio.AudioCapture.start_recording')
@patch('app.audio.AudioCapture.stop_recording')
def test_icon_color_changes(mock_stop_recording, mock_start_recording, tray_icon, qtbot):
    """Test that the icon color changes with status."""
    # Mock audio recording
    mock_stop_recording.return_value = b'test_audio_data'
    
    # Start listening (yellow)
    with qtbot.waitSignal(tray_icon.speech_manager.status_changed, timeout=1000):
        tray_icon.speech_manager.start_listening()
    assert mock_start_recording.called
    
    # Stop listening (green during processing, then red)
    with qtbot.waitSignal(tray_icon.speech_manager.status_changed, timeout=1000):
        tray_icon.speech_manager.stop_listening()
    assert mock_stop_recording.called 
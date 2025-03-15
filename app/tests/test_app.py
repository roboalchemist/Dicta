import sys
import pytest
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import Qt, PYQT_VERSION_STR
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor
from app.desktop_ui.main import DictaSystemTrayIcon

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName("Dicta")
    return app

def test_qapp_creation(qapp, qtbot):
    """Test that QApplication can be created"""
    assert qapp is not None
    assert qapp.applicationName() == "Dicta"

def test_qt_version():
    """Test that we're using the correct Qt version"""
    version_parts = tuple(map(int, PYQT_VERSION_STR.split('.')))
    assert version_parts >= (6, 0, 0), "Qt version should be 6.0.0 or higher"

def test_system_tray_icon_creation(qapp, qtbot):
    """Test that system tray icon can be created and shown"""
    tray_icon = DictaSystemTrayIcon()
    assert tray_icon is not None
    assert isinstance(tray_icon, QSystemTrayIcon)
    assert tray_icon.isSystemTrayAvailable()
    assert tray_icon.toolTip() == "Dicta - Voice Control"

def test_system_tray_menu(qapp, qtbot):
    """Test that system tray menu has the correct items"""
    tray_icon = DictaSystemTrayIcon()
    menu = tray_icon.contextMenu()
    assert menu is not None
    
    # Check that we have a Quit action
    actions = menu.actions()
    assert len(actions) == 1
    assert actions[0].text() == "Quit"

def test_icon_colors(qapp, qtbot):
    """Test that icon can be created with different colors"""
    tray_icon = DictaSystemTrayIcon()
    
    # Test red color (default)
    assert tray_icon.icon() is not None
    
    # Test changing colors
    for color in ["red", "yellow", "green"]:
        tray_icon.create_icon(color)
        assert tray_icon.icon() is not None 
"""Tests for the configuration manager."""
import os
import json
import pytest
from pathlib import Path
from app.config import ConfigManager, DEFAULT_CONFIG

@pytest.fixture
def temp_home(tmp_path):
    """Create a temporary home directory."""
    old_home = os.environ.get('HOME')
    os.environ['HOME'] = str(tmp_path)
    yield tmp_path
    if old_home:
        os.environ['HOME'] = old_home

def test_config_creation(temp_home):
    """Test that the configuration file is created with default values."""
    config = ConfigManager()
    
    # Check that the config directory was created
    assert config.config_dir.exists()
    assert config.config_dir.is_dir()
    
    # Check that the config file was created
    assert config.config_file.exists()
    assert config.config_file.is_file()
    
    # Check that the config file contains the default values
    with open(config.config_file, 'r') as f:
        saved_config = json.load(f)
    assert saved_config == DEFAULT_CONFIG

def test_config_loading(temp_home):
    """Test that the configuration can be loaded."""
    # Create a config file with custom values
    config_dir = Path.home() / ".dicta"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    
    custom_config = {
        "whisper": {
            "backend": "whisper.cpp",
            "model_size": "medium",
            "device": "cuda",
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(custom_config, f)
    
    # Load the config
    config = ConfigManager()
    
    # Check that our custom values were loaded
    assert config.get("whisper", "backend") == "whisper.cpp"
    assert config.get("whisper", "model_size") == "medium"
    assert config.get("whisper", "device") == "cuda"
    
    # Check that missing sections/keys get default values
    assert config.get("hotkeys") == DEFAULT_CONFIG["hotkeys"]
    assert config.get("voice_commands", "escape") == DEFAULT_CONFIG["voice_commands"]["escape"]

def test_config_saving(temp_home):
    """Test that configuration changes can be saved."""
    config = ConfigManager()
    
    # Make some changes
    config.set("whisper", "backend", "openai")
    config.set("hotkeys", "push_to_talk", "Ctrl+Space")
    
    # Create a new config manager to load from disk
    config2 = ConfigManager()
    
    # Check that our changes were saved
    assert config2.get("whisper", "backend") == "openai"
    assert config2.get("hotkeys", "push_to_talk") == "Ctrl+Space"

def test_config_error_handling(temp_home):
    """Test error handling in the configuration manager."""
    config = ConfigManager()
    
    # Test getting non-existent section/key
    with pytest.raises(KeyError):
        config.get("nonexistent_section")
    
    # Test setting value with invalid section type
    with pytest.raises(TypeError, match="Section must be a string"):
        config.set(123, "key", "value")  # type: ignore
    
    # Test setting value with invalid key type
    with pytest.raises(TypeError, match="Key must be a string"):
        config.set("whisper", 123, "value")  # type: ignore
        
    # Test setting value with invalid section name
    with pytest.raises(ValueError, match="Invalid section"):
        config.set("invalid_section", "key", "value")
    
    # Test saving to a read-only file
    if os.name != 'nt':  # Skip on Windows
        config.config_file.chmod(0o444)  # Make file read-only
        with pytest.raises(Exception):
            config.set("whisper", "backend", "openai") 
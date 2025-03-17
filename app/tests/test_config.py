"""Test configuration management."""

import os
import json
import tempfile
from pathlib import Path
import pytest
from app.config import Config, DEFAULT_CONFIG

def test_config_initialization():
    """Test that Config initializes correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test config in a temporary directory
        config = Config()
        config.config_dir = Path(temp_dir)
        config.config_file = config.config_dir / "config.json"
        
        # Check that default values are set
        assert config.get("service") == "MLX"
        assert config.get("model_size") == "medium"
        assert config.get("hotkey") == "ctrl+shift+space"
        assert config.get("auto_listen") is False

def test_config_save_and_load():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test config
        config = Config()
        config.config_dir = Path(temp_dir)
        config.config_file = config.config_dir / "config.json"
        
        # Modify some values
        config.set("service", "Groq")
        config.set("model_size", "large-v3")
        config.save()
        
        # Create a new config instance to load the saved values
        config2 = Config()
        config2.config_dir = Path(temp_dir)
        config2.config_file = config2.config_dir / "config.json"
        config2.load()
        
        # Check that values were loaded correctly
        assert config2.get("service") == "Groq"
        assert config2.get("model_size") == "large-v3"

def test_config_get_default():
    """Test getting configuration with default values."""
    config = Config()
    
    # Test getting existing value
    assert config.get("service") == "MLX"
    
    # Test getting non-existent value with default
    assert config.get("non_existent", "default") == "default"
    
    # Test getting non-existent value without default
    assert config.get("non_existent") is None

def test_config_set():
    """Test setting configuration values."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config()
        config.config_dir = Path(temp_dir)
        config.config_file = config.config_dir / "config.json"
        
        # Set a new value
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"
        
        # Verify the value was saved to file
        with open(config.config_file, "r") as f:
            saved_config = json.load(f)
            assert saved_config["test_key"] == "test_value"

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
    config = Config()
    
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
    config = Config()
    
    # Check that our custom values were loaded
    assert config.get("whisper", "backend") == "whisper.cpp"
    assert config.get("whisper", "model_size") == "medium"
    assert config.get("whisper", "device") == "cuda"
    
    # Check that missing sections/keys get default values
    assert config.get("hotkeys") == DEFAULT_CONFIG["hotkeys"]
    assert config.get("voice_commands", "escape") == DEFAULT_CONFIG["voice_commands"]["escape"]

def test_config_saving(temp_home):
    """Test that configuration changes can be saved."""
    config = Config()
    
    # Make some changes
    config.set("whisper", "backend", "openai")
    config.set("hotkeys", "push_to_talk", "Ctrl+Space")
    
    # Create a new config manager to load from disk
    config2 = Config()
    
    # Check that our changes were saved
    assert config2.get("whisper", "backend") == "openai"
    assert config2.get("hotkeys", "push_to_talk") == "Ctrl+Space"

def test_config_error_handling(temp_home):
    """Test error handling in the configuration manager."""
    config = Config()
    
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
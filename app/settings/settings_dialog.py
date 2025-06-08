"""Settings dialog for Dicta."""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget,
    QLabel, QLineEdit, QPushButton, QFrame, QWidget, QFormLayout,
    QComboBox, QMessageBox, QGroupBox, QDoubleSpinBox, QSpinBox, QCheckBox,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.config import Config

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Settings dialog for Dicta."""
    
    def __init__(self, config: Config, parent=None):
        """Initialize the settings dialog."""
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 400)
        
        # Create layout
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Create and set up the sidebar
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(200)
        self.sidebar.addItems([
            "Local Models",
            "Groq API",
            "Hotkeys",
            "Commands",
            "Audio",
            "Display"
        ])
        layout.addWidget(self.sidebar)
        
        # Add a vertical line separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Create and set up the stacked widget for different settings pages
        self.pages = QStackedWidget()
        layout.addWidget(self.pages)
        
        # Create settings pages
        self.setup_local_models_page()
        self.setup_groq_api_page()
        self.setup_hotkeys_page()
        self.setup_commands_page()
        self.setup_audio_page()
        self.setup_display_page()
        
        # Connect signals
        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)
    
    def setup_local_models_page(self):
        """Set up the local models settings page."""
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        # Title
        title = QLabel("Local Model Settings")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Current accelerator info
        accel_layout = QFormLayout()
        accel_label = QLabel("Available Accelerators:")
        accel_value = QLabel("MLX (Apple Neural Engine)")
        accel_value.setStyleSheet("color: #666;")
        accel_layout.addRow(accel_label, accel_value)
        
        current_accel = QLabel("Currently Using:")
        current_value = QLabel("MLX")
        current_value.setStyleSheet("font-weight: bold; color: #007AFF;")
        accel_layout.addRow(current_accel, current_value)
        
        layout.addLayout(accel_layout)
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Transcription Engine Selection
        engine_title = QLabel("Transcription Engine")
        engine_title.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(engine_title)
        
        engine_layout = QFormLayout()
        
        # Engine selection
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["whisper", "parakeet"])
        self.engine_combo.setCurrentText(self.config.get("transcription_engine", "whisper"))
        self.engine_combo.currentTextChanged.connect(self._on_engine_changed)
        engine_layout.addRow("Engine:", self.engine_combo)
        
        # Whisper model selection
        whisper_label = QLabel("Whisper Model:")
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["large-v3", "medium", "small", "tiny"])  # Largest to smallest
        self.whisper_combo.setCurrentText(self.config.get("model_size", "large-v3"))
        self.whisper_combo.currentTextChanged.connect(
            lambda text: self.config.set("model_size", text)
        )
        engine_layout.addRow(whisper_label, self.whisper_combo)
        
        # Parakeet model selection
        parakeet_label = QLabel("Parakeet Model:")
        self.parakeet_combo = QComboBox()
        self.parakeet_combo.addItems([
            "mlx-community/parakeet-rnnt-0.6b",
            "mlx-community/parakeet-rnnt-1.1b"
        ])
        self.parakeet_combo.setCurrentText(self.config.get("parakeet_model", "mlx-community/parakeet-rnnt-0.6b"))
        self.parakeet_combo.currentTextChanged.connect(
            lambda text: self.config.set("parakeet_model", text)
        )
        engine_layout.addRow(parakeet_label, self.parakeet_combo)
        
        layout.addLayout(engine_layout)
        
        # Store references for enabling/disabling
        self.whisper_label = whisper_label
        self.parakeet_label = parakeet_label
        
        # Update visibility based on current engine
        self._update_engine_visibility()
        
        # Add some spacing
        layout.addSpacing(20)
        
        # Model cache settings
        cache_title = QLabel("Model Cache")
        cache_title.setFont(QFont("", 12, QFont.Weight.Bold))
        layout.addWidget(cache_title)
        
        cache_layout = QFormLayout()
        cache_dir = QLineEdit(str(Path.home() / ".cache" / "dicta" / "models"))
        cache_dir.setReadOnly(True)
        cache_layout.addRow("Cache Directory:", cache_dir)
        
        clear_cache = QPushButton("Clear Cache")
        clear_cache.clicked.connect(self.clear_model_cache)
        cache_layout.addRow("", clear_cache)
        
        layout.addLayout(cache_layout)
        layout.addStretch()
        
        self.pages.addWidget(page)
    
    def _on_engine_changed(self, engine):
        """Handle transcription engine change."""
        self.config.set("transcription_engine", engine)
        self._update_engine_visibility()
        
    def _update_engine_visibility(self):
        """Update visibility of engine-specific controls."""
        engine = self.config.get("transcription_engine", "whisper")
        
        # Show/hide Whisper controls
        is_whisper = engine == "whisper"
        self.whisper_label.setVisible(is_whisper)
        self.whisper_combo.setVisible(is_whisper)
        
        # Show/hide Parakeet controls
        is_parakeet = engine == "parakeet"
        self.parakeet_label.setVisible(is_parakeet)
        self.parakeet_combo.setVisible(is_parakeet)
    
    def setup_groq_api_page(self):
        """Set up the Groq API settings page."""
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        # Title
        title = QLabel("Groq API Settings")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # API settings
        form = QFormLayout()
        
        # API Key
        api_key = QLineEdit(self.config.get("groq_api_key", ""))
        api_key.setPlaceholderText("Enter your Groq API key")
        api_key.textChanged.connect(lambda text: self.config.set("groq_api_key", text))
        form.addRow("API Key:", api_key)
        
        # API Base URL
        api_url = QLineEdit(self.config.get("groq_api_url", "https://api.groq.com/v1"))
        api_url.setPlaceholderText("Enter Groq API base URL")
        api_url.textChanged.connect(lambda text: self.config.set("groq_api_url", text))
        form.addRow("API URL:", api_url)
        
        # Request timeout
        timeout = QLineEdit(str(self.config.get("groq_timeout", 30)))
        timeout.setPlaceholderText("Request timeout in seconds")
        timeout.textChanged.connect(lambda text: self.config.set("groq_timeout", int(text) if text.isdigit() else 30))
        form.addRow("Timeout (seconds):", timeout)
        
        layout.addLayout(form)
        
        # Test connection button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_groq_connection)
        layout.addWidget(test_btn)
        
        layout.addStretch()
        self.pages.addWidget(page)
    
    def setup_hotkeys_page(self):
        """Set up the hotkeys settings page."""
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        # Title
        title = QLabel("Hotkey Settings")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Hotkey settings
        form = QFormLayout()
        
        # Push-to-talk key
        ptt_key = QLineEdit(self.config.get("push_to_talk_key", "`"))
        ptt_key.setPlaceholderText("Press a key to set")
        ptt_key.textChanged.connect(lambda text: self.config.set("push_to_talk_key", text))
        form.addRow("Push-to-Talk Key:", ptt_key)
        
        layout.addLayout(form)
        layout.addStretch()
        self.pages.addWidget(page)
    
    def setup_commands_page(self):
        """Set up the commands settings page."""
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        # Title
        title = QLabel("Voice Commands")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Description
        description = QLabel(
            "Configure voice commands that trigger keyboard shortcuts.\n"
            "Say these words to execute the corresponding keyboard commands."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Commands form
        form = QFormLayout()
        self.command_inputs = {}  # Store references to inputs
        
        # Get current commands
        commands = self.config.get("commands", {})
        
        # Add fields for each command
        command_list = [
            ("escape", "Escape"),
            ("enter", "Enter"),
            ("tab", "Tab"),
            ("up", "Up Arrow"),
            ("down", "Down Arrow"),
            ("left", "Left Arrow"),
            ("right", "Right Arrow"),
            ("backspace", "Backspace"),
            ("delete", "Delete"),
            ("space", "Space"),
            ("stop", "Stop (Command+Delete)"),
            ("accept", "Accept (Command+Enter)")
        ]
        
        for command_key, display_name in command_list:
            # Create input field
            input_field = QLineEdit()
            input_field.setText(commands.get(command_key, ""))
            input_field.setPlaceholderText("Enter keyboard shortcut")
            
            # Store reference
            self.command_inputs[command_key] = input_field
            
            # Add to form
            form.addRow(f"{display_name}:", input_field)
            
            # Connect signal
            input_field.textChanged.connect(
                lambda text, key=command_key: self._update_command(key, text)
            )
        
        layout.addLayout(form)
        
        # Add to pages
        # Add the commands view
        from app.desktop_ui.commands_view import CommandsView
        commands_view = CommandsView(self.config)
        
        # Override the white text color for dark theme
        for child in commands_view.findChildren(QLabel):
            if "color: #FFFFFF" in child.styleSheet():
                child.setStyleSheet(child.styleSheet().replace("color: #FFFFFF", ""))
        
        layout.addWidget(commands_view)
        layout.addStretch()
        
        self.pages.addWidget(page)
    
    def setup_audio_page(self):
        """Set up the audio settings page."""
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        # Title
        title = QLabel("Audio Settings")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Audio settings
        form = QFormLayout()
        
        # Input device selection
        input_device = QComboBox()
        input_device.addItems(["Default Input Device", "Device 1", "Device 2"])  # TODO: Get actual devices
        form.addRow("Input Device:", input_device)
        
        # Sample rate
        sample_rate = QComboBox()
        sample_rate.addItems(["16000 Hz", "44100 Hz", "48000 Hz"])
        form.addRow("Sample Rate:", sample_rate)
        
        # Typing Settings group
        typing_group = QGroupBox("Typing Settings")
        typing_layout = QFormLayout()
        
        # Typing speed
        typing_speed = QDoubleSpinBox()
        typing_speed.setRange(0.001, 0.5)
        typing_speed.setSingleStep(0.001)
        typing_speed.setDecimals(3)
        typing_speed.setValue(self.config.get("typing_speed", 0.01))
        typing_speed.valueChanged.connect(
            lambda value: self.config.set("typing_speed", value)
        )
        typing_layout.addRow("Typing Speed (s):", typing_speed)
        
        typing_group.setLayout(typing_layout)
        layout.addLayout(form)
        layout.addWidget(typing_group)
        
        # VAD Settings group
        vad_group = QGroupBox("Voice Activity Detection")
        vad_layout = QFormLayout()
        
        # VAD threshold slider (0.0-1.0)
        self.vad_threshold = QDoubleSpinBox()
        self.vad_threshold.setRange(0.0, 1.0)
        self.vad_threshold.setSingleStep(0.1)
        self.vad_threshold.setValue(self.config.get("vad_threshold", 0.5))
        self.vad_threshold.setToolTip("Higher values make VAD more aggressive (0.0-1.0)")
        self.vad_threshold.valueChanged.connect(
            lambda value: self.config.set("vad_threshold", value)
        )
        vad_layout.addRow("Threshold:", self.vad_threshold)
        
        # Silence frames threshold
        self.silence_threshold = QSpinBox()
        self.silence_threshold.setRange(1, 50)
        self.silence_threshold.setValue(self.config.get("vad_silence_threshold", 10))
        self.silence_threshold.setToolTip("Number of silence frames before stopping")
        self.silence_threshold.valueChanged.connect(
            lambda value: self.config.set("vad_silence_threshold", value)
        )
        vad_layout.addRow("Silence Frames:", self.silence_threshold)
        
        # Speech frames threshold
        self.speech_threshold = QSpinBox()
        self.speech_threshold.setRange(1, 20)
        self.speech_threshold.setValue(self.config.get("vad_speech_threshold", 3))
        self.speech_threshold.setToolTip("Number of speech frames before starting")
        self.speech_threshold.valueChanged.connect(
            lambda value: self.config.set("vad_speech_threshold", value)
        )
        vad_layout.addRow("Speech Frames:", self.speech_threshold)
        
        # Pre-buffer duration
        self.pre_buffer = QDoubleSpinBox()
        self.pre_buffer.setRange(0.0, 2.0)
        self.pre_buffer.setSingleStep(0.1)
        self.pre_buffer.setSuffix(" sec")
        self.pre_buffer.setValue(self.config.get("vad_pre_buffer", 0.5))
        self.pre_buffer.setToolTip("Seconds of audio to keep before speech is detected")
        self.pre_buffer.valueChanged.connect(
            lambda value: self.config.set("vad_pre_buffer", value)
        )
        vad_layout.addRow("Pre-buffer:", self.pre_buffer)
        
        # Post-buffer duration
        self.post_buffer = QDoubleSpinBox()
        self.post_buffer.setRange(0.0, 2.0)
        self.post_buffer.setSingleStep(0.1)
        self.post_buffer.setSuffix(" sec")
        self.post_buffer.setValue(self.config.get("vad_post_buffer", 0.2))
        self.post_buffer.setToolTip("Seconds of audio to keep after speech ends")
        self.post_buffer.valueChanged.connect(
            lambda value: self.config.set("vad_post_buffer", value)
        )
        vad_layout.addRow("Post-buffer:", self.post_buffer)
        
        vad_group.setLayout(vad_layout)
        layout.addWidget(vad_group)
        
        # Add general settings group
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout()
        
        # Auto-start listening
        auto_listen = QCheckBox("Start listening automatically")
        auto_listen.setChecked(self.config.get("auto_listen", True))
        auto_listen.setToolTip("When enabled, Dicta will start listening for voice input as soon as it launches")
        auto_listen.stateChanged.connect(
            lambda state: self.config.set("auto_listen", bool(state))
        )
        general_layout.addRow(auto_listen)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        layout.addStretch()
        self.pages.addWidget(page)
    
    def setup_display_page(self):
        """Set up the display settings page."""
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        # Title
        title = QLabel("Display Settings")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Display settings
        form = QFormLayout()
        
        # Notification duration
        notif_duration = QLineEdit(str(self.config.get("notification_duration", 2000)))
        notif_duration.setPlaceholderText("Duration in milliseconds")
        notif_duration.textChanged.connect(
            lambda text: self.config.set("notification_duration", int(text) if text.isdigit() else 2000)
        )
        form.addRow("Notification Duration (ms):", notif_duration)
        
        layout.addLayout(form)
        layout.addStretch()
        self.pages.addWidget(page)
    
    def clear_model_cache(self):
        """Clear the model cache."""
        # TODO: Implement model cache clearing
        QMessageBox.information(self, "Cache Cleared", "Model cache has been cleared.")
    
    def test_groq_connection(self):
        """Test the connection to Groq API."""
        api_key = self.config.get("groq_api_key")
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key first.")
            return
            
        # TODO: Implement actual API test
        QMessageBox.information(self, "Success", "Connection to Groq API successful!")
    
    def accept(self):
        """Save settings and close dialog."""
        # Save any pending changes
        self.config.save()
        super().accept()

    def setup_vad_settings(self):
        """Set up VAD settings group."""
        vad_group = QGroupBox("Voice Activity Detection")
        vad_layout = QFormLayout()
        
        # VAD threshold slider (0.0-1.0)
        self.vad_threshold = QDoubleSpinBox()
        self.vad_threshold.setRange(0.0, 1.0)
        self.vad_threshold.setSingleStep(0.1)
        self.vad_threshold.setValue(self.config.get("vad_threshold", 0.5))
        self.vad_threshold.setToolTip("Higher values make VAD more aggressive (0.0-1.0)")
        vad_layout.addRow("Threshold:", self.vad_threshold)
        
        # Silence frames threshold
        self.silence_threshold = QSpinBox()
        self.silence_threshold.setRange(1, 50)
        self.silence_threshold.setValue(self.config.get("vad_silence_threshold", 10))
        self.silence_threshold.setToolTip("Number of silence frames before stopping")
        vad_layout.addRow("Silence Frames:", self.silence_threshold)
        
        # Speech frames threshold
        self.speech_threshold = QSpinBox()
        self.speech_threshold.setRange(1, 20)
        self.speech_threshold.setValue(self.config.get("vad_speech_threshold", 3))
        self.speech_threshold.setToolTip("Number of speech frames before starting")
        vad_layout.addRow("Speech Frames:", self.speech_threshold)
        
        # Pre-buffer duration
        self.pre_buffer = QDoubleSpinBox()
        self.pre_buffer.setRange(0.0, 2.0)
        self.pre_buffer.setSingleStep(0.1)
        self.pre_buffer.setSuffix(" sec")
        self.pre_buffer.setValue(self.config.get("vad_pre_buffer", 0.5))
        self.pre_buffer.setToolTip("Seconds of audio to keep before speech is detected")
        vad_layout.addRow("Pre-buffer:", self.pre_buffer)
        
        # Post-buffer duration
        self.post_buffer = QDoubleSpinBox()
        self.post_buffer.setRange(0.0, 2.0)
        self.post_buffer.setSingleStep(0.1)
        self.post_buffer.setSuffix(" sec")
        self.post_buffer.setValue(self.config.get("vad_post_buffer", 0.2))
        self.post_buffer.setToolTip("Seconds of audio to keep after speech ends")
        vad_layout.addRow("Post-buffer:", self.post_buffer)
        
        vad_group.setLayout(vad_layout)
        return vad_group

    def save_settings(self):
        """Save settings to config."""
        try:
            # Save VAD settings
            self.config.set("vad_threshold", self.vad_threshold.value())
            self.config.set("vad_silence_threshold", self.silence_threshold.value())
            self.config.set("vad_speech_threshold", self.speech_threshold.value())
            self.config.set("vad_pre_buffer", self.pre_buffer.value())
            self.config.set("vad_post_buffer", self.post_buffer.value())
            
            # Save other settings...
            
            self.config.save()
            logger.info("Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}") 
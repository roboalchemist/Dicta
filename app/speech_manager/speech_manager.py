"""Speech manager module."""
import logging
from PyQt6.QtCore import QObject, pyqtSignal
from app.audio.vad import VADManager
from app.audio.audio_capture import AudioCapture
from app.speech.whisper_cpp import WhisperCppService

logger = logging.getLogger(__name__)

class SpeechManager(QObject):
    """Manages speech recognition and transcription."""
    
    # Signals
    transcription_ready = pyqtSignal(str)  # Emitted when transcription is ready
    status_changed = pyqtSignal(str)  # Emitted when status changes
    
    def __init__(self, speech_service, parent=None):
        """Initialize the speech manager.
        
        Args:
            speech_service: The speech-to-text service to use
            parent: Parent QObject
        """
        super().__init__(parent)
        self.audio_capture = AudioCapture()
        self.whisper = speech_service
        self.is_listening = False
        self.auto_listen = False
        
        # Initialize VAD
        self.vad_manager = VADManager(
            aggressiveness=2,  # Medium aggressiveness
            silence_threshold=10,  # 300ms of silence to end speech
            speech_threshold=3  # 90ms of speech to start
        )
        
        # Connect signals
        self.vad_manager.speech_started.connect(self.on_speech_started)
        self.vad_manager.speech_ended.connect(self.on_speech_ended)
        self.audio_capture.audio_data.connect(self.on_audio_data)
            
    def start_listening(self):
        """Start listening for speech."""
        if not self.is_listening:
            self.is_listening = True
            self.status_changed.emit("Listening")
            self.audio_capture.start()
            
    def stop_listening(self):
        """Stop listening for speech."""
        self.is_listening = False
        self.audio_capture.stop()
        self.status_changed.emit("Stopped")
        
    def toggle_auto_listen(self, enabled):
        """Toggle auto-listen mode."""
        self.auto_listen = enabled
        if enabled:
            self.start_listening()
        else:
            self.stop_listening()
            
    def on_audio_data(self, audio_data):
        """Handle incoming audio data."""
        if not self.is_listening:
            return
            
        # Process through VAD if in auto-listen mode
        if self.auto_listen:
            self.vad_manager.process_frame(audio_data)
        else:
            # Direct transcription when manually triggered
            self.process_audio(audio_data)
            
    def process_audio(self, audio_data):
        """Process audio data through Whisper.cpp."""
        try:
            text = self.whisper.transcribe_audio(audio_data)
            if text.strip():  # Only emit if we got actual text
                self.transcription_ready.emit(text)
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            
    def on_speech_started(self):
        """Handle speech start event."""
        logger.debug("Speech started")
        self.status_changed.emit("Speech detected")
        
    def on_speech_ended(self):
        """Handle speech end event."""
        logger.debug("Speech ended")
        self.status_changed.emit("Processing")
        
        # Process accumulated audio through Whisper
        if hasattr(self, '_current_audio'):
            self.process_audio(self._current_audio)
            
        if self.auto_listen:
            self.status_changed.emit("Listening") 
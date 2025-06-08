"""Speech manager that handles audio input and transcription."""

import numpy as np
import logging
from typing import Optional
from collections import deque
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
import time

from app.transcription import SpeechToText, WhisperService, ParakeetService
from app.audio import AudioService
from app.audio.vad import VADManager
from app.typing.text_typer import TextTyper
from app.config import config
from app.ollama import OllamaService

logger = logging.getLogger(__name__)

class TypingThread(QThread):
    """Thread for handling text typing and command execution."""
    
    typing_started = pyqtSignal()
    typing_finished = pyqtSignal()
    status_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """Initialize typing thread."""
        super().__init__(parent)
        self.text_queue = deque()
        self.word_queue = deque()  # High priority queue for individual words
        self.running = True
        self.text_typer = TextTyper()
        
    def enqueue_text(self, text: str):
        """Add text to the typing queue."""
        self.text_queue.append(text)
        if not self.isRunning():
            self.start()
    
    def enqueue_word(self, word: str):
        """Add word to high priority word queue for immediate typing."""
        self.word_queue.append(word)
        if not self.isRunning():
            self.start()
    
    def run(self):
        """Process text in the queue with priority for words."""
        while self.running:
            # Process words first (high priority)
            if self.word_queue:
                word = self.word_queue.popleft()
                self.typing_started.emit()
                self.status_changed.emit("Typing word")
                self.text_typer.type_text(word)
                self.typing_finished.emit()
            # Then process regular text
            elif self.text_queue:
                text = self.text_queue.popleft()
                self.typing_started.emit()
                self.status_changed.emit("Typing")
                self.text_typer.type_text(text)
                self.typing_finished.emit()
                self.status_changed.emit("Listening")
            else:
                self.msleep(50)  # Sleep to prevent busy waiting
    
    def stop(self):
        """Stop the typing thread."""
        self.running = False
        self.wait()

class SpeechThread(QThread):
    """Thread for handling speech processing and transcription."""
    
    transcription_ready = pyqtSignal(str)
    partial_transcription = pyqtSignal(str)  # New signal for streaming partial results
    word_transcribed = pyqtSignal(str)  # New signal for individual words
    status_changed = pyqtSignal(str)
    level_changed = pyqtSignal(int)
    model_loaded = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, model_type: str = "large-v3", parent=None):
        """Initialize speech thread."""
        super().__init__(parent)
        self.model_type = model_type
        self.speech_service = None
        self.is_listening = False
        self.level = 0
        self.model_is_loaded = False
        
        # Initialize audio service
        self.audio_service = AudioService()
        
        # Initialize VAD
        self.vad = VADManager(
            threshold=config.get("vad_threshold", 0.5),
            silence_threshold=config.get("vad_silence_threshold", 10),
            speech_threshold=config.get("vad_speech_threshold", 3),
            sampling_rate=config.get("vad_sampling_rate", 16000)
        )
        
        # Connect VAD signals
        self.vad.speech_started.connect(self.on_speech_started)
        self.vad.speech_ended.connect(self.on_speech_ended)
        
        # Initialize buffers with configurable sizes
        self.pre_buffer_duration = config.get("vad_pre_buffer", 1.0)  # Default 1.0s
        self.post_buffer_duration = config.get("vad_post_buffer", 0.2)  # Default 0.2s
        self.sample_rate = config.get("vad_sampling_rate", 16000)
        
        # Calculate buffer sizes in samples
        pre_buffer_size = int(self.pre_buffer_duration * self.sample_rate)
        post_buffer_size = int(self.post_buffer_duration * self.sample_rate)
        
        self.rolling_buffer = deque(maxlen=pre_buffer_size)
        self.active_buffer = []
        self.post_buffer = []
        
        # State tracking
        self.is_speech_active = False
        self.is_post_buffer_active = False
        self.running = True
        self.pending_auto_listen = False
        
        # Streaming mode tracking
        self.is_streaming_mode = False
        self.streaming_enabled = False
        
        # Load settings
        self.load_settings()
        
        logger.info(f"Initialized speech thread with pre-buffer: {self.pre_buffer_duration}s, "
                   f"post-buffer: {self.post_buffer_duration}s")
    
    def load_settings(self):
        """Load settings from config."""
        try:
            # Load VAD settings
            vad_threshold = config.get("vad_threshold", 0.5)
            vad_silence_threshold = config.get("vad_silence_threshold", 10)
            vad_speech_threshold = config.get("vad_speech_threshold", 3)
            vad_sampling_rate = config.get("vad_sampling_rate", 16000)
            
            # Load buffer settings
            self.pre_buffer_duration = config.get("vad_pre_buffer", 1.0)
            self.post_buffer_duration = config.get("vad_post_buffer", 0.2)
            
            # Update buffer sizes
            pre_buffer_size = int(self.pre_buffer_duration * self.sample_rate)
            self.rolling_buffer = deque(maxlen=pre_buffer_size)
            
            # Update VAD if it exists
            if hasattr(self, 'vad'):
                self.vad.set_threshold(vad_threshold)
                self.vad.set_silence_threshold(vad_silence_threshold)
                self.vad.set_speech_threshold(vad_speech_threshold)
                self.vad.set_pre_buffer(self.pre_buffer_duration)
                self.vad.set_post_buffer(self.post_buffer_duration)
            
            logger.info(f"Loaded VAD settings: threshold={vad_threshold}, "
                       f"silence_threshold={vad_silence_threshold}, "
                       f"speech_threshold={vad_speech_threshold}, "
                       f"pre_buffer={self.pre_buffer_duration}s, "
                       f"post_buffer={self.post_buffer_duration}s")
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    def run(self):
        """Run the speech processing thread."""
        try:
            # Determine which transcription engine to use
            transcription_engine = config.get("transcription_engine", "whisper")
            
            if transcription_engine == "parakeet":
                # Use Parakeet service
                parakeet_model = config.get("parakeet_model", "mlx-community/parakeet-rnnt-0.6b")
                logger.info(f"Loading Parakeet model {parakeet_model}")
                self.speech_service = ParakeetService(parakeet_model)
                self.streaming_enabled = True  # Enable streaming for Parakeet
            else:
                # Use Whisper service (default)
                logger.info(f"Loading Whisper model {self.model_type}")
                self.speech_service = WhisperService(self.model_type)
                self.streaming_enabled = False  # Whisper uses non-streaming mode
            
            if self.speech_service.ensure_model_loaded():
                logger.info(f"Model loaded successfully ({transcription_engine})")
                self.model_is_loaded = True
                self.model_loaded.emit()
                
                # Start listening if it was pending
                if self.pending_auto_listen:
                    self.start_listening()
                    self.pending_auto_listen = False
            
            # Start processing loop
            while self.running:
                if self.is_post_buffer_active:
                    self.process_post_buffer()
                self.msleep(10)  # Sleep to prevent busy waiting
                
        except Exception as e:
            logger.error(f"Error in speech thread: {e}")
            self.error_occurred.emit(str(e))
    
    def start_listening(self):
        """Start listening for audio input."""
        if not self.is_listening:
            try:
                # Check if model is loaded
                if not self.model_is_loaded:
                    logger.info("Deferring auto-listen until model is loaded")
                    self.pending_auto_listen = True
                    return
                
                # Start streaming mode if enabled
                if self.streaming_enabled and hasattr(self.speech_service, 'start_streaming'):
                    if self.speech_service.start_streaming():
                        self.is_streaming_mode = True
                        logger.info("Started streaming mode")
                    else:
                        logger.warning("Failed to start streaming mode, falling back to non-streaming")
                        self.is_streaming_mode = False
                
                self.audio_service.set_audio_callback(self.on_audio_data)
                self.audio_service.start_recording()
                self.is_listening = True
                self.status_changed.emit("Listening")
                logger.info("Started listening")
            except Exception as e:
                logger.error(f"Error starting listening: {e}")
                self.error_occurred.emit(str(e))
    
    def stop_listening(self):
        """Stop listening for audio input."""
        if self.is_listening:
            try:
                self.audio_service.stop_recording()
                self.is_listening = False
                
                # Stop streaming mode if active
                if self.is_streaming_mode and hasattr(self.speech_service, 'stop_streaming'):
                    self.speech_service.stop_streaming()
                    self.is_streaming_mode = False
                    logger.info("Stopped streaming mode")
                
                self.status_changed.emit("Not Listening")
                logger.info("Stopped listening")
                
                # Reset state
                self.is_speech_active = False
                self.is_post_buffer_active = False
                self.active_buffer = []
                self.post_buffer = []
                
            except Exception as e:
                logger.error(f"Error stopping listening: {e}")
                self.error_occurred.emit(str(e))
    
    def stop(self):
        """Stop the speech thread."""
        self.running = False
        if self.is_listening:
            self.stop_listening()
        if self.audio_service:
            self.audio_service.cleanup()
        self.wait()
    
    def on_audio_data(self, audio_data: np.ndarray):
        """Process incoming audio data."""
        if not self.is_listening:
            return
        
        try:
            # Log frame size at debug level
            logger.debug(f"Received audio frame with {len(audio_data)} samples")
            
            # Update level indicator
            rms = np.sqrt(np.mean(np.square(audio_data)))
            db = 20 * np.log10(max(rms, 1e-6))
            
            # Map dB to level
            if db < -50:
                new_level = 0
            elif db < -40:
                new_level = 1
            elif db < -30:
                new_level = 2
            elif db < -20:
                new_level = 3
            else:
                new_level = 4
            
            if not self.is_speech_active:
                new_level = min(1, new_level)
            
            if new_level != self.level:
                self.level = new_level
                self.level_changed.emit(self.level)
            
            # Process audio through VAD
            frame_data = self.vad.prepare_frame(audio_data)
            if len(frame_data) > 0:  # Only process if we have a complete frame
                self.vad.process_frame(frame_data)
                logger.debug("Processed complete VAD frame")
            
            # Skip streaming processing - we want to wait for complete speech
            # This allows VAD to work naturally without interference
            
            # Buffer management based on state
            if not self.is_speech_active and not self.is_post_buffer_active:
                # Keep filling rolling buffer for pre-speech context
                self.rolling_buffer.extend(audio_data)
            elif self.is_speech_active:
                # Collect active speech for final transcription (both streaming and non-streaming modes)
                self.active_buffer.extend(audio_data)
            elif self.is_post_buffer_active:
                # Collect post-speech context for final transcription (both streaming and non-streaming modes)
                self.post_buffer.extend(audio_data)
                if len(self.post_buffer) >= int(self.post_buffer_duration * self.sample_rate):
                    self.process_post_buffer()
            
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
    
    def on_speech_started(self):
        """Handle speech start event."""
        logger.debug("Speech segment started")
        if not self.is_speech_active:
            self.is_speech_active = True
            self.status_changed.emit("Speech detected")
            
            # Add pre-buffer to active buffer
            self.active_buffer.extend(list(self.rolling_buffer))
            logger.debug(f"Added {len(self.rolling_buffer)} samples from pre-buffer")
    
    def on_speech_ended(self):
        """Handle speech end event."""
        logger.debug("Speech segment ended")
        if self.is_speech_active:
            self.is_speech_active = False
            self.is_post_buffer_active = True
            self.status_changed.emit("Processing post-buffer")
            
            # Start post-buffer collection
            self.post_buffer = []
            # Post-buffer will be collected in on_audio_data
    
    def process_post_buffer(self):
        """Process the post buffer and transcribe the complete audio segment."""
        if len(self.post_buffer) >= int(self.post_buffer_duration * self.sample_rate):
            self.is_post_buffer_active = False
            
            # Combine all buffers
            complete_audio = np.concatenate([
                np.array(self.active_buffer, dtype=np.float32),
                np.array(self.post_buffer, dtype=np.float32)
            ])
            
            # Clear buffers
            self.active_buffer = []
            self.post_buffer = []
            
            try:
                # Transcribe the complete audio segment
                logger.debug(f"Transcribing audio segment of {len(complete_audio)} samples")
                text = self.speech_service.transcribe(complete_audio)
                if text:
                    # Log the exact text we got from the service
                    logger.info(f"Transcribed text (raw): {text}")
                    self.transcription_ready.emit(text)
                else:
                    logger.warning("Transcription returned empty text")
            except Exception as e:
                logger.error(f"Error transcribing audio: {e}")
                self.error_occurred.emit(str(e))
            
            self.status_changed.emit("Listening")

class SpeechManager(QObject):
    """Manages speech recognition and transcription."""
    
    transcription_ready = pyqtSignal(str)
    partial_transcription = pyqtSignal(str)  # New signal for partial results
    word_transcribed = pyqtSignal(str)  # New signal for individual words
    status_changed = pyqtSignal(str)
    level_changed = pyqtSignal(int)
    model_loaded = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, model_size="large-v3", parent: Optional[QObject] = None):
        """Initialize the speech manager.
        
        Args:
            model_size: Size of the whisper model to use
            parent: Parent QObject
        """
        super().__init__(parent)
        
        # Create speech and typing threads
        self.speech_thread = SpeechThread(model_size)
        self.typing_thread = TypingThread()
        
        # Initialize Ollama correction service
        self.correction_service = OllamaService()
        
        # Connect signals from speech thread
        self.speech_thread.transcription_ready.connect(self.on_transcription_ready)
        self.speech_thread.partial_transcription.connect(self.partial_transcription.emit)
        self.speech_thread.word_transcribed.connect(self.on_word_transcribed)
        self.speech_thread.status_changed.connect(self.status_changed.emit)
        self.speech_thread.level_changed.connect(self.level_changed.emit)
        self.speech_thread.model_loaded.connect(self.model_loaded.emit)
        self.speech_thread.error_occurred.connect(self.error_occurred.emit)
        
        # Connect signals from typing thread
        self.typing_thread.status_changed.connect(self.status_changed.emit)
        
        # Connect to config changes
        config.config_changed.connect(self.update_config)
        
        # Start the threads
        self.speech_thread.start()
        self.typing_thread.start()
        
        # Load settings
        self.update_config()
        
        logger.info(f"Speech manager initialized with model size: {model_size}")
    
    def on_transcription_ready(self, text: str):
        """Handle transcribed text by sending it to the typing thread."""
        # Log the exact text we're receiving
        logger.info(f"Received transcribed text (raw): {text}")
        
        # Check if AI correction is enabled
        if config.get("ollama_correction_enabled", True):
            try:
                # Try to correct the text with Ollama
                corrected_text = self.correction_service.correct_text(text)
                if corrected_text and corrected_text != text:
                    logger.info(f"Text corrected by MLX: '{text}' → '{corrected_text}'")
                    text = corrected_text
                else:
                    logger.debug("MLX correction returned same text or failed, using original")
            except Exception as e:
                logger.error(f"Error with MLX correction: {e}")
                # Continue with original text if MLX fails
        
        # Add a space after the sentence for proper separation
        if text and not text.endswith(' '):
            text += ' '
        
        # Log the final text we're sending to the typing thread
        logger.info(f"Sending text to typing thread (final): {text}")
        self.transcription_ready.emit(text)  # Emit for UI updates
        self.typing_thread.enqueue_text(text)  # Send to typing thread
    
    def on_word_transcribed(self, word: str):
        """Handle individual word transcription for streaming mode."""
        logger.info(f"Word transcribed: {word}")
        self.word_transcribed.emit(word)  # Emit for UI updates
        
        # Type the text as a batch using regular text queue (avoids clipboard race conditions)
        if word.strip():
            self.typing_thread.enqueue_text(word)
    
    @property
    def model_type(self) -> str:
        """Get the current model type."""
        return self.speech_thread.model_type
    
    def start_listening(self):
        """Start listening for speech."""
        self.speech_thread.start_listening()
    
    def stop_listening(self):
        """Stop listening for speech."""
        self.speech_thread.stop_listening()
    
    def update_config(self):
        """Update configuration settings."""
        try:
            # Load VAD settings
            vad_threshold = config.get("vad_threshold", 0.5)
            vad_silence_threshold = config.get("vad_silence_threshold", 10)
            vad_speech_threshold = config.get("vad_speech_threshold", 3)
            vad_sampling_rate = config.get("vad_sampling_rate", 16000)
            vad_pre_buffer = config.get("vad_pre_buffer", 1.0)
            vad_post_buffer = config.get("vad_post_buffer", 0.2)
            
            # Update VAD settings in speech thread
            if hasattr(self.speech_thread, 'vad'):
                self.speech_thread.vad.set_threshold(vad_threshold)
                self.speech_thread.vad.set_silence_threshold(vad_silence_threshold)
                self.speech_thread.vad.set_speech_threshold(vad_speech_threshold)
                self.speech_thread.vad.set_pre_buffer(vad_pre_buffer)
                self.speech_thread.vad.set_post_buffer(vad_post_buffer)
                
                # Update buffer sizes in speech thread
                self.speech_thread.pre_buffer_duration = vad_pre_buffer
                self.speech_thread.post_buffer_duration = vad_post_buffer
                pre_buffer_size = int(vad_pre_buffer * vad_sampling_rate)
                self.speech_thread.rolling_buffer = deque(maxlen=pre_buffer_size)
            
            logger.info(f"Updated VAD settings: threshold={vad_threshold}, "
                       f"silence_threshold={vad_silence_threshold}, "
                       f"speech_threshold={vad_speech_threshold}, "
                       f"pre_buffer={vad_pre_buffer}s, "
                       f"post_buffer={vad_post_buffer}s")
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            self.error_occurred.emit(str(e))
    
    def cleanup(self):
        """Clean up resources."""
        if self.speech_thread:
            self.speech_thread.stop()
            self.speech_thread.wait()
        if self.typing_thread:
            self.typing_thread.stop()
            self.typing_thread.wait()
        if hasattr(self, 'correction_service'):
            self.correction_service.cleanup()
        logger.info("Speech manager cleaned up") 
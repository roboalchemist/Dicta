"""Audio capture functionality."""
import logging
import pyaudio
import numpy as np
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class AudioCapture(QObject):
    """Handles audio capture from the microphone."""
    
    # Signals
    audio_data = pyqtSignal(bytes)  # Emits raw audio data
    error = pyqtSignal(str)         # Emits error messages
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize audio capture."""
        super().__init__(parent)
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        
        # Audio parameters
        self.format = pyaudio.paFloat32
        self.channels = 1
        self.rate = 16000
        self.chunk = 480  # 30ms at 16kHz
        
    def start(self):
        """Start audio capture."""
        if self.is_recording:
            return
            
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                stream_callback=self._audio_callback
            )
            self.stream.start_stream()
            self.is_recording = True
            logger.info("Started audio capture")
        except Exception as e:
            error_msg = f"Failed to start audio capture: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            
    def stop(self):
        """Stop audio capture."""
        if not self.is_recording:
            return
            
        try:
            self.stream.stop_stream()
            self.stream.close()
            self.is_recording = False
            logger.info("Stopped audio capture")
        except Exception as e:
            error_msg = f"Failed to stop audio capture: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Process audio data from the stream."""
        try:
            # Convert float32 audio data to bytes
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            audio_bytes = audio_data.tobytes()
            self.audio_data.emit(audio_bytes)
            return (in_data, pyaudio.paContinue)
        except Exception as e:
            error_msg = f"Error in audio callback: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            return (in_data, pyaudio.paAbort)
            
    def __del__(self):
        """Clean up resources."""
        if self.stream is not None:
            self.stop()
        if self.audio is not None:
            self.audio.terminate() 
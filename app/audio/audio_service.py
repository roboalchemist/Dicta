import pyaudio
import numpy as np
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        """Initialize audio service."""
        super().__init__()
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.audio_callback = None
        
        # Audio settings
        self.sample_rate = 16000
        self.channels = 1
        self.format = pyaudio.paFloat32
        # Set chunk size to match Silero VAD frame size (32ms at 16kHz = 512 samples)
        self.chunk_size = 512  # Required size for Silero VAD at 16kHz
        
        logger.debug(f"AudioService initialized with chunk size: {self.chunk_size} samples "
                    f"({self.chunk_size/self.sample_rate*1000:.1f}ms)")
    
    def set_audio_callback(self, callback):
        """Set the callback function for audio data."""
        self.audio_callback = callback
        logger.debug("Audio callback set")
    
    def start_recording(self):
        """Start recording audio."""
        if self.is_recording:
            logger.warning("Already recording")
            return
        
        try:
            def audio_callback(in_data, frame_count, time_info, status):
                """Handle incoming audio data."""
                try:
                    if self.audio_callback:
                        # Convert bytes to numpy array
                        audio_data = np.frombuffer(in_data, dtype=np.float32)
                        self.audio_callback(audio_data)
                    return (in_data, pyaudio.paContinue)
                except Exception as e:
                    logger.error(f"Error in audio callback: {e}")
                    return (in_data, pyaudio.paContinue)
            
            # Open audio stream
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=audio_callback
            )
            
            # Start the stream
            self.stream.start_stream()
            self.is_recording = True
            logger.info("Started recording")
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            raise
    
    def stop_recording(self):
        """Stop recording audio."""
        if not self.is_recording:
            logger.warning("Not recording")
            return
        
        try:
            # Stop and close the stream
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            self.is_recording = False
            logger.info("Stopped recording")
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.is_recording:
                self.stop_recording()
            
            if self.audio:
                self.audio.terminate()
                self.audio = None
            
            logger.info("AudioService cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up AudioService: {e}")
            raise

    def __del__(self):
        """Clean up resources."""
        self.cleanup() 
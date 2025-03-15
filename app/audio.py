import abc
import asyncio
import logging
import queue
import threading
import wave
from typing import AsyncIterator, Optional
import numpy as np
import pyaudio
import time
import os

logger = logging.getLogger(__name__)

class AudioCapture(abc.ABC):
    """Abstract base class for audio capture implementations."""
    
    @abc.abstractmethod
    async def start_recording(self) -> None:
        """Start recording audio."""
        pass
    
    @abc.abstractmethod
    async def stop_recording(self) -> None:
        """Stop recording audio."""
        pass
    
    @abc.abstractmethod
    async def get_audio_chunks(self) -> AsyncIterator[bytes]:
        """Get recorded audio chunks.
        
        Yields:
            Audio chunks as bytes in WAV format, suitable for speech-to-text processing.
        """
        pass

class PyAudioCapture(AudioCapture):
    """PyAudio implementation of audio capture."""
    
    # Audio recording parameters
    CHUNK_SIZE = 1024 * 2  # Number of frames per buffer
    FORMAT = pyaudio.paFloat32  # Audio format (32-bit float)
    CHANNELS = 1  # Mono audio
    RATE = 16000  # Sample rate (Hz) - Whisper models expect 16kHz
    
    def __init__(self):
        """Initialize PyAudio capture."""
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self._recording_thread: Optional[threading.Thread] = None
        
        # Find the default input device
        default_device = self.audio.get_default_input_device_info()
        self.device_index = default_device['index']
        logger.info(f"Using audio input device: {default_device['name']}")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for audio stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        # Convert audio data to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        
        # Add to queue if we're still recording
        if self.is_recording:
            self.audio_queue.put(audio_data)
        
        return (in_data, pyaudio.paContinue)
    
    def _record_thread(self):
        """Background thread for recording audio."""
        try:
            while self.is_recording:
                # Keep the stream running
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
            self.is_recording = False
    
    async def start_recording(self) -> None:
        """Start recording audio from the microphone."""
        if self.is_recording:
            logger.warning("Already recording")
            return
        
        try:
            # Open audio stream
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.CHUNK_SIZE,
                stream_callback=self._audio_callback
            )
            
            # Start the stream
            self.stream.start_stream()
            self.is_recording = True
            
            # Start background thread
            self._recording_thread = threading.Thread(target=self._record_thread)
            self._recording_thread.start()
            
            logger.info("Started audio recording")
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise
    
    async def stop_recording(self) -> None:
        """Stop recording audio."""
        if not self.is_recording:
            logger.warning("Not currently recording")
            return
        
        try:
            # Stop recording
            self.is_recording = False
            
            # Stop and close the stream
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # Wait for background thread to finish
            if self._recording_thread:
                self._recording_thread.join()
                self._recording_thread = None
            
            logger.info("Stopped audio recording")
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            raise
    
    def _convert_to_wav(self, audio_data: np.ndarray) -> bytes:
        """Convert numpy audio data to WAV format bytes."""
        with wave.open("temp.wav", "wb") as wav_file:
            wav_file.setnchannels(self.CHANNELS)
            wav_file.setsampwidth(4)  # 4 bytes for float32
            wav_file.setframerate(self.RATE)
            wav_file.writeframes(audio_data.tobytes())
        
        with open("temp.wav", "rb") as f:
            wav_bytes = f.read()
        
        return wav_bytes
    
    async def get_audio_chunks(self) -> AsyncIterator[bytes]:
        """Get recorded audio chunks in WAV format.
        
        Yields:
            Audio chunks as bytes in WAV format, suitable for speech-to-text processing.
        """
        while self.is_recording:
            try:
                # Get audio data from queue with timeout
                audio_data = await asyncio.get_event_loop().run_in_executor(
                    None, self.audio_queue.get, True, 0.1
                )
                
                # Convert to WAV format
                wav_bytes = await asyncio.get_event_loop().run_in_executor(
                    None, self._convert_to_wav, audio_data
                )
                
                yield wav_bytes
                
            except queue.Empty:
                # No audio data available, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error getting audio chunk: {e}")
                break
    
    def __del__(self):
        """Clean up PyAudio resources."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

class AudioCapture:
    """Class for capturing audio from the microphone."""
    
    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024):
        """Initialize audio capture with specified parameters."""
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = pyaudio.paFloat32
        
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self._audio_buffer = queue.Queue()
        self._record_thread = None
    
    def start_recording(self):
        """Start recording audio from the microphone."""
        if self.is_recording:
            logger.warning("Already recording")
            return
        
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.is_recording = True
            self._record_thread = threading.Thread(target=self._record_thread_func)
            self._record_thread.start()
            logger.info("Started recording")
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self.stop_recording()
    
    def stop_recording(self):
        """Stop recording audio."""
        self.is_recording = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        if self._record_thread:
            self._record_thread.join()
            self._record_thread = None
        
        logger.info("Stopped recording")
    
    def get_chunks(self):
        """Get all available audio chunks."""
        chunks = []
        while not self._audio_buffer.empty():
            chunks.append(self._audio_buffer.get())
        return chunks
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for audio stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        self._audio_buffer.put(in_data)
        return (None, pyaudio.paContinue)
    
    def _record_thread_func(self):
        """Background thread function for recording."""
        while self.is_recording:
            time.sleep(0.1)  # Prevent busy waiting
    
    def __del__(self):
        """Cleanup when the object is destroyed."""
        self.stop_recording()
        if self.audio:
            self.audio.terminate() 
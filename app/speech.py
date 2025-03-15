import abc
import logging
import os
from typing import Optional, AsyncIterator, List, Union
from groq import Groq
import tempfile
import numpy as np
from abc import ABC, abstractmethod
import wave
import speech_recognition as sr
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class SpeechToText(ABC):
    """Abstract base class for speech-to-text services."""
    
    def __init__(self):
        """Initialize the speech-to-text service."""
        self.client = None
        self.is_running = False
        
    @abstractmethod
    def transcribe_stream(self, audio_chunks: List[bytes]) -> str:
        """Transcribe streaming audio chunks."""
        pass
        
    @abstractmethod
    def stop(self) -> None:
        """Stop the transcription service."""
        pass
    
    def transcribe_audio(self, audio_data: Union[np.ndarray, bytes]) -> str:
        """Transcribe a complete audio sample."""
        # Convert audio data to the format expected by the API
        if isinstance(audio_data, np.ndarray):
            audio_data = audio_data.tobytes()
        return self._transcribe(audio_data)
    
    def _transcribe(self, audio_data: bytes) -> str:
        """Internal method to handle transcription."""
        raise NotImplementedError("Subclasses must implement _transcribe")

class GroqWhisperService(SpeechToText):
    """Implementation of speech-to-text using Groq's Whisper API."""
    
    MODELS = {
        "fast": "distil-whisper-large-v3-en",  # Fastest, English-only
        "balanced": "whisper-large-v3-turbo",  # Good balance of speed and features
        "accurate": "whisper-large-v3"  # Most accurate, full features
    }
    
    def __init__(self, api_key: Optional[str] = None, model: str = "balanced"):
        """Initialize the Groq Whisper service.
        
        Args:
            api_key: Groq API key. If not provided, will try to read from GROQ_API_KEY environment variable.
            model: Model to use, one of "fast", "balanced", or "accurate".
        """
        super().__init__()
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not found. Set GROQ_API_KEY environment variable.")
        
        if model not in self.MODELS:
            raise ValueError(f"Model must be one of {list(self.MODELS.keys())}")
        
        self.model = self.MODELS[model]
        self.client = Groq(api_key=self.api_key)
        self.is_running = True
        logger.info(f"Initialized Groq Whisper service with model {self.model}")
    
    def _save_audio_to_wav(self, audio_data: Union[bytes, np.ndarray], sample_rate: int = 16000) -> str:
        """Save audio data to a temporary WAV file.
        
        Args:
            audio_data: Raw audio data in bytes or numpy array
            sample_rate: Sample rate of the audio data
            
        Returns:
            Path to the temporary WAV file
        """
        if isinstance(audio_data, np.ndarray):
            # Convert float32 [-1.0, 1.0] to int16 [-32768, 32767]
            if audio_data.dtype == np.float32:
                audio_data = (audio_data * 32767).astype(np.int16)
            # Convert int16 to bytes
            audio_data = audio_data.tobytes()
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)
            return temp_file.name
        except Exception as e:
            try:
                os.unlink(temp_file.name)
            except:
                pass
            raise e
    
    def _transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio data using Groq's Whisper API.
        
        Args:
            audio_data: Raw audio data in bytes
            
        Returns:
            Transcribed text
        """
        try:
            # Save audio to temporary WAV file
            temp_path = self._save_audio_to_wav(audio_data)
            logger.debug(f"Saved audio to temporary file: {temp_path}")
            
            try:
                # Transcribe using Groq's API
                logger.debug(f"Starting transcription using model {self.model}")
                with open(temp_path, "rb") as audio_file:
                    logger.debug("Sending request to Groq API...")
                    response = self.client.audio.transcriptions.create(
                        file=(temp_path, audio_file.read()),  # Pass both filename and content
                        model=self.model,
                        response_format="text",
                        language="en",
                        temperature=0.0  # Use deterministic output
                    )
                    logger.debug(f"Received response from Groq API: {response}")
                    
                    if response:
                        text = str(response)  # Convert response to string
                        logger.debug(f"Transcribed text: {text}")
                        return text.strip()
                    logger.warning("Response from Groq API was empty")
                    return ""
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            return ""
    
    def transcribe_stream(self, audio_chunks: List[bytes]) -> str:
        """Transcribe streaming audio chunks using Groq's API.
        
        Args:
            audio_chunks: List of audio chunks in bytes
            
        Returns:
            Transcribed text
        """
        if not self.is_running:
            logger.warning("Transcription service is stopped")
            return ""
            
        try:
            # Combine chunks into a single audio sample
            audio_data = b''.join(audio_chunks)
            return self._transcribe(audio_data)
        except Exception as e:
            logger.error(f"Error during stream transcription: {e}")
            return ""
    
    def stop(self) -> None:
        """Stop the transcription service."""
        self.is_running = False
        logger.info("Stopped transcription service")

class GroqWhisperBackend(SpeechToText):
    """Groq Whisper API implementation of speech-to-text."""
    
    MODELS = {
        "fast": "groq-distil-whisper",  # Fastest, English-only
        "balanced": "whisper-large-v3-turbo",  # Good balance of speed and features
        "accurate": "whisper-large-v3"  # Most accurate, full features
    }
    
    def __init__(self, api_key: Optional[str] = None, model: str = "balanced"):
        """Initialize the Groq Whisper backend.
        
        Args:
            api_key: Groq API key. If not provided, will try to read from GROQ_API_KEY environment variable.
            model: Model to use, one of "fast" (English-only), "balanced", or "accurate".
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key must be provided either through constructor or GROQ_API_KEY environment variable")
        
        if model not in self.MODELS:
            raise ValueError(f"Model must be one of {list(self.MODELS.keys())}")
        
        self.model = self.MODELS[model]
        self.client = Groq(api_key=self.api_key)
        self._current_transcription = None
        logger.info(f"Initialized Groq Whisper backend with model {self.model}")

    async def transcribe_stream(self, audio_chunk: bytes) -> AsyncIterator[str]:
        """Transcribe an audio chunk using Groq's Whisper API.
        
        Args:
            audio_chunk: Raw audio data in bytes
            
        Yields:
            Text segments as they become available from the API
        """
        try:
            # Create a temporary file for the audio chunk
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
                temp_file.write(audio_chunk)
                temp_file.flush()
                
                # Start transcription
                logger.debug(f"Starting transcription of audio chunk using model {self.model}")
                with open(temp_file.name, "rb") as audio_file:
                    self._current_transcription = self.client.audio.transcriptions.create(
                        file=(temp_file.name, audio_file.read()),
                        model=self.model,
                        response_format="text",
                        language="en",
                        temperature=0.0  # Use deterministic output
                    )
                    
                    # Yield the transcribed text
                    # Note: The Groq API doesn't support true streaming yet,
                    # so we yield the entire text at once
                    if self._current_transcription:
                        yield self._current_transcription.text
                        
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            raise

    async def stop(self) -> None:
        """Stop the current transcription if any."""
        self._current_transcription = None
        logger.debug("Stopped transcription")

class SpeechManager(QObject):
    """Manages speech recognition and transcription."""
    
    # Signals
    transcription_ready = pyqtSignal(str)  # Emitted when transcription is ready
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.auto_listen = False
        
        # Calibrate microphone
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
    def start_listening(self):
        """Start listening for speech."""
        if not self.is_listening:
            self.is_listening = True
            self.listen()
            
    def stop_listening(self):
        """Stop listening for speech."""
        self.is_listening = False
        
    def toggle_auto_listen(self, enabled):
        """Toggle auto-listen mode."""
        self.auto_listen = enabled
        if enabled:
            self.start_listening()
        else:
            self.stop_listening()
            
    def listen(self):
        """Listen for speech and transcribe it."""
        if not self.is_listening:
            return
            
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source)
                
            try:
                text = self.recognizer.recognize_google(audio)
                self.transcription_ready.emit(text)
                
                if self.auto_listen:
                    self.listen()  # Continue listening if auto-listen is enabled
                    
            except sr.UnknownValueError:
                logger.warning("Speech was unintelligible")
                if self.auto_listen:
                    self.listen()
                    
            except sr.RequestError as e:
                logger.error(f"Could not request results from speech recognition service: {e}")
                if self.auto_listen:
                    self.listen()
                    
        except Exception as e:
            logger.error(f"Error during speech recognition: {e}")
            if self.auto_listen:
                self.listen() 
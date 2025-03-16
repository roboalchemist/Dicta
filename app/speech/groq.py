"""Groq Whisper implementation for speech-to-text."""
import logging
from typing import Union
import numpy as np
from groq import Groq
from .base import SpeechToText

logger = logging.getLogger(__name__)

class GroqWhisperService(SpeechToText):
    """Implementation of speech-to-text using Groq's Whisper API."""
    
    def __init__(self):
        """Initialize Groq Whisper service."""
        super().__init__()
        self.client = Groq()
        logger.info("Initialized Groq Whisper service")
    
    def transcribe_audio(self, audio_data: Union[np.ndarray, bytes]) -> str:
        """Transcribe audio using Groq's Whisper API."""
        try:
            # Convert audio data to bytes if needed
            if isinstance(audio_data, np.ndarray):
                audio_data = audio_data.tobytes()
            
            # Transcribe using Groq's API
            result = self.client.audio.transcriptions.create(
                file=("audio.wav", audio_data),
                model="whisper-1"
            )
            return result.text
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Groq: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the transcription service."""
        if hasattr(self, 'client'):
            self.client = None 
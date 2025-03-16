"""Base class for speech-to-text services."""
from abc import ABC, abstractmethod
from typing import Union
import numpy as np

class SpeechToText(ABC):
    """Abstract base class for speech-to-text services."""
    
    def __init__(self):
        """Initialize the speech-to-text service."""
        pass
    
    @abstractmethod
    def transcribe_audio(self, audio_data: Union[np.ndarray, bytes]) -> str:
        """Transcribe audio data to text.
        
        Args:
            audio_data: Audio data as either numpy array or bytes.
            
        Returns:
            Transcribed text.
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the transcription service and clean up resources."""
        pass 
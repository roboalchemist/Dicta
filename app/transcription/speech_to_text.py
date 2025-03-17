from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np

@dataclass
class TranscriptionResult:
    text: str
    language: str = "en"
    confidence: float = 1.0

class SpeechToText(ABC):
    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> TranscriptionResult:
        """Transcribe audio data to text.
        
        Args:
            audio: Audio data as a numpy array.
            
        Returns:
            A TranscriptionResult containing the transcribed text and metadata.
        """
        pass 
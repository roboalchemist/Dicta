"""Whisper.cpp implementation for speech-to-text."""
import logging
import platform
from typing import Union
import numpy as np
from pywhispercpp.model import Model
from .base import SpeechToText
from app.config import config

logger = logging.getLogger(__name__)

class WhisperCppService(SpeechToText):
    """Implementation of speech-to-text using Whisper.cpp."""
    
    def __init__(self):
        """Initialize Whisper.cpp service."""
        super().__init__()
        
        # Get model size from config
        model_size = config.get("whisper", "model_size")
        use_coreml = config.get("whisper", "use_coreml", True)  # Default to True on Apple Silicon
        
        try:
            # Base parameters
            params = {
                "n_threads": 6,  # Can be made configurable later
                "print_realtime": False,
                "print_progress": False,
                "print_special": False,
                "translate": False,
                "language": "en",
                "single_segment": True,  # Process each chunk independently
                "no_context": True,  # Don't use previous context
            }
            
            # Add Metal GPU params if on Apple Silicon
            if platform.system() == "Darwin" and platform.machine() == "arm64":
                params.update({
                    "backend": "metal" if use_coreml else "cpu",
                    "gpu_device": 0 if use_coreml else -1,
                })
                logger.info(f"Initializing WhisperCppService with model {model_size} (Metal GPU: {use_coreml})")
            else:
                logger.info(f"Initializing WhisperCppService with model {model_size}")
            
            # Initialize Whisper.cpp model
            self.model = Model(model_size, **params)
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def transcribe_audio(self, audio_data: Union[np.ndarray, bytes]) -> str:
        """Transcribe audio using Whisper.cpp."""
        try:
            # Convert audio data if needed
            if isinstance(audio_data, bytes):
                audio_data = np.frombuffer(audio_data, dtype=np.float32)
            
            # Transcribe using Whisper.cpp
            segments = self.model.transcribe(audio_data)
            # Join all segments into a single text
            return " ".join(segment.text for segment in segments)
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the transcription service."""
        if hasattr(self, 'model'):
            self.model = None 
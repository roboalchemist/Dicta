"""Parakeet service for transcription using MLX."""

from enum import Enum
from pathlib import Path
import numpy as np
import logging
import soundfile as sf
import tempfile
from typing import Optional, List
import os
import time

from .speech_to_text import SpeechToText, TranscriptionResult

logger = logging.getLogger(__name__)

class ParakeetModel(Enum):
    """Available Parakeet models."""
    
    # Real-time RNNT models
    RNNT_06B = ("mlx-community/parakeet-rnnt-0.6b", "Realtime-Small (parakeet-rnnt-0.6b)")
    RNNT_1B = ("mlx-community/parakeet-rnnt-1.1b", "Realtime-Large (parakeet-rnnt-1.1b)")

    def __init__(self, model_name: str, display_name: str):
        self.model_name = model_name
        self.display_name = display_name

class ParakeetService(SpeechToText):
    """Parakeet service for transcription using MLX."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, model_type: str = "mlx-community/parakeet-rnnt-0.6b"):
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super(ParakeetService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_type: str = "mlx-community/parakeet-rnnt-0.6b"):
        """Initialize parakeet service."""
        if not self._initialized:
            super().__init__()
            self._model = None
            self._model_type = None
            self._initialized = True
        
        # Always update model type if it changes
        if model_type != self._model_type:
            self._model_type = model_type
            self._model = None
            logger.info(f"Model type changed to {model_type}")
            # Don't initialize model here - do it lazily when needed
    
    def _initialize_model(self):
        """Initialize the Parakeet model."""
        try:
            logger.info(f"Loading Parakeet model: {self._model_type}")
            # Lazy import parakeet_mlx only when needed
            from parakeet_mlx import from_pretrained
            
            self._model = from_pretrained(self._model_type)
            self._is_initialized = True
            logger.info(f"Successfully loaded Parakeet model: {self._model_type}")
            
        except Exception as e:
            logger.error(f"Error initializing model {self._model_type}: {e}")
            self._model = None
            self._is_initialized = False
            raise
    
    @property
    def model_type(self) -> str:
        """Get the current model type."""
        return self._model_type
    
    def ensure_model_loaded(self) -> bool:
        """Ensure the model is loaded."""
        if self._model is None:
            self._initialize_model()
        return True
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        try:
            return [
                "mlx-community/parakeet-rnnt-0.6b",   # Real-time small
                "mlx-community/parakeet-rnnt-1.1b",   # Real-time large
            ]
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio data to text using Parakeet MLX."""
        try:
            total_start = time.perf_counter()
            logger.info("Starting Parakeet transcription process...")
            
            # Track actual transcription time
            transcription_time = 0.0
            overhead_time = 0.0
            
            # Ensure model is loaded
            load_start = time.perf_counter()
            self.ensure_model_loaded()
            load_time = time.perf_counter() - load_start
            overhead_time += load_time
            logger.info(f"Model load time: {load_time*1000:.2f}ms")
            
            # Convert audio data to float32 and normalize to [-1, 1]
            prep_start = time.perf_counter()
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.float64:
                audio_data = audio_data.astype(np.float32)
            
            # Ensure audio is in the correct range
            if np.abs(audio_data).max() > 1.0:
                audio_data = audio_data / np.abs(audio_data).max()
            
            prep_time = time.perf_counter() - prep_start
            overhead_time += prep_time
            logger.info(f"Audio preprocessing time: {prep_time*1000:.2f}ms")
            
            # Save audio data to a temporary file - Parakeet requires a file path
            save_start = time.perf_counter()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
                # Use 16kHz sample rate for optimal Parakeet performance
                sf.write(temp_file.name, audio_data, 16000, format='WAV')
                save_time = time.perf_counter() - save_start
                overhead_time += save_time
                logger.info(f"Audio save time: {save_time*1000:.2f}ms")
                
                # Transcribe audio with Parakeet
                parakeet_start = time.perf_counter()
                result = self._model.transcribe(temp_file.name)
                parakeet_time = time.perf_counter() - parakeet_start
                transcription_time = parakeet_time
                logger.info(f"Parakeet transcription time: {parakeet_time*1000:.2f}ms")
                
                # Parakeet returns an AlignedResult with text attribute
                text = result.text.strip()
                
                # Log additional timing info if available
                if hasattr(result, 'sentences') and result.sentences:
                    logger.info(f"Transcribed {len(result.sentences)} sentences")
                
            total_time = time.perf_counter() - total_start
            logger.info(f"Total transcription time: {total_time*1000:.2f}ms "
                       f"(transcription: {transcription_time*1000:.2f}ms, "
                       f"overhead: {overhead_time*1000:.2f}ms)")
            
            return text
            
        except Exception as e:
            logger.error(f"Error during Parakeet transcription: {e}")
            raise
    
    def get_model_info(self, model: ParakeetModel) -> dict:
        """Get information about a specific model."""
        return {
            "name": model.model_name,
            "display_name": model.display_name,
            "type": "parakeet"
        }
    
    def cleanup(self):
        """Clean up resources."""
        if self._model:
            del self._model
            self._model = None
        logger.info("Parakeet service cleaned up") 
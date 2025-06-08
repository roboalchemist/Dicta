from enum import Enum
from pathlib import Path
import numpy as np
import logging
import soundfile as sf
import tempfile
from typing import Optional, List
import os
from groq import Groq
import time

from .speech_to_text import SpeechToText, TranscriptionResult

logger = logging.getLogger(__name__)

class WhisperModel(Enum):
    # Tiny model (smallest)
    TINY = ("tiny", "Tiny")
    
    # Base model
    BASE = ("base", "Base")
    
    # Small models
    SMALL_EN = ("distil-small.en", "Small English")
    SMALL = ("small", "Small")
    
    # Medium models
    MEDIUM_EN = ("distil-medium.en", "Medium English")
    MEDIUM = ("medium", "Medium")
    
    # Large models (largest)
    LARGE_V3_EN = ("distil-large-v3", "Large v3 English")
    LARGE_V3 = ("large-v3", "Large v3")
    
    # GROQ models
    GROQ_WHISPER = ("whisper-1", "GROQ Whisper")
    
    def __init__(self, model_name: str, display_name: str):
        self.model_name = model_name
        self.display_name = display_name
    
    @property
    def quant(self) -> Optional[str]:
        if "q4" in self.display_name.lower():
            return "4bit"
        return None

class WhisperService(SpeechToText):
    """Whisper service for transcription using MLX."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, model_type: str = "large-v3"):
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super(WhisperService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_type: str = "large-v3"):
        """Initialize whisper service."""
        if not self._initialized:
            super().__init__()
            self._model = None
            self._model_type = None
            self._groq_client = None
            self._batch_size = 12  # Default batch size from yt2srt.py
            self._initialized = True
        
        # Always update model type if it changes
        if model_type != self._model_type:
            self._model_type = model_type
            self._model = None
            self._groq_client = None
            logger.info(f"Model type changed to {model_type}")
            # Don't initialize model here - do it lazily when needed
    
    def _initialize_model(self):
        """Initialize the appropriate model."""
        try:
            if self._model_type == "whisper-1":
                logger.info("Initializing GROQ Whisper client")
                self._groq_client = Groq()
            else:
                logger.info(f"Loading MLX Whisper model: {self._model_type}")
                # Lazy import lightning_whisper_mlx only when needed
                from lightning_whisper_mlx import LightningWhisperMLX
                # Increase batch size for better throughput on Apple Silicon
                self._model = LightningWhisperMLX(
                    model=self._model_type,
                    batch_size=24,  # Increased from 12 for better performance on M-series chips
                    quant=None      # No quantization for better accuracy
                )
            logger.info(f"Initialized WhisperService with model: {self._model_type}")
        except Exception as e:
            logger.error(f"Error initializing model {self._model_type}: {e}")
            raise
    
    @property
    def model_type(self) -> str:
        """Get the current model type."""
        return self._model_type
    
    def ensure_model_loaded(self) -> bool:
        """Ensure the model is loaded."""
        if self._model is None and not self._groq_client:
            self._initialize_model()
        return True
    
    def get_available_models(self) -> List[str]:
        """Get list of available models sorted by size from smallest to largest."""
        try:
            # Return our supported models in size order
            return [
                "tiny",           # Smallest
                "base",
                "distil-small.en",
                "small",
                "distil-medium.en",
                "medium",
                "distil-large-v3",
                "large-v3",       # Largest local model
                "whisper-1"       # GROQ API model
            ]
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio data to text using MLX."""
        try:
            total_start = time.perf_counter()
            logger.info("Starting transcription process...")
            
            # Track actual transcription time (GROQ API call or MLX inference)
            transcription_time = 0.0
            overhead_time = 0.0
            
            if self._groq_client:
                # Save audio data to temporary file for GROQ API
                save_start = time.perf_counter()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
                    sf.write(temp_file.name, audio_data, 16000)
                    save_time = time.perf_counter() - save_start
                    overhead_time += save_time
                    logger.info(f"Audio save time: {save_time*1000:.2f}ms")
                    
                    # Transcribe using GROQ API
                    api_start = time.perf_counter()
                    result = self._groq_client.audio.transcriptions.create(
                        file=("audio.wav", open(temp_file.name, "rb")),
                        model="whisper-1"
                    )
                    api_time = time.perf_counter() - api_start
                    transcription_time = api_time
                    text = result.text
                    logger.info(f"GROQ API transcription time: {api_time*1000:.2f}ms")
            else:
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
                
                # Save audio data to a temporary file - MLX requires a file path
                save_start = time.perf_counter()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
                    # Use soundfile's write function with memory buffer to avoid disk I/O
                    sf.write(temp_file.name, audio_data, 16000, format='WAV')
                    save_time = time.perf_counter() - save_start
                    overhead_time += save_time
                    logger.info(f"Audio save time: {save_time*1000:.2f}ms")
                    
                    # Transcribe audio with MLX
                    mlx_start = time.perf_counter()
                    result = self._model.transcribe(audio_path=temp_file.name)
                    mlx_time = time.perf_counter() - mlx_start
                    transcription_time = mlx_time
                    logger.info(f"MLX transcription time: {mlx_time*1000:.2f}ms")
                    
                    # MLX returns a dictionary with 'text' key
                    # Only strip whitespace from ends, preserve internal formatting
                    text = result["text"].strip()
                    
                    # Remove any leading/trailing periods that Whisper sometimes adds
                    text = text.strip('.')
                    
                    # Log the exact text for debugging
                    logger.info(f"MLX transcribed text (raw): {text}")
            
            total_time = time.perf_counter() - total_start
            
            # Log timing comparison
            logger.info("Transcription timing breakdown:")
            logger.info(f"  Pure transcription time: {transcription_time*1000:.2f}ms")
            logger.info(f"  Overhead time: {overhead_time*1000:.2f}ms")
            logger.info(f"  Total process time: {total_time*1000:.2f}ms")
            logger.info(f"  Transcription % of total: {(transcription_time/total_time)*100:.1f}%")
            
            return text
            
        except Exception as e:
            logger.error(f"Error transcribing audio with MLX: {e}")
            raise

    def get_model_info(self, model: WhisperModel) -> dict:
        """Get information about a specific model."""
        return {
            'name': model.display_name,
            'description': f"MLX Model {model.model_name}",
            'quant': model.quant
        }

    def cleanup(self):
        """Clean up resources."""
        if self._model:
            del self._model
            self._model = None
        if self._groq_client:
            self._groq_client = None
        logger.info("Cleaned up WhisperService resources")
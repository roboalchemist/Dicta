"""Parakeet service for transcription using MLX."""

from enum import Enum
from pathlib import Path
import numpy as np
import logging
import soundfile as sf
import tempfile
import traceback
from typing import Optional, List
import os
import time
import librosa

from .speech_to_text import SpeechToText, TranscriptionResult

logger = logging.getLogger(__name__)

# MLX compatibility patch for parakeet-mlx
def _patch_mlx_compatibility():
    """Patch MLX compatibility issues with parakeet-mlx."""
    try:
        import mlx.core as mx
        
        # Store original concat function
        _original_concat = mx.concat
        
        def patched_concat(*args, **kwargs):
            """Patched concat function that handles signature mismatches."""
            try:
                # The key insight: MLX expects axis as keyword-only argument
                # Signature: concat(arrays, axis=0, *, stream=None)
                
                if len(args) >= 1:
                    arrays = args[0]
                    
                    # Determine axis value
                    if len(args) >= 2:
                        # Called with positional axis: mx.concat([arrays], axis_value)
                        axis_value = args[1]
                    elif 'axis' in kwargs:
                        # Called with keyword axis: mx.concat([arrays], axis=axis_value)
                        axis_value = kwargs.pop('axis')  # Remove from kwargs to avoid duplicate
                    else:
                        # Default axis
                        axis_value = 0
                    
                    # Always call with axis as keyword argument
                    return _original_concat(arrays, axis=axis_value, **kwargs)
                
                # Fallback to original if no arrays provided
                return _original_concat(*args, **kwargs)
                
            except Exception as e:
                logger.debug(f"MLX concat patch failed: {e}")
                # Last resort - try the original call
                return _original_concat(*args, **kwargs)
        
        # Replace the concat function
        mx.concat = patched_concat
        logger.info("Applied MLX compatibility patch for concat function")
        
    except Exception as e:
        logger.warning(f"Failed to apply MLX compatibility patch: {e}")

# Apply the patch when the module is imported
_patch_mlx_compatibility()

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
    
    def __new__(cls, model_type: str = "mlx-community/parakeet-rnnt-1.1b"):
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super(ParakeetService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_type: str = "mlx-community/parakeet-rnnt-1.1b"):
        """Initialize parakeet service."""
        if not self._initialized:
            super().__init__()
            self._model = None
            self._model_type = None
            self._initialized = True
            self._streaming_transcriber = None
            self._last_finalized_text = ""
            self._word_count = 0
            # Intelligent buffering for high-accuracy "streaming" using regular API
            self._audio_buffer = []
            self._buffer_duration_ms = 1000  # 1 second buffer for high accuracy
            self._overlap_duration_ms = 200   # 200ms overlap to maintain context
            self._min_process_ms = 800        # Minimum 800ms before processing
            self._target_sample_rate = 16000  # Optimal sample rate for Parakeet
            self._last_processed_words = set()  # Track words to avoid duplicates
        
        # Always update model type if it changes
        if model_type != self._model_type:
            self._model_type = model_type
            self._model = None
            self._streaming_transcriber = None
            self._last_finalized_text = ""
            self._word_count = 0
            self._audio_buffer = []
            # Note: DON'T reset _last_processed_words to preserve deduplication state
            # across model changes. Only reset it on explicit start_streaming() calls.
            logger.info(f"Model type changed to {model_type}")
            # Don't initialize model here - do it lazily when needed
    
    @property
    def model_type(self) -> str:
        """Get the current model type."""
        return self._model_type
    
    def ensure_model_loaded(self) -> bool:
        """Ensure the model is loaded and ready."""
        if self._model is None:
            try:
                logger.info(f"Loading Parakeet model: {self._model_type}")
                
                # Use the correct API for parakeet-mlx
                import parakeet_mlx
                self._model = parakeet_mlx.from_pretrained(self._model_type)
                
                logger.info(f"Successfully loaded Parakeet model: {self._model_type}")
                return True
                
            except Exception as e:
                logger.error(f"Error loading Parakeet model: {e}")
                return False
        
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
        if self._streaming_transcriber:
            try:
                self._streaming_transcriber.__exit__(None, None, None)
            except:
                pass
            self._streaming_transcriber = None
        if self._model:
            del self._model
            self._model = None
        logger.info("Parakeet service cleaned up")
    
    def start_streaming(self) -> bool:
        """Start high-accuracy pseudo-streaming mode using regular transcription API."""
        try:
            # Ensure model is loaded
            self.ensure_model_loaded()
            
            # Reset state for new session
            self._audio_buffer = []
            self._last_processed_words = set()
            self._last_finalized_text = ""
            self._word_count = 0
            
            logger.info("Started high-accuracy pseudo-streaming using regular transcription API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start pseudo-streaming: {e}")
            return False
    
    def stop_streaming(self) -> bool:
        """Stop pseudo-streaming mode."""
        try:
            # Clear buffers
            self._audio_buffer = []
            self._last_processed_words = set()
            self._last_finalized_text = ""
            
            logger.info("Stopped pseudo-streaming mode")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping pseudo-streaming: {e}")
            return False
    
    def process_streaming_audio(self, audio_chunk: np.ndarray) -> dict:
        """Process audio using intelligent buffering with regular transcription API for high accuracy."""
        try:
            logger.debug(f"Processing audio chunk: shape={audio_chunk.shape}, dtype={audio_chunk.dtype}")
            
            # Ensure audio is in the right format (float32, normalized)
            if audio_chunk.dtype != np.float32:
                audio_chunk = audio_chunk.astype(np.float32)
                logger.debug("Converted audio to float32")
            
            # Normalize if needed
            if np.max(np.abs(audio_chunk)) > 1.0:
                audio_chunk = audio_chunk / np.max(np.abs(audio_chunk))
                logger.debug("Normalized audio amplitudes")
            
            # Add to buffer (accumulate small real-time chunks)
            self._audio_buffer.extend(audio_chunk.tolist())
            
            # Calculate buffer duration
            buffer_duration_ms = (len(self._audio_buffer) / self._target_sample_rate) * 1000
            logger.debug(f"Audio buffer: {len(self._audio_buffer)} samples ({buffer_duration_ms:.1f}ms)")
            
            # Only process when we have sufficient audio for high accuracy
            if buffer_duration_ms >= self._min_process_ms:
                # Use regular transcription API for high accuracy
                result_text = self._transcribe_buffer_with_regular_api()
                
                if result_text:
                    # Extract only NEW words to simulate streaming
                    new_words = self._extract_truly_new_words(result_text)
                    
                    if new_words:
                        logger.info(f"New words detected: {new_words}")
                        
                        # Update tracking
                        current_words = set(result_text.lower().split())
                        self._last_processed_words.update(current_words)
                        self._last_finalized_text = result_text
                        
                        # Keep overlap for context continuity
                        overlap_samples = int((self._overlap_duration_ms / 1000) * self._target_sample_rate)
                        if len(self._audio_buffer) > overlap_samples:
                            self._audio_buffer = self._audio_buffer[-overlap_samples:]
                        
                        return {
                            "partial_text": result_text,
                            "finalized_text": result_text,
                            "new_words": new_words
                        }
                    else:
                        # No new words, trim buffer more aggressively
                        trim_samples = int((self._min_process_ms / 2 / 1000) * self._target_sample_rate)
                        if len(self._audio_buffer) > trim_samples:
                            self._audio_buffer = self._audio_buffer[trim_samples:]
                
            # Not ready to process yet or no new words
            return {"partial_text": "", "finalized_text": "", "new_words": []}
            
        except Exception as e:
            logger.error(f"Error processing streaming audio: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"partial_text": "", "finalized_text": "", "new_words": []}
    
    def _transcribe_buffer_with_regular_api(self) -> str:
        """Transcribe current buffer using regular API for high accuracy."""
        try:
            # Save buffer to temporary file
            import tempfile
            import soundfile as sf
            
            buffer_audio = np.array(self._audio_buffer, dtype=np.float32)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                sf.write(temp_file.name, buffer_audio, self._target_sample_rate)
                
                # Use regular transcription API
                self.ensure_model_loaded()
                result = self._model.transcribe(temp_file.name)
                
                # Clean up
                import os
                os.unlink(temp_file.name)
                
                if hasattr(result, 'text'):
                    return result.text.strip()
                else:
                    return str(result).strip()
                    
        except Exception as e:
            logger.error(f"Error in regular API transcription: {e}")
            return ""
    
    def _extract_truly_new_words(self, current_text: str) -> list:
        """Extract words that are truly new compared to previous transcriptions."""
        if not current_text:
            return []
        
        current_words = set(word.lower() for word in current_text.split())
        new_words = current_words - self._last_processed_words
        
        # Return in order they appear in text
        ordered_new_words = []
        text_words = current_text.lower().split()
        for word in text_words:
            if word in new_words and word not in ordered_new_words:
                ordered_new_words.append(word)
        
        return ordered_new_words 
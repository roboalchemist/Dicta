"""Voice Activity Detection using Silero VAD."""
import logging
import torch
import numpy as np
import onnxruntime
from typing import Optional, Tuple
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
import urllib.request
import hashlib
import time
import requests
import os

logger = logging.getLogger(__name__)

# ONNX model URL and expected SHA256
ONNX_MODEL_URL = "https://huggingface.co/onnx-community/silero-vad/resolve/ddc9a7e80d6758f6fc795a1e8a04b798eb929d3a/onnx/model.onnx"
ONNX_MODEL_SHA256 = "a4a068cd6cf1ea8355b84327595838ca748ec29a25bc91fc82e6c299ccdc5808"

class VADManager(QObject):
    """Voice Activity Detection Manager using Silero VAD."""
    
    # Signals
    speech_started = pyqtSignal()  # Emitted when speech is detected
    speech_ended = pyqtSignal()    # Emitted when speech ends
    
    def __init__(self, 
                 threshold: float = 0.5,
                 silence_threshold: int = 10,
                 speech_threshold: int = 3,
                 sampling_rate: int = 16000,
                 pre_buffer: float = 1.0,
                 post_buffer: float = 0.2,
                 parent=None):
        """Initialize the VAD manager.
        
        Args:
            threshold: VAD threshold (0-1, higher is more aggressive)
            silence_threshold: Number of consecutive silence frames to trigger silence
            speech_threshold: Number of consecutive speech frames to trigger speech
            sampling_rate: Audio sampling rate (default: 16000)
            pre_buffer: Seconds of audio to keep before speech is detected (default: 1.0)
            post_buffer: Seconds of audio to keep after speech ends (default: 0.2)
        """
        super().__init__(parent)
        
        # Initialize parameters
        self.threshold = max(0.0, min(threshold, 1.0))  # Clamp between 0 and 1
        self.silence_threshold = max(1, silence_threshold)  # Ensure positive
        self.speech_threshold = max(1, speech_threshold)    # Ensure positive
        self.sampling_rate = sampling_rate
        
        # Initialize buffer durations
        self.pre_buffer_duration = max(0.0, min(pre_buffer, 2.0))  # Clamp between 0 and 2 seconds
        self.post_buffer_duration = max(0.0, min(post_buffer, 2.0))  # Clamp between 0 and 2 seconds
        self.pre_buffer_samples = int(self.pre_buffer_duration * sampling_rate)
        self.post_buffer_samples = int(self.post_buffer_duration * sampling_rate)
        
        # Audio parameters - Silero VAD requires 512 samples at 16kHz (32ms)
        self.frame_duration = 32  # ms
        self.samples_per_frame = 512 if sampling_rate == 16000 else 256
        
        # Timing tracking
        self.speech_start_time = None
        self.total_vad_time = 0
        self.frame_count = 0
        
        # Initialize state
        self.reset_state()
        
        # Initialize model path
        self.model_path = os.path.join(os.path.dirname(__file__), "silero_vad.onnx")
        
        try:
            # Download model if it doesn't exist or hash doesn't match
            if not os.path.exists(self.model_path):
                download_model(self.model_path)
            else:
                # Verify existing model hash
                with open(self.model_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    if file_hash != ONNX_MODEL_SHA256:
                        logger.info("Existing VAD model hash mismatch, downloading new model...")
                        download_model(self.model_path)
            
            # Initialize ONNX runtime session
            self.session = onnxruntime.InferenceSession(self.model_path)
            
            # Initialize VAD state (2 layers, batch size 1, hidden size 128)
            self.state = np.zeros((2, 1, 128), dtype=np.float32)
            
            logger.info("VAD model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VAD: {e}")
            raise
        
        logger.debug(f"Initialized VADManager with threshold={threshold}, "
                    f"silence_threshold={silence_threshold}, "
                    f"speech_threshold={speech_threshold}, "
                    f"sampling_rate={sampling_rate}, "
                    f"samples_per_frame={self.samples_per_frame}, "
                    f"pre_buffer={self.pre_buffer_duration}s, "
                    f"post_buffer={self.post_buffer_duration}s")
    
    def reset_state(self):
        """Reset the VAD state."""
        self.silence_counter = 0
        self.speech_counter = 0
        self.is_speaking = False
        self.frame_buffer = []
        if hasattr(self, 'state'):
            self.state = np.zeros((2, 1, 128), dtype=np.float32)
        logger.debug("Reset VAD state")
    
    def process_frame(self, frame: np.ndarray) -> bool:
        """Process a frame of audio data and detect speech.
        
        Args:
            frame: Audio frame data as numpy array
            
        Returns:
            bool: True if speech is detected, False otherwise
        """
        try:
            # Start timing
            start_time = time.time()
            
            # Add frame to buffer
            self.frame_buffer.extend(frame.tolist())
            
            # Process if we have enough samples
            if len(self.frame_buffer) >= self.samples_per_frame:
                # Extract frame and prepare for VAD
                frame_data = np.array(self.frame_buffer[:self.samples_per_frame], dtype=np.float32)
                self.frame_buffer = self.frame_buffer[self.samples_per_frame:]
                
                # Ensure frame is normalized between -1 and 1
                if np.abs(frame_data).max() > 1:
                    frame_data = frame_data / np.abs(frame_data).max()
                
                # Run VAD inference with all required inputs
                ort_inputs = {
                    'input': frame_data.reshape(1, -1),
                    'sr': np.array(self.sampling_rate, dtype=np.int64),
                    'state': self.state
                }
                
                # Run inference and get outputs
                outputs = self.session.run(None, ort_inputs)
                speech_prob = outputs[0][0][0]  # probability
                self.state = outputs[1]  # updated state
                
                # Track timing
                self.frame_count += 1
                process_time = time.time() - start_time
                self.total_vad_time += process_time
                
                # Log timing info every 100 frames
                if self.frame_count % 100 == 0:
                    avg_time = self.total_vad_time / self.frame_count
                    logger.info(f"VAD avg processing time: {avg_time*1000:.2f}ms per frame")
                
                # Update speech detection state
                is_speech = speech_prob >= self.threshold
                
                if is_speech:
                    self.speech_counter += 1
                    self.silence_counter = 0
                    
                    # Emit speech_started if we cross the threshold
                    if not self.is_speaking and self.speech_counter >= self.speech_threshold:
                        self.is_speaking = True
                        self.speech_start_time = time.time()
                        self.speech_started.emit()
                        logger.debug("Speech started")
                else:
                    self.silence_counter += 1
                    self.speech_counter = 0
                    
                    # Emit speech_ended if we cross the silence threshold
                    if self.is_speaking and self.silence_counter >= self.silence_threshold:
                        self.is_speaking = False
                        speech_duration = time.time() - self.speech_start_time
                        logger.info(f"Speech ended after {speech_duration:.2f}s")
                        self.speech_ended.emit()
                
                return self.is_speaking
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
            return False
    
    def prepare_frame(self, frame: np.ndarray) -> np.ndarray:
        """Prepare an audio frame for VAD processing.
        
        Args:
            frame: Input audio frame
            
        Returns:
            np.ndarray: Processed frame ready for VAD
        """
        try:
            # Convert to float32 if needed
            if frame.dtype != np.float32:
                frame = frame.astype(np.float32)
            
            # Ensure frame is normalized between -1 and 1
            if np.abs(frame).max() > 1:
                frame = frame / np.abs(frame).max()
            
            return frame
            
        except Exception as e:
            logger.error(f"Error preparing frame: {e}")
            return np.array([], dtype=np.float32)

    def get_stats(self) -> dict:
        """Get current VAD statistics.
        
        Returns:
            dict: Dictionary containing VAD statistics
        """
        stats = {
            'avg_process_time_ms': (self.total_vad_time / max(1, self.frame_count)) * 1000,
            'total_frames': self.frame_count,
            'is_speaking': self.is_speaking,
            'speech_counter': self.speech_counter,
            'silence_counter': self.silence_counter,
            'threshold': self.threshold,
            'speech_threshold': self.speech_threshold,
            'silence_threshold': self.silence_threshold,
            'sampling_rate': self.sampling_rate,
            'frame_duration_ms': self.frame_duration,
            'samples_per_frame': self.samples_per_frame,
            'pre_buffer_duration': self.pre_buffer_duration,
            'post_buffer_duration': self.post_buffer_duration
        }
        
        if self.speech_start_time and self.is_speaking:
            stats['current_speech_duration'] = time.time() - self.speech_start_time
        
        return stats

    def set_threshold(self, threshold: float):
        """Set VAD threshold (0-1)."""
        self.threshold = max(0.0, min(threshold, 1.0))  # Clamp between 0 and 1
        logger.debug(f"Set VAD threshold to {self.threshold}")

    def set_silence_threshold(self, threshold: int):
        """Set number of consecutive silence frames needed to trigger silence."""
        self.silence_threshold = max(1, threshold)  # Ensure positive
        logger.debug(f"Set silence threshold to {threshold}")

    def set_speech_threshold(self, threshold: int):
        """Set number of consecutive speech frames needed to trigger speech."""
        self.speech_threshold = max(1, threshold)  # Ensure positive
        logger.debug(f"Set speech threshold to {threshold}")

    def set_pre_buffer(self, duration: float):
        """Set the duration of audio to keep before speech is detected.
        
        Args:
            duration: Duration in seconds (0.0-2.0)
        """
        self.pre_buffer_duration = max(0.0, min(duration, 2.0))  # Clamp between 0 and 2 seconds
        self.pre_buffer_samples = int(self.pre_buffer_duration * self.sampling_rate)
        logger.debug(f"Set pre-buffer to {self.pre_buffer_duration}s ({self.pre_buffer_samples} samples)")

    def set_post_buffer(self, duration: float):
        """Set the duration of audio to keep after speech ends.
        
        Args:
            duration: Duration in seconds (0.0-2.0)
        """
        self.post_buffer_duration = max(0.0, min(duration, 2.0))  # Clamp between 0 and 2 seconds
        self.post_buffer_samples = int(self.post_buffer_duration * self.sampling_rate)
        logger.debug(f"Set post-buffer to {self.post_buffer_duration}s ({self.post_buffer_samples} samples)")

def download_model(model_path: str) -> None:
    """Download the VAD model from the official repository."""
    try:
        logger.info("Downloading VAD model...")
        with requests.get(ONNX_MODEL_URL, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(model_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        # Verify the downloaded file's hash
        with open(model_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            if file_hash != ONNX_MODEL_SHA256:
                os.remove(model_path)
                raise ValueError(f"Downloaded model hash {file_hash} does not match expected {ONNX_MODEL_SHA256}")
            
        logger.info("VAD model downloaded and verified successfully")
    except requests.Timeout:
        logger.error("Timeout while downloading VAD model")
        if os.path.exists(model_path):
            os.remove(model_path)
        raise
    except requests.RequestException as e:
        logger.error(f"Error downloading VAD model: {e}")
        if os.path.exists(model_path):
            os.remove(model_path)
        raise
    except Exception as e:
        logger.error(f"Unexpected error while downloading VAD model: {e}")
        if os.path.exists(model_path):
            os.remove(model_path)
        raise 
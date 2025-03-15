import webrtcvad
import numpy as np
import logging
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class VADManager(QObject):
    """Voice Activity Detection Manager using WebRTC VAD."""
    
    # Signals
    speech_started = pyqtSignal()  # Emitted when speech is detected
    speech_ended = pyqtSignal()    # Emitted when speech ends
    
    def __init__(self, aggressiveness=1, silence_threshold=10, speech_threshold=3):
        """
        Initialize the VAD manager.
        
        Args:
            aggressiveness (int): VAD aggressiveness (0-3, higher is more aggressive)
            silence_threshold (int): Number of consecutive silence frames to trigger silence
            speech_threshold (int): Number of consecutive speech frames to trigger speech
        """
        super().__init__()
        self.vad = webrtcvad.Vad(max(0, min(aggressiveness, 3)))  # Clamp between 0 and 3
        self.silence_threshold = max(1, silence_threshold)  # Ensure positive
        self.speech_threshold = max(1, speech_threshold)    # Ensure positive
        self.silence_counter = 0
        self.speech_counter = 0
        self.is_speaking = False
        self.sample_rate = 16000
        self.frame_duration = 30  # ms (10, 20, or 30)
        
        logger.debug(f"Initialized VADManager with aggressiveness={aggressiveness}, "
                    f"silence_threshold={silence_threshold}, speech_threshold={speech_threshold}")
    
    def set_aggressiveness(self, aggressiveness):
        """Set VAD aggressiveness level (0-3)."""
        aggressiveness = max(0, min(aggressiveness, 3))  # Clamp between 0 and 3
        self.vad.set_mode(aggressiveness)
        logger.debug(f"Set VAD aggressiveness to {aggressiveness}")
    
    def set_silence_threshold(self, threshold):
        """Set number of consecutive silence frames needed to trigger silence."""
        threshold = max(1, threshold)  # Ensure positive
        self.silence_threshold = threshold
        logger.debug(f"Set silence threshold to {threshold}")
    
    def set_speech_threshold(self, threshold):
        """Set number of consecutive speech frames needed to trigger speech."""
        threshold = max(1, threshold)  # Ensure positive
        self.speech_threshold = threshold
        logger.debug(f"Set speech threshold to {threshold}")
    
    def process_frame(self, frame_data, sample_rate=16000):
        """
        Process an audio frame and determine if it contains speech.
        
        Args:
            frame_data (bytes): Raw audio frame data (must be 10, 20, or 30ms of audio)
            sample_rate (int): Audio sample rate (must be 8000, 16000, 32000, or 48000 Hz)
            
        Returns:
            bool: True if speaking is detected, False otherwise
        """
        try:
            # Log frame data details
            frame_len = len(frame_data)
            expected_len = int(sample_rate * self.frame_duration / 1000) * 2  # 2 bytes per sample
            logger.debug(f"Processing frame - Length: {frame_len}, Expected: {expected_len} bytes")
            
            # Convert first few samples to int16 for debugging
            samples = np.frombuffer(frame_data[:10], dtype=np.int16)
            logger.debug(f"First few samples: {samples}")
            
            is_speech = self.vad.is_speech(frame_data, sample_rate)
            logger.debug(f"VAD raw result: {is_speech}")
        except Exception as e:
            logger.error(f"Error processing VAD frame: {e}", exc_info=True)
            return self.is_speaking
        
        was_speaking = self.is_speaking
        
        if is_speech:
            self.speech_counter += 1
            self.silence_counter = 0
            if self.speech_counter >= self.speech_threshold and not self.is_speaking:
                self.is_speaking = True
                self.speech_started.emit()
                logger.debug(f"Speech started (speech_counter: {self.speech_counter})")
        else:
            self.silence_counter += 1
            self.speech_counter = 0
            if self.silence_counter >= self.silence_threshold and self.is_speaking:
                self.is_speaking = False
                self.speech_ended.emit()
                logger.debug(f"Speech ended (silence_counter: {self.silence_counter})")
        
        logger.debug(f"Frame processed - Speech counter: {self.speech_counter}, "
                    f"Silence counter: {self.silence_counter}, "
                    f"Was speaking: {was_speaking}, Is speaking: {self.is_speaking}, "
                    f"Raw VAD result: {is_speech}")
        return self.is_speaking
    
    def reset(self):
        """Reset the VAD state."""
        self.silence_counter = 0
        self.speech_counter = 0
        self.is_speaking = False
        logger.debug("Reset VAD state") 
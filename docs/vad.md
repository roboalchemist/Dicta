# Implementing Voice Activity Detection (VAD) with WebRTC and PyQt

## Overview

This guide explains how to implement Voice Activity Detection (VAD) using Google's WebRTC VAD implementation with PyQt integration. This combination provides a robust, real-time speech detection system that can be used in any Python application requiring voice activity detection.

## Required Libraries

```bash
pip install webrtcvad    # Google's WebRTC VAD implementation
pip install PyQt6        # Qt framework for Python (or PyQt5)
pip install numpy        # For audio processing
pip install pydub        # For audio file handling (if needed)
```

## Core Implementation

### Basic VAD Manager

Here's a basic implementation that combines WebRTC VAD with PyQt signals:

```python
from PyQt6.QtCore import QObject, pyqtSignal
import webrtcvad
import logging

class VADManager(QObject):
    """Voice Activity Detection manager using WebRTC VAD."""
    
    # Signals for speech state changes
    speech_started = pyqtSignal()
    speech_ended = pyqtSignal()
    
    def __init__(self, 
                 aggressiveness=2, 
                 silence_threshold=10,
                 speech_threshold=3):
        """
        Initialize VAD manager.
        
        Args:
            aggressiveness (int): VAD aggressiveness (0-3)
            silence_threshold (int): Frames of silence before speech_ended
            speech_threshold (int): Frames of speech before speech_started
        """
        super().__init__()
        
        # Initialize WebRTC VAD
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(aggressiveness)
        
        # Configuration
        self.silence_threshold = silence_threshold
        self.speech_threshold = speech_threshold
        
        # State tracking
        self.is_speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
        
        logging.debug("VAD initialized with: "
                     f"aggressiveness={aggressiveness}, "
                     f"silence_threshold={silence_threshold}, "
                     f"speech_threshold={speech_threshold}")

    def process_frame(self, frame_data):
        """
        Process a single audio frame.
        
        Args:
            frame_data (bytes): Raw audio frame (16kHz, 16-bit mono PCM)
                              Must be exactly 480 samples (960 bytes)
        
        Returns:
            bool: True if currently in speaking state
        """
        try:
            # Validate frame size
            expected_size = 960  # 30ms at 16kHz, 16-bit
            if len(frame_data) != expected_size:
                logging.warning(f"Invalid frame size: {len(frame_data)} bytes "
                              f"(expected {expected_size})")
                return self.is_speaking

            # Get VAD decision for this frame
            is_speech = self.vad.is_speech(frame_data, 16000)
            
            # Update counters
            if is_speech:
                self.speech_frames += 1
                self.silence_frames = 0
            else:
                self.silence_frames += 1
                self.speech_frames = 0
            
            # State machine logic
            if not self.is_speaking and self.speech_frames >= self.speech_threshold:
                self.is_speaking = True
                self.speech_started.emit()
                logging.debug("Speech started")
                
            elif self.is_speaking and self.silence_frames >= self.silence_threshold:
                self.is_speaking = False
                self.speech_ended.emit()
                logging.debug("Speech ended")
            
            return self.is_speaking
            
        except Exception as e:
            logging.error(f"Error processing frame: {e}")
            return self.is_speaking
```

### Audio Requirements

WebRTC VAD has specific audio format requirements:

```python
SAMPLE_RATE = 16000      # Must be 16kHz
SAMPLE_WIDTH = 2         # 16-bit audio
CHANNELS = 1             # Mono only
FRAME_DURATION = 30      # 30ms frames (can also use 10ms or 20ms)
SAMPLES_PER_FRAME = int(SAMPLE_RATE * FRAME_DURATION / 1000)  # 480 samples
FRAME_SIZE = SAMPLES_PER_FRAME * SAMPLE_WIDTH  # 960 bytes
```

### Audio Frame Preparation

Here's a utility function to prepare audio frames for VAD:

```python
import numpy as np

def prepare_audio_frame(audio_data, sample_rate=16000):
    """
    Prepare audio data for VAD processing.
    
    Args:
        audio_data (numpy.ndarray): Audio data
        sample_rate (int): Sample rate of the audio
    
    Returns:
        bytes: Processed frame ready for VAD
    """
    # Resample if needed
    if sample_rate != 16000:
        # Use your preferred resampling method
        # Example: librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
        pass
    
    # Convert to 16-bit PCM
    audio_16bit = (audio_data * 32767).astype(np.int16)
    
    # Convert to bytes
    frame_bytes = audio_16bit.tobytes()
    
    # Ensure exact frame size (pad or truncate)
    if len(frame_bytes) < FRAME_SIZE:
        frame_bytes = frame_bytes.ljust(FRAME_SIZE, b'\0')
    elif len(frame_bytes) > FRAME_SIZE:
        frame_bytes = frame_bytes[:FRAME_SIZE]
    
    return frame_bytes
```

## Integration Examples

### 1. Basic Audio Processing Loop

```python
from PyQt6.QtCore import QThread, pyqtSignal

class AudioProcessor(QThread):
    """Example audio processing thread."""
    
    def __init__(self, vad_manager):
        super().__init__()
        self.vad_manager = vad_manager
        self.running = False
        
    def run(self):
        self.running = True
        while self.running:
            # Get your audio data here (e.g., from microphone)
            audio_frame = get_audio_frame()  # Implementation depends on your audio source
            
            # Prepare frame for VAD
            frame_data = prepare_audio_frame(audio_frame)
            
            # Process with VAD
            is_speaking = self.vad_manager.process_frame(frame_data)
            
            # Do something with the result
            if is_speaking:
                # Handle active speech
                pass
```

### 2. Qt Application Integration

```python
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

class VoiceApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        
        # Create VAD manager
        self.vad_manager = VADManager(
            aggressiveness=2,
            silence_threshold=10,
            speech_threshold=3
        )
        
        # Connect signals
        self.vad_manager.speech_started.connect(self.on_speech_started)
        self.vad_manager.speech_ended.connect(self.on_speech_ended)
        
        # Start audio processing
        self.audio_processor = AudioProcessor(self.vad_manager)
        self.audio_processor.start()
    
    def on_speech_started(self):
        # Handle speech start
        pass
    
    def on_speech_ended(self):
        # Handle speech end
        pass
```

## Testing

### Test Fixtures

```python
import pytest
import numpy as np

@pytest.fixture
def vad_manager():
    return VADManager(
        aggressiveness=2,
        silence_threshold=5,
        speech_threshold=2
    )

@pytest.fixture
def silence_frame():
    """Generate 30ms of silence."""
    samples = np.zeros(480, dtype=np.int16)
    return samples.tobytes()

@pytest.fixture
def voice_frame():
    """Generate 30ms of simulated voice."""
    t = np.linspace(0, 0.03, 480)
    # Create a mix of frequencies typical in speech
    signal = (np.sin(2 * np.pi * 200 * t) +  # Fundamental
             0.5 * np.sin(2 * np.pi * 400 * t) +  # First harmonic
             0.25 * np.sin(2 * np.pi * 600 * t))  # Second harmonic
    # Normalize and convert to 16-bit
    signal = (signal * 32767).astype(np.int16)
    return signal.tobytes()
```

### Test Cases

```python
def test_vad_silence(vad_manager, silence_frame):
    """Test silence detection."""
    for _ in range(10):
        is_speaking = vad_manager.process_frame(silence_frame)
    assert not is_speaking

def test_vad_voice(vad_manager, voice_frame):
    """Test voice detection."""
    for _ in range(5):
        is_speaking = vad_manager.process_frame(voice_frame)
    assert is_speaking

def test_speech_transition(vad_manager, voice_frame, silence_frame):
    """Test transition from speech to silence."""
    # Trigger speech detection
    for _ in range(5):
        vad_manager.process_frame(voice_frame)
    
    # Transition to silence
    for _ in range(15):
        vad_manager.process_frame(silence_frame)
    
    assert not vad_manager.is_speaking
```

## Best Practices

1. **Frame Processing**
   - Always validate frame sizes
   - Handle audio format conversion properly
   - Use consistent frame durations

2. **Threading**
   - Process audio in a separate thread
   - Use Qt's signal/slot mechanism for thread-safe communication
   - Handle thread cleanup properly

3. **Error Handling**
   - Validate audio input
   - Handle exceptions in frame processing
   - Log VAD decisions for debugging

4. **Performance**
   - Process frames in real-time
   - Minimize buffer copies
   - Use appropriate frame sizes for your use case

## Troubleshooting

1. **No Speech Detection**
   ```python
   # Check frame format
   logging.debug(f"Frame size: {len(frame_data)} bytes")
   logging.debug(f"First few samples: {np.frombuffer(frame_data[:10], dtype=np.int16)}")
   ```

2. **False Positives**
   ```python
   # Increase aggressiveness and thresholds
   vad_manager = VADManager(
       aggressiveness=3,
       speech_threshold=5,  # Require more speech frames
       silence_threshold=8   # More silence before ending
   )
   ```

3. **Delayed Response**
   ```python
   # Reduce thresholds for faster response
   vad_manager = VADManager(
       silence_threshold=5,  # Faster silence detection
       speech_threshold=2    # Faster speech detection
   )
   ```

## References

- [WebRTC VAD Documentation](https://github.com/wiseman/py-webrtcvad)
- [PyQt Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Audio Processing with NumPy](https://numpy.org/doc/stable/reference/routines.audio.html) 
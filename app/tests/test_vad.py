import pytest
import numpy as np
import wave
import logging
from pydub import AudioSegment
from app.audio.vad import VADManager
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def vad_manager():
    """Create a VAD manager instance."""
    # Use highest aggressiveness and lower thresholds for testing
    manager = VADManager(aggressiveness=3, silence_threshold=3, speech_threshold=2)
    logger.debug("Created VAD manager with high aggressiveness and lower thresholds")
    return manager

@pytest.fixture
def silence_frame():
    """Generate a frame of silence."""
    # Create exactly 30ms of silence at 16kHz (480 samples = 960 bytes)
    samples_per_frame = int(16000 * 0.03)  # 480 samples for 30ms at 16kHz
    bytes_per_frame = samples_per_frame * 2  # 960 bytes (2 bytes per sample)
    samples = np.zeros(samples_per_frame, dtype=np.int16)
    frame_bytes = samples.tobytes()
    logger.debug(f"Silence frame size: {len(samples)} samples ({len(frame_bytes)} bytes)")
    assert len(frame_bytes) == bytes_per_frame, \
        f"Silence frame size mismatch: {len(frame_bytes)} != {bytes_per_frame} bytes"
    return frame_bytes

@pytest.fixture
def voice_frames():
    """Get a sequence of voice frames from test audio file."""
    # Load the test audio file
    test_file = os.path.join('app', 'tests', 'test-data', 'test_speaking_audio.mp3')
    audio = AudioSegment.from_mp3(test_file)
    
    # Convert to mono and set sample rate to 16kHz
    audio = audio.set_channels(1).set_frame_rate(16000)
    
    # Calculate exact frame size required by WebRTC VAD
    frame_duration = 30  # ms
    samples_per_frame = int(16000 * frame_duration / 1000)  # 480 samples for 30ms at 16kHz
    bytes_per_frame = samples_per_frame * 2  # 960 bytes (2 bytes per sample for 16-bit audio)
    logger.debug(f"Required frame size: {samples_per_frame} samples ({bytes_per_frame} bytes)")
    
    # Find a segment with actual voice (skip any initial silence)
    check_duration = 500  # ms
    check_segment = audio[:check_duration]
    rms = check_segment.rms
    logger.debug(f"Audio RMS level: {rms}")
    
    frames = []
    # Find frames with significant audio
    for i in range(0, check_duration - frame_duration, frame_duration):
        frame = audio[i:i + frame_duration]
        # Convert to raw PCM bytes
        samples = np.array(frame.get_array_of_samples(), dtype=np.int16)
        
        # Ensure exact frame size
        if len(samples) < samples_per_frame:
            samples = np.pad(samples, (0, samples_per_frame - len(samples)))
        elif len(samples) > samples_per_frame:
            samples = samples[:samples_per_frame]
        
        frame_bytes = samples.tobytes()
        assert len(frame_bytes) == bytes_per_frame, \
            f"Frame size mismatch: {len(frame_bytes)} != {bytes_per_frame} bytes"
        
        # Only collect frames that have significant audio
        if frame.rms > rms * 0.5:
            frames.append(frame_bytes)
            if len(frames) >= 10:  # Get 10 frames of voice
                break
    
    if not frames:
        raise ValueError("Could not find enough voice frames with sufficient audio level")
    
    logger.debug(f"Collected {len(frames)} voice frames")
    return frames

@pytest.fixture
def silence_frames():
    """Generate a sequence of silence frames."""
    # Create exactly 30ms of silence at 16kHz (480 samples = 960 bytes)
    samples_per_frame = int(16000 * 0.03)  # 480 samples for 30ms at 16kHz
    bytes_per_frame = samples_per_frame * 2  # 960 bytes (2 bytes per sample)
    samples = np.zeros(samples_per_frame, dtype=np.int16)
    frame_bytes = samples.tobytes()
    logger.debug(f"Created silence frame: {samples_per_frame} samples ({bytes_per_frame} bytes)")
    assert len(frame_bytes) == bytes_per_frame, \
        f"Silence frame size mismatch: {len(frame_bytes)} != {bytes_per_frame} bytes"
    return [frame_bytes] * 10  # Return 10 frames of silence

def test_vad_initialization(vad_manager):
    """Test that the VAD manager initializes with default settings."""
    assert vad_manager.sample_rate == 16000
    assert vad_manager.frame_duration == 30
    assert vad_manager.silence_threshold == 3
    assert vad_manager.speech_threshold == 2
    assert not vad_manager.is_speaking

def test_vad_with_silence(vad_manager, silence_frame, qtbot):
    """Test VAD behavior with silence."""
    # Process several frames of silence
    for _ in range(5):
        result = vad_manager.process_frame(silence_frame)
        assert not result  # Should not detect speech
    assert not vad_manager.is_speaking

def test_vad_with_voice(vad_manager, voice_frames, qtbot):
    """Test VAD behavior with voice sample."""
    # Process enough frames to trigger speech detection
    with qtbot.waitSignal(vad_manager.speech_started, timeout=1000):
        for _ in range(vad_manager.speech_threshold + 1):
            vad_manager.process_frame(voice_frames[0])
            logger.debug(f"Processed voice frame, is_speaking: {vad_manager.is_speaking}")
    assert vad_manager.is_speaking

def test_transition_to_silence(vad_manager, voice_frames, silence_frames, qtbot):
    """Test transition from speech to silence."""
    # First get to speech state
    with qtbot.waitSignal(vad_manager.speech_started, timeout=1000):
        for i, frame in enumerate(voice_frames):
            result = vad_manager.process_frame(frame)
            logger.debug(f"Voice frame {i} processed - is_speech: {result}")
    
    logger.debug("Speech detected, now transitioning to silence...")
    
    # Then transition to silence
    with qtbot.waitSignal(vad_manager.speech_ended, timeout=1000):
        for i, frame in enumerate(silence_frames):
            result = vad_manager.process_frame(frame)
            logger.debug(f"Silence frame {i} processed - is_speech: {result}")
    
    assert not vad_manager.is_speaking

def test_alternating_voice_silence(vad_manager, voice_frames, silence_frames, qtbot):
    """Test alternating between voice and silence."""
    signals_received = []
    
    # Connect signals
    vad_manager.speech_started.connect(lambda: signals_received.append("started"))
    vad_manager.speech_ended.connect(lambda: signals_received.append("ended"))
    
    # Process sequence: silence -> speech -> silence
    # Initial silence
    for i, frame in enumerate(silence_frames[:3]):
        result = vad_manager.process_frame(frame)
        logger.debug(f"Initial silence frame {i} processed - is_speech: {result}")
    
    # Speech
    for i, frame in enumerate(voice_frames):
        result = vad_manager.process_frame(frame)
        logger.debug(f"Voice frame {i} processed - is_speech: {result}")
    
    # Back to silence
    for i, frame in enumerate(silence_frames):
        result = vad_manager.process_frame(frame)
        logger.debug(f"Final silence frame {i} processed - is_speech: {result}")
    
    # Wait for signals to be processed
    qtbot.wait(100)  # Reduced wait time since we're more aggressive now
    logger.debug(f"Signals received: {signals_received}")
    assert signals_received == ["started", "ended"]

def test_aggressiveness_setting(vad_manager):
    """Test setting VAD aggressiveness levels."""
    # Test valid levels
    for level in range(4):
        vad_manager.set_aggressiveness(level)
    
    # Test invalid levels (should be clamped)
    vad_manager.set_aggressiveness(-1)  # Should clamp to 0
    # We can't test the actual mode since webrtcvad doesn't expose it
    # Just verify that setting invalid values doesn't raise exceptions
    vad_manager.set_aggressiveness(4)  # Should clamp to 3

def test_threshold_settings(vad_manager):
    """Test setting silence and speech thresholds."""
    vad_manager.set_silence_threshold(15)
    assert vad_manager.silence_threshold == 15
    
    vad_manager.set_speech_threshold(5)
    assert vad_manager.speech_threshold == 5
    
    # Test minimum values (should be clamped to 1)
    vad_manager.set_silence_threshold(0)
    assert vad_manager.silence_threshold == 1
    
    vad_manager.set_speech_threshold(-1)
    assert vad_manager.speech_threshold == 1 
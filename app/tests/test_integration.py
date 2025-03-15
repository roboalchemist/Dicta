import os
import pytest
import wave
import pyaudio
import logging
import numpy as np
from pydub import AudioSegment
from app.speech import GroqWhisperService
from app.audio import AudioCapture

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

TEST_AUDIO_PATH = os.path.join('app', 'tests', 'test-data', 'test_speaking_audio.mp3')

@pytest.fixture
def speech_to_text():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY environment variable not set")
    return GroqWhisperService(api_key=api_key, model="fast")

@pytest.fixture
def audio_capture():
    return AudioCapture()

def test_direct_api_transcription(speech_to_text):
    """Test direct transcription of the audio file using the API."""
    # Load the audio file
    audio = AudioSegment.from_mp3(TEST_AUDIO_PATH)
    
    # Convert to wav format in memory (Whisper expects PCM WAV)
    audio = audio.set_frame_rate(16000).set_channels(1)
    
    # Get raw audio data
    samples = np.array(audio.get_array_of_samples())
    
    # Transcribe
    result = speech_to_text.transcribe_audio(samples)
    
    # Check if we got a non-empty result
    assert result.strip() != ""
    print(f"Transcription result: {result}")

@pytest.mark.asyncio
async def test_streaming_transcription(speech_to_text, audio_capture):
    """Test transcription by streaming audio through PyAudio as if it were live."""
    # Load the audio file
    audio = AudioSegment.from_mp3(TEST_AUDIO_PATH)
    audio = audio.set_frame_rate(16000).set_channels(1)
    
    # Convert to numpy array
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0  # Normalize to [-1.0, 1.0]
    
    # Start recording (this initializes PyAudio stream)
    audio_capture.start_recording()
    
    # Simulate streaming chunks of audio
    chunk_size = 1024
    for i in range(0, len(samples), chunk_size):
        chunk = samples[i:i + chunk_size]
        if len(chunk) < chunk_size:
            # Pad the last chunk if needed
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
        audio_capture._audio_buffer.put(chunk.tobytes())
    
    # Get the processed chunks
    chunks = audio_capture.get_chunks()
    
    # Stop recording
    audio_capture.stop_recording()
    
    # Transcribe the chunks
    result = speech_to_text.transcribe_stream(chunks)
    
    # Check if we got a non-empty result
    assert result.strip() != ""
    print(f"Streaming transcription result: {result}") 
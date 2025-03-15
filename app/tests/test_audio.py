import pytest
from unittest.mock import MagicMock, patch
import numpy as np
import pyaudio
import wave
from app.audio import PyAudioCapture

@pytest.fixture
def mock_pyaudio():
    with patch('pyaudio.PyAudio') as mock:
        # Mock device info
        device_info = {
            'index': 0,
            'name': 'Test Microphone',
            'maxInputChannels': 1
        }
        mock.return_value.get_default_input_device_info.return_value = device_info
        
        # Mock audio stream
        mock_stream = MagicMock()
        mock.return_value.open.return_value = mock_stream
        
        yield mock

@pytest.fixture
def audio_capture(mock_pyaudio):
    capture = PyAudioCapture()
    yield capture
    # Cleanup
    if capture.stream:
        capture.stream.stop_stream()
        capture.stream.close()
    if capture.audio:
        capture.audio.terminate()

@pytest.mark.asyncio
async def test_audio_capture_initialization(audio_capture, mock_pyaudio):
    """Test that PyAudioCapture initializes correctly."""
    # Verify PyAudio was initialized
    mock_pyaudio.assert_called_once()
    
    # Verify default device was queried
    mock_pyaudio.return_value.get_default_input_device_info.assert_called_once()
    
    # Verify initial state
    assert audio_capture.stream is None
    assert not audio_capture.is_recording
    assert audio_capture._recording_thread is None

@pytest.mark.asyncio
async def test_audio_capture_start_recording(audio_capture, mock_pyaudio):
    """Test starting audio recording."""
    await audio_capture.start_recording()
    
    # Verify stream was opened with correct parameters
    mock_pyaudio.return_value.open.assert_called_once_with(
        format=pyaudio.paFloat32,
        channels=1,
        rate=16000,
        input=True,
        input_device_index=0,
        frames_per_buffer=2048,
        stream_callback=audio_capture._audio_callback
    )
    
    # Verify stream was started
    assert audio_capture.stream.start_stream.called
    assert audio_capture.is_recording
    assert audio_capture._recording_thread is not None
    
    # Cleanup
    await audio_capture.stop_recording()

@pytest.mark.asyncio
async def test_audio_capture_stop_recording(audio_capture):
    """Test stopping audio recording."""
    # Start recording first
    await audio_capture.start_recording()
    
    # Stop recording
    await audio_capture.stop_recording()
    
    # Verify everything was cleaned up
    assert not audio_capture.is_recording
    assert audio_capture.stream is None
    assert audio_capture._recording_thread is None

@pytest.mark.asyncio
async def test_audio_capture_get_chunks(audio_capture):
    """Test getting audio chunks."""
    # Start recording
    await audio_capture.start_recording()
    
    # Create some test audio data
    test_data = np.zeros(2048, dtype=np.float32)
    audio_capture.audio_queue.put(test_data)
    
    # Get one chunk
    chunks = []
    async for chunk in audio_capture.get_audio_chunks():
        chunks.append(chunk)
        break  # Only get one chunk
    
    # Verify we got a WAV file
    assert len(chunks) == 1
    chunk = chunks[0]
    
    # Verify it's a valid WAV file
    with wave.open("test_output.wav", "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(4)  # 4 bytes for float32
        wav_file.setframerate(16000)
        wav_file.writeframes(chunk)
    
    # Stop recording
    await audio_capture.stop_recording()

@pytest.mark.asyncio
async def test_audio_capture_error_handling(audio_capture, mock_pyaudio):
    """Test error handling during recording."""
    # Make the stream raise an error
    mock_pyaudio.return_value.open.side_effect = Exception("Test error")
    
    # Verify the error is propagated
    with pytest.raises(Exception) as exc_info:
        await audio_capture.start_recording()
    assert "Test error" in str(exc_info.value) 
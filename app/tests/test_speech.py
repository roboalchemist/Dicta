import os
import pytest
from unittest.mock import MagicMock, patch
import httpx
from groq import AuthenticationError
from app.speech import GroqWhisperBackend

@pytest.fixture
def mock_groq_client():
    with patch('app.speech.Groq') as mock_groq:
        mock_client = MagicMock()
        mock_groq.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_transcription_response():
    class MockResponse:
        def __init__(self, text):
            self.text = text
    return MockResponse("Hello, this is a test transcription.")

@pytest.mark.asyncio
async def test_groq_whisper_initialization():
    """Test that the Groq Whisper backend initializes correctly."""
    # Test with API key in constructor
    backend = GroqWhisperBackend(api_key="test_key")
    assert backend.api_key == "test_key"
    assert backend.model == backend.MODELS["balanced"]  # Default model
    
    # Test with API key in environment
    with patch.dict(os.environ, {"GROQ_API_KEY": "env_key"}):
        backend = GroqWhisperBackend()
        assert backend.api_key == "env_key"
    
    # Test invalid model
    with pytest.raises(ValueError):
        GroqWhisperBackend(api_key="test_key", model="invalid_model")
    
    # Test missing API key
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError):
            GroqWhisperBackend()

@pytest.mark.asyncio
async def test_groq_whisper_transcribe(mock_groq_client, mock_transcription_response):
    """Test that transcription works correctly."""
    # Setup mock response
    mock_groq_client.audio.transcriptions.create.return_value = mock_transcription_response
    
    # Initialize backend
    backend = GroqWhisperBackend(api_key="test_key")
    
    # Test transcription
    audio_chunk = b"fake audio data"
    async for text in backend.transcribe_stream(audio_chunk):
        assert text == "Hello, this is a test transcription."
    
    # Verify API was called correctly
    mock_groq_client.audio.transcriptions.create.assert_called_once()
    call_kwargs = mock_groq_client.audio.transcriptions.create.call_args.kwargs
    assert call_kwargs["model"] == backend.MODELS["balanced"]
    assert call_kwargs["response_format"] == "text"
    assert call_kwargs["language"] == "en"
    assert call_kwargs["temperature"] == 0.0

@pytest.mark.asyncio
async def test_groq_whisper_stop():
    """Test that stop clears the current transcription."""
    backend = GroqWhisperBackend(api_key="test_key")
    backend._current_transcription = "some transcription"
    
    await backend.stop()
    assert backend._current_transcription is None

@pytest.mark.asyncio
async def test_groq_whisper_error_handling(mock_groq_client):
    """Test that errors are handled correctly."""
    # Create a mock HTTP response for the error
    mock_request = httpx.Request("POST", "https://api.groq.com/audio/transcriptions")
    mock_response = httpx.Response(401, request=mock_request)
    mock_response._content = b'{"error": {"message": "Invalid API Key", "type": "invalid_request_error", "code": "invalid_api_key"}}'
    
    # Setup mock to raise an authentication error
    mock_groq_client.audio.transcriptions.create.side_effect = AuthenticationError(
        message="Error code: 401 - Invalid API Key",
        response=mock_response,
        body={"error": {"message": "Invalid API Key", "type": "invalid_request_error", "code": "invalid_api_key"}}
    )
    
    # Initialize backend
    backend = GroqWhisperBackend(api_key="test_key")
    
    with pytest.raises(AuthenticationError) as exc_info:
        async for _ in backend.transcribe_stream(b"fake audio data"):
            pass
    
    assert "Invalid API Key" in str(exc_info.value) 
#!/usr/bin/env python3
"""
Test suite for WhisperService class.
"""

import os
import time
import unittest
from pathlib import Path
from whisper_service import WhisperService, WhisperModel, TranscriptionResult

class TestWhisperService(unittest.TestCase):
    """Test cases for WhisperService."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.service = WhisperService()
        
        # Create a test audio file
        cls.test_file = "test_audio.wav"
        os.system(f'ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" -ar 16000 -ac 1 {cls.test_file}')
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        if os.path.exists(cls.test_file):
            os.remove(cls.test_file)
    
    def test_model_verification(self):
        """Test that models are correctly verified."""
        available_models = self.service.get_available_models()
        self.assertGreater(len(available_models), 0, "No models available")
        
        # Check specific models
        model_names = {model.model_name for model in available_models}
        expected_models = {
            # Base model
            "base",
            # Tiny model
            "tiny",
            # Small models
            "small",
            "distil-small.en",
            # Medium models
            "medium",
            "distil-medium.en",
            # Large models
            "large-v3",
            "distil-large-v3"
        }
        self.assertTrue(
            expected_models.issubset(model_names),
            f"Missing models. Expected {expected_models}, got {model_names}"
        )
    
    def test_model_info(self):
        """Test getting model information."""
        for model in WhisperModel:
            info = self.service.get_model_info(model)
            self.assertIsInstance(info, dict)
            self.assertEqual(info["name"], model.display_name)
            self.assertIsInstance(info["description"], str)
            self.assertIsInstance(info["quant"], (type(None), str))
    
    def test_transcription(self):
        """Test transcription with different models."""
        test_models = [
            WhisperModel.TINY,  # Fastest multilingual
            WhisperModel.SMALL_EN,  # Fast English-only
            WhisperModel.MEDIUM_EN,  # Balanced English-only
            WhisperModel.LARGE_V3,  # Most accurate
        ]
        
        for model in test_models:
            with self.subTest(model=model.model_name):
                # Transcribe audio with MLX
                result = self.service.transcribe(self.test_file, model)
                text = result.text.strip()
                
                # Verify result
                self.assertIsInstance(text, str)
                self.assertGreater(len(text), 0, "Transcription returned empty text")
    
    def test_audio_conversion(self):
        """Test audio conversion functionality."""
        # Test with explicit output file
        output_file = "test_output.wav"
        try:
            converted = self.service._convert_audio(self.test_file, output_file)
            self.assertTrue(converted.exists())
            self.assertEqual(converted.name, "test_output.wav")
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)
        
        # Test with temporary file
        converted = self.service._convert_audio(self.test_file)
        self.assertTrue(converted.exists())
        self.assertTrue(str(converted).endswith(".wav"))
        
        # Cleanup is handled by the service
    
    def test_model_caching(self):
        """Test that models are properly cached."""
        model = WhisperModel.TINY
        
        # First transcription should initialize the model
        start_time = time.time()
        self.service.transcribe(self.test_file, model)
        first_load_time = time.time() - start_time
        
        # Second transcription should use cached model
        start_time = time.time()
        self.service.transcribe(self.test_file, model)
        second_load_time = time.time() - start_time
        
        # Second load should be significantly faster
        self.assertLess(
            second_load_time,
            first_load_time * 0.8,  # At least 20% faster
            "Model caching not working effectively"
        )

if __name__ == "__main__":
    unittest.main() 
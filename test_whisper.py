#!/usr/bin/env python3
import os
import logging
from lightning_whisper_mlx import LightningWhisperMLX

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_models():
    """Test different whisper models to verify they work correctly."""
    # Test both regular and quantized models
    test_configs = [
        {"model": "tiny", "quant": None},
        {"model": "tiny", "quant": "8bit"},
        {"model": "distil-large-v3", "quant": None},
    ]
    
    # Create a small test audio file using ffmpeg
    test_file = "test_audio.wav"
    os.system(f'ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" -ar 16000 -ac 1 {test_file}')
    
    for config in test_configs:
        model_name = config["model"]
        quant = config["quant"]
        model_str = f"{model_name}{'-' + quant if quant else ''}"
        
        logger.info(f"\nTesting model: {model_str}")
        try:
            # Initialize model
            whisper = LightningWhisperMLX(
                model=model_name,
                batch_size=12,
                quant=quant
            )
            
            # Transcribe
            result = whisper.transcribe(test_file)
            logger.info(f"Transcription result: {result['text']}")
            logger.info(f"Model {model_str} test completed successfully")
            
        except Exception as e:
            logger.error(f"Error testing model {model_str}: {str(e)}")
    
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_models() 
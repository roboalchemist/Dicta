"""Ollama-based text correction service."""

import requests
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class OllamaService:
    """Service for correcting text using Ollama with Gemma model."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "gemma3:1b"):
        """Initialize the Ollama service.
        
        Args:
            base_url: Ollama server URL
            model_name: Model to use for text correction
        """
        self.base_url = base_url
        self.model_name = model_name
        self.system_prompt = (
            "your job is to Add punctuation and capitalization to phrases that are output by a speech to text system. "
            "Do not offer any helpful feedback. Your job is only to capitalize, add puncutation where needed, and fix any obvious word errors if needed. "
            "You will only be provided the text to correct. Implement the corrects. This is not a chat. "
            "You will be immediately provided a new line to correct. Any line after that is a new line and should be corrected independently of any previous lines."
        )
        
        logger.info(f"Initialized Ollama service with model: {model_name}")
    
    def correct_text(self, text: str) -> Optional[str]:
        """Correct text using Ollama.
        
        Args:
            text: The raw speech-to-text output to correct
            
        Returns:
            Corrected text with proper punctuation and capitalization, or None if failed
        """
        if not text or not text.strip():
            return text
            
        if not self.is_available():
            logger.error("Ollama service not available")
            return text
            
        try:
            logger.info(f"Sending text to Ollama for correction: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Use the chat API for better system prompt support
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system", 
                            "content": self.system_prompt
                        },
                        {
                            "role": "user", 
                            "content": f"The text: {text.strip()}"
                        }
                    ],
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                corrected_text = result.get("message", {}).get("content", "").strip()
                
                if corrected_text:
                    logger.info(f"Text corrected by Ollama: '{text}' → '{corrected_text}'")
                    return corrected_text
                else:
                    logger.warning("Ollama returned empty response")
                    return text
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return text
                
        except Exception as e:
            logger.error(f"Error correcting text with Ollama: {e}")
            return text  # Return original text on error
    
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [model.get("name", "") for model in models]
                is_model_available = any(self.model_name in model for model in available_models)
                
                if not is_model_available:
                    logger.warning(f"Model {self.model_name} not found. Available models: {available_models}")
                
                return is_model_available
            return False
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
            return False
    
    def cleanup(self):
        """Clean up Ollama service resources."""
        # No cleanup needed for HTTP-based service
        logger.info("Ollama service cleaned up") 
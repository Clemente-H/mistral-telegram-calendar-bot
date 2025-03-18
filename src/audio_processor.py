import os
import logging
import tempfile
from typing import Optional

# Importar whisper.cpp
import pywhispercpp

# Configure logging
logger = logging.getLogger(__name__)

class AudioProcessor:
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading the model multiple times."""
        if cls._instance is None:
            cls._instance = super(AudioProcessor, cls).__new__(cls)
            cls._instance.model = None
        return cls._instance
    
    def load_model(self, model_size: str = "tiny"):
        """
        Loads the Whisper model.
        
        Args:
            model_size: Size of the model ('tiny', 'base', 'small', 'medium', 'large')
        """
        try:
            logger.info(f"Loading Whisper.cpp model: {model_size}")
            # Whisper.cpp descargará automáticamente el modelo si no existe
            self.model = pywhispercpp.Whisper(model_size)
            logger.info("Whisper.cpp model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading Whisper.cpp model: {str(e)}")
            return False
    
    def ensure_model_loaded(self, model_size: str = "tiny"):
        """Ensures the model is loaded before transcription."""
        if self.model is None:
            return self.load_model(model_size)
        return True
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None) -> Optional[str]:
        """
        Transcribes audio file to text.
        
        Args:
            audio_file_path: Path to the audio file
            language: Optional language code (e.g., 'es', 'fr', 'en')
            
        Returns:
            Optional[str]: Transcribed text or None if failed
        """
        if not self.ensure_model_loaded():
            logger.error("Could not load Whisper.cpp model")
            return None
        
        try:
            # Configurar opciones de transcripción
            options = {
                "language": language if language else None
            }
            
            # Transcribir el audio
            logger.info(f"Transcribing audio file: {audio_file_path}")
            result = self.model.transcribe(audio_file_path)
            
            # Devolver el texto transcrito
            transcribed_text = result.strip()
            logger.info(f"Transcription successful: {transcribed_text[:30]}...")
            return transcribed_text
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return None
"""Speech manager module."""
import logging
import speech_recognition as sr
from PyQt6.QtCore import QObject, pyqtSignal
from app.audio.vad import VADManager

logger = logging.getLogger(__name__)

class SpeechManager(QObject):
    """Manages speech recognition and transcription."""
    
    # Signals
    transcription_ready = pyqtSignal(str)  # Emitted when transcription is ready
    status_changed = pyqtSignal(str)  # Emitted when status changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.auto_listen = False
        
        # Initialize VAD
        self.vad_manager = VADManager(
            aggressiveness=2,  # Medium aggressiveness
            silence_threshold=10,  # 300ms of silence to end speech
            speech_threshold=3  # 90ms of speech to start
        )
        
        # Connect VAD signals
        self.vad_manager.speech_started.connect(self.on_speech_started)
        self.vad_manager.speech_ended.connect(self.on_speech_ended)
        
        # Calibrate microphone
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
    def start_listening(self):
        """Start listening for speech."""
        if not self.is_listening:
            self.is_listening = True
            self.status_changed.emit("Listening")
            if self.auto_listen:
                self.listen_with_vad()
            else:
                self.listen()
            
    def stop_listening(self):
        """Stop listening for speech."""
        self.is_listening = False
        self.status_changed.emit("Stopped")
        
    def toggle_auto_listen(self, enabled):
        """Toggle auto-listen mode."""
        self.auto_listen = enabled
        if enabled:
            self.start_listening()
        else:
            self.stop_listening()
            
    def listen(self):
        """Listen for speech and transcribe it."""
        if not self.is_listening:
            return
            
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source)
                
            try:
                text = self.recognizer.recognize_google(audio)
                self.transcription_ready.emit(text)
                
                if self.auto_listen:
                    self.listen()  # Continue listening if auto-listen is enabled
                    
            except sr.UnknownValueError:
                logger.warning("Speech was unintelligible")
                if self.auto_listen:
                    self.listen()
                    
            except sr.RequestError as e:
                logger.error(f"Could not request results from speech recognition service: {e}")
                if self.auto_listen:
                    self.listen()
                    
        except Exception as e:
            logger.error(f"Error during speech recognition: {e}")
            if self.auto_listen:
                self.listen()
                
    def listen_with_vad(self):
        """Listen for speech using VAD."""
        if not self.is_listening:
            return
            
        try:
            with self.microphone as source:
                # Configure source for VAD
                source.SAMPLE_RATE = 16000
                source.CHUNK = 480  # 30ms at 16kHz
                
                # Start listening
                while self.is_listening:
                    buffer = source.stream.read(source.CHUNK)
                    self.vad_manager.process_frame(buffer)
                    
        except Exception as e:
            logger.error(f"Error during VAD listening: {e}")
            if self.auto_listen:
                self.listen_with_vad()
                
    def on_speech_started(self):
        """Handle speech start event."""
        logger.debug("Speech started")
        self.status_changed.emit("Speech detected")
        
    def on_speech_ended(self):
        """Handle speech end event."""
        logger.debug("Speech ended")
        self.status_changed.emit("Processing")
        
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=1.0)
                
            try:
                text = self.recognizer.recognize_google(audio)
                self.transcription_ready.emit(text)
                
            except sr.UnknownValueError:
                logger.warning("Speech was unintelligible")
                
            except sr.RequestError as e:
                logger.error(f"Could not request results from speech recognition service: {e}")
                
        except Exception as e:
            logger.error(f"Error during speech recognition: {e}")
            
        finally:
            if self.auto_listen:
                self.status_changed.emit("Listening")
                self.listen_with_vad() 
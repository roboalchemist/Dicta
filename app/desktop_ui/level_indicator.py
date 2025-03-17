from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QRect
import numpy as np
import logging
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class LevelIndicator(QWidget):
    """Widget that displays audio levels as 5 vertical bars."""
    
    def __init__(self, parent=None):
        """Initialize the level indicator."""
        super().__init__(parent)
        
        # Set fixed size for the widget
        self.setFixedSize(64, 64)  # Match the size of our microphone icon
        
        # Initialize levels
        self.levels = [0.0] * 5  # 5 bars, each from 0.0 to 1.0
        
        # Colors for different level ranges
        self.colors = {
            'low': QColor(0, 255, 0),      # Green for low levels
            'medium': QColor(255, 255, 0),  # Yellow for medium levels
            'high': QColor(255, 0, 0)       # Red for high levels
        }
        
        # Background color
        self.background_color = QColor(32, 32, 32, 200)  # Semi-transparent dark gray
        
    def update_levels(self, audio_data: np.ndarray):
        """Update the level bars based on audio data.
        
        Args:
            audio_data: numpy array of float32 audio samples in [-1, 1] range
        """
        if len(audio_data) == 0:
            return
            
        try:
            # Calculate RMS value of the audio data
            rms = np.sqrt(np.mean(np.square(audio_data)))
            
            # Convert RMS to dB, with some reasonable thresholds
            db = 20 * np.log10(max(rms, 1e-6))  # Avoid log of 0
            
            # Normalize to 0-1 range for visualization
            # Assuming typical speech is between -50dB and -10dB
            normalized = (db + 50) / 40  # Now 0.0 to 1.0
            normalized = max(0.0, min(1.0, normalized))  # Clamp to 0-1
            
            # Distribute the level across the 5 bars
            # Each bar represents a 20% range of the total level
            for i in range(5):
                threshold = (i + 1) * 0.2
                if normalized >= threshold:
                    self.levels[i] = min(1.0, normalized)
                else:
                    # Partial fill for the current bar
                    remaining = normalized - (i * 0.2)
                    self.levels[i] = max(0.0, min(1.0, remaining * 5))
            
            logger.debug(f"Audio levels - RMS: {rms:.3f}, dB: {db:.1f}, normalized: {normalized:.2f}")
            
            # Request a repaint
            self.update()
            
        except Exception as e:
            logger.error(f"Error updating audio levels: {e}")
    
    def paintEvent(self, event):
        """Paint the level bars."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), self.background_color)
        
        # Calculate bar dimensions
        width = self.width()
        height = self.height()
        bar_width = width / 7  # 5 bars with 2 units of padding
        bar_spacing = bar_width / 2
        bar_bottom = height - 4  # 4 pixels padding from bottom
        
        # Draw each bar
        x = bar_spacing * 2  # Start after padding
        for level in self.levels:
            # Calculate bar height
            bar_height = max(4, int(level * (height - 8)))  # Min 4 pixels, 8 pixels total padding
            
            # Calculate color based on level
            if level < 0.4:  # Low level
                color = self.colors['low']
            elif level < 0.7:  # Medium level
                color = self.colors['medium']
            else:  # High level
                color = self.colors['high']
            
            # Draw bar background (darker version of the color)
            dark_color = QColor(color)
            dark_color.setAlpha(40)
            bar_rect = QRect(int(x), 4, int(bar_width), height - 8)
            painter.fillRect(bar_rect, dark_color)
            
            # Draw active bar portion
            if bar_height > 0:
                bar_rect = QRect(
                    int(x),
                    bar_bottom - bar_height,
                    int(bar_width),
                    bar_height
                )
                painter.fillRect(bar_rect, color)
            
            x += bar_width + bar_spacing
    
    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        # Position the widget near the menu bar icon
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            # Position in the top-right corner with some padding
            self.move(
                screen_geometry.width() - self.width() - 20,  # 20px from right
                22  # Just below menu bar
            )
        self.raise_()  # Ensure it's on top 
"""Signal icon generator for voice activity levels."""

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor
from PyQt6.QtCore import Qt
import os

class SignalIcon:
    """Generates signal bar icons for voice activity levels."""
    
    def __init__(self, size: int = 44):
        """Initialize the signal icon generator.
        
        Args:
            size: Size of the icon in pixels (both width and height)
        """
        self.size = size
        self._icon_cache = {}  # Cache icons to avoid recreating them
        
    def generate(self, active_bars: int) -> QIcon:
        """Generate an icon with the specified number of active bars.
        
        Args:
            active_bars: Number of bars to show as active (0-4)
        
        Returns:
            QIcon representing the signal level
        """
        # Cache the icon to avoid recreating it every time
        if active_bars in self._icon_cache:
            return self._icon_cache[active_bars]
            
        # Create a pixmap
        pixmap = QPixmap(self.size, self.size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Define colors based on activity level
        if active_bars == 0:
            # No activity - dark gray (more visible)
            active_color = QColor(60, 60, 60)  # Darker gray
        elif active_bars <= 2:
            # Low activity - red (waiting to hear voice)
            active_color = QColor(255, 80, 80)  # Red
        elif active_bars == 3:
            # Medium activity - yellow (actively listening)
            active_color = QColor(255, 200, 0)  # Yellow
        else:
            # High activity - green (processing/typing)
            active_color = QColor(0, 200, 0)  # Green
        
        inactive_color = QColor(255, 255, 255)  # White for inactive bars (modern macOS style)
        
        # Draw 4 signal bars
        num_bars = 4
        bar_width = int(self.size * 0.15)  # Make bars thicker
        bar_spacing = int(self.size * 0.05)
        total_width = (num_bars * bar_width) + ((num_bars - 1) * bar_spacing)
        start_x = (self.size - total_width) // 2
        
        for i in range(num_bars):
            # Calculate bar height (increasing from left to right)
            bar_height = int(self.size * (0.3 + (i * 0.15)))  # 30%, 45%, 60%, 75% of icon size
            
            # Calculate position
            bar_x = start_x + i * (bar_width + bar_spacing)
            bar_y = self.size - bar_height - 2  # Leave small margin at bottom
            
            # Choose color based on whether this bar should be active
            if i < active_bars:
                color = active_color
            else:
                color = inactive_color
            
            # Draw the bar
            painter.fillRect(bar_x, bar_y, bar_width, bar_height, QBrush(color))
        
        painter.end()
        
        # Create and cache the icon
        icon = QIcon(pixmap)
        self._icon_cache[active_bars] = icon
        return icon 
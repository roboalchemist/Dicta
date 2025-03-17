"""Signal icon generator for voice activity levels."""

from PyQt6.QtGui import QPainter, QColor, QIcon, QPixmap
from PyQt6.QtCore import Qt, QRect, QSize

class SignalIcon:
    """Generates cellular-style signal bar icons for voice activity levels."""
    
    def __init__(self, size: int = 22):  # Menu bar icons are typically 22x22
        """Initialize the signal icon generator.
        
        Args:
            size: Size of the icon in pixels (both width and height)
        """
        self.size = size
        self.active_color = QColor(0, 255, 0)  # Green for active bars
        self.inactive_color = QColor(128, 128, 128, 60)  # Semi-transparent gray for inactive
        
    def generate(self, active_bars: int) -> QIcon:
        """Generate an icon with the specified number of active bars.
        
        Args:
            active_bars: Number of bars to show as active (0-4)
        
        Returns:
            QIcon with the signal bars drawn
        """
        # Create pixmap
        pixmap = QPixmap(self.size, self.size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Create painter
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate bar dimensions
        total_bars = 4
        bar_width = self.size / (total_bars * 2)  # Leave space between bars
        max_height = self.size - 4  # Leave some padding
        
        # Draw bars from shortest to tallest
        x = 2  # Start with some padding
        for i in range(total_bars):
            # Calculate bar height (each bar is taller than the previous)
            height = max_height * ((i + 1) / total_bars)
            
            # Calculate y position (align to bottom)
            y = self.size - height - 2  # 2px padding from bottom
            
            # Determine if this bar should be active
            is_active = i < active_bars
            color = self.active_color if is_active else self.inactive_color
            
            # Draw bar
            painter.fillRect(
                QRect(int(x), int(y), int(bar_width), int(height)),
                color
            )
            
            # Move to next bar position
            x += bar_width * 1.5  # Add some space between bars
        
        painter.end()
        return QIcon(pixmap) 
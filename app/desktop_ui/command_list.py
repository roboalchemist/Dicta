"""Command list window for managing voice commands."""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QHeaderView, QMainWindow, QWidget
)
from PyQt6.QtCore import Qt, pyqtSlot
from .command_mapper import CommandMapper

logger = logging.getLogger(__name__)

class CommandListWindow(QMainWindow):
    """Window for managing voice commands."""

    def __init__(self, command_mapper: CommandMapper):
        super().__init__()
        self.command_mapper = command_mapper
        self.setup_ui()
        self.load_commands()

    def setup_ui(self):
        """Set up the window UI."""
        self.setWindowTitle("Voice Commands")
        self.setGeometry(100, 100, 400, 300)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create input fields
        input_layout = QVBoxLayout()  # Changed to VBox to stack error labels
        
        # Command input section
        command_section = QVBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Voice Command")
        self.command_error = QLabel()
        self.command_error.setStyleSheet("QLabel { color: red; }")
        self.command_error.hide()
        command_section.addWidget(self.command_input)
        command_section.addWidget(self.command_error)
        
        # Key input section
        key_section = QVBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Key (e.g. 'escape')")
        self.key_error = QLabel()
        self.key_error.setStyleSheet("QLabel { color: red; }")
        self.key_error.hide()
        key_section.addWidget(self.key_input)
        key_section.addWidget(self.key_error)
        
        # Add input sections to layout
        input_row = QHBoxLayout()
        input_row.addLayout(command_section)
        input_row.addLayout(key_section)
        input_layout.addLayout(input_row)
        layout.addLayout(input_layout)

        # Create buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_command)
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_command)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_command)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.remove_button)
        layout.addLayout(button_layout)

        # Create command table
        self.command_table = QTableWidget()
        self.command_table.setColumnCount(2)
        self.command_table.setHorizontalHeaderLabels(["Command", "Key"])
        self.command_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.command_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.command_table)

        # Handle keyboard events
        self.command_table.keyPressEvent = self.handle_table_key_press

        # Connect input changes to clear errors
        self.command_input.textChanged.connect(lambda: self.command_error.hide())
        self.key_input.textChanged.connect(lambda: self.key_error.hide())

    def handle_table_key_press(self, event):
        """Handle keyboard events in the command table."""
        if event.key() == Qt.Key.Key_Delete:
            self.remove_command()
        else:
            QTableWidget.keyPressEvent(self.command_table, event)

    def show_error(self, field: str, message: str):
        """Show an error message for a field.
        
        Args:
            field: Which field has the error ('command' or 'key')
            message: The error message to display
        """
        if field == 'command':
            self.command_error.setText(message)
            self.command_error.show()
        elif field == 'key':
            self.key_error.setText(message)
            self.key_error.show()

    def clear_errors(self):
        """Clear all error messages."""
        self.command_error.hide()
        self.key_error.hide()

    def add_command(self):
        """Add a new command."""
        command = self.command_input.text().strip()
        key = self.key_input.text().strip()
        
        if not command or not key:
            self.show_error("command" if not command else "key", "Field cannot be empty")
            return
        
        try:
            # Check for duplicates
            if command.lower() in self.command_mapper.commands:
                self.show_error("command", "Command already exists")
                return
            
            # Try to add command
            self.command_mapper.add_command(command, key)
            self.load_commands()
            self.command_input.clear()
            self.key_input.clear()
            self.clear_errors()
            
        except ValueError as e:
            self.show_error("key", str(e))

    def edit_command(self):
        """Edit the selected command."""
        selected_rows = self.command_table.selectedItems()
        if not selected_rows:
            self.show_error("command", "Please select a command to edit")
            return
        
        old_command = self.command_table.item(self.command_table.currentRow(), 0).text()
        new_command = self.command_input.text().strip()
        new_key = self.key_input.text().strip()
        
        if not new_command or not new_key:
            self.show_error("command" if not new_command else "key", "Field cannot be empty")
            return
        
        try:
            # Check for duplicates (excluding the command being edited)
            if new_command.lower() != old_command.lower() and new_command.lower() in self.command_mapper.commands:
                self.show_error("command", "Command already exists")
                return
            
            # Remove old command and add new one
            self.command_mapper.remove_command(old_command)
            self.command_mapper.add_command(new_command, new_key)
            self.load_commands()
            self.command_input.clear()
            self.key_input.clear()
            self.clear_errors()
            
        except ValueError as e:
            self.show_error("key", str(e))

    def remove_command(self):
        """Remove the selected command."""
        self.clear_errors()
        selected_rows = self.command_table.selectedItems()
        if not selected_rows:
            self.show_error('command', "Please select a command to remove")
            return

        command = self.command_table.item(selected_rows[0].row(), 0).text()
        self.command_mapper.remove_command(command)
        self.load_commands()

    def load_commands(self):
        """Load commands into the table."""
        self.command_table.setRowCount(0)
        commands = self.command_mapper.get_commands()
        for command, key in commands.items():
            row = self.command_table.rowCount()
            self.command_table.insertRow(row)
            self.command_table.setItem(row, 0, QTableWidgetItem(command))
            self.command_table.setItem(row, 1, QTableWidgetItem(key))
            
        logger.debug(f"Loaded {len(commands)} commands into table") 
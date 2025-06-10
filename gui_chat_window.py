from PyQt5.QtWidgets import QMainWindow, QTextEdit, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class ChatWindow(QMainWindow):
    """A window to display AI chat conversations."""
    
    def __init__(self, title, worker_manager):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 800, 600)  # Larger window for better readability
        self.worker_manager = worker_manager
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        
        # Set a monospace font for better formatting
        font = QFont("Courier New", 10)
        self.chat_display.setFont(font)
        
        layout.addWidget(self.chat_display)

    def append_separator(self, title):
        """Add a separator between conversations."""
        separator = "-" * 80
        self.chat_display.append(f"\n{separator}")
        self.chat_display.append(f"New Conversation: {title}")
        self.chat_display.append(f"{separator}\n")
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def append_model_info(self, model_name):
        """Add model information to the chat."""
        self.chat_display.append(f'<span style="color: blue"><b>Using Model: {model_name}</b></span>\n')
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
    def append_message(self, role, content):
        """Add a message to the chat display."""
        # Format based on role
        if role == "system":
            color = "blue"
            prefix = "System"
        elif role == "user":
            color = "green"
            prefix = "User"
        else:  # assistant
            color = "purple"
            prefix = "Assistant"
        
        # Add formatted message with improved readability
        self.chat_display.append(f'<span style="color: {color}"><b>{prefix}:</b></span>')
        # Format the content with proper line breaks and indentation
        formatted_content = content.replace('\n', '\n    ')  # Add indentation
        self.chat_display.append(f"    {formatted_content}")  # Initial indentation
        self.chat_display.append("")  # Empty line for spacing
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker_manager and self.worker_manager.worker and self.worker_manager.worker.isRunning():
            # Attempt to clean up the worker gracefully
            self.worker_manager.cleanup_worker()
            # Give a small delay for cleanup
            self.worker_manager.worker.wait(1000)  # Wait up to 1 second
            
        # Now we can safely close
        self.chat_display.clear()  # Clear the display
        event.accept()

import os
import logging
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import QTimer

class BaseGuiHandler:
    """Base class for GUI handlers with common functionality."""
    
    # Define autonomy workflow stages and their progress percentages
    AUTONOMY_STAGES = {
        "READY": {"value": 0, "text": "Ready to start"},
        "FIND_PART": {"value": 10, "text": "Finding part..."},
        "DOWNLOAD_EOL": {"value": 20, "text": "Downloading EOL datasheet..."},
        "ANALYZE_EOL": {"value": 30, "text": "Analyzing EOL part..."},
        "FIND_ALTERNATIVES": {"value": 50, "text": "Finding alternative parts..."},
        "DOWNLOAD_ALTERNATIVES": {"value": 70, "text": "Downloading alternative datasheets..."},
        "COMPARE_PARTS": {"value": 85, "text": "Comparing all parts..."},
        "EXPORT": {"value": 95, "text": "Exporting document..."},
        "COMPLETE": {"value": 100, "text": "Process complete"}
    }
    
    def __init__(self, main_window):
        """Initialize the base handler with the main window reference."""
        self.window = main_window
        self.datasheets_dir = main_window.datasheets_dir
        self.worker_manager = main_window.worker_manager
    
    def update_autonomy_progress(self, stage):
        """Update the autonomy mode progress bar and label."""
        if not self.window.autonomy_mode:
            return
            
        stage_info = self.AUTONOMY_STAGES.get(stage, {"value": 0, "text": "Unknown stage"})
        self.window.autonomy_progress_bar.setValue(stage_info["value"])
        self.window.autonomy_stage_label.setText(stage_info["text"])
        logging.info(f"Autonomy progress updated: {stage} - {stage_info['value']}% - {stage_info['text']}")
    
    def show_error(self, title, message):
        """Show an error message if not in autonomy mode."""
        if not self.window.autonomy_mode:
            QMessageBox.critical(self.window, title, message)
        logging.error(message)
    
    def show_warning(self, title, message):
        """Show a warning message if not in autonomy mode."""
        if not self.window.autonomy_mode:
            QMessageBox.warning(self.window, title, message)
        logging.warning(message)
    
    def process_next_part(self):
        """Process the next part in the queue."""
        if not hasattr(self.window, 'pending_parts') or not self.window.pending_parts:
            self.window.set_status("All parts processed successfully.")
            return

        part_number = self.window.pending_parts.pop(0)
        self.window.set_status(f"Processing part {len(self.window.pending_parts) + 1}...")

        try:
            # This will be implemented in the derived class
            self.handle_find_part([part_number])
        except Exception as e:
            logging.error(f"Error processing part {part_number}: {str(e)}")
            self.process_next_part()

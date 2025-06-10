import logging
import os # For os.path.basename
from PyQt5.QtWidgets import QMessageBox, QApplication

from gui_handlers_base import BaseGuiHandler
from config import config
from utils import encode_pdf_to_base64 # Import the new function

class AnalysisHandler(BaseGuiHandler):
    """Handler for EOL part analysis functionality."""
    
    def handle_analyze_eol(self):
        """Handle the Analyze EOL Part button click."""
        logging.info("handle_analyze_eol called")
        
        # Update progress if in autonomy mode
        if self.window.autonomy_mode:
            self.update_autonomy_progress("ANALYZE_EOL")
        
        if not hasattr(self.window, 'eol_pdf_path') or not self.window.eol_pdf_path:
            self.show_warning("Missing Datasheet Path", "EOL PDF path not found. Please download the datasheet first.")
            return

        pdf_path = self.window.eol_pdf_path
        if not os.path.exists(pdf_path):
            self.show_warning("Datasheet Not Found", f"The datasheet at {pdf_path} was not found.")
            return

        self.window.set_status("Encoding and analyzing EOL part datasheet...")
        self.window.results_area.setPlainText("Encoding PDF and preparing analysis...")
        logging.info(f"Starting EOL analysis for PDF: {pdf_path}")

        try:
            base64_pdf = encode_pdf_to_base64(pdf_path)
            data_url = f"data:application/pdf;base64,{base64_pdf}"
            pdf_filename = os.path.basename(pdf_path)
        except Exception as e:
            logging.error(f"Failed to encode PDF: {e}")
            self.show_error("Encoding Error", f"Failed to encode PDF: {e}")
            self.window.set_status("Failed to encode PDF.")
            return

        from ai_prompts import EOL_ANALYSIS_SYSTEM_PROMPT, EOL_ANALYSIS_USER_PROMPT
        
        # The EOL_ANALYSIS_USER_PROMPT should be a generic instruction now,
        # e.g., "Analyze the key specifications from the provided EOL datasheet."
        # The PDF content itself is sent via the 'file' type.
        messages = [
            {"role": "system", "content": EOL_ANALYSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": EOL_ANALYSIS_USER_PROMPT # This prompt will need to be updated
                    },
                    {
                        "type": "file",
                        "file": {
                            "filename": pdf_filename,
                            "file_data": data_url
                        }
                    },
                ]
            }
        ]

        # Ensure previous worker is cleaned up
        if hasattr(self.worker_manager, 'worker') and self.worker_manager.worker:
            logging.info("Cleaning up previous worker before EOL analysis")
            self.worker_manager.cleanup_worker()
            QApplication.processEvents()

        # Create and start worker immediately without timer
        logging.info("Creating API worker for EOL analysis")
        model = config.get_model("eol_analysis")
        self.worker_manager.create_api_worker(
            model, 
            messages, 
            self.handle_eol_analysis_result, 
            "Analyzing EOL part datasheet...",
            window_title="EOL Part Analysis"
        )
        logging.info("API worker for EOL analysis created")

    def handle_eol_analysis_result(self, result):
        """Handle the EOL datasheet analysis result."""
        logging.info("handle_eol_analysis_result called")
        self.window.eol_part_specs = result
        self.window.results_area.setPlainText(f"EOL Part Specifications:\n\n{result}")
        self.window.find_alternatives_button.setEnabled(True)
        self.window.set_status("EOL part analysis completed. Click 'Find Alternative Parts' to get suggestions.")
        # Cleanup will be handled by the worker's finished signal
        
        # If in autonomy mode, proceed to the next step
        if self.window.autonomy_mode:
            logging.info("Autonomy mode is enabled, proceeding to find alternatives")
            # Force UI updates before proceeding
            QApplication.processEvents()
            # Call directly without timer
            self.window.handlers.alternatives_handler.handle_find_alternatives()
            logging.info("Called handle_find_alternatives in autonomy mode")

import os
import logging
import re
import PyPDF2
from PyQt5.QtWidgets import QMessageBox, QApplication

from api_client import clean_pdf_url
from gui_utils import download_pdf
from utils import sanitize_filename # Import the new utility
from gui_handlers_base import BaseGuiHandler
from config import config

class PartSearchHandler(BaseGuiHandler):
    """Handler for part search and datasheet download functionality."""
    
    def handle_find_part(self, part_numbers=None, autonomy_mode=None):
        """Handle the Find Part button click."""
        # Set autonomy mode from parameter or checkbox
        if autonomy_mode is not None:
            self.window.autonomy_mode = autonomy_mode
        else:
            # Use the checkbox state if not explicitly provided
            self.window.autonomy_mode = self.window.autonomy_mode_checkbox.isChecked()
            
        logging.info(f"handle_find_part called with autonomy_mode: {self.window.autonomy_mode}")
        
        # Update progress if in autonomy mode
        if self.window.autonomy_mode:
            self.update_autonomy_progress("FIND_PART")
        
        if part_numbers:
            self.window.pending_parts = part_numbers
            if self.window.autonomy_mode:
                self.process_next_part()
            return

        part_name = self.window.input_field.text().strip()
        if not part_name:
            self.show_warning("Input Error", "Please enter a part name or number.")
            return

        # Always use manual input since spreadsheet lookup has been removed
        self.window.part_info_area.setPlainText(f"Part Number: {part_name}")
        spreadsheet_data = {"Description": part_name, "Item_Code": part_name}
        
        try:
            # Search for datasheet URL using the part number
            description = spreadsheet_data.get('Description', '')
            self.window.status_label.setText(f"Searching for datasheet for {part_name}...")
            
            def handle_url_result(result):
                if not result:
                    self.window.set_status("Failed to find datasheet URL. Please try again.")
                    return
                
                try:
                    # Extract PDF URL from result
                    pdf_urls = re.findall(r'https?://[^\s<>"]+?\.pdf(?:\[\d+\])?', result)
                    if not pdf_urls:
                        raise Exception("No PDF URL found in response")
                    
                    # Clean up the URL
                    pdf_url = clean_pdf_url(pdf_urls[-1])
                    
                    # Download and process the datasheet
                    self.window.set_status(f"Downloading datasheet from {pdf_url}...")
                    if self.window.autonomy_mode:
                        self.update_autonomy_progress("DOWNLOAD_EOL")
                    
                    logging.info(f"Starting download of EOL PDF from {pdf_url}")
                    pdf_content = download_pdf(pdf_url, timeout=60)
                    logging.info(f"Successfully downloaded EOL PDF")
                    
                    # Sanitize part_name for use in filename
                    sanitized_part_name = sanitize_filename(part_name)
                    filename = f"eol_{sanitized_part_name}.pdf"
                    pdf_path = os.path.join(self.datasheets_dir, filename)
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    # Attempt to extract text from PDF, but don't let it block the process
                    text = "" # Default to empty string
                    try:
                        pdf_reader = PyPDF2.PdfReader(pdf_path)
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text: # Ensure text was extracted
                                text += page_text
                        if not text:
                            logging.warning(f"PyPDF2 extracted no text from {pdf_path}. Content might be image-based or encrypted without PyCryptodome.")
                    except Exception as ex_text_extract:
                        logging.warning(f"Could not extract text from PDF {pdf_path} due to: {ex_text_extract}. Proceeding with PDF path only.")
                        # This could be the PyCryptodome error, or other PyPDF2 issues.
                        # We set text to empty, but pdf_path is still valid for API submission.
                    
                    # Store content (even if empty) and path, then update UI
                    self.window.eol_pdf_content = text
                    self.window.eol_pdf_path = pdf_path # Store the path to the PDF
                    self.window.eol_pdf_label.setText(f"Downloaded: {filename}")
                    self.window.eol_pdf_label.setStyleSheet("color: green;")
                    self.window.analyze_button.setEnabled(True)
                    self.window.set_status("EOL datasheet downloaded. Click 'Analyze EOL Part' to proceed.")
                    
                    # If in autonomy mode, proceed to the next step
                    if self.window.autonomy_mode:
                        logging.info(f"Autonomy mode is enabled, proceeding to analyze EOL part")
                        # Force UI updates before proceeding
                        QApplication.processEvents()
                        # Call directly without timer
                        self.window.handlers.analysis_handler.handle_analyze_eol()
                        logging.info(f"Called handle_analyze_eol in autonomy mode")
                    
                except Exception as e:
                    error_msg = f"Failed to process datasheet: {str(e)}"
                    self.show_error("Error", error_msg)
                    self.window.eol_pdf_label.setText("Failed to process PDF")
                    self.window.eol_pdf_label.setStyleSheet("color: red;")
                    self.window.set_status("Failed to process datasheet. Please try again.")
            
            # Create API worker for datasheet URL search
            from ai_prompts import DATASHEET_URL_BASE_PROMPT
            messages = [
                {"role": "user", "content": DATASHEET_URL_BASE_PROMPT.format(part_number=part_name)}
            ]
            
            # Get model from configuration
            model = config.get_model("datasheet_search")
            
            self.worker_manager.create_api_worker(
                model,
                messages,
                handle_url_result,
                "Searching for datasheet...",
                window_title="Datasheet Search"
            )
            
        except Exception as e:
            error_msg = f"Failed to start datasheet search: {str(e)}"
            self.show_error("Error", error_msg)
            self.window.eol_pdf_label.setText("Failed to find PDF")
            self.window.eol_pdf_label.setStyleSheet("color: red;")
            self.window.status_label.setText("Failed to start datasheet search. Please try again.")

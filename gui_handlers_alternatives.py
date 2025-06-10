import os
import logging
import re
import PyPDF2
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import QTimer

from api_client import clean_pdf_url
from gui_utils import download_pdf
from gui_handlers_base import BaseGuiHandler
from config import config

class AlternativesHandler(BaseGuiHandler):
    """Handler for finding and downloading alternative parts."""
    
    def handle_find_alternatives(self):
        """Handle the Find Alternative Parts button click."""
        logging.info("handle_find_alternatives called")
        
        # Update progress if in autonomy mode
        if self.window.autonomy_mode:
            self.update_autonomy_progress("FIND_ALTERNATIVES")
            
        if not hasattr(self.window, 'eol_part_specs') or not self.window.eol_part_specs:
            if not self.window.autonomy_mode:
                self.show_warning("Missing Analysis", "Please analyze the EOL part datasheet first.")
            else:
                logging.warning("Please analyze the EOL part datasheet first.")
            return

        # Check if deep search is enabled
        deep_search = self.window.deep_search
        search_type = "deep" if deep_search else "standard"
        self.window.set_status(f"Finding alternative parts ({search_type} search)...")
        self.window.results_area.setPlainText(f"Searching for alternative parts using {search_type} search...")
        logging.info(f"Starting alternatives search with {search_type} search mode")

        # Use different prompt based on deep search setting
        from ai_prompts import ALTERNATIVES_SYSTEM_PROMPT, ALTERNATIVES_USER_PROMPT, DEEP_ALTERNATIVES_USER_PROMPT
        
        # Select the appropriate prompt based on deep search setting
        user_prompt = DEEP_ALTERNATIVES_USER_PROMPT if deep_search else ALTERNATIVES_USER_PROMPT
        
        messages = [
            {"role": "system", "content": ALTERNATIVES_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt.format(specs=self.window.eol_part_specs)}
        ]

        # Ensure previous worker is cleaned up
        if hasattr(self.worker_manager, 'worker') and self.worker_manager.worker:
            logging.info("Cleaning up previous worker before alternatives search")
            self.worker_manager.cleanup_worker()
            QApplication.processEvents()

        # Create and start worker immediately without timer
        logging.info("Creating API worker for alternatives search")
        model = config.get_model("alternatives_search")
        self.worker_manager.create_api_worker(
            model, 
            messages, 
            self.handle_alternatives_result, 
            "Finding alternative parts...",
            window_title="Alternative Parts Search"
        )
        logging.info("API worker for alternatives search created")

    def handle_alternatives_result(self, result):
        """Handle the alternatives search result."""
        self.window.alternatives_specs = result
        self.window.alternatives_area.setPlainText(result)
        
        # Extract part numbers from the result by looking for lines starting with numbers or markdown headers
        part_numbers = []
        lines = result.split('\n')
        for line in lines:
            # Look for lines that start with a number and period (e.g., "1. Kontron COMe‑6413")
            # or markdown headers with numbers (e.g., "## 1. **D10 by DuroPC**")
            if match := re.search(r'(?:^|\#\#\s+)\d+\.\s+(?:\*\*)?([^•\n\*]+)(?:\*\*)?', line):
                # Extract and clean the part name/number
                part_name = match.group(1).strip()
                part_numbers.append(part_name)
                
        # Process all found alternatives in autonomy mode or deep search mode
        # Otherwise limit to 3 for standard mode
        if self.window.autonomy_mode or self.window.deep_search:
            # Process all found alternatives (up to 20)
            logging.info(f"Processing all {len(part_numbers)} alternatives found")
        else:
            # In standard mode, limit to 3 alternatives
            part_numbers = part_numbers[:3]
            logging.info(f"Standard mode: Limited to 3 alternatives")
            
        if not part_numbers:
            self.show_warning("No Parts Found", "No valid part numbers found in the alternatives list.")
            return
            
        # Initialize counters for tracking downloads
        self.window.alt_pdf_contents = []
        self.window.alt_pdf_names = []
        self.remaining_downloads = len(part_numbers)
        self.successful_downloads = 0
        
        # Store part numbers for sequential processing
        self.window.pending_alternatives = part_numbers
        QApplication.processEvents()
        
        # Update progress if in autonomy mode
        if self.window.autonomy_mode:
            self.update_autonomy_progress("DOWNLOAD_ALTERNATIVES")
            
        self.process_next_alternative()
        
        # Note: We don't call handle_compare_datasheets here in autonomy mode
        # Instead, we wait for all downloads to complete in handle_alternative_download_complete
        # This prevents race conditions where we try to compare before all downloads are done
            
    def process_next_alternative(self):
        """Process the next alternative part in the queue."""
        if not hasattr(self.window, 'pending_alternatives') or not self.window.pending_alternatives:
            return
            
        part_number = self.window.pending_alternatives[0]
        self.window.set_status(f"Searching for datasheet for {part_number}...")
        
        # Set a timeout timer to ensure we don't get stuck on a download
        download_timeout = QTimer()
        download_timeout.setSingleShot(True)
        download_timeout.timeout.connect(lambda: self.handle_download_timeout(part_number))
        download_timeout.start(120000)  # 2 minute timeout
        
        # Store the timer for later cleanup
        if not hasattr(self.window, 'download_timers'):
            self.window.download_timers = {}
        self.window.download_timers[part_number] = download_timeout
        
        # Create API worker for datasheet URL search
        from ai_prompts import DATASHEET_URL_BASE_PROMPT
        messages = [
            {"role": "user", "content": DATASHEET_URL_BASE_PROMPT.format(part_number=part_number)}
        ]
        
        def handle_url_result(result):
            if not result:
                self.handle_alternative_download_complete()
                return
            
            try:
                # Extract PDF URL from result
                pdf_urls = re.findall(r'https?://[^\s<>"]+?\.pdf(?:\[\d+\])?', result)
                if not pdf_urls:
                    raise Exception("No PDF URL found in response")
                
                # Clean up the URL
                pdf_url = clean_pdf_url(pdf_urls[-1])
                
                # Download and process the datasheet
                self.window.set_status(f"Downloading datasheet for {part_number}...")
                
                # Download the PDF with a timeout
                try:
                    logging.info(f"Starting download of PDF for {part_number} from {pdf_url}")
                    pdf_content = download_pdf(pdf_url, timeout=60)
                    
                    # Save the PDF
                    filename = f"alt_{part_number}.pdf"
                    pdf_path = os.path.join(self.datasheets_dir, filename)
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    logging.info(f"Successfully downloaded and saved PDF for {part_number}")
                    
                    # Consider the download successful at this point
                    self.successful_downloads += 1
                    self.window.alt_pdf_names.append(filename)
                    
                    # Try to extract text from PDF, but don't fail if it doesn't work
                    try:
                        pdf_reader = PyPDF2.PdfReader(pdf_path)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text()
                        
                        # Store content
                        self.window.alt_pdf_contents.append(text)
                        logging.info(f"Successfully extracted text from PDF for {part_number}")
                    except Exception as extract_error:
                        logging.warning(f"Could not extract text from PDF for {part_number}, but file was downloaded: {str(extract_error)}")
                        # Add empty text to maintain index alignment with alt_pdf_names
                        self.window.alt_pdf_contents.append("")
                    
                except Exception as download_error:
                    logging.error(f"Failed to download PDF for {part_number}: {str(download_error)}")
                    if not self.window.autonomy_mode:
                        QMessageBox.warning(self.window, "Warning", f"Failed to download datasheet for {part_number}")
                    # Continue with the next alternative even if this one failed
                
            except Exception as e:
                logging.error(f"Failed to process URL for {part_number}: {str(e)}")
                if not self.window.autonomy_mode:
                    QMessageBox.warning(self.window, "Warning", f"Failed to get URL for {part_number}")
            
            finally:
                # Clean up the timer if it still exists
                if hasattr(self.window, 'download_timers') and part_number in self.window.download_timers:
                    self.window.download_timers[part_number].stop()
                    del self.window.download_timers[part_number]
                
                QApplication.processEvents()
                # Remove the processed part and handle completion
                self.window.pending_alternatives.pop(0)
                self.handle_alternative_download_complete()
                # Process next alternative if any remain
                if self.window.pending_alternatives:
                    QApplication.processEvents()
                    self.process_next_alternative()
        
        # Ensure previous worker is cleaned up
        if hasattr(self.worker_manager, 'worker') and self.worker_manager.worker:
            logging.info(f"Cleaning up previous worker before alternative datasheet search for {part_number}")
            self.worker_manager.cleanup_worker()
            QApplication.processEvents()

        try:
            # Create and start worker immediately without timer
            logging.info(f"Creating API worker for alternative datasheet search for {part_number}")
            model = config.get_model("datasheet_search")
            self.worker_manager.create_api_worker(
                model,
                messages,
                handle_url_result,
                f"Searching for {part_number} datasheet...",
                window_title=f"Alternative Datasheet - {part_number}"
            )
            logging.info(f"API worker for alternative datasheet search created for {part_number}")
        except Exception as e:
            logging.error(f"Failed to create worker for {part_number}: {str(e)}")
            QApplication.processEvents()
            # Remove the failed part and continue with next
            self.window.pending_alternatives.pop(0)
            self.handle_alternative_download_complete()
            if self.window.pending_alternatives:
                self.process_next_alternative()
        
    def handle_download_timeout(self, part_number):
        """Handle a timeout during download of an alternative datasheet."""
        logging.warning(f"Download timeout for {part_number} after 2 minutes")
        
        # Clean up the timer
        if hasattr(self.window, 'download_timers') and part_number in self.window.download_timers:
            self.window.download_timers[part_number].stop()
            del self.window.download_timers[part_number]
        
        # If the part is still in the pending list, remove it and continue
        if hasattr(self.window, 'pending_alternatives') and self.window.pending_alternatives and self.window.pending_alternatives[0] == part_number:
            logging.info(f"Skipping {part_number} due to timeout")
            self.window.pending_alternatives.pop(0)
            
            # Update the UI to show we're skipping this part
            self.window.set_status(f"Skipping {part_number} due to download timeout")
            
            # Process the next alternative
            QApplication.processEvents()
            self.handle_alternative_download_complete()
            
            # Continue with the next alternative if any remain
            if hasattr(self.window, 'pending_alternatives') and self.window.pending_alternatives:
                QApplication.processEvents()
                self.process_next_alternative()
        
    def handle_alternative_download_complete(self):
        """Handle completion of an alternative datasheet download."""
        self.remaining_downloads -= 1
        
        # If all downloads are complete, update UI
        if self.remaining_downloads == 0:
            try:
                if self.successful_downloads > 0:
                    self.window.alt_pdf_label.setText(f"Downloaded {self.successful_downloads} alternative datasheets")
                    self.window.alt_pdf_label.setStyleSheet("color: green;")
                    self.window.compare_button.setEnabled(True)
                    self.window.set_status("Alternative datasheets downloaded. Click 'Compare All Parts' to analyze.")
                else:
                    self.window.alt_pdf_label.setText("Failed to download datasheets")
                    self.window.alt_pdf_label.setStyleSheet("color: red;")
                    self.window.set_status("Failed to download alternative datasheets. Please try again.")
                
                # Process events and keep window active
                QApplication.processEvents()
                self.window.keep_active()
                QApplication.processEvents()
                
                # If in autonomy mode, proceed to the next step after all downloads are complete
                if self.window.autonomy_mode and self.successful_downloads > 0:
                    logging.info("Autonomy mode is enabled, proceeding to compare datasheets")
                    # Force UI updates before proceeding
                    QApplication.processEvents()
                    # Call directly without timer
                    self.window.handlers.comparison_handler.handle_compare_datasheets()
                    logging.info("Called handle_compare_datasheets in autonomy mode")
                
            except Exception as e:
                error_msg = f"Error updating UI after downloads: {str(e)}"
                logging.error(error_msg)
                if not self.window.autonomy_mode:
                    QMessageBox.critical(self.window, "Error", error_msg)

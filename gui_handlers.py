import os
import logging
import PyPDF2
import requests
import re
import csv
import pandas as pd
from io import StringIO
from datetime import datetime
from PyQt5.QtWidgets import (
    QMessageBox, QInputDialog, QFileDialog, QTableWidgetItem, QApplication
)
from PyQt5.QtCore import Qt, QThread, QTimer

from api_client import get_datasheet_url, clean_pdf_url
from document_exporter import export_document
from gui_utils import find_in_spreadsheet, download_pdf, create_exports_dir
from config import config

class GuiHandlers:
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
            # Only show warning if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.warning(self.window, "Input Error", "Please enter a part name or number.")
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
                    from gui_utils import download_pdf
                    logging.info(f"Starting download of EOL PDF from {pdf_url}")
                    pdf_content = download_pdf(pdf_url, timeout=60)
                    logging.info(f"Successfully downloaded EOL PDF")
                    
                    # Save the PDF
                    filename = f"eol_{part_name}.pdf"
                    pdf_path = os.path.join(self.datasheets_dir, filename)
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    # Extract text from PDF
                    pdf_reader = PyPDF2.PdfReader(pdf_path)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    
                    # Store content and update UI
                    self.window.eol_pdf_content = text
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
                        self.handle_analyze_eol()
                        logging.info(f"Called handle_analyze_eol in autonomy mode")
                    
                except Exception as e:
                    error_msg = f"Failed to process datasheet: {str(e)}"
                    logging.error(error_msg)
                    # Only show error if not in autonomy mode
                    if not self.window.autonomy_mode:
                        QMessageBox.critical(self.window, "Error", error_msg)
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
            logging.error(error_msg)
            # Only show error if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.critical(self.window, "Error", error_msg)
            self.window.eol_pdf_label.setText("Failed to find PDF")
            self.window.eol_pdf_label.setStyleSheet("color: red;")
            self.window.status_label.setText("Failed to start datasheet search. Please try again.")

    def handle_analyze_eol(self):
        """Handle the Analyze EOL Part button click."""
        logging.info("handle_analyze_eol called")
        
        # Update progress if in autonomy mode
        if self.window.autonomy_mode:
            self.update_autonomy_progress("ANALYZE_EOL")
        if not hasattr(self.window, 'eol_pdf_content'):
            # Only show warning if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.warning(self.window, "Missing Datasheet", "Please wait for the EOL part datasheet to be downloaded.")
            return

        self.window.set_status("Analyzing EOL part datasheet...")
        self.window.results_area.setPlainText("Analyzing datasheet content...")
        logging.info("Starting EOL analysis")

        from ai_prompts import EOL_ANALYSIS_SYSTEM_PROMPT, EOL_ANALYSIS_USER_PROMPT
        messages = [
            {"role": "system", "content": EOL_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": EOL_ANALYSIS_USER_PROMPT.format(pdf_content=self.window.eol_pdf_content)}
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
            self.handle_find_alternatives()
            logging.info("Called handle_find_alternatives in autonomy mode")

    def handle_find_alternatives(self):
        """Handle the Find Alternative Parts button click."""
        logging.info("handle_find_alternatives called")
        
        # Update progress if in autonomy mode
        if self.window.autonomy_mode:
            self.update_autonomy_progress("FIND_ALTERNATIVES")
        if not self.window.eol_part_specs:
            # Only show warning if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.warning(self.window, "Missing Analysis", "Please analyze the EOL part datasheet first.")
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
        
        # Store the alternatives result
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
            # Only show warning if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.warning(self.window, "No Parts Found", "No valid part numbers found in the alternatives list.")
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
        
    def process_next_part(self):
        """Process the next part in the queue."""
        if not hasattr(self.window, 'pending_parts') or not self.window.pending_parts:
            self.window.set_status("All parts processed successfully.")
            return

        part_number = self.window.pending_parts.pop(0)
        self.window.set_status(f"Processing part {len(self.window.pending_parts) + 1}...")

        try:
            self.handle_find_part([part_number])
        except Exception as e:
            logging.error(f"Error processing part {part_number}: {str(e)}")
            self.process_next_part()
            
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
                    # Only show warning if not in autonomy mode
                    if not self.window.autonomy_mode:
                        QMessageBox.warning(self.window, "Warning", f"Failed to download datasheet for {part_number}")
                    # Continue with the next alternative even if this one failed
                
            except Exception as e:
                logging.error(f"Failed to process URL for {part_number}: {str(e)}")
                # Only show warning if not in autonomy mode
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
                    self.handle_compare_datasheets()
                    logging.info("Called handle_compare_datasheets in autonomy mode")
                
            except Exception as e:
                logging.error(f"Error updating UI after downloads: {str(e)}")
                # Only show error if not in autonomy mode
                if not self.window.autonomy_mode:
                    QMessageBox.critical(self.window, "Error", f"Error updating interface: {str(e)}")

    def handle_compare_datasheets(self):
        """Handle the Compare All Parts button click."""
        # Update progress if in autonomy mode
        if self.window.autonomy_mode:
            self.update_autonomy_progress("COMPARE_PARTS")
        if not hasattr(self.window, 'eol_pdf_content') or not self.window.alt_pdf_contents:
            # Only show warning if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.warning(self.window, "Missing Datasheets", "Please wait for all datasheets to be downloaded.")
            return

        if not self.window.relevant_specs:
            # First, determine relevant specs to compare
            self.window.set_status("Determining relevant specifications for comparison...")
            self.window.results_area.setPlainText("Analyzing datasheets to determine key specifications...")

            all_datasheets = [self.window.eol_pdf_content] + self.window.alt_pdf_contents
            from ai_prompts import SPECS_DETERMINATION_SYSTEM_PROMPT, SPECS_DETERMINATION_USER_PROMPT
            messages = [
                {"role": "system", "content": SPECS_DETERMINATION_SYSTEM_PROMPT},
                {"role": "user", "content": SPECS_DETERMINATION_USER_PROMPT.format(datasheets=all_datasheets)}
            ]

            # Ensure previous worker is cleaned up
            if hasattr(self.worker_manager, 'worker') and self.worker_manager.worker:
                self.worker_manager.cleanup_worker()
                QApplication.processEvents()

            # Create and start worker immediately without timer
            logging.info("Creating API worker for specs determination")
            model = config.get_model("specs_determination")
            self.worker_manager.create_api_worker(
                model, 
                messages, 
                self.handle_specs_determination, 
                "Determining relevant specifications...",
                window_title="Specifications Analysis"
            )
            logging.info("API worker for specs determination created")
        else:
            # If we already have relevant specs, proceed with comparison
            self.perform_comparison()

    def handle_specs_determination(self, result):
        """Handle the result of specs determination."""
        try:
            # Split the comma-separated list into individual specs
            specs = [spec.strip() for spec in result.split(',') if spec.strip()]
            if not specs:
                raise ValueError("No specifications found in the response")
            
            self.window.relevant_specs = specs
            self.perform_comparison()
        except Exception as e:
            # Only show error if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.critical(self.window, "Error", f"Failed to process specifications: {e}")
            self.window.set_status("Error determining specifications. Please try again.")
        # Cleanup will be handled by the worker's finished signal

    def perform_comparison(self):
        """Perform the actual comparison using determined specs."""
        self.window.set_status("Comparing specifications across all parts...")
        self.window.results_area.setPlainText("Analyzing and comparing all datasheets...")

        try:
            # Format the datasheets with names for better identification
            alt_datasheets_text = []
            for i, (name, content) in enumerate(zip(self.window.alt_pdf_names, self.window.alt_pdf_contents)):
                try:
                    alt_datasheets_text.append(f"Alternative {i+1} ({name}):\n{content}")
                except Exception as e:
                    self.window.set_status(f"Error processing alternative {i+1}: {str(e)}")
                    continue

            if not alt_datasheets_text:
                raise ValueError("No valid alternative datasheets could be processed")

            # Process all datasheets at once instead of batches
            from ai_prompts import COMPARISON_SYSTEM_PROMPT, COMPARISON_USER_PROMPT
            messages = [
                {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
                {"role": "user", "content": COMPARISON_USER_PROMPT.format(
                    specs=','.join(self.window.relevant_specs),
                    eol_datasheet=self.window.eol_pdf_content,
                    alt_datasheets=chr(10).join(alt_datasheets_text)
                )}
            ]

            self.window.set_status("Comparing specifications across all parts...")
            
            # Ensure previous worker is cleaned up
            if hasattr(self.worker_manager, 'worker') and self.worker_manager.worker:
                self.worker_manager.cleanup_worker()
                QApplication.processEvents()

            # Create and start worker immediately without timer
            logging.info("Creating API worker for comparison")
            model = config.get_model("comparison")
            self.worker_manager.create_api_worker(
                model, 
                messages, 
                self.handle_comparison_result,
                "Comparing all specifications...",
                window_title="Parts Comparison"
            )
            logging.info("API worker for comparison created")
                
        except Exception as e:
            # Only show error if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.critical(self.window, "Error", f"Failed to prepare comparison: {str(e)}")
            self.window.set_status("Error preparing comparison. Please try again.")
            # Cleanup will be handled by the worker's finished signal
            pass


    def handle_comparison_result(self, result):
        """Handle the result of the datasheet comparison."""
        try:
            # Verify we have a valid result with both table and analysis
            if not result or not result.strip():
                raise ValueError("Empty comparison result received")

            # Split into table and analysis sections
            parts = result.strip().split('\n\n', 2)
            if len(parts) < 2:
                raise ValueError("Comparison result missing table or analysis section")

            # Process CSV table
            table_lines = parts[0].strip().split('\n')
            if len(table_lines) < 2:  # Need at least headers and one data row
                raise ValueError("Invalid comparison table format")

            # Parse CSV data
            csv_reader = csv.reader(StringIO(parts[0]))
            table_data = list(csv_reader)

            # Set up table widget
            headers = table_data[0]
            rows = table_data[1:]
            
            self.window.comparison_table.setRowCount(len(rows))
            self.window.comparison_table.setColumnCount(len(headers))
            self.window.comparison_table.setHorizontalHeaderLabels(headers)

            # Populate table
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(value if value else 'N/A')
                    self.window.comparison_table.setItem(i, j, item)

            # Auto-adjust columns to content
            self.window.comparison_table.resizeColumnsToContents()
            self.window.comparison_table.setVisible(True)

            # Show analysis in results area
            analysis_text = '\n\n'.join(parts[1:])
            self.window.results_area.setPlainText(f"Analysis and Recommendation:\n\n{analysis_text}")

            # Update UI elements
            self.window.comparison_result = result
            self.window.export_button.setEnabled(True)
            self.window.set_status("Comparison analysis completed. Click 'Export Document' to generate report.")
            
            # Process events to ensure UI updates
            QApplication.processEvents()
            
            # Keep the main window active
            self.window.keep_active()
            QApplication.processEvents()
            
            # If in autonomy mode, proceed to the next step
            if self.window.autonomy_mode:
                logging.info("Autonomy mode is enabled, proceeding to export document")
                # Force UI updates before proceeding
                QApplication.processEvents()
                # Update progress
                self.update_autonomy_progress("EXPORT")
                # Call directly without timer
                self.handle_export_document()
                logging.info("Called handle_export_document in autonomy mode")
        
        except Exception as e:
            error_msg = f"Failed to process comparison result: {str(e)}"
            logging.error(error_msg)
            # Only show error if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.critical(self.window, "Error", error_msg)
            self.window.set_status("Error processing comparison result. Please try again.")
            # Keep the main window active
            self.window.keep_active()
            
    def handle_export_document(self):
        """Handle the Export Document button click."""
        try:
            # Verify we have comparison data
            if not hasattr(self.window, 'comparison_result') or not self.window.comparison_result.strip():
                QMessageBox.warning(self.window, "Missing Data", "Please complete the comparison analysis before exporting.")
                return

            if not self.prompt_user_info():
                return

            # In autonomy mode, use a default file path in the exports directory
            if self.window.autonomy_mode:
                # Get part name for the file name
                part_name = self.window.input_field.text().strip()
                # Create a timestamp for uniqueness
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Create the exports directory if it doesn't exist
                exports_dir = create_exports_dir()
                # Create a default file path in the exports directory
                file_path = os.path.join(exports_dir, f"EOL_Report_{part_name}_{timestamp}.docx")
                logging.info(f"Autonomy mode: Using default file path: {file_path}")
            else:
                # In normal mode, prompt the user for a file path
                file_path, _ = QFileDialog.getSaveFileName(self.window, "Save File", "", "Word Documents (*.docx)")
                if not file_path:
                    return

            # Export the document and chat log using the document_exporter module
            # Include the alternatives text in the export
            export_document(
                file_path, 
                self.window.requester_info, 
                self.window.comparison_result, 
                self.worker_manager,
                alternatives_text=self.window.alternatives_specs
            )
            chat_log_path = file_path.rsplit('.', 1)[0] + '_chat_log.txt'
            
            # Update progress to complete if in autonomy mode
            if self.window.autonomy_mode:
                # Explicitly set progress bar to 100% and update text
                logging.info("Setting progress bar to 100% - Process complete")
                self.update_autonomy_progress("COMPLETE")
                
                # Update status message
                self.window.set_status("Process complete. Document exported successfully.")
                
                # Force immediate UI updates
                QApplication.processEvents()
                self.window.keep_active()
                QApplication.processEvents()
                
                # Log completion
                logging.info(f"Autonomy mode: Document saved at {file_path}, chat log saved at {chat_log_path}")
                
                # Add a delay before proceeding to next part
                def delayed_next_part():
                    logging.info("Delayed next part processing starting")
                    self.process_next_part()
                
                # Use QTimer for the delay
                QTimer.singleShot(2000, delayed_next_part)  # 2 second delay
            else:
                # Only show success message if not in autonomy mode
                QMessageBox.information(self.window, "Success", 
                    f"Document saved at {file_path}\nChat log saved at {chat_log_path}")
                # Process next part immediately in manual mode
                self.process_next_part()

        except Exception as e:
            error_msg = f"Failed to export document: {str(e)}"
            logging.error(error_msg)
            # Only show error if not in autonomy mode
            if not self.window.autonomy_mode:
                QMessageBox.critical(self.window, "Error", error_msg)
                
    def prompt_user_info(self):
        """Prompt the user for required information to export the document."""
        # Get current date
        current_date = datetime.now().strftime("%d/%m/%Y")
        
        # Get part details
        part_name = self.window.input_field.text().strip()
        spreadsheet_data = {"Description": part_name, "Item_Code": part_name}
        
        # Pre-fill known information
        self.window.requester_info = {
            "Date": current_date,
            "EOL Part Name": spreadsheet_data.get('Description', ''),
            "EOL Part Number": spreadsheet_data.get('Item_Code', '')
        }
        
        # Check if we have saved user info from previous exports
        if hasattr(self.window, 'saved_user_info'):
            # Use saved info to pre-fill user-specific fields
            for field, value in self.window.saved_user_info.items():
                if field not in self.window.requester_info:
                    self.window.requester_info[field] = value
        
        # In autonomy mode, use default values for all required fields
        if self.window.autonomy_mode:
            # Create a dictionary to store user info for future use if it doesn't exist
            if not hasattr(self.window, 'saved_user_info'):
                self.window.saved_user_info = {}
                
            # Set default values for required fields if not already set
            required_fields = {
                "Name": "Auto Generated",
                "Department": "Auto Generated",
                "Position": "Auto Generated",
                "Description": part_name,
                "Work Order": "Auto Generated",
                "Reason for Replacement": "End of Life Replacement",
            }
            
            for field, default_value in required_fields.items():
                if field not in self.window.requester_info or not self.window.requester_info[field]:
                    self.window.requester_info[field] = default_value
                    # Save for future use
                    self.window.saved_user_info[field] = default_value
                elif field not in self.window.saved_user_info:
                    # Save existing values for future use
                    self.window.saved_user_info[field] = self.window.requester_info[field]
            
            return True
        
        # Only prompt for user-specific information in non-autonomy mode
        required_fields = {
            "Name": "Enter your name:",
            "Department": "Enter your department:",
            "Position": "Enter your position:",
            "Description": "Enter the part description:",
            "Work Order": "Enter the work order number:",
            "Reason for Replacement": "Why does the part need replacing?",
        }

        # Create a dictionary to store user info for future use
        if not hasattr(self.window, 'saved_user_info'):
            self.window.saved_user_info = {}

        for field, prompt in required_fields.items():
            if field not in self.window.requester_info or not self.window.requester_info[field]:
                text, ok = QInputDialog.getText(self.window, "Missing Information", prompt)
                if ok and text.strip():
                    self.window.requester_info[field] = text.strip()
                    # Save for future use
                    self.window.saved_user_info[field] = text.strip()
                else:
                    QMessageBox.warning(self.window, "Input Missing", f"{field} is required to proceed.")
                    return False
            elif field not in self.window.saved_user_info:
                # Save existing values for future use
                self.window.saved_user_info[field] = self.window.requester_info[field]
                
        return True

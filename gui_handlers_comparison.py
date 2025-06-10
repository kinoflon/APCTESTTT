import os
import logging
import csv
from io import StringIO
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QApplication, QInputDialog, QFileDialog, QTableWidgetItem
from PyQt5.QtCore import QTimer

from document_exporter import export_document
from gui_utils import create_exports_dir
from gui_handlers_base import BaseGuiHandler
from config import config

class ComparisonHandler(BaseGuiHandler):
    """Handler for comparing parts and exporting results."""
    
    def handle_compare_datasheets(self):
        """Handle the Compare All Parts button click."""
        # Update progress if in autonomy mode
        if self.window.autonomy_mode:
            self.update_autonomy_progress("COMPARE_PARTS")
            
        if not hasattr(self.window, 'eol_pdf_content') or not self.window.alt_pdf_contents:
            self.show_warning("Missing Datasheets", "Please wait for all datasheets to be downloaded.")
            return

        if not hasattr(self.window, 'relevant_specs') or not self.window.relevant_specs:
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
        DEFAULT_SPECS = [
            "Input Voltage Range", "Output Voltage Range", "Maximum Output Current", 
            "Switching Frequency", "Package Type", "Operating Temperature Range", 
            "Efficiency", "Quiescent Current", "Key Feature 1", "Key Feature 2"
        ]
        try:
            specs = []
            if result and result.strip():
                # Split the comma-separated list into individual specs
                specs = [spec.strip() for spec in result.split(',') if spec.strip()]
            
            if not specs:
                logging.warning(f"API did not return a valid list of specifications. Raw result: '{result}'. Falling back to default specs.")
                self.window.set_status("Could not determine specs from API, using default specs for comparison.")
                QApplication.processEvents() # Ensure status update is visible
                specs = DEFAULT_SPECS
            
            if not specs: # Should not happen if DEFAULT_SPECS is defined
                raise ValueError("No specifications found in the response and no default specs available.")

            self.window.relevant_specs = specs
            self.perform_comparison()
        except Exception as e:
            error_msg = f"Failed to process specifications: {e}. Falling back to default specs."
            logging.error(error_msg, exc_info=True)
            self.show_error("Specs Determination Error", f"{error_msg}\nUsing default specifications.")
            self.window.set_status("Error determining specifications. Using default specs.")
            QApplication.processEvents() # Ensure status update is visible
            self.window.relevant_specs = DEFAULT_SPECS # Use default on error too
            if not self.window.relevant_specs: # Final check
                 self.show_error("Critical Error", "Default specifications are missing. Cannot proceed.")
                 self.window.set_status("Critical error: Default specs missing.")
                 return
            self.perform_comparison() # Attempt to proceed with default specs
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
            error_msg = f"Failed to prepare comparison: {str(e)}"
            self.show_error("Error", error_msg)
            self.window.set_status("Error preparing comparison. Please try again.")
            # Cleanup will be handled by the worker's finished signal

    def handle_comparison_result(self, result):
        """Handle the result of the datasheet comparison."""
        try:
            # Verify we have a valid result with both table and analysis
            if not result or not result.strip():
                logging.error(f"Received empty or whitespace-only comparison result: '{result}'")
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
            self.show_error("Error", error_msg)
            self.window.set_status("Error processing comparison result. Please try again.")
            # Keep the main window active
            self.window.keep_active()

    def handle_export_document(self):
        """Handle the Export Document button click."""
        try:
            # Verify we have comparison data
            if not hasattr(self.window, 'comparison_result') or not self.window.comparison_result.strip():
                self.show_warning("Missing Data", "Please complete the comparison analysis before exporting.")
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
                self.window.autonomy_progress_bar.setValue(100)
                self.window.autonomy_stage_label.setText("Process complete")
                
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
            error_msg = f"Failed to export document: {e}"
            self.show_error("Error", error_msg)

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
                    self.show_warning("Input Missing", f"{field} is required to proceed.")
                    return False
            elif field not in self.window.saved_user_info:
                # Save existing values for future use
                self.window.saved_user_info[field] = self.window.requester_info[field]
                
        return True

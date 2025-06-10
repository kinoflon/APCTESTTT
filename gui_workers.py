import logging
import openai # Keep for openai.error types if api_client.ApiWorker still raises them
# import uuid # Not used, consider removing if not needed elsewhere after this change
from PyQt5.QtCore import QThread, pyqtSignal # QThread might not be needed if ApiWorker is imported
from PyQt5.QtWidgets import QProgressDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Import the robust ApiWorker from api_client.py
from api_client import ApiWorker

# The ApiWorker class previously defined here is now removed.

class WorkerManager:
    """Manages worker threads, progress dialogs, and chat windows."""
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.worker = None
        self.progress_dialog = None
        self.conversation_contexts = []  # Store all conversation contexts in order

    def create_api_worker(self, model, messages, result_handler, status_message, conversation_id=None, window_title=None):
        """Create and start an API worker."""
        try:
            # Store conversation context without displaying
            self.conversation_contexts.append({
                "title": window_title or status_message,
                "model": model,
                "messages": messages
            })

            # Create worker
            # Get the root logger configured in main.py or use a specific logger
            app_logger = logging.getLogger() # Or logging.getLogger(__name__) or specific logger
            self.worker = ApiWorker(model, messages, logger=app_logger)
            
            # Connect signals in specific order
            # 1. First connect the result and error handlers
            self.worker.finished_signal.connect(lambda result: self.handle_api_result(result, result_handler))
            self.worker.error_signal.connect(self.handle_api_error)
            self.worker.progress_signal.connect(self.update_progress)
            
            # 2. Connect cleanup to finished_signal instead of finished
            self.worker.finished_signal.connect(lambda _: self.cleanup_worker())

            # Create and show progress dialog
            self.progress_dialog = QProgressDialog("Processing request...", "Cancel", 0, 100, self.parent)
            self.progress_dialog.setWindowTitle("Please Wait")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setMinimumDuration(0)
            self.progress_dialog.setValue(0)
            self.progress_dialog.canceled.connect(self.cancel_worker)

            self.worker.start()
            self.progress_dialog.show()
            logging.info(f"API worker created and started. Model: {model}, Status: {status_message}")

            return conversation_id

        except Exception as e:
            error_message = f"Failed to create API worker: {str(e)}"
            logging.error(error_message)
            QMessageBox.critical(self.parent, "Error", error_message)

    def update_progress(self, value):
        """Update the progress dialog."""
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.setValue(value)
        QApplication.processEvents()  # Ensure UI updates are processed

    def cancel_worker(self):
        """Cancel the worker and clean up."""
        self.cleanup_worker()

    def handle_api_result(self, result, result_handler):
        """Handle successful API response."""
        # Update latest conversation context
        if self.conversation_contexts:
            self.conversation_contexts[-1]["messages"].append({
                "role": "assistant",
                "content": result
            })
        
        # Process events to ensure UI updates
        QApplication.processEvents()
        
        # Call the original result handler
        result_handler(result)
        
        # Process events again after result handler
        QApplication.processEvents()

    def handle_api_error(self, error_message):
        """Handle API errors."""
        QMessageBox.critical(self.parent, "API Error", error_message)
        # Add error to conversation context
        if self.conversation_contexts:
            self.conversation_contexts[-1]["messages"].append({
                "role": "system",
                "content": f"Error: {error_message}"
            })
        print(f"API Error: {error_message}")
        
    def export_chat_log(self, file_path):
        """Export all conversations to a text file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for context in self.conversation_contexts:
                    # Write conversation title and model
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Conversation: {context['title']}\n")
                    f.write(f"Model: {context['model']}\n")
                    f.write(f"{'='*80}\n\n")
                    
                    # Write all messages
                    for msg in context['messages']:
                        role = msg['role'].capitalize()
                        content = msg['content'].replace('\n', '\n    ')  # Indent content
                        f.write(f"{role}:\n    {content}\n\n")
                    
                    f.write(f"\n{'='*80}\n")  # Separator between conversations
            return True
        except Exception as e:
            logging.error(f"Failed to export chat log: {str(e)}")
            return False

    def cleanup_worker(self):
        """Clean up the worker thread and progress dialog."""
        try:
            # Store reference to current worker and progress dialog
            worker = self.worker
            dialog = self.progress_dialog
            
            # Clear references immediately to prevent new operations
            self.worker = None
            self.progress_dialog = None
            
            # Process any pending events
            QApplication.processEvents()

            # Close progress dialog if it exists
            if dialog:
                try:
                    dialog.close()
                    dialog.deleteLater()
                except Exception as e:
                    logging.error(f"Error closing dialog: {str(e)}")

            # Handle worker thread if it exists
            if worker:
                try:
                    # Stop the worker
                    if hasattr(worker, 'stop'):
                        worker.stop()
                    
                    # Wait for the worker to finish
                    if worker.isRunning():
                        if not worker.wait(2000):  # Wait up to 2 seconds
                            worker.terminate()
                            worker.wait()
                    
                    # Schedule worker for deletion
                    worker.deleteLater()
                except Exception as e:
                    logging.error(f"Error stopping worker: {str(e)}")
                    try:
                        worker.terminate()
                        worker.wait()
                    except:
                        pass

            # Final event processing
            QApplication.processEvents()

        except Exception as e:
            logging.error(f"Error during worker cleanup: {str(e)}")
            # Ensure references are cleared even if cleanup fails
            self.worker = None
            self.progress_dialog = None

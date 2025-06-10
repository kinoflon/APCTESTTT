import sys
import logging
import os
import atexit
from PyQt5.QtWidgets import QApplication
from gui_main import MainWindow

# Define an absolute path for the log file
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')

# Set up logging with more detailed debug information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s', # Added logger name
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file_path, mode='w') # Use absolute path, mode 'w' to overwrite
    ],
    force=True  # Force reconfiguration if already configured
)

# Get the root logger
root_logger = logging.getLogger()
# Ensure all handlers are attached to the root logger
# (basicConfig should do this, but being explicit can help in complex scenarios)
if not root_logger.handlers:
    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_file_path, mode='w')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)


def logging_cleanup():
    logging.info("Application exiting, flushing logs.")
    for handler in logging.getLogger().handlers:
        handler.flush()
        handler.close()

atexit.register(logging_cleanup)

def handle_thread_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions in QThread"""
    logging.error("Uncaught exception in thread:", exc_info=(exc_type, exc_value, exc_traceback))

def main():
    # Set exception handler for threads
    # Note: sys.excepthook is for the main thread. For QThreads, you might need a different approach
    # if they don't propagate exceptions to the main thread in a way that excepthook catches them.
    # However, the QThread itself should ideally handle its exceptions and log them.
    sys.excepthook = handle_thread_exception
    """Main entry point of the application."""
    try:
        logging.info("Starting application")
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        logging.info("Application window shown")
        sys.exit(app.exec_())
    except Exception as e:
        logging.exception("Application failed to start")
        sys.exit(1)

if __name__ == "__main__":
    main()

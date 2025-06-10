import os
import sys
import logging
import re # For filename sanitization
import base64 # Added for PDF encoding
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Wrapper function for logging exceptions
def log_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.exception(f"Exception in {func.__name__}: {str(e)}")
            raise
    return wrapper

def encode_pdf_to_base64(pdf_path):
    """Encode a PDF file to a base64 string."""
    try:
        with open(pdf_path, "rb") as pdf_file:
            return base64.b64encode(pdf_file.read()).decode('utf-8')
    except FileNotFoundError:
        logging.error(f"PDF file not found at path: {pdf_path}")
        raise
    except Exception as e:
        logging.error(f"Error encoding PDF {pdf_path} to base64: {e}")
        raise

def sanitize_filename(filename_str):
    """
    Sanitizes a string to be used as a filename by removing or replacing
    characters that are typically not allowed in filenames on common OSes.
    """
    if not isinstance(filename_str, str):
        filename_str = str(filename_str)
    
    # Remove or replace characters illegal in Windows filenames
    # Illegal characters: < > : " / \ | ? *
    # Also, control characters (0-31) are problematic.
    # We'll replace them with an underscore.
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename_str)
    
    # Replace multiple underscores with a single one
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores or whitespace that might have been created
    sanitized = sanitized.strip('_ ')
    
    # Limit filename length (optional, but good practice)
    # Max path length on Windows is 260, so keep filenames reasonable.
    # This doesn't account for directory path, just the filename part.
    max_len = 100
    if len(sanitized) > max_len:
        name, ext = os.path.splitext(sanitized)
        name = name[:max_len - len(ext) -1] # -1 for the dot
        sanitized = name + ext

    if not sanitized: # If the name becomes empty after sanitization
        sanitized = "sanitized_empty_filename"
        
    return sanitized

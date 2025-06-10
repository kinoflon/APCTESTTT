# Combined single-file version of the EOL Parts Replacement Finder
# This file aggregates all modules from the original project.

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
# End of utils.py
import sys
import os
import logging
import pandas as pd
import requests
from urllib.parse import urlparse

def find_in_spreadsheet(df, search_term):
    """Find a part in the spreadsheet data."""
    if df is None:
        return None
    
    # Search in Item_Code and Description columns
    mask = df['Item_Code'].str.contains(search_term, case=False, na=False) | \
           df['Description'].str.contains(search_term, case=False, na=False)
    
    matches = df[mask]
    if len(matches) > 0:
        # Return the first match as a dictionary
        return matches.iloc[0].to_dict()
    return None

def load_spreadsheet():
    """
    This function previously loaded the Ostendo stock list spreadsheet.
    Now it returns None as the spreadsheet lookup has been removed.
    """
    logging.info("Spreadsheet lookup has been removed from the application")
    return None


def create_datasheets_dir():
    """Create the datasheets directory if it doesn't exist, using resource_path for PyInstaller compatibility."""
    # For PyInstaller, 'datasheets' will be a path inside the _MEIPASS temp folder or relative to exe if not onefile
    datasheets_dir = resource_path('datasheets')
    
    # Ensure the directory exists. In a one-file bundle, resource_path might point to a
    # directory that doesn't exist yet if it's the first run and it's meant to be writable.
    # However, for bundled 'datas' in PyInstaller, they are typically read-only.
    # If we intend to WRITE to this 'datasheets' dir, it should NOT be bundled as a data file
    # in the .spec but rather created in a user-writable location (e.g., AppData or next to exe).
    # Given the current .spec, 'datasheets' IS bundled. This means it's read-only.
    # The current logic of saving downloaded PDFs into this 'datasheets_dir' will fail
    # if it's pointing to the read-only bundled location.
    
    # For a one-file app, if we need a *writable* datasheets directory,
    # it should be created relative to the executable or in a user's app data folder.
    # Let's assume for now the intention is to have a writable 'datasheets' folder
    # *next to the executable* if it's a one-folder build, or in a temp location if one-file.
    # The `resource_path` handles the _MEIPASS scenario correctly for *reading* bundled files.
    # If `sys._MEIPASS` is not set (e.g. running from .py), it resolves to `os.path.abspath(".")`.
    
    # If the path from resource_path (potentially in _MEIPASS) is not writable,
    # or if we always want a user-accessible datasheets dir, we should choose a different base.
    # A common strategy for writable data for a frozen app:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle (onefile or onedir)
        # Create datasheets next to the executable for onedir, or handle for onefile
        # For onefile, _MEIPASS is temporary. We need a persistent writable location.
        # Let's create it in the user's documents or appdata, or simply next to where the .exe *appears* to be.
        # For simplicity, let's try creating it next to where the .exe is run from,
        # which might be different from where it's stored if it's a one-file temp extraction.
        # A safer bet for user-writable data is app data.
        app_data_path = os.path.join(os.path.expanduser('~'), 'EOL_App_Data')
        datasheets_dir_writable = os.path.join(app_data_path, 'datasheets')
        if not os.path.exists(app_data_path):
            os.makedirs(app_data_path, exist_ok=True)
        logging.info(f"Using writable datasheets directory for bundled app: {datasheets_dir_writable}")
    else:
        # Running as a script, use local 'datasheets' directory
        datasheets_dir_writable = os.path.join(os.path.abspath("."), 'datasheets')
        logging.info(f"Using local datasheets directory for script: {datasheets_dir_writable}")

    os.makedirs(datasheets_dir_writable, exist_ok=True)
    return datasheets_dir_writable

def create_exports_dir():
    """Create the exports directory if it doesn't exist, ensuring PyInstaller compatibility."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        app_data_path = os.path.join(os.path.expanduser('~'), 'EOL_App_Data')
        exports_dir = os.path.join(app_data_path, 'exports')
        if not os.path.exists(app_data_path):
            os.makedirs(app_data_path, exist_ok=True)
        logging.info(f"Using writable exports directory for bundled app: {exports_dir}")
    else:
        exports_dir = os.path.join(os.path.abspath("."), 'exports')
        logging.info(f"Using local exports directory for script: {exports_dir}")
    os.makedirs(exports_dir, exist_ok=True)
    return exports_dir

def download_pdf(url, timeout=60):
    """
    Download a PDF with appropriate headers based on the source website.
    Returns the response content if successful, raises an exception if failed.
    """
    # Common browser headers
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'DNT': '1'
    }

    # Get the domain from the URL
    domain = urlparse(url).netloc.lower()

    # Special headers for specific websites
    site_specific_headers = {
        'mouser.com': {
            **default_headers,
            'Referer': 'https://www.mouser.com/',
            'Origin': 'https://www.mouser.com'
        },
        'digikey.com': {
            **default_headers,
            'Referer': 'https://www.digikey.com/',
            'Origin': 'https://www.digikey.com'
        },
        'arrow.com': {
            **default_headers,
            'Referer': 'https://www.arrow.com/',
            'Origin': 'https://www.arrow.com'
        }
    }

    # Select appropriate headers
    headers = None
    for site, site_headers in site_specific_headers.items():
        if site in domain:
            headers = site_headers
            break
    if headers is None:
        headers = default_headers
    
    # List of domains with known SSL certificate issues
    ssl_verify_exceptions = [
        'ibase.com.tw',
        'ibase.com'
    ]
    
    # Determine if we should verify SSL for this domain
    verify_ssl = domain not in ssl_verify_exceptions
    
    if not verify_ssl:
        logging.warning(f"Disabling SSL verification for {domain} due to known certificate issues")

    # Try to download with headers
    try:
        response = requests.get(url, headers=headers, timeout=timeout, verify=verify_ssl)
        response.raise_for_status()
        
        # Verify it's a PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
            raise ValueError(f"Response is not a PDF (Content-Type: {content_type})")
        
        return response.content
    except requests.exceptions.RequestException as e:
        # Log the full error details
        logging.error(f"Failed to download PDF from {url}: {str(e)}")
        logging.error(f"Response headers: {getattr(e.response, 'headers', 'No headers')}")
        logging.error(f"Response status code: {getattr(e.response, 'status_code', 'No status code')}")
        
        # If we get an SSL error and we haven't already disabled verification, try again without SSL verification
        if isinstance(e, requests.exceptions.SSLError) and verify_ssl:
            logging.warning(f"SSL error encountered, retrying without SSL verification for {url}")
            try:
                response = requests.get(url, headers=headers, timeout=timeout, verify=False)
                response.raise_for_status()
                
                # Verify it's a PDF
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
                    raise ValueError(f"Response is not a PDF (Content-Type: {content_type})")
                
                # Add this domain to the list of SSL exceptions for future reference
                if domain not in ssl_verify_exceptions:
                    logging.info(f"Adding {domain} to SSL verification exceptions for future downloads")
                
                return response.content
            except requests.exceptions.RequestException as retry_e:
                logging.error(f"Failed to download PDF even without SSL verification: {str(retry_e)}")
                raise retry_e
        raise
# End of gui_utils.py
from docx import Document
from docx.shared import Inches
import csv
from io import StringIO
import logging

def export_document(file_path, requester_info, comparison_result, worker_manager=None, alternatives_text=None):
    """Export the data to a formatted Word document file and save chat log.
    
    Args:
        file_path: Path to save the document
        requester_info: Dictionary containing requester information
        comparison_result: String containing the comparison result
        worker_manager: WorkerManager instance for exporting chat log
        alternatives_text: String containing the suggested alternatives text
    """
    doc = Document()
    
    # Title
    title = doc.add_heading("EOL Part Replacement Suggestion Form", level=1)
    title.alignment = 1  # Center alignment

    # Function to add centered section headers
    def add_section_header(text):
        header = doc.add_heading(text, level=2)
        header.alignment = 1
        
    # Function to add horizontal line
    def add_horizontal_line():
        paragraph = doc.add_paragraph()
        paragraph.add_run('_' * 100)
        paragraph.alignment = 1
        doc.add_paragraph()  # Add space after line

    # Section 1: Requester Information
    add_section_header("Section 1: Requester Information")
    for field in ["Name", "Department", "Position", "Date"]:
        value = requester_info.get(field, "")
        doc.add_paragraph(f"{field}: {value}")
    add_horizontal_line()

    # Section 2: EOL Part Details
    add_section_header("Section 2: EOL Part Details")
    eol_fields = [
        "EOL Part Name", "EOL Part Number", "Description", "Work Order",
        "Reason for Replacement"
    ]
    for field in eol_fields:
        value = requester_info.get(field, "")
        if field in ["Description", "Work Order"]:
            doc.add_paragraph(f"{field}:")
            doc.add_paragraph(value, style='List Bullet')
        else:
            doc.add_paragraph(f"{field}: {value}")
    add_horizontal_line()

    # Section 3: Comparison Table
    add_section_header("Section 3: Comparison Table")
    parts = comparison_result.split('\n\n', 2)
    if len(parts) >= 2:
        csv_table = parts[0]
        try:
            csv_reader = csv.reader(StringIO(csv_table))
            table_data = list(csv_reader)

            if table_data:
                # Transpose the table data
                transposed_data = list(zip(*table_data))
                
                # Create the table with transposed dimensions
                table = doc.add_table(rows=len(transposed_data), cols=len(transposed_data[0]))
                table.style = 'Table Grid'

                for i, row in enumerate(transposed_data):
                    for j, cell_value in enumerate(row):
                        cell = table.cell(i, j)
                        cell.text = cell_value.strip()
                        if j == 0:  # Bold the first column (specs)
                            for paragraph in cell.paragraphs:
                                for run in paragraph.runs:
                                    run.bold = True
                table.autofit = True
            else:
                doc.add_paragraph("No data available for comparison table.")
        except Exception as e:
            doc.add_paragraph(f"Error creating table: {str(e)}")
    else:
        doc.add_paragraph("No comparison table data available.")
    add_horizontal_line()

    # Section 4: Comparison Summary
    add_section_header("Section 4: Comparison Summary")
    if len(parts) >= 2:
        analysis_text = '\n\n'.join(parts[1:])  # Join all remaining parts
        paragraphs = analysis_text.split('\n')
        for paragraph in paragraphs:
            if paragraph.strip():  # Only add non-empty paragraphs
                doc.add_paragraph(paragraph.strip())
    else:
        doc.add_paragraph("No analysis and recommendation available.")
    add_horizontal_line()
    
    # Section 5: Suggested Alternatives
    add_section_header("Section 5: Suggested Alternatives")
    if alternatives_text and alternatives_text.strip():
        # Add the alternatives text
        paragraphs = alternatives_text.split('\n')
        for paragraph in paragraphs:
            if paragraph.strip():  # Only add non-empty paragraphs
                doc.add_paragraph(paragraph.strip())
    else:
        doc.add_paragraph("No suggested alternatives available.")
    add_horizontal_line()

    # Section 6: Additional Comments
    add_section_header("Section 6: Additional Comments")
    doc.add_paragraph("[User can add comments here after export]")
    for _ in range(5):
        doc.add_paragraph("_" * 50)
    add_horizontal_line()

    # Section 7: Signatures
    add_section_header("Section 7: Signatures")
    doc.add_paragraph("Procurement Manager:")
    doc.add_paragraph("Name: ____________________")
    doc.add_paragraph("Signature: ____________________")
    doc.add_paragraph("Date: ____________________")
    doc.add_paragraph()
    doc.add_paragraph("Engineering Reviewer:")
    doc.add_paragraph("Name: ____________________")
    doc.add_paragraph("Signature: ____________________")
    doc.add_paragraph("Date: ____________________")

    # Save the document
    doc.save(file_path)
    
    # Save chat log if worker_manager is provided
    if worker_manager:
        # Create chat log filename by replacing .docx with .txt
        chat_log_path = file_path.rsplit('.', 1)[0] + '_chat_log.txt'
        if worker_manager.export_chat_log(chat_log_path):
            logging.info(f"Chat log saved to: {chat_log_path}")
        else:
            logging.error("Failed to save chat log")
# End of document_exporter.py
"""
This module contains all AI prompts used throughout the application.
"""

# Datasheet URL finder prompt
DATASHEET_URL_BASE_PROMPT = """
Find the direct PDF download URL for the datasheet of the "{part_number}" electronic component.

Search reputable sources such as:
- Official manufacturer's website
- Well-known electronics distributors (e.g., Digi-Key, Mouser)
- Other verified sources

Requirements:
- URL must point directly to the PDF file (ending with ".pdf")
- URL must be verified as correct
- Provide only the direct PDF URL with no additional text or explanation
"""

# EOL Analysis prompts
EOL_ANALYSIS_SYSTEM_PROMPT = """
You are an expert in electronic components. 
Analyze the provided datasheet and extract detailed specifications.
"""

EOL_ANALYSIS_USER_PROMPT = """
Please analyze the provided datasheet (sent as a file) and provide a comprehensive list of specifications.

Include:
- Physical specifications
- Electrical characteristics
- Operating conditions
- Other relevant details

Focus on extracting structured data suitable for comparison.
"""

# Alternative parts prompts
ALTERNATIVES_SYSTEM_PROMPT = """
You are an expert in electronic components.
Suggest suitable alternative parts based on the specifications.
"""

ALTERNATIVES_USER_PROMPT = """
Based on these specifications, suggest up to 5 alternative parts that could serve as replacements.
Note: Please suggest no more than 5 alternatives to ensure efficient processing.

IMPORTANT: Format your response as a simple numbered list, with each line starting with a number followed by a period and the part number, like this:
1. Part123
2. Part456
3. Part789

Do not provide explanations for each part. Do not include any additional text.
Do not include any URLs or links.

Original specifications:
{specs}
"""

# Deep search version for alternatives
DEEP_ALTERNATIVES_USER_PROMPT = """
Based on these specifications, suggest up to 12 alternative parts that could serve as replacements.
Provide a comprehensive list of alternatives from various manufacturers.

IMPORTANT: Format your response as a simple numbered list, with each line starting with a number followed by a period and the part number, like this:
1. Part123
2. Part456
3. Part789
...
20. Part999

Do not provide explanations for each part.

Original specifications:
{specs}
"""

# Specs determination prompt
SPECS_DETERMINATION_SYSTEM_PROMPT = """
You are an expert in electronic components analysis.
Your task is to determine the most relevant specifications for comparing these electronic components.
Return ONLY a comma-separated list of specification names, nothing else.
"""

SPECS_DETERMINATION_USER_PROMPT = """
Analyze these datasheets and list the 10-20 most important specifications for comparison.

Focus on:
- Critical parameters affecting compatibility
- Key performance indicators
- Essential operating characteristics

Format: Return ONLY a comma-separated list of specification names.

Datasheets to analyze:
{datasheets}
"""

# Comparison prompt
COMPARISON_SYSTEM_PROMPT = """
You are an expert in electronic components analysis.
Your task is to compare an EOL (End of Life) component with its potential alternatives.

Output Format Requirements:
1. First output a comparison table in CSV format:
   - First row must be: Part Name,{specs}
   - First data row MUST be the EOL part
   - Following rows are the alternative parts
   - Use consistent units
   - Use 'N/A' for missing data
   - No text between rows

2. After the CSV table, leave one blank line then provide:
   - Analysis of key differences
   - Compatibility considerations
   - Clear recommendation for best alternative

Keep responses focused and concise.
"""

COMPARISON_USER_PROMPT = """
Compare these components and provide a CSV table followed by analysis.

Specifications to compare:
{specs}

EOL Component:
{eol_datasheet}

Alternative Components:
{alt_datasheets}

Remember:
1. Start with CSV table
2. Leave blank line
3. Provide analysis and recommendation
"""
# End of ai_prompts.py
"""Configuration settings for the EOL Parts Replacement Finder application."""
import os
import json
import logging

class Config:
    """Configuration class for the application."""
    
    def __init__(self):
        """Initialize the configuration with default values."""
        # Default model settings
        self.models = {
            # Model for analyzing EOL part datasheets
            "eol_analysis": "google/gemini-2.5-flash-preview:online",
            
            # Model for finding alternative parts
            "alternatives_search": "google/gemini-2.5-flash-preview:online",
            
            # Model for searching for datasheets
            "datasheet_search": "perplexity/llama-3.1-sonar-large-128k-online",
            
            # Model for determining relevant specifications
            "specs_determination": "google/gemini-2.5-pro-preview",
            
            # Model for comparing parts
            "comparison": "google/gemini-2.5-pro-preview"
        }
        
        # API keys
        self.api_keys = {
            "openrouter": "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"
        }
        
        # Try to load configuration from file
        self.load_config()
    
    def load_config(self):
        """Load configuration from config.json if it exists."""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Update models if present in config
                if 'models' in config_data:
                    self.models.update(config_data['models'])
                
                # Update API keys if present in config
                if 'api_keys' in config_data:
                    self.api_keys.update(config_data['api_keys'])
                
                logging.info("Configuration loaded from config.json")
            except Exception as e:
                logging.error(f"Error loading configuration: {str(e)}")
    
    def save_config(self):
        """Save current configuration to config.json."""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        try:
            config_data = {
                'models': self.models,
                'api_keys': self.api_keys
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logging.info("Configuration saved to config.json")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get_model(self, task):
        """Get the model to use for a specific task."""
        return self.models.get(task, self.models.get("eol_analysis"))  # Default to eol_analysis model
    
    def set_model(self, task, model):
        """Set the model to use for a specific task."""
        self.models[task] = model
        return self.save_config()
        
    def get_api_key(self, service):
        """Get the API key for a specific service."""
        return self.api_keys.get(service, "")
    
    def set_api_key(self, service, key):
        """Set the API key for a specific service."""
        self.api_keys[service] = key
        return self.save()
        
    def save(self):
        """Save the current configuration."""
        return self.save_config()

# Create a singleton instance
config = Config()
# End of config.py
import logging
# logger = logging.getLogger(__name__) # Removed from module level
import requests
import re
import openai
from PyQt5.QtCore import QThread, pyqtSignal

# Import configuration

# Configure OpenRouter API and Endpoint
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = config.get_api_key("openrouter")

# Set the API key
openai.api_key = "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"
# Save the key to the configuration
config.set_api_key("openrouter", openai.api_key)
config.save()

def clean_pdf_url(url):
    """Clean up PDF URL by removing reference numbers and extra characters."""
    # Remove reference numbers in square brackets (e.g., [4])
    url = re.sub(r'\[\d+\]$', '', url)
    # Remove any other common reference patterns that might appear
    url = re.sub(r'\(\d+\)$', '', url)
    # Remove any trailing special characters
    url = re.sub(r'[^\w\-\.\/\:]$', '', url)
    return url.strip()

def get_datasheet_url(part_number, description, worker_manager):
    """Get datasheet URL using AI with multiple attempts."""
    if not worker_manager:
        raise ValueError("Worker manager is required for datasheet URL retrieval")

    # List of major electronic component distributors
    distributors = [
        "Digi-Key (www.digikey.com)",
        "Mouser Electronics (www.mouser.com)",
        "Arrow Electronics (www.arrow.com)",
        "Newark/Farnell (www.newark.com)",
        "RS Components (www.rs-online.com)",
        "TME (www.tme.eu)",
        "Future Electronics (www.futureelectronics.com)"
    ]

    # Import and use prompt from ai_prompts.py
    base_prompt = DATASHEET_URL_BASE_PROMPT.format(part_number=part_number)

    # Add distributor suggestions
    base_prompt += "\n\nPlease check these distributor websites:"
    for distributor in distributors[:3]:  # Start with first 3 distributors
        base_prompt += f"\n- {distributor}"

    messages = [{"role": "user", "content": base_prompt}]
    
    # Get the model from configuration
    model = config.get_model("datasheet_search")
    
    # Create a worker for the API call
    app_logger = logging.getLogger() # Get the root logger configured in main.py
    worker = ApiWorker(model, messages, logger=app_logger)
    
    # Connect signals
    result = None
    error = None
    
    def handle_result(response):
        nonlocal result
        result = response
        
    def handle_error(err):
        nonlocal error
        error = err
    
    worker.finished_signal.connect(handle_result)
    worker.error_signal.connect(handle_error)
    
    # Start the worker and wait for completion
    worker.start()
    worker.wait()
    
    # Check for errors
    if error:
        raise Exception(f"Failed to get datasheet URL: {error}")
    
    if not result:
        raise Exception("No response received from API")
    
    # Extract PDF URL from response
    pdf_urls = re.findall(r'https?://[^\s<>"]+?\.pdf(?:\[\d+\])?', result)
    if not pdf_urls:
        raise Exception("No PDF URL found in response")
    
    # Clean up and return the URL
    pdf_url = clean_pdf_url(pdf_urls[-1])
    return pdf_url

class ApiWorker(QThread):
    """A Worker thread to perform API requests asynchronously."""
    finished_signal = pyqtSignal(str)  # Signal to send back the result
    error_signal = pyqtSignal(str)    # Signal to send back any error
    progress_signal = pyqtSignal(int) # Signal to update progress

    def __init__(self, model, messages, logger): # Added logger argument
        super().__init__()
        self.model = model
        self.messages = messages
        self._is_running = False
        self._should_stop = False
        self.logger = logger # Use passed logger

    def stop(self):
        """Signal the thread to stop."""
        self._should_stop = True
        self.wait()  # Wait for the thread to finish

    def run(self):
        """Perform the API call."""
        self.logger.info("ApiWorker run method entered.") # Earliest possible log
        self.logger.info(f"ApiWorker started for model: {self.model}")
        self._is_running = True
        self._should_stop = False
        
        try:
            self.logger.debug("Simulating progress updates...")
            # Simulate progress updates
            for i in range(1, 101):
                if self._should_stop:
                    self.logger.info("ApiWorker stopping during progress simulation.")
                    return
                self.progress_signal.emit(i)
                self.msleep(50)  # Sleep for 50ms between updates

            if self._should_stop:
                self.logger.info("ApiWorker stopping before API call.")
                return

            self.logger.info(f"Attempting API call to OpenRouter with model: {self.model}")
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=self.messages,
            )
            self.logger.info("API call completed, attempting to log response details.")
            self.logger.info(f"Type of response: {type(response)}")

            if hasattr(response, 'keys'):
                self.logger.info(f"Response keys: {list(response.keys())}")
            elif hasattr(response, '__dict__'):
                 self.logger.info(f"Response attributes: {list(response.__dict__.keys())}")
            else:
                self.logger.info("Response object does not have 'keys' or '__dict__'.")
            
            try:
                # Simplified logging of the raw response
                self.logger.info(f"Full API Response (raw string): {str(response)}")
            except Exception as e_log_response:
                self.logger.error(f"Error logging full API response: {e_log_response}", exc_info=True)
            
            if self._should_stop:
                self.logger.info("ApiWorker stopping after API call, before processing response.")
                return

            # Handle different response formats from different models
            if isinstance(response, dict):
                # Try to extract content based on different API response formats
                if 'choices' in response and response['choices'] and \
                   isinstance(response['choices'], list) and len(response['choices']) > 0 and \
                   isinstance(response['choices'][0], dict) and 'message' in response['choices'][0] and \
                   isinstance(response['choices'][0]['message'], dict) and 'content' in response['choices'][0]['message']:
                    # OpenAI-style response format
                    result = response["choices"][0]["message"]["content"]
                elif 'candidates' in response and response['candidates'] and \
                     isinstance(response['candidates'], list) and len(response['candidates']) > 0 and \
                     isinstance(response['candidates'][0], dict) and 'content' in response['candidates'][0] and \
                     isinstance(response['candidates'][0]['content'], dict) and 'parts' in response['candidates'][0]['content'] and \
                     isinstance(response['candidates'][0]['content']['parts'], list) and len(response['candidates'][0]['content']['parts']) > 0 and \
                     isinstance(response['candidates'][0]['content']['parts'][0], dict) and 'text' in response['candidates'][0]['content']['parts'][0]:
                    # Gemini-style response format (common structure)
                    result = response['candidates'][0]['content']['parts'][0]['text']
                elif 'model_response' in response:
                    # Possible alternative format
                    result = response["model_response"]
                elif 'response' in response:
                    # Another possible format
                    result = response["response"]
                elif 'content' in response: # This could be a simple dict like {'content': 'text'} or a list
                    if isinstance(response['content'], str):
                        result = response["content"]
                    # Handle cases like Anthropic via OpenRouter: "content": [{"type": "text", "text": "Hello!"}]
                    elif isinstance(response['content'], list) and len(response['content']) > 0 and \
                         isinstance(response['content'][0], dict) and 'text' in response['content'][0] and \
                         response['content'][0].get('type') == 'text': # Check type if available
                        result = response['content'][0]['text']
                    else:
                        self.logger.error(f"Found 'content' key, but its value is not a string or recognized list structure. Content type: {type(response['content'])}. Full response (snippet): {str(response)[:500]}...")
                        raise ValueError(f"Unknown API response format with 'content' key. Available keys: {list(response.keys())}")
                elif 'text' in response:
                    # Simple text response
                    result = response["text"]
                else:
                    # If we can't find a recognized format, log the keys and raise an error
                    self.logger.error(f"Unknown API response format. Keys: {list(response.keys())}. Full response (snippet): {str(response)[:500]}...")
                    raise ValueError(f"Unknown API response format. Available keys: {list(response.keys())}")
            else:
                # If response is not a dict, try to convert it to a string
                self.logger.warning(f"API response is not a dictionary. Type: {type(response)}")
                result = str(response)
            self.logger.debug(f"API result extracted: {result[:100]}...") # Log snippet of result
            self.finished_signal.emit(result)
            
        except openai.error.APIError as e:
            self.logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            self.error_signal.emit(f"OpenAI API error: {str(e)}")
            self.finished_signal.emit("")  # Emit empty result to trigger cleanup
        except openai.error.Timeout as e:
            self.logger.error("Request timed out.", exc_info=True)
            self.error_signal.emit("Request timed out. Please try again.")
            self.finished_signal.emit("")
        except openai.error.RateLimitError as e:
            self.logger.error("Rate limit exceeded.", exc_info=True)
            self.error_signal.emit("Rate limit exceeded. Please try again later.")
            self.finished_signal.emit("")
        except ValueError as e: # This is the one we are interested in
            self.logger.error(f"Invalid API response in ApiWorker: {str(e)}", exc_info=True)
            try:
                self.logger.error(f"Problematic response type: {type(response)}, snippet: {str(response)[:500]}")
            except NameError:
                self.logger.error("Problematic response object was not available for logging.")
            except Exception as e_log_val_err:
                self.logger.error(f"Further error logging problematic response: {e_log_val_err}")
            self.error_signal.emit(f"Invalid API response: {str(e)}")
            self.finished_signal.emit("")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in ApiWorker: {str(e)}", exc_info=True)
            self.error_signal.emit(f"An unexpected error occurred: {str(e)}")
            self.finished_signal.emit("")
        finally:
            self._is_running = False
            self.logger.info(f"ApiWorker finished. Model: {self.model}")
# End of api_client.py
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
# End of gui_chat_window.py
import logging
import openai # Keep for openai.error types if api_client.ApiWorker still raises them
# import uuid # Not used, consider removing if not needed elsewhere after this change
from PyQt5.QtCore import QThread, pyqtSignal # QThread might not be needed if ApiWorker is imported
from PyQt5.QtWidgets import QProgressDialog, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Import the robust ApiWorker from api_client.py

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
# End of gui_workers.py
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
# End of gui_handlers_base.py
import os
import logging
import re
import PyPDF2
from PyQt5.QtWidgets import QMessageBox, QApplication


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
# End of gui_handlers_part_search.py
import logging
import os # For os.path.basename
from PyQt5.QtWidgets import QMessageBox, QApplication


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
# End of gui_handlers_analysis.py
import os
import logging
import re
import PyPDF2
from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtCore import QTimer


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
# End of gui_handlers_alternatives.py
import os
import logging
import csv
from io import StringIO
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QApplication, QInputDialog, QFileDialog, QTableWidgetItem
from PyQt5.QtCore import QTimer


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
# End of gui_handlers_comparison.py
import logging


class GuiHandlersManager:
    """Main handler class that manages all individual handlers."""
    
    def __init__(self, main_window):
        """Initialize all handlers."""
        self.window = main_window
        
        # Create handler instances
        self.part_search_handler = PartSearchHandler(main_window)
        self.analysis_handler = AnalysisHandler(main_window)
        self.alternatives_handler = AlternativesHandler(main_window)
        self.comparison_handler = ComparisonHandler(main_window)
        
        # Store handlers in the window for cross-handler access
        self.window.handlers = self
        
        logging.info("GUI handlers initialized")
    
    def handle_find_part(self, part_numbers=None, autonomy_mode=None):
        """Delegate to part search handler."""
        return self.part_search_handler.handle_find_part(part_numbers, autonomy_mode)
    
    def handle_analyze_eol(self):
        """Delegate to analysis handler."""
        return self.analysis_handler.handle_analyze_eol()
    
    def handle_find_alternatives(self):
        """Delegate to alternatives handler."""
        return self.alternatives_handler.handle_find_alternatives()
    
    def handle_compare_datasheets(self):
        """Delegate to comparison handler."""
        return self.comparison_handler.handle_compare_datasheets()
    
    def handle_export_document(self):
        """Delegate to comparison handler."""
        return self.comparison_handler.handle_export_document()
    
    def process_next_part(self):
        """Delegate to part search handler."""
        return self.part_search_handler.process_next_part()
# End of gui_handlers_main.py
import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QTableWidget, QCheckBox, QProgressBar
)
from PyQt5.QtCore import Qt

class MainWindow(QWidget):
    @log_exceptions
    def __init__(self):
        super().__init__()
        logging.info("Initializing MainWindow")

        # Data variables
        self.eol_part_specs = ""
        self.alternatives_specs = ""
        self.comparison_result = ""
        self.requester_info = {}
        self.rationale = ""
        self.alt_pdf_contents = []  # List to store multiple alternative datasheets
        self.alt_pdf_names = []     # List to store names of alternative datasheets
        self.relevant_specs = None   # Store the AI-determined relevant specs
        self.autonomy_mode = False   # Flag to track if autonomy mode is enabled

        # Set up the interface
        self.setWindowTitle("EOL Parts Replacement Finder")
        self.setGeometry(100, 100, 800, 800)
        # Enable close button to allow closing at any point

        # Spreadsheet lookup has been removed
        self.stock_data = None

        # Create datasheets directory
        self.datasheets_dir = create_datasheets_dir()

        # Create worker manager
        self.worker_manager = WorkerManager(self)

        # Create handlers
        self.handlers = GuiHandlersManager(self)

        # Initialize UI components
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface components."""
        # Input section with manual input option
        input_layout = QHBoxLayout()
        
        input_fields_layout = QVBoxLayout()
        self.input_label = QLabel("Enter Part Name or Number:")
        self.input_field = QLineEdit()
        input_fields_layout.addWidget(self.input_label)
        input_fields_layout.addWidget(self.input_field)
        
        # Add checkboxes for options
        options_layout = QHBoxLayout()
        
        self.autonomy_mode_checkbox = QCheckBox("Autonomy Mode")
        self.autonomy_mode_checkbox.setToolTip("Enable to process everything automatically until export")
        self.autonomy_mode_checkbox.stateChanged.connect(self.toggle_autonomy_mode)
        options_layout.addWidget(self.autonomy_mode_checkbox)
        
        self.deep_search_checkbox = QCheckBox("Deep Search")
        self.deep_search_checkbox.setToolTip("Find more alternatives (20 instead of 5) and download more datasheets (5 instead of 3)")
        self.deep_search = False
        self.deep_search_checkbox.stateChanged.connect(self.toggle_deep_search)
        options_layout.addWidget(self.deep_search_checkbox)
        
        input_fields_layout.addLayout(options_layout)
        input_layout.addLayout(input_fields_layout)
        
        # Create autonomy progress tracking elements
        self.autonomy_progress_container = QWidget()
        progress_layout = QVBoxLayout(self.autonomy_progress_container)
        progress_layout.setContentsMargins(0, 5, 0, 5)  # Minimal margins

        self.autonomy_stage_label = QLabel("Ready")
        self.autonomy_stage_label.setAlignment(Qt.AlignCenter)
        self.autonomy_stage_label.setStyleSheet("font-weight: bold;")

        self.autonomy_progress_bar = QProgressBar()
        self.autonomy_progress_bar.setTextVisible(True)  # Show percentage
        self.autonomy_progress_bar.setRange(0, 100)
        self.autonomy_progress_bar.setValue(0)

        progress_layout.addWidget(self.autonomy_stage_label)
        progress_layout.addWidget(self.autonomy_progress_bar)

        # Initially hide the progress elements
        self.autonomy_progress_container.setVisible(False)
        
        self.find_specs_button = QPushButton("Find Part")

        # Part Info section
        self.part_info_label = QLabel("Part Information:")
        self.part_info_area = QTextEdit()
        self.part_info_area.setReadOnly(True)
        self.part_info_area.setMaximumHeight(100)

        # EOL PDF section
        self.eol_pdf_label = QLabel("No EOL datasheet downloaded")
        self.eol_pdf_label.setStyleSheet("color: gray;")
        
        # EOL Analysis section
        self.analyze_button = QPushButton("Analyze EOL Part")
        self.analyze_button.setEnabled(False)
        
        # Find Alternatives section
        self.find_alternatives_button = QPushButton("Find Alternative Parts")
        self.find_alternatives_button.setEnabled(False)
        
        # Alternatives section
        self.alternatives_label = QLabel("Suggested Alternatives:")
        self.alternatives_area = QTextEdit()
        self.alternatives_area.setReadOnly(True)
        self.alternatives_area.setMaximumHeight(100)
        
        # Alternative datasheets status
        self.alt_pdf_label = QLabel("No alternative datasheets downloaded")
        self.alt_pdf_label.setStyleSheet("color: gray;")

        # Compare button
        self.compare_button = QPushButton("Compare All Parts")
        self.compare_button.setEnabled(False)

        # Results section
        self.results_label = QLabel("Analysis Results:")
        self.results_area = QTextEdit()
        self.results_area.setReadOnly(True)
        
        # Comparison Table
        self.table_label = QLabel("Comparison Table:")
        self.comparison_table = QTableWidget()
        self.comparison_table.setVisible(False)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")

        # Export button
        self.export_button = QPushButton("Export Document")
        self.export_button.setEnabled(False)

        # Layout
        layout = QVBoxLayout()
        layout.addLayout(input_layout)
        # Add progress tracking container after input section
        layout.addWidget(self.autonomy_progress_container)
        layout.addWidget(self.find_specs_button)
        layout.addWidget(self.part_info_label)
        layout.addWidget(self.part_info_area)
        layout.addWidget(self.eol_pdf_label)
        layout.addWidget(self.analyze_button)
        layout.addWidget(self.find_alternatives_button)
        layout.addWidget(self.alternatives_label)
        layout.addWidget(self.alternatives_area)
        layout.addWidget(self.alt_pdf_label)
        layout.addWidget(self.compare_button)
        layout.addWidget(self.results_label)
        layout.addWidget(self.results_area)
        layout.addWidget(self.table_label)
        layout.addWidget(self.comparison_table)
        layout.addWidget(self.status_label)
        layout.addWidget(self.export_button)
        self.setLayout(layout)

        # Button actions
        self.find_specs_button.clicked.connect(self.handlers.handle_find_part)
        self.analyze_button.clicked.connect(self.handlers.handle_analyze_eol)
        self.find_alternatives_button.clicked.connect(self.handlers.handle_find_alternatives)
        self.compare_button.clicked.connect(self.handlers.handle_compare_datasheets)
        self.export_button.clicked.connect(self.handlers.handle_export_document)

    def toggle_autonomy_mode(self):
        """Enable or disable autonomy mode and hide/show buttons accordingly."""
        autonomy_enabled = self.autonomy_mode_checkbox.isChecked()
        self.autonomy_mode = autonomy_enabled
        logging.info(f"Autonomy mode {'enabled' if autonomy_enabled else 'disabled'}")
        
        # Hide/show buttons based on autonomy mode
        self.analyze_button.setVisible(not autonomy_enabled)
        self.find_alternatives_button.setVisible(not autonomy_enabled)
        self.compare_button.setVisible(not autonomy_enabled)
        
        # Show/hide progress tracking elements
        self.autonomy_progress_container.setVisible(autonomy_enabled)
        if autonomy_enabled:
            self.autonomy_progress_bar.setValue(0)
            self.autonomy_stage_label.setText("Ready to start")
        
        # In autonomy mode, only the export button remains visible
        # as user input is required for the export dialog
        self.export_button.setVisible(True)
        
        # Update status to inform user
        if autonomy_enabled:
            self.set_status("Autonomy mode enabled. Enter part number and click 'Find Part' to start automated process.")
        else:
            self.set_status("Manual mode enabled. Use the buttons to proceed through each step.")
    
    def toggle_deep_search(self):
        """Enable or disable deep search mode."""
        deep_search_enabled = self.deep_search_checkbox.isChecked()
        self.deep_search = deep_search_enabled
        logging.info(f"Deep search mode {'enabled' if deep_search_enabled else 'disabled'}")
        
        # Update status to inform user
        if deep_search_enabled:
            self.set_status("Deep search mode enabled. Will find more alternatives and download more datasheets.")
        else:
            self.set_status("Standard search mode enabled.")

    def closeEvent(self, event):
        """Handle cleanup when window is closed."""
        # Perform cleanup if workers are running
        if hasattr(self, 'worker_manager'):
            # Log that we're closing with potentially active workers
            if self.worker_manager.worker and self.worker_manager.worker.isRunning():
                logging.info("Closing application with active workers - performing cleanup")
            
            # Always attempt to clean up workers
            self.worker_manager.cleanup_worker()
            
        # Always accept the close event to ensure the app can be closed
        event.accept()
        logging.info("Application closed by user")

    def keep_active(self):
        """Keep the window active and visible."""
        if self.isVisible():
            self.activateWindow()
            self.raise_()
            
    def set_status(self, message):
        """Update the status label with a message."""
        self.status_label.setText(message)
# End of gui_main.py
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
# End of gui_handlers.py
import sys
import logging
import os
import atexit
from PyQt5.QtWidgets import QApplication

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
# End of main.py

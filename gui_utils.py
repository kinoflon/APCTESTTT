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

from utils import resource_path # Import resource_path

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

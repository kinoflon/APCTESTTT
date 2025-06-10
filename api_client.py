import logging
# logger = logging.getLogger(__name__) # Removed from module level
import requests
import re
import openai
from PyQt5.QtCore import QThread, pyqtSignal

# Import configuration
from config import config

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
    from ai_prompts import DATASHEET_URL_BASE_PROMPT
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

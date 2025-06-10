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

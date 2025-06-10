import logging

from gui_handlers_base import BaseGuiHandler
from gui_handlers_part_search import PartSearchHandler
from gui_handlers_analysis import AnalysisHandler
from gui_handlers_alternatives import AlternativesHandler
from gui_handlers_comparison import ComparisonHandler

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

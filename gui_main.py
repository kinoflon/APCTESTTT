import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QTableWidget, QCheckBox, QProgressBar
)
from PyQt5.QtCore import Qt
from utils import log_exceptions
from gui_utils import load_spreadsheet, create_datasheets_dir
from gui_workers import WorkerManager
from gui_handlers_main import GuiHandlersManager

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

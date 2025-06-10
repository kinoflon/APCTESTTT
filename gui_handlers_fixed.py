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

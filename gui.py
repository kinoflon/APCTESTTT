[Previous content remains the same until find_part method]

    def find_part(self):
        """Find and display part information from spreadsheet."""
        part_name = self.input_field.text().strip()
        if not part_name:
            QMessageBox.warning(self, "Input Error", "Please enter a part name or number.")
            return

        # Handle manual input vs spreadsheet lookup
        if self.manual_input_checkbox.isChecked():
            # For manual input, create a simple info display
            self.part_info_area.setPlainText(f"Manual Input Part Number: {part_name}")
            spreadsheet_data = {"Description": part_name, "Item_Code": part_name}
        else:
            # Look up the part in the spreadsheet
            spreadsheet_data = self.find_in_spreadsheet(part_name)
            if spreadsheet_data is None:
                QMessageBox.warning(self, "Not Found", f"Part '{part_name}' not found in the spreadsheet.")
                return
            # Format and display the data
            formatted_data = "\n".join([f"{key}: {value}" for key, value in spreadsheet_data.items() if pd.notna(value)])
            self.part_info_area.setPlainText(formatted_data)
        
        try:
            # Search for datasheet URL using the part number
            description = spreadsheet_data.get('Description', '')
            self.set_status(f"Searching for datasheet for {part_name}...")
            pdf_url = get_datasheet_url(part_name, description)  # Use actual part number for search
            
            # Download and process the datasheet
            self.set_status(f"Downloading datasheet from {pdf_url}...")
            pdf_response = requests.get(pdf_url, timeout=30)
            pdf_response.raise_for_status()
            
            # Save the PDF
            filename = f"eol_{part_name}.pdf"
            pdf_path = os.path.join(self.datasheets_dir, filename)
            with open(pdf_path, 'wb') as f:
                f.write(pdf_response.content)
            
            # Extract text from PDF
            pdf_reader = PyPDF2.PdfReader(pdf_path)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            
            # Store content and update UI
            self.eol_pdf_content = text
            self.eol_pdf_label.setText(f"Downloaded: {filename}")
            self.eol_pdf_label.setStyleSheet("color: green;")
            self.analyze_button.setEnabled(True)
            self.set_status("EOL datasheet downloaded. Click 'Analyze EOL Part' to proceed.")
            
        except Exception as e:
            error_msg = f"Failed to find/download datasheet: {str(e)}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            self.eol_pdf_label.setText("Failed to download PDF")
            self.eol_pdf_label.setStyleSheet("color: red;")
            self.set_status("Failed to find/download EOL datasheet. Please try again.")

[Rest of the file content remains the same]

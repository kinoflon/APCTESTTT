# EOL Parts Replacement Finder

A desktop application to help engineers find suitable replacements for end-of-life (EOL) electronic components.

## Features

- **EOL Part Analysis**: Upload and analyze datasheets for end-of-life components
- **Alternative Parts Search**: Find suitable replacement parts based on EOL component specifications
- **Datasheet Comparison**: Compare specifications across multiple components to find the best match
- **Report Generation**: Export comprehensive reports with comparison tables and recommendations
- **Autonomy Mode**: Fully automated workflow from part search to report generation
- **Deep Search Mode**: Enhanced search capabilities for finding more alternative parts

## MCP Integration

The application integrates with the Model Context Protocol (MCP) to provide enhanced capabilities:

### Datasheet Processor

The Datasheet Processor MCP server provides tools for extracting and processing information from PDF datasheets:

- **Text Extraction**: Extract text content from PDF datasheets
- **Table Extraction**: Extract tabular data from PDF datasheets
- **OCR Processing**: Optical character recognition for scanned datasheets
- **Specification Extraction**: Extract specific specifications from datasheets

### Component Analyzer

The Component Analyzer MCP server provides tools for analyzing electronic components:

- **Component Search**: Search for electronic components by name or specifications
- **Alternative Finding**: Find alternative components based on specifications
- **Component Comparison**: Compare multiple components across key specifications
- **Availability Checking**: Check component availability across major distributors
- **Detailed Information**: Get detailed specifications for electronic components

## Usage

1. Enter a part number or name in the search field
2. Click "Find Part" to search for and download the EOL part datasheet
3. Click "Analyze EOL Part" to extract specifications from the datasheet
4. Click "Find Alternative Parts" to search for suitable replacements
5. Click "Compare All Parts" to generate a comparison table and analysis
6. Click "Export Document" to generate a comprehensive report

### Autonomy Mode

Enable "Autonomy Mode" to automate the entire process from part search to report generation. In this mode, the application will:

1. Search for and download the EOL part datasheet
2. Analyze the EOL part specifications
3. Find alternative parts
4. Download alternative part datasheets
5. Compare all parts
6. Generate a report

### Deep Search Mode

Enable "Deep Search Mode" to find more alternative parts and download more datasheets. This mode is useful for hard-to-find components or when you need a wider range of alternatives.

## Requirements

- Python 3.8+
- PyQt5
- PyPDF2
- Anthropic Claude API access

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python main.py`

## Configuration

The application can be configured through the `config.json` file, which allows you to:

- Specify which AI models to use for different tasks
- Configure API settings
- Customize the application behavior

## License

This project is licensed under the MIT License - see the LICENSE file for details.

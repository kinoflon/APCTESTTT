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

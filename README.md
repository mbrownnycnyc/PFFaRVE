# Pretty Fly for a Vuln Risk Evaluator (PFFaRVE)

Meet PFFaRVE, a Flask-based web application that performs AI-powered vulnerability risk assessment using Claude Sonnet 4 via Abacus.AI.

![wat](https://github.com/mbrownnycnyc/PFFaRVE/blob/main/static/logo.png?raw=true)


## Features

- **AI-Powered Analysis**: Uses Claude Sonnet 4 through Abacus.AI for intelligent risk assessment
- **Severity Classification**: Upload custom severity criteria in Markdown format
- **AttackIQ Integration**: Process AttackIQ BAS assessment JSON data
- **Comprehensive Analysis**: Provides both initial and adjusted severity ratings with risk factors
- **Modern UI**: Dark/light theme toggle with responsive design
- **File Downloads**: Export analysis as Markdown and enhanced JSON with severity analysis

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Abacus.AI API

Edit `config.json` with your Abacus.AI credentials:

* see: https://abacus.ai/app/profile/apikey
  
```json
{
  "abacus_api_key": "your-actual-abacus-ai-api-key",
  "abacus_api_url": "https://api.abacus.ai/v1/chat/completions",
  "model": "claude-sonnet-4",
  "timeout": 300,
  "max_tokens": 4000,
  "temperature": 0.1
}
```

### 3. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### 4. config.json explanation

* Model Selection: Configurable AI model (claude-sonnet-4)
* Token Limits: Configurable max_tokens (4000)
* Temperature Control: Configurable creativity level (0.1 for focused responses)
* Timeout Handling: Configurable request timeout (300 seconds) with proper error handling
* debug_logging: enables logging
  * Model, max_tokens, temperature, and timeout settings
  * Complete API configuration details
  * Timeout error handling
* just_log_prompts: Logs the complete prompt to the debug log file
  * Skips the API call to Abacus.AI (saves API costs/calls)
  * Generates a mock analysis report indicating prompt-only mode
  * Marks all outputs with "(PROMPT-ONLY MODE)" indicators
  * Still processes files and creates downloadable reports

## Usage

### 1. Upload Files

- **Severity Classification**: Upload a `.md` file containing your severity criteria (see `severity_rating.md` example)
- **AttackIQ Data**: Upload a `.json` file with AttackIQ assessment results (see `jira_tickets.json` example)

### 2. Process with AI

Click "Analyze with Claude Sonnet 4" to send your data to the AI for analysis. The system will:

- Inject your severity criteria into the prompt
- Attach the JSON data file
- Send everything to Claude Sonnet 4 via Abacus.AI
- Analyze every ticket in the array for risk assessment

### 3. Download Results

After processing, you can download:

- **Analysis (MD)**: Markdown report with detailed analysis
- **Enhanced JSON**: Original JSON with added `severity_analysis` objects for each ticket

## File Structure

```
pffavre/
├── app.py                 # Main Flask application
├── config.json           # Abacus.AI API configuration
├── requirements.txt      # Python dependencies
├── templates/
│   └── upload.html       # Web interface template
├── severity_rating.md    # Example severity criteria
├── jira_tickets.json     # Example AttackIQ data
└── README.md            # This file
```

## Severity Analysis Structure

Each ticket in the processed JSON will have a `severity_analysis` object added:

```json
{
  "severity_analysis": {
    "initial_severity": "Critical|High|Medium|Low",
    "initial_risk_factors": [
      "specific risk factor 1",
      "specific risk factor 2"
    ],
    "adjusted_severity": "Critical|High|Medium|Low", 
    "adjusted_risk_factors": [
      "reasoning for adjusted rating 1",
      "reasoning for adjusted rating 2"
    ],
    "mitigating_factors": [
      "mitigating factor 1",
      "mitigating factor 2",
      "mitigating factor 3"
    ]
  }
}
```

## API Integration

The application integrates with Abacus.AI using the following prompt structure:

1. **Severity Criteria**: Your uploaded markdown content is injected into the prompt
2. **JSON Data**: Attached as a file to the API request
3. **Analysis Requirements**: Detailed instructions for analyzing every ticket
4. **Output Format**: Specifies both markdown analysis and JSON enhancement requirements

## Security Notes

- Keep your `config.json` file secure and never commit API keys to version control
- The application processes files in memory and creates temporary files only during API calls
- All temporary files are cleaned up after processing

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your Abacus.AI API key is valid and has access to Claude Sonnet 4
2. **File Format Error**: Verify your files are in the correct format (.md for severity, .json for data)
3. **JSON Parse Error**: Ensure your JSON file is valid and contains a "tickets" array
4. **Timeout Error**: Large files may take longer to process; consider increasing the timeout in config.json

### Logs

Check the console output for detailed error messages and processing logs.

## Example Files

The repository includes example files:

- `severity_rating.md`: Sample severity classification criteria
- `jira_tickets.json`: Sample AttackIQ assessment data structure

## License

This project is provided as-is for educational and professional use.

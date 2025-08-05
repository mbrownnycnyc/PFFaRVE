import os
import json
import tempfile
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template
import requests

app = Flask(__name__)

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found")
        return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON in config.json")
        return None

def setup_logging(config):
    """Setup logging based on configuration"""
    if not config.get('debug_logging', False):
        return None
    
    log_file = config.get('log_file', 'pffavre_debug.log')
    
    # Truncate log file if setting is enabled
    if config.get('truncate_log_file_on_run', False):
        try:
            # Clear the log file by opening in write mode
            with open(log_file, 'w') as f:
                f.write(f"=== PFFaRVE Log Started at {datetime.now().isoformat()} ===\n")
            print(f"Log file '{log_file}' truncated")
        except Exception as e:
            print(f"Warning: Could not truncate log file '{log_file}': {e}")
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a'),  # Append mode since we may have truncated above
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== PFFaRVE Application Started ===")
    logger.info(f"Logging to file: {log_file}")
    logger.info(f"Log truncation on run: {config.get('truncate_log_file_on_run', False)}")
    
    return logger

def read_file_with_encoding(file_path):
    """Read file with multiple encoding attempts"""
    encodings = ['utf-8', 'windows-1252', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            return content, encoding
        except UnicodeDecodeError:
            continue
    
    raise UnicodeDecodeError(f"Could not decode file {file_path} with any of the attempted encodings: {encodings}")

def call_abacus_api(config, prompt, logger=None):
    """Call Abacus.AI API with the given prompt"""
    
    if logger:
        logger.info("=== API Call Starting ===")
        logger.info(f"Model: {config.get('model', 'claude-sonnet-4')}")
        logger.info(f"Max tokens: {config.get('max_tokens', 4000)}")
        logger.info(f"Temperature: {config.get('temperature', 0.1)}")
        logger.info(f"Prompt length: {len(prompt)} characters")
        logger.debug("=== PROMPT START ===")
        logger.debug(prompt)
        logger.debug("=== PROMPT END ===")
    
    # If in prompt-only mode, return mock response
    if config.get('just_log_prompts', False):
        mock_response = """# Vulnerability Risk Analysis Report

## Executive Summary
This is a mock analysis response for testing purposes. The actual API call was skipped due to 'just_log_prompts' being enabled in the configuration.

## Analysis Results
- Total tickets analyzed: [Mock Data]
- High severity issues: [Mock Data]
- Medium severity issues: [Mock Data]
- Low severity issues: [Mock Data]

## Recommendations
1. Review high-severity vulnerabilities immediately
2. Implement security patches for critical systems
3. Conduct regular security assessments

*Note: This is mock data generated for testing purposes.*
"""
        if logger:
            logger.info("=== MOCK RESPONSE (just_log_prompts=true) ===")
            logger.info("Returning mock analysis instead of calling API")
        
        return mock_response
    
    # Prepare API request
    headers = {
        'Authorization': f'Bearer {config["abacus_api_key"]}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': config.get('model', 'claude-sonnet-4'),
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': config.get('max_tokens', 4000),
        'temperature': config.get('temperature', 0.1)
    }
    
    try:
        if logger:
            logger.info("Sending request to Abacus.AI API...")
        
        response = requests.post(
            config['abacus_api_url'],
            headers=headers,
            json=payload,
            timeout=config.get('timeout', 300)
        )
        
        if logger:
            logger.info(f"API Response Status: {response.status_code}")
        
        response.raise_for_status()
        
        result = response.json()
        
        if logger:
            logger.debug("=== API RESPONSE START ===")
            logger.debug(json.dumps(result, indent=2))
            logger.debug("=== API RESPONSE END ===")
        
        # Extract the content from the response
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            if logger:
                logger.info(f"Successfully received response ({len(content)} characters)")
            return content
        else:
            error_msg = "Unexpected API response format"
            if logger:
                logger.error(error_msg)
            raise ValueError(error_msg)
    
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        if logger:
            logger.error(error_msg)
        raise Exception(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse API response: {str(e)}"
        if logger:
            logger.error(error_msg)
        raise Exception(error_msg)

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    config = load_config()
    if not config:
        return jsonify({'success': False, 'error': 'Configuration file not found or invalid'})
    
    # Setup logging
    logger = setup_logging(config)
    
    if logger:
        logger.info("=== New Analysis Request ===")
    
    try:
        # Check if files are present
        if 'severity_file' not in request.files or 'json_file' not in request.files:
            error_msg = 'Both severity_file and json_file are required'
            if logger:
                logger.error(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        severity_file = request.files['severity_file']
        json_file = request.files['json_file']
        
        if severity_file.filename == '' or json_file.filename == '':
            error_msg = 'Both files must be selected'
            if logger:
                logger.error(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        if logger:
            logger.info(f"Processing files: {severity_file.filename}, {json_file.filename}")
        
        # Save uploaded files temporarily
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.md') as temp_severity:
            severity_file.save(temp_severity.name)
            severity_content, severity_encoding = read_file_with_encoding(temp_severity.name)
        
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.json') as temp_json:
            json_file.save(temp_json.name)
            json_content, json_encoding = read_file_with_encoding(temp_json.name)
        
        if logger:
            logger.info(f"Severity file encoding: {severity_encoding}")
            logger.info(f"JSON file encoding: {json_encoding}")
        
        # Parse JSON data
        try:
            json_data = json.loads(json_content)
            if logger:
                logger.info(f"JSON parsed successfully. Keys: {list(json_data.keys())}")
            if 'tickets' in json_data:
                logger.info(f"Found {len(json_data['tickets'])} tickets")
        except json.JSONDecodeError as e:
            error_msg = f'Invalid JSON file: {str(e)}'
            if logger:
                logger.error(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        # Create the prompt for analysis
        prompt = f"""You are a cybersecurity expert analyzing vulnerability data. Please analyze the following AttackIQ assessment data using the provided severity classification criteria.

SEVERITY CLASSIFICATION CRITERIA:
{severity_content}

ATTACKIQ ASSESSMENT DATA:
{json_content}

Please provide:
1. A comprehensive markdown analysis report
2. For each ticket in the JSON data, add a "severity_analysis" object with:
   - initial_severity: Based on the raw data
   - adjusted_severity: Your expert assessment
   - risk_factors: List of factors that increase risk
   - mitigating_factors: List of factors that reduce risk
   - confidence_score: Your confidence in the assessment (0-100)
   - reasoning: Brief explanation of your assessment

Return your response in the following format:
1. First, provide the markdown analysis report
2. Then, provide the enhanced JSON with severity_analysis added to each ticket

Separate the markdown and JSON sections clearly."""

        if logger:
            logger.info("Calling Abacus.AI API for analysis...")
        
        # Call the API
        analysis_result = call_abacus_api(config, prompt, logger)
        
        if logger:
            logger.info("Analysis completed successfully")
        
        # Try to split the response into markdown and JSON parts
        # This is a simple approach - in production you might want more sophisticated parsing
        parts = analysis_result.split('```json')
        if len(parts) > 1:
            markdown_part = parts[0].strip()
            json_part = parts[1].split('```')[0].strip()
            try:
                enhanced_json = json.loads(json_part)
            except:
                enhanced_json = json_data  # Fallback to original
        else:
            markdown_part = analysis_result
            enhanced_json = json_data  # Fallback to original
        
        # Save results to temporary files
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md', encoding='utf-8') as markdown_file:
            markdown_file.write(markdown_part)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as json_file_enhanced:
            json.dump(enhanced_json, json_file_enhanced, indent=2)
        
        if logger:
            logger.info(f"Results saved to: {markdown_file.name}, {json_file_enhanced.name}")
            logger.info("=== Analysis Request Completed Successfully ===")
        
        # Clean up temporary input files
        try:
            os.unlink(temp_severity.name)
            os.unlink(temp_json.name)
        except:
            pass
        
        return jsonify({
            'success': True,
            'markdown_file': markdown_file.name,
            'json_file': json_file_enhanced.name,
            'tickets_analyzed': len(json_data.get('tickets', [])),
            'model_used': config.get('model', 'claude-sonnet-4'),
            'prompt_only_mode': config.get('just_log_prompts', False),
            'analysis_preview': analysis_result[:500] + '...' if len(analysis_result) > 500 else analysis_result,
            # Add these for frontend compatibility:
            'analysis': analysis_result,  # Full analysis text
            'modified_json': enhanced_json  # Enhanced JSON data
        })
    
    except Exception as e:
        error_msg = f'Analysis failed: {str(e)}'
        if logger:
            logger.error(error_msg)
            logger.error("=== Analysis Request Failed ===")
        return jsonify({'success': False, 'error': error_msg})

@app.route('/download/markdown/<filename>')
def download_markdown(filename):
    """Download markdown analysis file"""
    try:
        # Security: Only allow files in temp directory with .md extension
        if not filename.endswith('.md'):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Construct full path (assuming files are in system temp directory)
        import tempfile
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True, download_name='vulnerability_analysis.md')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/json/<filename>')
def download_json(filename):
    """Download enhanced JSON file"""
    try:
        # Security: Only allow files in temp directory with .json extension
        if not filename.endswith('.json'):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Construct full path (assuming files are in system temp directory)
        import tempfile
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True, download_name='enhanced_tickets.json')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    config = load_config()
    if config:
        logger = setup_logging(config)
        if logger:
            logger.info("=== PFFaRVE Flask Application Starting ===")
        print("PFFaRVE server starting...")
        print("Access the application at: http://127.0.0.1:5000")
        app.run(debug=True, host='127.0.0.1', port=5000)
    else:
        print("Failed to load configuration. Please check config.json")
# Headquarters Finder

A robust Python application that automatically retrieves corporate headquarters information using the Google Gemini 2.5 Pro API. Designed for high accuracy (90%+ target) and scalable processing of large CSV datasets.

## Features

- **High Accuracy**: Uses Gemini 2.5 Pro with optimized prompts for 90%+ accuracy
- **Batch Processing**: Processes up to 15,000+ records in configurable batches
- **Progress Saving**: Automatically saves progress every 50 records to prevent data loss
- **Resume Functionality**: Can resume processing from where it left off
- **Comprehensive Logging**: Detailed logging with rotating file handler
- **Validation**: Compare results against gold standard for accuracy measurement
- **Windows Executable**: One-click executable for easy deployment

## Requirements

- Python 3.8 or later
- Google Gemini API key
- Windows 10/11 (for executable version)

## Installation

### Option 1: Python Script

1. Clone or download the project files
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your API key in `config.ini`
4. Run the application:
   ```bash
   python main.py
   ```

### Option 2: Windows Executable

1. Download the `HeadquartersFinder.exe` file
2. Place your input CSV file in the same directory
3. Edit `config.ini` to set your API key
4. Double-click `HeadquartersFinder.exe` to run

## Configuration

Edit the `config.ini` file to configure the application:

```ini
[API]
api_key = YOUR_GEMINI_API_KEY_HERE
model_name = gemini-2.5-pro
temperature = 0.1
max_output_tokens = 8192

[FILES]
input_file = input file for 2nd upwork job.csv
output_file = data/output.csv
log_file = logs/headquarters_finder.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 1.0

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
```

### Required Configuration

1. **API Key**: Get your Gemini API key from [Google AI Studio](https://ai.google.dev/)
2. **Input File**: Path to your CSV file with company names
3. **Output File**: Where to save the results

### Optional Configuration

- **Batch Size**: Number of records to process at once (default: 50)
- **Retry Attempts**: Number of retries for failed API requests (default: 3)
- **Delay Between Requests**: Seconds to wait between API calls (default: 1.0)

## Input CSV Format

Your input CSV file must contain a column named "Payee Name of Record" with company names:

```csv
Geographic Location,Payee Name of Record,Address1 of Record,Address 2 of Record,City of Record,State of Record,Zip of Record
State of California,JTN HOSPICE INC,,,,,
"Cook County, Illinois",TUR VENTURES LLC,1200 E ALGONQUIN RD,,MOUNT PROSPECT,IL,60056
```

## Output Format

The application adds the following columns to your data:

- `HQ_Street_Address`: Corporate headquarters street address
- `HQ_City`: Corporate headquarters city
- `HQ_State`: Corporate headquarters state
- `HQ_ZIP`: Corporate headquarters ZIP code
- `HQ_Country`: Corporate headquarters country
- `Status`: Processing status (Pending/Complete/Error)
- `Error_Message`: Error details if processing failed
- `Processed_Timestamp`: When the record was processed

## Usage

### Basic Usage

```bash
python main.py
```

### With Validation

```bash
python main.py --validate
```

### Test API Connection

```bash
python main.py --test
```

### Custom Config File

```bash
python main.py --config my_config.ini
```

## Command Line Options

- `--config`: Specify custom configuration file (default: config.ini)
- `--validate`: Validate results against gold standard file
- `--test`: Test API connection only

## Project Structure

```
headquarters-finder/
├── main.py                 # Main application entry point
├── config.ini             # Configuration file
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── src/
│   ├── core/
│   │   ├── api_client.py      # Gemini API client
│   │   ├── csv_processor.py   # CSV file operations
│   │   └── data_validator.py  # Gold standard validation
│   ├── services/
│   │   └── headquarters_service.py  # Main business logic
│   └── utils/
│       ├── config.py      # Configuration management
│       └── logger.py      # Logging setup
├── data/                  # Input/output data files
└── logs/                  # Log files
```

## Logging

The application creates detailed logs in the `logs/` directory:

- `headquarters_finder.log`: Main application log
- `api_client.log`: API request logs
- `csv_processor.log`: CSV processing logs
- `headquarters_service.log`: Service operation logs
- `data_validator.log`: Validation logs

Logs are automatically rotated when they reach 10MB, keeping 3 backup files.

## Error Handling

The application includes comprehensive error handling:

- **API Failures**: Automatic retry with exponential backoff
- **File Errors**: Graceful handling of missing or corrupted files
- **Network Issues**: Robust handling of connection problems
- **Data Validation**: Detailed validation error reporting

## Performance

- **Batch Processing**: Processes 50 records at a time for optimal performance
- **Progress Saving**: Saves progress every 50 records to prevent data loss
- **Rate Limiting**: Respects API rate limits with configurable delays
- **Memory Efficient**: Processes large datasets without memory issues

## Troubleshooting

### Common Issues

1. **API Key Error**: Make sure your Gemini API key is correctly set in `config.ini`
2. **File Not Found**: Ensure your input CSV file exists and path is correct
3. **Permission Errors**: Make sure the application has write permissions for output directory
4. **Network Issues**: Check your internet connection and API key validity

### Debug Mode

Set log level to DEBUG in `config.ini` for detailed logging:

```ini
[LOGGING]
log_level = DEBUG
```

### Validation Issues

If validation fails:
1. Ensure your gold standard file exists and is properly formatted
2. Check that company names match between input and gold standard
3. Verify the gold standard file has the required columns

## Support

For issues or questions:
1. Check the log files in the `logs/` directory
2. Verify your configuration in `config.ini`
3. Test API connection with `python main.py --test`

## License

This project is developed for Upwork client delivery. All rights reserved.

## Version History

- v1.0.0: Initial release with full functionality
  - Gemini 2.5 Pro API integration
  - Batch processing with progress saving
  - Comprehensive logging and error handling
  - Windows executable support
  - Gold standard validation

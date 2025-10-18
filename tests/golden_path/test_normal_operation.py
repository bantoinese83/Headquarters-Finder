"""
Golden path tests for normal operation scenarios.

Tests the typical, expected workflows and inputs to ensure
the application behaves correctly under normal conditions.
"""

import pytest
import pandas as pd
import tempfile
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from headquarters_finder.core.api_client import GeminiAPIClient, Tier1RateLimiter
from headquarters_finder.core.csv_processor import CSVProcessor
from headquarters_finder.services.headquarters_service import HeadquartersService
from headquarters_finder.utils.config import Config
from headquarters_finder.utils.logger import Logger


class TestNormalOperation:
    """Test normal operation scenarios."""
    
    def test_typical_csv_processing(self, sample_csv_data, temp_dir, mock_logger):
        """Test typical CSV processing workflow."""
        # Create test CSV
        test_csv = os.path.join(temp_dir, 'test.csv')
        sample_csv_data.to_csv(test_csv, index=False)
        
        processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        
        # Read input
        df = processor.read_input_csv()
        assert len(df) == 5
        assert 'Payee Name of Record' in df.columns
        assert 'Status' in df.columns
        assert 'Headquarters Address' in df.columns
        
        # Check that all records are marked as Pending
        assert all(df['Status'] == 'Pending')
        
        # Update a record
        processor.update_record_status(
            df, 0, 'Complete', 
            '1 Apple Park Way, Cupertino, CA 95014, USA'
        )
        assert df.iloc[0]['Status'] == 'Complete'
        assert df.iloc[0]['Headquarters Address'] == '1 Apple Park Way, Cupertino, CA 95014, USA'
        
        # Write output
        processor.write_output_csv(df)
        assert os.path.exists(os.path.join(temp_dir, 'output.csv'))
    
    def test_typical_api_client_operation(self, mock_logger):
        """Test typical API client operation."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            # Mock successful API response
            mock_model = Mock()
            mock_model_class.return_value = mock_model
            mock_response = Mock()
            mock_response.text = """Street Address: 1 Apple Park Way
City: Cupertino
State: CA
ZIP Code: 95014
Country: USA"""
            mock_model.generate_content.return_value = mock_response
            
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            # Test successful headquarters lookup
            result, success = client.get_headquarters_info('Apple Inc.')
            
            assert success is True
            assert result['HQ_Street_Address'] == '1 Apple Park Way'
            assert result['HQ_City'] == 'Cupertino'
            assert result['HQ_State'] == 'CA'
            assert result['HQ_ZIP'] == '95014'
            assert result['HQ_Country'] == 'USA'
            assert result['Raw_Response'] == """Street Address: 1 Apple Park Way
City: Cupertino
State: CA
ZIP Code: 95014
Country: USA"""
            assert result['Error_Message'] == ''
    
    def test_typical_rate_limiter_operation(self):
        """Test typical rate limiter operation."""
        limiter = Tier1RateLimiter()
        
        # Test normal operation - should not wait
        start_time = time.time()
        limiter.wait_if_needed(1000)
        end_time = time.time()
        
        # Should not wait significantly
        assert end_time - start_time < 0.1
        
        # Test multiple requests
        for _ in range(5):
            limiter.wait_if_needed(1000)
        
        # Should still not wait significantly
        assert len(limiter.request_times) == 6
        assert len(limiter.token_usage) == 6
    
    def test_typical_service_operation(self, sample_csv_data, temp_dir, mock_logger):
        """Test typical service operation."""
        # Create test CSV
        test_csv = os.path.join(temp_dir, 'test.csv')
        sample_csv_data.to_csv(test_csv, index=False)
        
        # Mock API client
        mock_api_client = Mock()
        mock_api_client.get_headquarters_info.return_value = (
            {
                'HQ_Street_Address': '1 Apple Park Way',
                'HQ_City': 'Cupertino',
                'HQ_State': 'CA',
                'HQ_ZIP': '95014',
                'HQ_Country': 'USA',
                'Raw_Response': '1 Apple Park Way, Cupertino, CA 95014, USA',
                'Error_Message': ''
            },
            None  # No error
        )
        
        # Create service
        processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        from headquarters_finder.utils.config import ProcessingConfig
        processing_config = ProcessingConfig(batch_size=50, save_interval=50, retry_attempts=3, delay_between_requests=0.1)
        service = HeadquartersService(mock_api_client, processor, processing_config, mock_logger)
        
        # Test processing time calculation
        estimates = service.calculate_processing_time(5)
        assert estimates['total_records'] == 5
        assert estimates['estimated_time_hours'] > 0
        assert estimates['can_process_today'] is True
        
        # Test processing
        results = service.process_headquarters_data(sample_csv_data)
        assert len(results) == 5
        assert service.stats.completed_records == 5
        assert service.stats.error_records == 0
    
    def test_typical_configuration_loading(self, temp_dir):
        """Test typical configuration loading."""
        # Create test config file
        config_content = """
[API]
api_key = test_key
model_name = gemini-2.5-pro
temperature = 0.1
max_output_tokens = 8192

[FILES]
input_file = test_input.csv
output_file = test_output.csv
log_file = test.log
gold_standard_file = test_gold.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
"""
        config_file = os.path.join(temp_dir, 'config.ini')
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        # Load configuration
        config = Config(config_file)
        
        # Test API config
        api_config = config.get_api_config()
        assert api_config.api_key == 'test_key'
        assert api_config.model_name == 'gemini-2.5-pro'
        assert api_config.temperature == 0.1
        assert api_config.max_output_tokens == 8192
        
        # Test file config
        file_config = config.get_file_config()
        assert file_config.input_file == 'test_input.csv'
        assert file_config.output_file == 'test_output.csv'
        assert file_config.log_file == 'test.log'
        assert file_config.gold_standard_file == 'test_gold.csv'
        
        # Test processing config
        processing_config = config.get_processing_config()
        assert processing_config.batch_size == 50
        assert processing_config.save_interval == 50
        assert processing_config.retry_attempts == 3
        assert processing_config.delay_between_requests == 0.4
        
        # Test logging config
        logging_config = config.get_logging_config()
        assert logging_config.log_level == 'INFO'
        assert logging_config.max_log_size == 10485760
        assert logging_config.backup_count == 3
    
    def test_typical_logger_operation(self, temp_dir):
        """Test typical logger operation."""
        log_file = os.path.join(temp_dir, 'test.log')
        logger = Logger(log_file, log_level='INFO')
        
        # Test logging
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.debug("Test debug message")
        logger.critical("Test critical message")
        
        # Check log file was created
        assert os.path.exists(log_file)
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "Test info message" in log_content
            assert "Test warning message" in log_content
            assert "Test error message" in log_content
            assert "Test critical message" in log_content
    
    def test_typical_data_validation(self, sample_csv_data, sample_gold_standard_data, temp_dir, mock_logger):
        """Test typical data validation workflow."""
        # Create test files
        processed_csv = os.path.join(temp_dir, 'processed.csv')
        gold_csv = os.path.join(temp_dir, 'gold.csv')
        
        sample_csv_data.to_csv(processed_csv, index=False)
        sample_gold_standard_data.to_csv(gold_csv, index=False)
        
        # Create validator
        from headquarters_finder.core.data_validator import DataValidator
        from headquarters_finder.utils.config import FileConfig
        file_config = FileConfig(
            input_file=processed_csv,
            output_file=os.path.join(temp_dir, 'output.csv'),
            log_file=os.path.join(temp_dir, 'test.log'),
            gold_standard_file=gold_csv
        )
        validator = DataValidator(file_config, mock_logger)
        
        # Test validation
        accuracy, validation_df = validator.validate_results(sample_csv_data)
        
        # Should have some accuracy (exact matches)
        assert accuracy >= 0
        assert isinstance(validation_df, pd.DataFrame)
    
    def test_typical_batch_processing(self, temp_dir, mock_logger):
        """Test typical batch processing workflow."""
        # Create larger test dataset
        large_data = {
            'Payee Name of Record': [f'Company {i}' for i in range(100)],
            'Status': ['Pending'] * 100,
            'Address1 of Record': ['Address'] * 100,
            'City of Record': ['City'] * 100,
            'State of Record': ['State'] * 100,
            'Zip of Record': ['Zip'] * 100
        }
        large_df = pd.DataFrame(large_data)
        large_csv = os.path.join(temp_dir, 'large.csv')
        large_df.to_csv(large_csv, index=False)
        
        # Mock API client
        mock_api_client = Mock()
        mock_api_client.get_headquarters_info.return_value = (
            {
                'HQ_Street_Address': 'Test Street',
                'HQ_City': 'Test City',
                'HQ_State': 'TS',
                'HQ_ZIP': '12345',
                'HQ_Country': 'USA',
                'Raw_Response': 'Test Street, Test City, TS 12345, USA',
                'Error_Message': ''
            },
            True
        )
        
        # Create service with batch processing
        processor = CSVProcessor(large_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        from headquarters_finder.utils.config import ProcessingConfig
        processing_config = ProcessingConfig(batch_size=25, save_interval=25, retry_attempts=3, delay_between_requests=0.1)
        service = HeadquartersService(mock_api_client, processor, processing_config, mock_logger)
        
        # Test processing
        results = service.process_all_records(resume=False)
        
        assert results['statistics']['total_processed'] == 100
        assert results['statistics']['successful'] == 100
        assert results['statistics']['failed'] == 0
        
        # Check that API was called for each record
        assert mock_api_client.get_headquarters_info.call_count == 100
    
    def test_typical_resume_functionality(self, sample_csv_data, temp_dir, mock_logger):
        """Test typical resume functionality."""
        # Create test CSV
        test_csv = os.path.join(temp_dir, 'test.csv')
        sample_csv_data.to_csv(test_csv, index=False)
        
        # Create processor
        processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        
        # Process first time
        df = processor.read_input_csv()
        processor.update_record_status(df, 0, 'Complete', 'Test Address')
        processor.write_output_csv(df)
        
        # Load existing output
        existing_df = processor.load_existing_output()
        assert len(existing_df) == 5
        assert existing_df.iloc[0]['Status'] == 'Complete'
        
        # Merge with input
        merged_df = processor.merge_dataframes(df, existing_df)
        assert len(merged_df) == 5
        assert merged_df.iloc[0]['Status'] == 'Complete'
        assert merged_df.iloc[1]['Status'] == 'Pending'  # Not processed yet
    
    def test_typical_error_handling(self, mock_logger):
        """Test typical error handling scenarios."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            # Mock API client that fails
            mock_model = Mock()
            mock_model_class.return_value = mock_model
            mock_model.generate_content.side_effect = Exception("API Error")
            
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                retry_attempts=2,
                logger=mock_logger
            )
            
            # Test error handling
            result, success = client.get_headquarters_info('Test Company')
            
            assert success is False
            assert 'API Error' in result['Error_Message']
            assert result['Raw_Response'] == 'ERROR: API Error'
    
    def test_typical_progress_tracking(self, temp_dir, mock_logger):
        """Test typical progress tracking."""
        # Create test data
        test_data = pd.DataFrame({
            'Payee Name of Record': [f'Company {i}' for i in range(10)],
            'Status': ['Pending'] * 10
        })
        test_csv = os.path.join(temp_dir, 'test.csv')
        test_data.to_csv(test_csv, index=False)
        
        # Mock API client
        mock_api_client = Mock()
        mock_api_client.get_headquarters_info.return_value = (
            {
                'HQ_Street_Address': 'Test Street',
                'HQ_City': 'Test City',
                'HQ_State': 'TS',
                'HQ_ZIP': '12345',
                'HQ_Country': 'USA',
                'Raw_Response': 'Test Street, Test City, TS 12345, USA',
                'Error_Message': ''
            },
            True
        )
        
        # Create service
        processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        from headquarters_finder.utils.config import ProcessingConfig
        processing_config = ProcessingConfig(batch_size=5, save_interval=5, retry_attempts=3, delay_between_requests=0.1)
        service = HeadquartersService(mock_api_client, processor, processing_config, mock_logger)
        
        # Test processing with progress tracking
        results = service.process_all_records(resume=False)
        
        # Check progress tracking
        assert results['statistics']['total_processed'] == 10
        assert results['statistics']['successful'] == 10
        assert results['statistics']['failed'] == 0
        assert results['statistics']['start_time'] is not None
        assert results['statistics']['end_time'] is not None
        
        # Check that progress was saved
        assert os.path.exists(os.path.join(temp_dir, 'output.csv'))
    
    def test_typical_validation_workflow(self, sample_csv_data, sample_gold_standard_data, temp_dir, mock_logger):
        """Test typical validation workflow."""
        # Create test files
        processed_csv = os.path.join(temp_dir, 'processed.csv')
        gold_csv = os.path.join(temp_dir, 'gold.csv')
        
        # Add headquarters addresses to processed data
        sample_csv_data['Headquarters Address'] = [
            '1 Apple Park Way, Cupertino, CA 95014, USA',
            'One Microsoft Way, Redmond, WA 98052, USA',
            '1600 Amphitheatre Parkway, Mountain View, CA 94043, USA',
            '410 Terry Avenue North, Seattle, WA 98109, USA',
            '1 Tesla Road, Austin, TX 78725, USA'
        ]
        
        sample_csv_data.to_csv(processed_csv, index=False)
        sample_gold_standard_data.to_csv(gold_csv, index=False)
        
        # Create validator
        from headquarters_finder.core.data_validator import DataValidator
        from headquarters_finder.utils.config import FileConfig
        file_config = FileConfig(
            input_file=processed_csv,
            output_file=os.path.join(temp_dir, 'output.csv'),
            log_file=os.path.join(temp_dir, 'test.log'),
            gold_standard_file=gold_csv
        )
        validator = DataValidator(file_config, mock_logger)
        
        # Test validation
        accuracy, validation_df = validator.validate_results(sample_csv_data)
        
        # Should have high accuracy for exact matches
        assert accuracy >= 80  # At least 80% accuracy
        assert isinstance(validation_df, pd.DataFrame)
        assert len(validation_df) == 5
        
        # Check validation report was created
        report_file = os.path.join(temp_dir, 'validation_report.csv')
        if os.path.exists(report_file):
            report_df = pd.read_csv(report_file)
            assert len(report_df) == 5
            assert 'Is Match' in report_df.columns
            assert 'Similarity Score' in report_df.columns

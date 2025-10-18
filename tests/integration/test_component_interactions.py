"""
Integration tests for component interactions.

Tests how different components work together to ensure
the application functions correctly as a whole system.
"""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from headquarters_finder.core.api_client import GeminiAPIClient, Tier1RateLimiter
from headquarters_finder.core.csv_processor import CSVProcessor
from headquarters_finder.services.headquarters_service import HeadquartersService
from headquarters_finder.utils.config import Config
from headquarters_finder.utils.logger import Logger


class TestComponentIntegration:
    """Test integration between different components."""
    
    def test_api_client_csv_processor_integration(self, sample_csv_data, temp_dir, mock_logger):
        """Test integration between API client and CSV processor."""
        # Create test CSV
        test_csv = os.path.join(temp_dir, 'test.csv')
        sample_csv_data.to_csv(test_csv, index=False)
        
        # Create components
        processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        
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
            
            # Test integration
            df = processor.read_input_csv()
            result, success = client.get_headquarters_info(df.iloc[0]['Payee Name of Record'])
            
            assert success is True
            assert result['HQ_Street_Address'] == '1 Apple Park Way'
            
            # Update CSV with result
            processor.update_record_status(
                df, 0, 'Complete', 
                f"{result['HQ_Street_Address']}, {result['HQ_City']}, {result['HQ_State']} {result['HQ_ZIP']}, {result['HQ_Country']}"
            )
            
            assert df.iloc[0]['Status'] == 'Complete'
            assert '1 Apple Park Way' in df.iloc[0]['Headquarters Address']
    
        def test_service_processor_integration(self, sample_csv_data, temp_dir, mock_logger):
            """Test integration between service and processor."""
            # Create test CSV
            test_csv = os.path.join(temp_dir, 'test.csv')
            sample_csv_data.to_csv(test_csv, index=False)
            
            # Create components
            processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
            
            # Mock API client directly
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
                True  # Success
            )
            
            # Create service
            from headquarters_finder.utils.config import ProcessingConfig
            processing_config = ProcessingConfig(batch_size=50, save_interval=50, retry_attempts=3, delay_between_requests=0.1)
            service = HeadquartersService(mock_api_client, processor, processing_config, mock_logger)
            
            # Test integration
            results = service.process_all_records(resume=False)
            
            assert results['statistics']['total_processed'] == 5
            assert results['statistics']['successful'] == 5
            assert results['statistics']['failed'] == 0
            
            # Check output file was created
            assert os.path.exists(os.path.join(temp_dir, 'output.csv'))
            
            # Verify output content
            output_df = pd.read_csv(os.path.join(temp_dir, 'output.csv'))
            assert len(output_df) == 5
            assert all(output_df['Status'] == 'Complete')
            # Check that headquarters addresses were populated
            headquarters_addresses = output_df['Headquarters Address'].dropna()
            assert len(headquarters_addresses) > 0
            assert all('Apple Park Way' in addr for addr in headquarters_addresses)
    
    def test_config_service_integration(self, sample_csv_data, temp_dir, mock_logger):
        """Test integration between configuration and service."""
        # Create test config
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
        # Create test CSV
        test_csv = os.path.join(temp_dir, 'test_input.csv')
        sample_csv_data.to_csv(test_csv, index=False)
        
        # Update config to use absolute path
        config_content = config_content.replace('input_file = test_input.csv', f'input_file = {test_csv}')
        config_content = config_content.replace('output_file = test_output.csv', f'output_file = {os.path.join(temp_dir, "test_output.csv")}')
        config_content = config_content.replace('log_file = test.log', f'log_file = {os.path.join(temp_dir, "test.log")}')
        config_content = config_content.replace('gold_standard_file = test_gold.csv', f'gold_standard_file = {os.path.join(temp_dir, "test_gold.csv")}')
        
        config_file = os.path.join(temp_dir, 'config.ini')
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        # Load configuration
        config = Config(config_file)
        
        # Create components with config
        processor = CSVProcessor(
            config.get_file_config().input_file,
            config.get_file_config().output_file,
            mock_logger
        )
        
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            # Mock API client
            mock_model = Mock()
            mock_model_class.return_value = mock_model
            mock_response = Mock()
            mock_response.text = """Street Address: 1 Apple Park Way
City: Cupertino
State: CA
ZIP Code: 95014
Country: USA"""
            mock_model.generate_content.return_value = mock_response
            
            api_config = config.get_api_config()
            client = GeminiAPIClient(
                api_key=api_config.api_key,
                model_name=api_config.model_name,
                temperature=api_config.temperature,
                max_output_tokens=api_config.max_output_tokens,
                logger=mock_logger
            )
            
            # Create service with config
            processing_config = config.get_processing_config()
            service = HeadquartersService(
                client, processor, 
                processing_config,
                mock_logger
            )
            
            # Test integration
            results = service.process_all_records(resume=False)
            
            assert results['statistics']['total_processed'] == 5
            assert results['statistics']['successful'] == 5
            assert results['statistics']['failed'] == 0
    
    def test_logger_component_integration(self, sample_csv_data, temp_dir):
        """Test integration between logger and all components."""
        # Create test CSV
        test_csv = os.path.join(temp_dir, 'test.csv')
        sample_csv_data.to_csv(test_csv, index=False)
        
        # Create logger
        log_file = os.path.join(temp_dir, 'test.log')
        logger = Logger(log_file, log_level='INFO')
        
        # Create components with logger
        processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), logger)
        
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            # Mock API client
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
                logger=logger
            )
            
            # Create service with logger
            from headquarters_finder.utils.config import ProcessingConfig
            processing_config = ProcessingConfig(batch_size=50, save_interval=50, retry_attempts=3, delay_between_requests=0.1)
            service = HeadquartersService(client, processor, processing_config, logger)
            
            # Test integration
            results = service.process_all_records(resume=False)
            
            assert results['statistics']['total_processed'] == 5
            assert results['statistics']['successful'] == 5
            assert results['statistics']['failed'] == 0
            
            # Check log file was created and has content
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert 'Starting headquarters processing' in log_content
                assert 'Headquarters processing completed' in log_content
    
    def test_rate_limiter_api_client_integration(self, mock_logger):
        """Test integration between rate limiter and API client."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            # Mock API client
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
            
            # Test rate limiter integration
            result1, success1 = client.get_headquarters_info('Apple Inc.')
            result2, success2 = client.get_headquarters_info('Microsoft Corp.')
            
            assert success1 is True
            assert success2 is True
            assert result1['HQ_Street_Address'] == '1 Apple Park Way'
            assert result2['HQ_Street_Address'] == '1 Apple Park Way'
            
            # Rate limiter should be working
            assert isinstance(client.rate_limiter, Tier1RateLimiter)
            assert len(client.rate_limiter.request_times) == 2
            assert len(client.rate_limiter.token_usage) == 2
    
    def test_processor_service_integration_with_resume(self, sample_csv_data, temp_dir, mock_logger):
        """Test integration between processor and service with resume functionality."""
        # Create test CSV
        test_csv = os.path.join(temp_dir, 'test.csv')
        sample_csv_data.to_csv(test_csv, index=False)
        
        # Create components
        processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            # Mock API client
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
            
            # Create service
            from headquarters_finder.utils.config import ProcessingConfig
            processing_config = ProcessingConfig(batch_size=50, save_interval=50, retry_attempts=3, delay_between_requests=0.1)
            service = HeadquartersService(client, processor, processing_config, mock_logger)
            
            # Process first time
            results1 = service.process_all_records(resume=False)
            assert results1['statistics']['total_processed'] == 5
            assert results1['statistics']['successful'] == 5
            
            # Modify input to add more records
            new_data = pd.DataFrame({
                'Payee Name of Record': ['New Company 1', 'New Company 2'],
                'Status': ['Pending', 'Pending'],
                'Address1 of Record': ['Address 1', 'Address 2'],
                'City of Record': ['City 1', 'City 2'],
                'State of Record': ['ST', 'ST'],
                'Zip of Record': ['12345', '12345']
            })
            
            # Append to existing CSV
            existing_df = pd.read_csv(test_csv)
            combined_df = pd.concat([existing_df, new_data], ignore_index=True)
            combined_df.to_csv(test_csv, index=False)
            
            # Process with resume
            results2 = service.process_all_records(resume=True)
            
            # Should process only new records
            assert results2['statistics']['total_processed'] == 2
            assert results2['statistics']['successful'] == 2
            
            # Check final output
            output_df = pd.read_csv(os.path.join(temp_dir, 'output.csv'))
            assert len(output_df) == 7  # 5 original + 2 new
            assert all(output_df['Status'] == 'Complete')
    
    def test_validation_integration(self, sample_csv_data, sample_gold_standard_data, temp_dir, mock_logger):
        """Test integration between validation and other components."""
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
        
        # Test validation integration
        accuracy, validation_df = validator.validate_results(sample_csv_data)
        
        assert accuracy >= 80  # Should have high accuracy
        assert isinstance(validation_df, pd.DataFrame)
        assert len(validation_df) == 5
        
        # Check validation report
        report_file = os.path.join(temp_dir, 'validation_report.csv')
        if os.path.exists(report_file):
            report_df = pd.read_csv(report_file)
            assert len(report_df) == 5
            assert 'Is Match' in report_df.columns
            assert 'Similarity Score' in report_df.columns
    
    def test_end_to_end_workflow(self, sample_csv_data, temp_dir):
        """Test complete end-to-end workflow integration."""
        # Create test CSV
        test_csv = os.path.join(temp_dir, 'test.csv')
        sample_csv_data.to_csv(test_csv, index=False)
        
        # Create logger
        log_file = os.path.join(temp_dir, 'test.log')
        logger = Logger(log_file, log_level='INFO')
        
        # Create components
        processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), logger)
        
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            # Mock API client
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
                logger=logger
            )
            
            # Create service
            from headquarters_finder.utils.config import ProcessingConfig
            processing_config = ProcessingConfig(batch_size=50, save_interval=50, retry_attempts=3, delay_between_requests=0.1)
            service = HeadquartersService(client, processor, processing_config, logger)
            
            # Test complete workflow
            results = service.process_all_records(resume=False)
            
            # Verify results
            assert results['statistics']['total_processed'] == 5
            assert results['statistics']['successful'] == 5
            assert results['statistics']['failed'] == 0
            
            # Check output file
            assert os.path.exists(os.path.join(temp_dir, 'output.csv'))
            output_df = pd.read_csv(os.path.join(temp_dir, 'output.csv'))
            assert len(output_df) == 5
            assert all(output_df['Status'] == 'Complete')
            
            # Check log file
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert 'Starting headquarters processing' in log_content
                assert 'Headquarters processing completed' in log_content

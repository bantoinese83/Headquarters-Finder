"""
Unit tests for main.py - Headquarters Finder application entry point.

Tests the main application class, CLI interface, and complete workflow orchestration.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from headquarters_finder.main import HeadquartersFinderApp, main


class TestHeadquartersFinderApp:
    """Test the main HeadquartersFinderApp class."""

    def test_app_initialization_success(self):
        """Test successful application initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid config file
            config_content = """
[API]
api_key = test_key_12345
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
delay_between_requests = 0.1

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
"""
            config_file = os.path.join(temp_dir, 'config.ini')
            with open(config_file, 'w') as f:
                f.write(config_content)

            # Create test CSV
            test_csv = os.path.join(temp_dir, 'test_input.csv')
            sample_data = pd.DataFrame({
                'Payee Name of Record': ['Apple Inc.', 'Microsoft Corp.'],
                'Status': ['Pending', 'Pending'],
                'Address1 of Record': ['Address 1', 'Address 2'],
                'City of Record': ['City 1', 'City 2'],
                'State of Record': ['ST', 'ST'],
                'Zip of Record': ['12345', '12345']
            })
            sample_data.to_csv(test_csv, index=False)

            # Initialize app
            app = HeadquartersFinderApp(config_file)

            # Test initialization
            assert app.config_file == Path(config_file)
            assert app.config is None
            assert app.logger is None
            assert app.api_client is None
            assert app.csv_processor is None
            assert app.headquarters_service is None
            assert app.data_validator is None

    def test_app_initialization_config_file_not_found(self):
        """Test initialization with missing config file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            HeadquartersFinderApp("nonexistent_config.ini")

    @patch('headquarters_finder.main.Config')
    @patch('headquarters_finder.main.Logger')
    @patch('headquarters_finder.main.GeminiAPIClient')
    @patch('headquarters_finder.main.CSVProcessor')
    @patch('headquarters_finder.main.HeadquartersService')
    @patch('headquarters_finder.main.DataValidator')
    def test_initialize_success(self, mock_data_validator, mock_headquarters_service,
                               mock_csv_processor, mock_api_client, mock_logger, mock_config):
        """Test successful component initialization."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.validate_config.return_value = True
        mock_config_instance.get_file_config.return_value = {
            'input_file': 'test.csv', 'output_file': 'output.csv',
            'log_file': 'test.log', 'gold_standard_file': 'gold.csv'
        }
        mock_config_instance.get_logging_config.return_value = {
            'log_level': 'INFO', 'max_log_size': 10485760, 'backup_count': 3
        }
        mock_config_instance.get_api_config.return_value = {
            'api_key': 'test_key', 'model_name': 'gemini-2.5-pro',
            'temperature': 0.1, 'max_output_tokens': 8192
        }
        mock_config_instance.get_processing_config.return_value = {
            'batch_size': 50, 'save_interval': 50, 'retry_attempts': 3,
            'delay_between_requests': 0.1
        }
        mock_config.return_value = mock_config_instance

        mock_logger_instance = Mock()
        mock_logger_instance.info = Mock()
        mock_logger_instance.error = Mock()
        mock_logger.return_value = mock_logger_instance

        mock_api_client_instance = Mock()
        mock_api_client_instance.test_connection.return_value = True
        mock_api_client.return_value = mock_api_client_instance

        mock_csv_processor_instance = Mock()
        mock_csv_processor.return_value = mock_csv_processor_instance

        mock_headquarters_service_instance = Mock()
        mock_headquarters_service.return_value = mock_headquarters_service_instance

        mock_data_validator_instance = Mock()
        mock_data_validator.return_value = mock_data_validator_instance

        # Create app and initialize
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("[API]\napi_key = test\n")
            config_file = f.name

        try:
            app = HeadquartersFinderApp(config_file)
            result = app.initialize()

            # Verify initialization succeeded
            assert result is True
            assert app.config == mock_config_instance
            assert app.logger == mock_logger_instance
            assert app.api_client == mock_api_client_instance
            assert app.csv_processor == mock_csv_processor_instance
            assert app.headquarters_service == mock_headquarters_service_instance
            assert app.data_validator == mock_data_validator_instance

            # Verify method calls
            mock_config.assert_called_once_with(config_file)
            mock_config_instance.validate_config.assert_called_once()
            mock_logger.assert_called_once()
            mock_api_client.assert_called_once()
            mock_api_client_instance.test_connection.assert_called_once()
            mock_csv_processor.assert_called_once()
            mock_headquarters_service.assert_called_once()
            mock_data_validator.assert_called_once()

        finally:
            os.unlink(config_file)

    def test_initialize_config_validation_failure(self):
        """Test initialization with invalid configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("[API]\n# Missing api_key\n")
            config_file = f.name

        try:
            app = HeadquartersFinderApp(config_file)

            with patch('builtins.print') as mock_print:
                result = app.initialize()

                assert result is False
                mock_print.assert_called_once()
                assert "Invalid configuration" in mock_print.call_args[0][0]

        finally:
            os.unlink(config_file)

    def test_initialize_api_connection_failure(self):
        """Test initialization with API connection failure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("[API]\napi_key = test_key\n")
            config_file = f.name

        try:
            with patch('headquarters_finder.main.Config') as mock_config_class, \
                 patch('headquarters_finder.main.Logger') as mock_logger_class, \
                 patch('headquarters_finder.main.GeminiAPIClient') as mock_api_client_class:

                # Setup mocks
                mock_config = Mock()
                mock_config.validate_config.return_value = True
                mock_config.get_file_config.return_value = {'input_file': 'test.csv'}
                mock_config.get_logging_config.return_value = {'log_level': 'INFO'}
                mock_config.get_api_config.return_value = {'api_key': 'test_key'}
                mock_config.get_processing_config.return_value = {'batch_size': 50}
                mock_config_class.return_value = mock_config

                mock_logger = Mock()
                mock_logger_class.return_value = mock_logger

                mock_api_client = Mock()
                mock_api_client.test_connection.return_value = False
                mock_api_client_class.return_value = mock_api_client

                app = HeadquartersFinderApp(config_file)
                result = app.initialize()

                assert result is False
                mock_api_client.test_connection.assert_called_once()

        finally:
            os.unlink(config_file)

    def test_initialize_exception_handling(self):
        """Test initialization exception handling."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("[API]\napi_key = test_key\n")
            config_file = f.name

        try:
            with patch('headquarters_finder.main.Config') as mock_config_class:
                mock_config_class.side_effect = Exception("Test error")

                app = HeadquartersFinderApp(config_file)

                with patch('builtins.print') as mock_print:
                    result = app.initialize()

                    assert result is False
                    mock_print.assert_called_once()
                    assert "Failed to initialize application" in mock_print.call_args[0][0]

        finally:
            os.unlink(config_file)

    @patch('headquarters_finder.main.CSVProcessor')
    def test_run_workflow_with_pending_records(self, mock_csv_processor_class):
        """Test run method with pending records and time estimation."""
        # Setup mocks
        mock_csv_processor = Mock()
        mock_csv_processor.read_input_csv.return_value = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.', 'Microsoft Corp.'],
            'Status': ['Pending', 'Error'],
            'Address1 of Record': ['Address 1', 'Address 2'],
            'City of Record': ['City 1', 'City 2'],
            'State of Record': ['ST', 'ST'],
            'Zip of Record': ['12345', '12345']
        })
        mock_csv_processor_class.return_value = mock_csv_processor

        mock_headquarters_service = Mock()
        mock_headquarters_service.calculate_processing_time.return_value = {
            'total_records': 2,
            'estimated_time_hours': 0.5,
            'daily_capacity': 100,
            'can_process_today': True,
            'days_needed': 0.1
        }
        mock_headquarters_service.process_all_records.return_value = {
            'statistics': {'successful': 2, 'failed': 0, 'total_processed': 2},
            'output_file': 'output.csv'
        }

        # Create app with mocked components
        app = HeadquartersFinderApp.__new__(HeadquartersFinderApp)
        app.csv_processor = mock_csv_processor
        app.headquarters_service = mock_headquarters_service
        app.logger = Mock()
        app.logger.info = Mock()
        app.logger.warning = Mock()

        # Run workflow
        results = app.run(validate=False)

        # Verify results
        assert results['statistics']['successful'] == 2
        assert results['statistics']['failed'] == 0
        assert results['output_file'] == 'output.csv'

        # Verify method calls
        mock_csv_processor.read_input_csv.assert_called_once()
        mock_headquarters_service.calculate_processing_time.assert_called_once_with(2)
        mock_headquarters_service.process_all_records.assert_called_once_with(resume=True)

        # Verify logging calls
        assert app.logger.info.call_count >= 3  # At least 3 info calls
        app.logger.info.assert_any_call("Starting headquarters processing workflow")
        app.logger.info.assert_any_call("Tier 1 Processing Estimates:")

    @patch('headquarters_finder.main.CSVProcessor')
    def test_run_workflow_no_pending_records(self, mock_csv_processor_class):
        """Test run method with no pending records."""
        # Setup mocks
        mock_csv_processor = Mock()
        mock_csv_processor.read_input_csv.return_value = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.', 'Microsoft Corp.'],
            'Status': ['Complete', 'Complete'],
            'Address1 of Record': ['Address 1', 'Address 2'],
            'City of Record': ['City 1', 'City 2'],
            'State of Record': ['ST', 'ST'],
            'Zip of Record': ['12345', '12345']
        })
        mock_csv_processor_class.return_value = mock_csv_processor

        mock_headquarters_service = Mock()
        mock_headquarters_service.process_all_records.return_value = {
            'statistics': {'successful': 0, 'failed': 0, 'total_processed': 0},
            'output_file': 'output.csv'
        }

        # Create app with mocked components
        app = HeadquartersFinderApp.__new__(HeadquartersFinderApp)
        app.csv_processor = mock_csv_processor
        app.headquarters_service = mock_headquarters_service
        app.logger = Mock()
        app.logger.info = Mock()

        # Run workflow
        results = app.run(validate=False)

        # Verify results
        assert results['statistics']['successful'] == 0
        assert results['statistics']['failed'] == 0

        # Verify method calls
        mock_csv_processor.read_input_csv.assert_called_once()
        # calculate_processing_time should not be called when no pending records
        mock_headquarters_service.calculate_processing_time.assert_not_called()
        mock_headquarters_service.process_all_records.assert_called_once_with(resume=True)

    @patch('headquarters_finder.main.CSVProcessor')
    def test_run_workflow_with_validation(self, mock_csv_processor_class):
        """Test run method with validation against gold standard."""
        # Setup mocks
        mock_csv_processor = Mock()
        mock_csv_processor.read_input_csv.return_value = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.'],
            'Status': ['Pending'],
            'Address1 of Record': ['Address 1'],
            'City of Record': ['City 1'],
            'State of Record': ['ST'],
            'Zip of Record': ['12345']
        })
        mock_csv_processor_class.return_value = mock_csv_processor

        mock_headquarters_service = Mock()
        mock_headquarters_service.calculate_processing_time.return_value = {
            'total_records': 1, 'estimated_time_hours': 0.1, 'daily_capacity': 100,
            'can_process_today': True, 'days_needed': 0.01
        }
        mock_headquarters_service.process_all_records.return_value = {
            'statistics': {'successful': 1, 'failed': 0, 'total_processed': 1},
            'output_file': 'output.csv'
        }

        mock_data_validator = Mock()
        mock_data_validator.validate_against_gold_standard.return_value = {
            'accuracy': 95.0, 'total_compared': 1, 'matches': 1, 'mismatches': 0
        }
        mock_data_validator.generate_validation_report = Mock()

        # Create app with mocked components
        app = HeadquartersFinderApp.__new__(HeadquartersFinderApp)
        app.csv_processor = mock_csv_processor
        app.headquarters_service = mock_headquarters_service
        app.data_validator = mock_data_validator
        app.config = Mock()
        app.config.get_file_config.return_value = {'gold_standard_file': 'gold.csv'}
        app.logger = Mock()
        app.logger.info = Mock()
        app.logger.warning = Mock()

        # Run workflow with validation
        with patch('os.path.exists', return_value=True):
            results = app.run(validate=True)

        # Verify validation was called
        mock_data_validator.validate_against_gold_standard.assert_called_once_with(
            'output.csv', 'gold.csv'
        )
        mock_data_validator.generate_validation_report.assert_called_once()
        assert 'validation' in results
        assert 'validation_report' in results

    @patch('headquarters_finder.main.CSVProcessor')
    def test_run_workflow_gold_standard_not_found(self, mock_csv_processor_class):
        """Test run method when gold standard file doesn't exist."""
        # Setup mocks
        mock_csv_processor = Mock()
        mock_csv_processor.read_input_csv.return_value = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.'],
            'Status': ['Pending'],
            'Address1 of Record': ['Address 1'],
            'City of Record': ['City 1'],
            'State of Record': ['ST'],
            'Zip of Record': ['12345']
        })
        mock_csv_processor_class.return_value = mock_csv_processor

        mock_headquarters_service = Mock()
        mock_headquarters_service.calculate_processing_time.return_value = {
            'total_records': 1, 'estimated_time_hours': 0.1, 'daily_capacity': 100,
            'can_process_today': True, 'days_needed': 0.01
        }
        mock_headquarters_service.process_all_records.return_value = {
            'statistics': {'successful': 1, 'failed': 0, 'total_processed': 1},
            'output_file': 'output.csv'
        }

        # Create app with mocked components
        app = HeadquartersFinderApp.__new__(HeadquartersFinderApp)
        app.csv_processor = mock_csv_processor
        app.headquarters_service = mock_headquarters_service
        app.config = Mock()
        app.config.get_file_config.return_value = {'gold_standard_file': 'gold.csv'}
        app.logger = Mock()
        app.logger.info = Mock()
        app.logger.warning = Mock()

        # Run workflow with validation but gold file doesn't exist
        with patch('os.path.exists', return_value=False):
            results = app.run(validate=True)

        # Verify validation was skipped
        assert results['validation'] == {'error': 'Gold standard file not found'}
        assert 'validation_report' not in results

    def test_run_workflow_exception_handling(self):
        """Test run method exception handling."""
        # Create app with mocked components that raises exception
        app = HeadquartersFinderApp.__new__(HeadquartersFinderApp)
        app.headquarters_service = Mock()
        app.headquarters_service.process_all_records.side_effect = Exception("Test error")
        app.logger = Mock()
        app.logger.info = Mock()
        app.logger.error = Mock()

        # Run workflow and expect exception
        with pytest.raises(Exception, match="Test error"):
            app.run(validate=False)

        # Verify error was logged
        app.logger.error.assert_called_once_with("Error in main workflow: Test error")

    def test_print_summary(self):
        """Test print summary functionality."""
        # Create app
        app = HeadquartersFinderApp.__new__(HeadquartersFinderApp)

        # Test results
        results = {
            'statistics': {
                'total_processed': 100,
                'successful': 95,
                'failed': 5,
                'success_rate': 95.0,
                'processing_time_seconds': 120.5
            },
            'output_file': 'output.csv',
            'validation': {
                'accuracy': 92.0,
                'total_compared': 100,
                'matches': 92,
                'mismatches': 8,
                'validation_report': 'validation_report.md'
            }
        }

        # Print summary
        with patch('builtins.print') as mock_print:
            app.print_summary(results)

            # Verify print calls
            assert mock_print.call_count >= 9  # Multiple print calls
            mock_print.assert_any_call("\n" + "="*60)
            mock_print.assert_any_call("HEADQUARTERS FINDER - PROCESSING SUMMARY")
            mock_print.assert_any_call(f"Total Processed: 100")
            mock_print.assert_any_call(f"Successful: 95")
            mock_print.assert_any_call(f"Failed: 5")
            mock_print.assert_any_call(f"Success Rate: 95.0%")
            mock_print.assert_any_call(f"Processing Time: 120.5 seconds")
            mock_print.assert_any_call(f"\nOutput File: output.csv")
            mock_print.assert_any_call(f"\nValidation Results:")
            mock_print.assert_any_call(f"Accuracy: 92.0%")
            mock_print.assert_any_call(f"Records Compared: 100")
            mock_print.assert_any_call(f"Matches: 92")
            mock_print.assert_any_call(f"Mismatches: 8")
            mock_print.assert_any_call(f"Validation Report: validation_report.md")


class TestMainFunction:
    """Test the main() function and CLI interface."""

    @patch('headquarters_finder.main.HeadquartersFinderApp')
    def test_main_successful_run(self, mock_app_class):
        """Test successful main execution."""
        # Setup mocks
        mock_app = Mock()
        mock_app.initialize.return_value = True
        mock_app.run.return_value = {
            'statistics': {'successful': 10, 'failed': 0, 'total_processed': 10},
            'output_file': 'output.csv'
        }
        mock_app.print_summary = Mock()
        mock_app_class.return_value = mock_app

        # Mock command line arguments
        test_args = ['main.py', '--config', 'test_config.ini']

        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:

            # Run main function
            main()

            # Verify app was created and methods called
            mock_app_class.assert_called_once_with('test_config.ini')
            mock_app.initialize.assert_called_once()
            mock_app.run.assert_called_once_with(validate=False)
            mock_app.print_summary.assert_called_once()
            mock_print.assert_any_call("\nProcessing completed successfully!")

    @patch('headquarters_finder.main.HeadquartersFinderApp')
    def test_main_with_validation(self, mock_app_class):
        """Test main execution with validation flag."""
        # Setup mocks
        mock_app = Mock()
        mock_app.initialize.return_value = True
        mock_app.run.return_value = {
            'statistics': {'successful': 10, 'failed': 0, 'total_processed': 10},
            'output_file': 'output.csv',
            'validation': {'accuracy': 95.0}
        }
        mock_app.print_summary = Mock()
        mock_app_class.return_value = mock_app

        # Mock command line arguments with validation flag
        test_args = ['main.py', '--config', 'test_config.ini', '--validate']

        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:

            # Run main function
            main()

            # Verify validation was enabled
            mock_app.run.assert_called_once_with(validate=True)
            mock_print.assert_any_call("\nProcessing completed successfully!")

    @patch('headquarters_finder.main.HeadquartersFinderApp')
    def test_main_test_mode(self, mock_app_class):
        """Test main execution in test mode."""
        # Setup mocks
        mock_app = Mock()
        mock_app.initialize.return_value = True
        mock_app_class.return_value = mock_app

        # Mock command line arguments with test flag
        test_args = ['main.py', '--config', 'test_config.ini', '--test']

        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:

            # Run main function
            main()

            # Verify only initialization happened (no run)
            mock_app_class.assert_called_once_with('test_config.ini')
            mock_app.initialize.assert_called_once()
            mock_app.run.assert_not_called()
            mock_print.assert_any_call("API connection test successful!")

    @patch('headquarters_finder.main.HeadquartersFinderApp')
    def test_main_initialization_failure(self, mock_app_class):
        """Test main execution with initialization failure."""
        # Setup mocks
        mock_app = Mock()
        mock_app.initialize.return_value = False
        mock_app_class.return_value = mock_app

        # Mock command line arguments
        test_args = ['main.py', '--config', 'test_config.ini']

        with patch('sys.argv', test_args):

            # Run main function and expect exit
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    @patch('headquarters_finder.main.HeadquartersFinderApp')
    def test_main_keyboard_interrupt(self, mock_app_class):
        """Test main execution with keyboard interrupt."""
        # Setup mocks
        mock_app = Mock()
        mock_app.initialize.return_value = True
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_app.logger = Mock()
        mock_app_class.return_value = mock_app

        # Mock command line arguments
        test_args = ['main.py', '--config', 'test_config.ini']

        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:

            # Run main function and expect exit
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_print.assert_any_call("\nProcessing interrupted by user")
            mock_app.logger.info.assert_called_once_with("Processing interrupted by user")

    @patch('headquarters_finder.main.HeadquartersFinderApp')
    def test_main_general_exception(self, mock_app_class):
        """Test main execution with general exception."""
        # Setup mocks
        mock_app = Mock()
        mock_app.initialize.return_value = True
        mock_app.run.side_effect = Exception("Test error")
        mock_app.logger = Mock()
        mock_app_class.return_value = mock_app

        # Mock command line arguments
        test_args = ['main.py', '--config', 'test_config.ini']

        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:

            # Run main function and expect exit
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            mock_print.assert_any_call("\nERROR: Test error")
            mock_app.logger.error.assert_called_once_with("Application error: Test error")

    @patch('headquarters_finder.main.HeadquartersFinderApp')
    def test_main_validation_warning_low_accuracy(self, mock_app_class):
        """Test main execution with low validation accuracy warning."""
        # Setup mocks
        mock_app = Mock()
        mock_app.initialize.return_value = True
        mock_app.run.return_value = {
            'statistics': {'successful': 10, 'failed': 0, 'total_processed': 10},
            'output_file': 'output.csv',
            'validation': {'accuracy': 85.0}  # Below 90% threshold
        }
        mock_app.print_summary = Mock()
        mock_app_class.return_value = mock_app

        # Mock command line arguments with validation flag
        test_args = ['main.py', '--config', 'test_config.ini', '--validate']

        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:

            # Run main function
            main()

            # Verify warning was printed
            mock_print.assert_any_call("\nWARNING: Accuracy below 90% target: 85.0%")

    @patch('headquarters_finder.main.HeadquartersFinderApp')
    def test_main_validation_error(self, mock_app_class):
        """Test main execution with validation error."""
        # Setup mocks
        mock_app = Mock()
        mock_app.initialize.return_value = True
        mock_app.run.return_value = {
            'statistics': {'successful': 10, 'failed': 0, 'total_processed': 10},
            'output_file': 'output.csv',
            'validation': {'error': 'Gold standard file not found'}
        }
        mock_app.print_summary = Mock()
        mock_app_class.return_value = mock_app

        # Mock command line arguments with validation flag
        test_args = ['main.py', '--config', 'test_config.ini', '--validate']

        with patch('sys.argv', test_args), \
             patch('builtins.print') as mock_print:

            # Run main function
            main()

            # Verify error warning was printed
            mock_print.assert_any_call("\nWARNING: Validation failed - Gold standard file not found")

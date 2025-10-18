"""
Unit tests for CSVProcessor class.

Tests the CSVProcessor class with comprehensive coverage including
golden path scenarios, edge cases, and error conditions.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

from headquarters_finder.core.csv_processor import (
    CSVProcessor, 
    CSVProcessingError, 
    ProcessingStats
)


class TestProcessingStats:
    """Test cases for ProcessingStats dataclass."""
    
    def test_processing_stats_initialization(self):
        """Test ProcessingStats initialization with default values."""
        stats = ProcessingStats()
        assert stats.total_records == 0
        assert stats.processed_records == 0
        assert stats.pending_records == 0
        assert stats.completed_records == 0
        assert stats.error_records == 0
        assert stats.skipped_records == 0
    
    def test_processing_stats_custom_values(self):
        """Test ProcessingStats with custom values."""
        stats = ProcessingStats(
            total_records=100,
            processed_records=50,
            pending_records=25,
            completed_records=20,
            error_records=5,
            skipped_records=5
        )
        assert stats.total_records == 100
        assert stats.processed_records == 50
        assert stats.pending_records == 25
        assert stats.completed_records == 20
        assert stats.error_records == 5
        assert stats.skipped_records == 5


class TestCSVProcessor:
    """Test cases for CSVProcessor class."""
    
    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary input and output files for testing."""
        input_file = tmp_path / "test_input.csv"
        output_file = tmp_path / "test_output.csv"
        
        # Create sample input data
        sample_data = {
            'Geographic Location': ['State of California', 'Cook County, Illinois'],
            'Payee Name of Record': ['JTN HOSPICE INC', 'TUR VENTURES LLC'],
            'Address1 of Record': ['', '1200 E ALGONQUIN RD'],
            'Address 2 of Record': ['', ''],
            'City of Record': ['', 'MOUNT PROSPECT'],
            'State of Record': ['', 'IL'],
            'Zip of Record': ['', '60056'],
            'Status': ['Pending', 'Pending'],
            'Headquarters Address': ['', ''],
            'Processed_Timestamp': ['', ''],
            'Error_Message': ['', '']
        }
        df = pd.DataFrame(sample_data)
        df.to_csv(input_file, index=False)
        
        return str(input_file), str(output_file)
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        logger = Mock()
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()
        return logger
    
    def test_csv_processor_initialization(self, temp_files, mock_logger):
        """Test CSVProcessor initialization with valid files."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        assert processor.input_file == Path(input_file)
        assert processor.output_file == Path(output_file)
        assert processor.logger == mock_logger
    
    def test_csv_processor_initialization_file_not_found(self, mock_logger):
        """Test CSVProcessor initialization with non-existent input file."""
        # CSVProcessor should initialize successfully even with non-existent input file
        # The error should be raised when trying to read the file
        processor = CSVProcessor("non_existent.csv", "output.csv", mock_logger)
        assert processor.input_file == Path("non_existent.csv")
        assert processor.output_file == Path("output.csv")
    
    def test_csv_processor_initialization_creates_output_dir(self, tmp_path, mock_logger):
        """Test CSVProcessor creates output directory if it doesn't exist."""
        input_file = tmp_path / "test_input.csv"
        output_file = tmp_path / "subdir" / "test_output.csv"
        
        # Create input file
        pd.DataFrame({'Payee Name of Record': ['Test Company']}).to_csv(input_file, index=False)
        
        processor = CSVProcessor(str(input_file), str(output_file), mock_logger)
        assert processor.output_file.parent.exists()
    
    def test_read_input_csv_success(self, temp_files, mock_logger):
        """Test successful reading of input CSV file."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        df = processor.read_input_csv()
        
        assert len(df) == 2
        assert 'Payee Name of Record' in df.columns
        assert 'Status' in df.columns
        assert 'Headquarters Address' in df.columns
        assert 'Processed_Timestamp' in df.columns
        assert 'Error_Message' in df.columns
        mock_logger.info.assert_called()
    
    def test_read_input_csv_missing_required_column(self, tmp_path, mock_logger):
        """Test reading CSV with missing required column."""
        input_file = tmp_path / "test_input.csv"
        output_file = tmp_path / "test_output.csv"
        
        # Create CSV without required column
        pd.DataFrame({'Other Column': ['Value']}).to_csv(input_file, index=False)
        
        processor = CSVProcessor(str(input_file), str(output_file), mock_logger)
        
        with pytest.raises(CSVProcessingError, match="Input CSV must contain 'Payee Name of Record' column"):
            processor.read_input_csv()
    
    def test_read_input_csv_empty_file(self, tmp_path, mock_logger):
        """Test reading empty CSV file."""
        input_file = tmp_path / "empty.csv"
        output_file = tmp_path / "test_output.csv"
        
        # Create empty CSV
        pd.DataFrame().to_csv(input_file, index=False)
        
        processor = CSVProcessor(str(input_file), str(output_file), mock_logger)
        df = processor.read_input_csv()
        
        assert df.empty
        mock_logger.warning.assert_called()
    
    def test_read_input_csv_file_not_found(self, mock_logger):
        """Test reading non-existent CSV file."""
        processor = CSVProcessor("non_existent.csv", "output.csv", mock_logger)
        
        with pytest.raises(FileNotFoundError):
            processor.read_input_csv()
    
    def test_write_output_csv_success(self, temp_files, mock_logger):
        """Test successful writing of output CSV file."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        df = pd.DataFrame({'Test Column': ['Test Value']})
        processor.write_output_csv(df)
        
        assert Path(output_file).exists()
        mock_logger.info.assert_called()
    
    def test_write_output_csv_error(self, temp_files, mock_logger):
        """Test writing CSV with error handling."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        # Create invalid DataFrame that will cause write error
        df = Mock()
        df.to_csv.side_effect = Exception("Write error")
        
        with pytest.raises(CSVProcessingError, match="Failed to write output CSV"):
            processor.write_output_csv(df)
    
    def test_get_records_to_process(self, temp_files, mock_logger):
        """Test filtering records to process."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        df = pd.DataFrame({
            'Status': ['Pending', 'Complete', 'Error', 'Pending'],
            'Payee Name of Record': ['Company1', 'Company2', 'Company3', 'Company4']
        })
        
        result = processor.get_records_to_process(df)
        
        assert len(result) == 3  # Pending, Error, Pending
        assert all(status in ['Pending', 'Error'] for status in result['Status'])
    
    def test_update_record_status(self, temp_files, mock_logger):
        """Test updating record status."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        df = pd.DataFrame({
            'Status': ['Pending'],
            'Headquarters Address': [''],
            'Processed_Timestamp': [''],
            'Error_Message': ['']
        })
        
        processor.update_record_status(
            df, 0, 'Complete', '123 Main St', 'No errors'
        )
        
        assert df.at[0, 'Status'] == 'Complete'
        assert df.at[0, 'Headquarters Address'] == '123 Main St'
        assert df.at[0, 'Error_Message'] == 'No errors'
        assert df.at[0, 'Processed_Timestamp'] != ''
    
    def test_load_existing_output_success(self, temp_files, mock_logger):
        """Test loading existing output file."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        # Create existing output file
        existing_data = pd.DataFrame({
            'Payee Name of Record': ['Existing Company'],
            'Status': ['Complete']
        })
        existing_data.to_csv(output_file, index=False)
        
        result = processor.load_existing_output()
        
        assert len(result) == 1
        assert result.at[0, 'Payee Name of Record'] == 'Existing Company'
        mock_logger.info.assert_called()
    
    def test_load_existing_output_file_not_found(self, temp_files, mock_logger):
        """Test loading non-existent output file."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        result = processor.load_existing_output()
        
        assert result.empty
    
    def test_load_existing_output_empty_file(self, temp_files, mock_logger):
        """Test loading empty output file."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        # Create empty output file
        pd.DataFrame().to_csv(output_file, index=False)
        
        result = processor.load_existing_output()
        
        assert result.empty
        mock_logger.warning.assert_called()
    
    def test_merge_dataframes_empty_existing(self, temp_files, mock_logger):
        """Test merging with empty existing data."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        input_df = pd.DataFrame({
            'Payee Name of Record': ['Company1'],
            'Status': ['Pending']
        })
        existing_df = pd.DataFrame()
        
        result = processor.merge_dataframes(input_df, existing_df)
        
        assert len(result) == 1
        assert result.at[0, 'Payee Name of Record'] == 'Company1'
    
    def test_merge_dataframes_with_existing(self, temp_files, mock_logger):
        """Test merging with existing data."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        input_df = pd.DataFrame({
            'Payee Name of Record': ['Company1', 'Company2'],
            'Status': ['Pending', 'Pending']
        })
        existing_df = pd.DataFrame({
            'Payee Name of Record': ['Company1'],
            'Status': ['Complete'],
            'Headquarters Address': ['123 Main St']
        })
        
        result = processor.merge_dataframes(input_df, existing_df)
        
        assert len(result) == 2
        # Company1 should be updated with existing data
        company1_row = result[result['Payee Name of Record'] == 'Company1'].iloc[0]
        assert company1_row['Status'] == 'Complete'
        assert company1_row['Headquarters Address'] == '123 Main St'
        # Company2 should remain unchanged
        company2_row = result[result['Payee Name of Record'] == 'Company2'].iloc[0]
        assert company2_row['Status'] == 'Pending'
    
    def test_merge_dataframes_missing_columns(self, temp_files, mock_logger):
        """Test merging when existing data is missing required columns."""
        input_file, output_file = temp_files
        processor = CSVProcessor(input_file, output_file, mock_logger)
        
        input_df = pd.DataFrame({
            'Payee Name of Record': ['Company1'],
            'Status': ['Pending']
        })
        existing_df = pd.DataFrame({
            'Payee Name of Record': ['Company1'],
            'Other Column': ['Value']
        })
        
        result = processor.merge_dataframes(input_df, existing_df)
        
        assert len(result) == 1
        assert result.at[0, 'Payee Name of Record'] == 'Company1'
        assert result.at[0, 'Status'] == 'Pending'


class TestCSVProcessingError:
    """Test cases for CSVProcessingError exception."""
    
    def test_csv_processing_error_creation(self):
        """Test CSVProcessingError creation."""
        error = CSVProcessingError("Test error message")
        assert str(error) == "Test error message"
    
    def test_csv_processing_error_with_cause(self):
        """Test CSVProcessingError with cause."""
        original_error = ValueError("Original error")
        error = CSVProcessingError("Test error message")
        error.__cause__ = original_error
        assert str(error) == "Test error message"

    def test_processing_stats_duration_calculation(self):
        """Test ProcessingStats duration calculation."""
        from datetime import datetime, timedelta

        stats = ProcessingStats()
        stats.start_time = datetime.now() - timedelta(hours=2, minutes=30, seconds=45)
        stats.end_time = datetime.now()

        duration = stats.duration()
        assert "2h 30m 45.00s" in duration or "2h 30m" in duration  # Format may vary slightly

    def test_processing_stats_duration_no_times(self):
        """Test ProcessingStats duration when no times are set."""
        stats = ProcessingStats()
        assert stats.duration() == "N/A"

    def test_processing_stats_duration_partial_times(self):
        """Test ProcessingStats duration with only start time."""
        from datetime import datetime

        stats = ProcessingStats()
        stats.start_time = datetime.now()
        # end_time is None
        assert stats.duration() == "N/A"

    def test_processing_stats_format_duration_hours(self):
        """Test ProcessingStats duration formatting for hours."""
        from datetime import timedelta

        stats = ProcessingStats()
        duration = timedelta(hours=3, minutes=15, seconds=30)
        formatted = stats._format_duration(duration)
        assert formatted == "3h 15m 30.00s"

    def test_processing_stats_format_duration_minutes(self):
        """Test ProcessingStats duration formatting for minutes."""
        from datetime import timedelta

        stats = ProcessingStats()
        duration = timedelta(minutes=45, seconds=30)
        formatted = stats._format_duration(duration)
        assert formatted == "45m 30.00s"

    def test_processing_stats_format_duration_seconds(self):
        """Test ProcessingStats duration formatting for seconds."""
        from datetime import timedelta

        stats = ProcessingStats()
        duration = timedelta(seconds=30)
        formatted = stats._format_duration(duration)
        assert formatted == "30.00s"

    def test_processing_stats_reset(self):
        """Test ProcessingStats reset functionality."""
        stats = ProcessingStats(
            total_records=100,
            processed_records=50,
            pending_records=25,
            completed_records=20,
            error_records=5,
            skipped_records=5,
            accuracy=80.0
        )
        from datetime import datetime
        stats.start_time = datetime.now()
        stats.end_time = datetime.now()

        stats.reset()

        assert stats.total_records == 0
        assert stats.processed_records == 0
        assert stats.pending_records == 0
        assert stats.completed_records == 0
        assert stats.error_records == 0
        assert stats.skipped_records == 0
        assert stats.accuracy == 0.0
        assert stats.start_time is None
        assert stats.end_time is None

    def test_csv_processor_initialization_directory_creation_failure(self, mock_logger):
        """Test CSVProcessor initialization with directory creation failure."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = OSError("Permission denied")

            with pytest.raises(OSError, match="Failed to create output directory"):
                CSVProcessor("input.csv", "/root/forbidden/output.csv", mock_logger)

    def test_csv_processor_read_input_csv_encoding_error(self, temp_files, mock_logger):
        """Test CSV reading with encoding error."""
        input_file, output_file = temp_files

        # Create a file with invalid UTF-8 content
        with open(input_file, 'wb') as f:
            f.write(b'\xff\xfeinvalid utf8 content')

        processor = CSVProcessor(input_file, output_file, mock_logger)

        with pytest.raises(Exception):  # Should raise some kind of exception
            processor.read_input_csv()

    def test_csv_processor_write_output_csv_error(self, temp_files, mock_logger):
        """Test CSV writing with error."""
        input_file, output_file = temp_files

        processor = CSVProcessor(input_file, output_file, mock_logger)

        # Create a DataFrame
        df = pd.DataFrame({'test': ['data']})

        # Mock to_csv to raise an exception
        with patch.object(df, 'to_csv', side_effect=Exception("Disk full")):
            with pytest.raises(CSVProcessingError, match="Failed to write output CSV"):
                processor.write_output_csv(df)

    def test_csv_processor_merge_dataframes_missing_columns(self, mock_logger):
        """Test DataFrame merging with missing columns."""
        input_df = pd.DataFrame({
            'Payee Name of Record': ['Company A', 'Company B'],
            'Status': ['Pending', 'Complete']
        })

        existing_df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Complete'],
            'Headquarters Address': ['123 Main St'],
            'Processed_Timestamp': ['2023-01-01'],
            'Error_Message': [''],
            'Custom_Column': ['custom_value']  # Column that doesn't exist in input
        })

        processor = CSVProcessor("input.csv", "output.csv", mock_logger)
        result = processor.merge_dataframes(input_df, existing_df)

        # Should have all columns from both DataFrames
        assert 'Custom_Column' in result.columns
        assert len(result) == 2

    def test_csv_processor_save_progress_with_batch_info(self, temp_files, mock_logger):
        """Test saving progress with batch information."""
        input_file, output_file = temp_files

        processor = CSVProcessor(input_file, output_file, mock_logger)

        df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Complete']
        })

        processor.save_progress(df, "Batch 1/10 completed")

        mock_logger.info.assert_called_with("Progress saved: Batch 1/10 completed")

    def test_csv_processor_save_progress_without_batch_info(self, temp_files, mock_logger):
        """Test saving progress without batch information."""
        input_file, output_file = temp_files

        processor = CSVProcessor(input_file, output_file, mock_logger)

        df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Complete']
        })

        processor.save_progress(df)

        mock_logger.info.assert_called_with("Progress saved to output file")

    def test_csv_processor_save_progress_exception_handling(self, temp_files, mock_logger):
        """Test saving progress with exception handling."""
        input_file, output_file = temp_files

        processor = CSVProcessor(input_file, output_file, mock_logger)

        df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Complete']
        })

        # Mock to_csv to raise an exception
        with patch.object(df, 'to_csv', side_effect=Exception("Disk error")):
            with pytest.raises(Exception, match="Disk error"):
                processor.save_progress(df)

            mock_logger.error.assert_called_once()

    def test_csv_processor_load_existing_output_exception_handling(self, temp_files, mock_logger):
        """Test loading existing output with exception handling."""
        input_file, output_file = temp_files

        # Create a file that exists but has invalid CSV content
        with open(output_file, 'w') as f:
            f.write("invalid,csv,content\nmissing,proper,structure")

        processor = CSVProcessor(input_file, output_file, mock_logger)

        result = processor.load_existing_output()

        # Should return empty DataFrame and log warning
        assert result.empty
        mock_logger.warning.assert_called_once()

    def test_csv_processor_merge_with_existing_exception_handling(self, mock_logger):
        """Test merging with existing data exception handling."""
        input_df = pd.DataFrame({
            'Payee Name of Record': ['Company A']
        })

        existing_df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Complete']
        })

        processor = CSVProcessor("input.csv", "output.csv", mock_logger)

        # Mock pandas operations to raise exception
        with patch('pandas.DataFrame.copy', side_effect=Exception("Memory error")):
            result = processor.merge_with_existing(input_df, existing_df)

            # Should return input_df as fallback
            pd.testing.assert_frame_equal(result, input_df)
            mock_logger.error.assert_called_once()

    def test_csv_processor_get_processing_summary(self, mock_logger):
        """Test getting processing summary."""
        df = pd.DataFrame({
            'Status': ['Pending', 'Complete', 'Error', 'Pending', 'Complete']
        })

        processor = CSVProcessor("input.csv", "output.csv", mock_logger)
        summary = processor.get_processing_summary(df)

        assert summary['Total'] == 5
        assert summary['Pending'] == 2
        assert summary['Complete'] == 2
        assert summary['Error'] == 1

    def test_csv_processor_get_processing_summary_empty_dataframe(self, mock_logger):
        """Test getting processing summary with empty DataFrame."""
        df = pd.DataFrame()

        processor = CSVProcessor("input.csv", "output.csv", mock_logger)
        summary = processor.get_processing_summary(df)

        assert summary['Total'] == 0
        assert summary['Pending'] == 0
        assert summary['Complete'] == 0
        assert summary['Error'] == 0

    def test_csv_processor_export_validation_report_success(self, temp_files, mock_logger):
        """Test successful validation report export."""
        input_file, output_file = temp_files

        processor = CSVProcessor(input_file, output_file, mock_logger)

        df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Complete']
        })

        validation_results = {
            'status': 'Completed',
            'accuracy': 95.0,
            'notes': 'High accuracy achieved'
        }

        report_file = processor.export_validation_report(df, validation_results)

        expected_report_file = output_file.replace('.csv', '_validation_report.csv')
        assert report_file == expected_report_file
        assert os.path.exists(expected_report_file)

        # Check report content
        report_df = pd.read_csv(expected_report_file)
        assert 'Validation_Status' in report_df.columns
        assert 'Accuracy_Score' in report_df.columns
        assert 'Validation_Notes' in report_df.columns

    def test_csv_processor_export_validation_report_exception_handling(self, temp_files, mock_logger):
        """Test validation report export exception handling."""
        input_file, output_file = temp_files

        processor = CSVProcessor(input_file, output_file, mock_logger)

        df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Complete']
        })

        validation_results = {
            'status': 'Completed',
            'accuracy': 95.0,
            'notes': 'High accuracy achieved'
        }

        # Mock to_csv to raise exception
        with patch.object(df, 'to_csv', side_effect=Exception("Disk error")):
            report_file = processor.export_validation_report(df, validation_results)

            assert report_file == ""
            mock_logger.error.assert_called_once()

    def test_csv_processor_update_record_status_with_dict(self, mock_logger):
        """Test updating record status with dictionary data."""
        df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Pending'],
            'Processed_Timestamp': [''],
            'Error_Message': [''],
            'HQ_Street_Address': [''],
            'HQ_City': [''],
            'HQ_State': [''],
            'HQ_ZIP': [''],
            'HQ_Country': [''],
            'Headquarters Address': ['']
        })

        processor = CSVProcessor("input.csv", "output.csv", mock_logger)

        headquarters_data = {
            'HQ_Street_Address': '123 Main St',
            'HQ_City': 'Anytown',
            'HQ_State': 'CA',
            'HQ_ZIP': '12345',
            'HQ_Country': 'USA'
        }

        processor.update_record_status(df, 0, 'Complete', headquarters_data)

        assert df.at[0, 'Status'] == 'Complete'
        assert 'Processed_Timestamp' in df.columns
        assert df.at[0, 'HQ_Street_Address'] == '123 Main St'
        assert df.at[0, 'HQ_City'] == 'Anytown'

    def test_csv_processor_update_record_status_with_string(self, mock_logger):
        """Test updating record status with string data."""
        df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Pending'],
            'Processed_Timestamp': [''],
            'Error_Message': [''],
            'Headquarters Address': ['']
        })

        processor = CSVProcessor("input.csv", "output.csv", mock_logger)

        processor.update_record_status(df, 0, 'Complete', '123 Main St, Anytown, CA 12345, USA')

        assert df.at[0, 'Status'] == 'Complete'
        assert 'Processed_Timestamp' in df.columns
        assert df.at[0, 'Headquarters Address'] == '123 Main St, Anytown, CA 12345, USA'

    def test_csv_processor_update_record_status_with_error(self, mock_logger):
        """Test updating record status with error message."""
        df = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Status': ['Pending'],
            'Processed_Timestamp': [''],
            'Error_Message': ['']
        })

        processor = CSVProcessor("input.csv", "output.csv", mock_logger)

        processor.update_record_status(df, 0, 'Error', error_message='API quota exceeded')

        assert df.at[0, 'Status'] == 'Error'
        assert 'Processed_Timestamp' in df.columns
        assert df.at[0, 'Error_Message'] == 'API quota exceeded'

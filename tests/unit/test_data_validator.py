"""
Unit tests for DataValidator class.

Tests the data validation functionality with comprehensive coverage including
golden path scenarios, edge cases, and error conditions.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

from headquarters_finder.core.data_validator import DataValidator
from headquarters_finder.utils.config import FileConfig


class TestDataValidator:
    """Test cases for DataValidator class."""
    
    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary files for testing."""
        gold_standard_file = tmp_path / "gold_standard.csv"
        output_file = tmp_path / "output.csv"
        
        return str(gold_standard_file), str(output_file)
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        logger = Mock()
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.debug = Mock()
        return logger
    
    @pytest.fixture
    def file_config(self, temp_files):
        """Create file configuration for testing."""
        gold_standard_file, output_file = temp_files
        return FileConfig(
            input_file="input.csv",
            output_file=output_file,
            log_file="log.log",
            gold_standard_file=gold_standard_file
        )
    
    @pytest.fixture
    def sample_processed_data(self):
        """Create sample processed data for testing."""
        return pd.DataFrame({
            'Payee Name of Record': [
                'Google Inc.',
                'Apple Inc.',
                'Microsoft Corporation',
                'Amazon.com Inc.',
                'Not Found Company'
            ],
            'Headquarters Address': [
                '1600 Amphitheatre Parkway, Mountain View, CA 94043, USA',
                '1 Apple Park Way, Cupertino, CA 95014, USA',
                'One Microsoft Way, Redmond, WA 98052, USA',
                '410 Terry Avenue North, Seattle, WA 98109, USA',
                'Not Found'
            ]
        })
    
    @pytest.fixture
    def sample_gold_standard_data(self):
        """Create sample gold standard data for testing."""
        return pd.DataFrame({
            'Payee Name of Record': [
                'Google Inc.',
                'Apple Inc.',
                'Microsoft Corporation',
                'Amazon.com Inc.',
                'Not Found Company'
            ],
            'Headquarters Address': [
                '1600 Amphitheatre Parkway, Mountain View, CA 94043, USA',
                '1 Apple Park Way, Cupertino, CA 95014, USA',
                'One Microsoft Way, Redmond, WA 98052, USA',
                '410 Terry Avenue North, Seattle, WA 98109, USA',
                'Not Found'
            ]
        })
    
    def test_data_validator_initialization(self, file_config, mock_logger):
        """Test DataValidator initialization."""
        validator = DataValidator(file_config, mock_logger)
        
        assert validator.file_config == file_config
        assert validator.logger == mock_logger
        assert validator.gold_standard_csv == file_config.gold_standard_file
    
    def test_normalize_address_empty_string(self, file_config, mock_logger):
        """Test address normalization with empty string."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_address("")
        assert result == ""
    
    def test_normalize_address_none(self, file_config, mock_logger):
        """Test address normalization with None."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_address(None)
        assert result == ""
    
    def test_normalize_address_nan_string(self, file_config, mock_logger):
        """Test address normalization with 'nan' string."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_address("nan")
        assert result == ""
    
    def test_normalize_address_valid_address(self, file_config, mock_logger):
        """Test address normalization with valid address."""
        validator = DataValidator(file_config, mock_logger)
        
        address = "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA"
        result = validator._normalize_address(address)
        
        expected = "1600 amphitheatre parkway mountain view ca 94043 usa"
        assert result == expected
    
    def test_normalize_address_with_punctuation(self, file_config, mock_logger):
        """Test address normalization with punctuation."""
        validator = DataValidator(file_config, mock_logger)
        
        address = "123 Main St., Suite #100, New York, NY 10001-1234, USA!"
        result = validator._normalize_address(address)
        
        expected = "123 main st suite 100 new york ny 10001 1234 usa"
        assert result == expected
    
    def test_normalize_address_multiple_spaces(self, file_config, mock_logger):
        """Test address normalization with multiple spaces."""
        validator = DataValidator(file_config, mock_logger)
        
        address = "123   Main    St    New    York"
        result = validator._normalize_address(address)
        
        expected = "123 main st new york"
        assert result == expected
    
    def test_normalize_company_name_empty_string(self, file_config, mock_logger):
        """Test company name normalization with empty string."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name("")
        assert result == ""
    
    def test_normalize_company_name_none(self, file_config, mock_logger):
        """Test company name normalization with None."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name(None)
        assert result == ""
    
    def test_normalize_company_name_nan_string(self, file_config, mock_logger):
        """Test company name normalization with 'nan' string."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name("nan")
        assert result == ""
    
    def test_normalize_company_name_with_inc_suffix(self, file_config, mock_logger):
        """Test company name normalization with Inc. suffix."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name("Google Inc.")
        expected = "google"
        assert result == expected
    
    def test_normalize_company_name_with_llc_suffix(self, file_config, mock_logger):
        """Test company name normalization with LLC suffix."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name("Test Company LLC")
        expected = "test company"
        assert result == expected
    
    def test_normalize_company_name_with_corp_suffix(self, file_config, mock_logger):
        """Test company name normalization with Corp suffix."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name("Microsoft Corporation")
        expected = "microsoft"
        assert result == expected
    
    def test_normalize_company_name_with_gmbh_suffix(self, file_config, mock_logger):
        """Test company name normalization with GmbH suffix."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name("SAP GmbH")
        expected = "sap"
        assert result == expected
    
    def test_normalize_company_name_with_punctuation(self, file_config, mock_logger):
        """Test company name normalization with punctuation."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name("Test & Company, Inc.")
        expected = "test  company"
        assert result == expected
    
    def test_normalize_company_name_multiple_spaces(self, file_config, mock_logger):
        """Test company name normalization with multiple spaces."""
        validator = DataValidator(file_config, mock_logger)
        
        result = validator._normalize_company_name("Test   Company   Inc")
        expected = "test company"
        assert result == expected
    
    def test_validate_results_no_gold_standard_file(self, file_config, mock_logger, sample_processed_data):
        """Test validation when no gold standard file exists."""
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(sample_processed_data)
        
        assert accuracy == 0.0
        assert validation_df.empty
        mock_logger.warning.assert_called()
    
    def test_validate_results_gold_standard_file_not_found(self, file_config, mock_logger, sample_processed_data):
        """Test validation when gold standard file doesn't exist."""
        # Set non-existent file
        file_config.gold_standard_file = "non_existent.csv"
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(sample_processed_data)
        
        assert accuracy == 0.0
        assert validation_df.empty
        mock_logger.warning.assert_called()
    
    def test_validate_results_gold_standard_load_error(self, file_config, mock_logger, sample_processed_data):
        """Test validation when gold standard file fails to load."""
        # Create a file that will cause load error
        Path(file_config.gold_standard_file).write_text("invalid,csv,content\nwith,missing,columns")
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(sample_processed_data)
        
        assert accuracy == 0.0
        assert validation_df.empty
        mock_logger.error.assert_called()
    
    def test_validate_results_missing_processed_columns(self, file_config, mock_logger, sample_gold_standard_data):
        """Test validation when processed data is missing required columns."""
        # Create gold standard file
        sample_gold_standard_data.to_csv(file_config.gold_standard_file, index=False)
        
        # Create processed data missing required columns
        processed_data = pd.DataFrame({'Other Column': ['Value']})
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(processed_data)
        
        assert accuracy == 0.0
        assert validation_df.empty
        mock_logger.error.assert_called()
    
    def test_validate_results_missing_gold_standard_columns(self, file_config, mock_logger, sample_processed_data):
        """Test validation when gold standard data is missing required columns."""
        # Create processed data
        sample_processed_data.to_csv(file_config.output_file, index=False)
        
        # Create gold standard data missing required columns
        gold_data = pd.DataFrame({'Other Column': ['Value']})
        gold_data.to_csv(file_config.gold_standard_file, index=False)
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(sample_processed_data)
        
        assert accuracy == 0.0
        assert validation_df.empty
        mock_logger.error.assert_called()
    
    def test_validate_results_no_matching_records(self, file_config, mock_logger):
        """Test validation when no records match between datasets."""
        # Create processed data
        processed_data = pd.DataFrame({
            'Payee Name of Record': ['Company A'],
            'Headquarters Address': ['Address A']
        })
        processed_data.to_csv(file_config.output_file, index=False)
        
        # Create gold standard data with different company
        gold_data = pd.DataFrame({
            'Payee Name of Record': ['Company B'],
            'Headquarters Address': ['Address B']
        })
        gold_data.to_csv(file_config.gold_standard_file, index=False)
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(processed_data)
        
        assert accuracy == 0.0
        assert validation_df.empty
        mock_logger.warning.assert_called()
    
    def test_validate_results_perfect_match(self, file_config, mock_logger, sample_processed_data, sample_gold_standard_data):
        """Test validation with perfect matches."""
        # Create gold standard file
        sample_gold_standard_data.to_csv(file_config.gold_standard_file, index=False)
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(sample_processed_data)
        
        assert accuracy == 100.0
        assert len(validation_df) == 5
        assert all(validation_df['Is Match'])
        mock_logger.info.assert_called()
    
    def test_validate_results_partial_match(self, file_config, mock_logger):
        """Test validation with partial matches."""
        # Create processed data
        processed_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.', 'Apple Inc.'],
            'Headquarters Address': [
                '1600 Amphitheatre Parkway, Mountain View, CA 94043, USA',
                '1 Apple Park Way, Cupertino, CA 95014, USA'
            ]
        })
        processed_data.to_csv(file_config.output_file, index=False)
        
        # Create gold standard data with one match and one mismatch
        gold_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.', 'Apple Inc.'],
            'Headquarters Address': [
                '1600 Amphitheatre Parkway, Mountain View, CA 94043, USA',
                'Different Address, Different City, CA 12345, USA'
            ]
        })
        gold_data.to_csv(file_config.gold_standard_file, index=False)
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(processed_data)
        
        assert accuracy == 50.0  # 1 out of 2 matches
        assert len(validation_df) == 2
        assert validation_df['Is Match'].sum() == 1
        mock_logger.info.assert_called()
    
    def test_validate_results_fuzzy_match(self, file_config, mock_logger):
        """Test validation with fuzzy matching."""
        # Create processed data
        processed_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.'],
            'Headquarters Address': ['1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA']
        })
        processed_data.to_csv(file_config.output_file, index=False)
        
        # Create gold standard data with slightly different address
        gold_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.'],
            'Headquarters Address': ['1600 Amphitheatre Parkway, Mountain View, CA 94043, USA']
        })
        gold_data.to_csv(file_config.gold_standard_file, index=False)
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(processed_data)
        
        # Should match due to high similarity (above 0.8 threshold)
        assert accuracy == 100.0
        assert len(validation_df) == 1
        assert validation_df['Is Match'].iloc[0] == True
        assert validation_df['Similarity Score'].iloc[0] >= 0.8
    
    def test_validate_results_low_similarity_no_match(self, file_config, mock_logger):
        """Test validation with low similarity scores."""
        # Create processed data
        processed_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.'],
            'Headquarters Address': ['123 Main St, Anytown, NY 12345, USA']
        })
        processed_data.to_csv(file_config.output_file, index=False)
        
        # Create gold standard data with very different address
        gold_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.'],
            'Headquarters Address': ['1600 Amphitheatre Parkway, Mountain View, CA 94043, USA']
        })
        gold_data.to_csv(file_config.gold_standard_file, index=False)
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(processed_data)
        
        assert accuracy == 0.0
        assert len(validation_df) == 1
        assert validation_df['Is Match'].iloc[0] == False
        assert validation_df['Similarity Score'].iloc[0] < 0.8
    
    def test_validate_results_empty_addresses(self, file_config, mock_logger):
        """Test validation with empty addresses."""
        # Create processed data
        processed_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.'],
            'Headquarters Address': ['']
        })
        processed_data.to_csv(file_config.output_file, index=False)
        
        # Create gold standard data
        gold_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.'],
            'Headquarters Address': ['']
        })
        gold_data.to_csv(file_config.gold_standard_file, index=False)
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(processed_data)
        
        # Empty addresses should not match
        assert accuracy == 0.0
        assert len(validation_df) == 1
        assert validation_df['Is Match'].iloc[0] == False
    
    def test_validate_results_creates_validation_report(self, file_config, mock_logger, sample_processed_data, sample_gold_standard_data):
        """Test validation creates detailed validation report."""
        # Create gold standard file
        sample_gold_standard_data.to_csv(file_config.gold_standard_file, index=False)
        
        validator = DataValidator(file_config, mock_logger)
        
        accuracy, validation_df = validator.validate_results(sample_processed_data)
        
        # Check if validation report file was created
        report_file = Path(file_config.output_file).parent / "validation_report.csv"
        assert report_file.exists()
        
        # Check report content
        report_df = pd.read_csv(report_file)
        assert len(report_df) == 5
        assert 'Payee Name of Record' in report_df.columns
        assert 'Processed Address' in report_df.columns
        assert 'Gold Standard Address' in report_df.columns
        assert 'Is Match' in report_df.columns
        assert 'Similarity Score' in report_df.columns
        
        mock_logger.info.assert_called()
    
    def test_validate_results_debug_logging(self, file_config, mock_logger):
        """Test validation debug logging for mismatches."""
        # Create processed data
        processed_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.'],
            'Headquarters Address': ['123 Main Street, New York, NY 10001']
        })
        processed_data.to_csv(file_config.output_file, index=False)

        # Create gold standard data with very different address
        gold_data = pd.DataFrame({
            'Payee Name of Record': ['Google Inc.'],
            'Headquarters Address': ['456 Oak Avenue, Los Angeles, CA 90210']
        })
        gold_data.to_csv(file_config.gold_standard_file, index=False)

        validator = DataValidator(file_config, mock_logger)

        accuracy, validation_df = validator.validate_results(processed_data)

        # Should log debug message for mismatch
        mock_logger.debug.assert_called()
        debug_call = mock_logger.debug.call_args[0][0]
        assert "Mismatch for Google Inc." in debug_call

    def test_normalize_company_name_with_ampersand(self, file_config, mock_logger):
        """Test company name normalization with ampersand."""
        validator = DataValidator(file_config, mock_logger)

        # Test with ampersand
        result = validator._normalize_company_name("Johnson & Johnson Inc.")
        assert result == "johnson  johnson"

    def test_normalize_company_name_edge_cases(self, file_config, mock_logger):
        """Test company name normalization edge cases."""
        validator = DataValidator(file_config, mock_logger)

        # Test empty and None cases
        assert validator._normalize_company_name("") == ""
        assert validator._normalize_company_name(None) == ""
        assert validator._normalize_company_name("nan") == ""

    def test_validate_results_gold_standard_load_error(self, file_config, mock_logger, sample_processed_data):
        """Test validation with gold standard loading error."""
        # Mock file exists but has invalid CSV content
        with patch('os.path.exists', return_value=True), \
             patch('pandas.read_csv', side_effect=Exception("Invalid CSV format")):

            validator = DataValidator(file_config, mock_logger)
            accuracy, validation_df = validator.validate_results(sample_processed_data)

            assert accuracy == 0.0
            assert validation_df.empty
            mock_logger.error.assert_called_once()

    def test_validate_results_missing_required_columns_processed(self, file_config, mock_logger):
        """Test validation with missing required columns in processed data."""
        processed_df = pd.DataFrame({
            'Company Name': ['Google Inc.'],  # Wrong column name
            'Headquarters Address': ['1600 Amphitheatre Parkway']
        })

        validator = DataValidator(file_config, mock_logger)
        accuracy, validation_df = validator.validate_results(processed_df)

        assert accuracy == 0.0
        assert validation_df.empty
        mock_logger.error.assert_called_once()

    def test_validate_results_missing_required_columns_gold(self, file_config, mock_logger, sample_processed_data):
        """Test validation with missing required columns in gold standard."""
        with patch('os.path.exists', return_value=True), \
             patch('pandas.read_csv', return_value=pd.DataFrame({
                 'Company Name': ['Google Inc.'],  # Wrong column name
                 'Headquarters Address': ['1600 Amphitheatre Parkway']
             })):

            validator = DataValidator(file_config, mock_logger)
            accuracy, validation_df = validator.validate_results(sample_processed_data)

            assert accuracy == 0.0
            assert validation_df.empty
            mock_logger.error.assert_called_once()

    def test_validate_results_no_matching_records(self, file_config, mock_logger, sample_processed_data):
        """Test validation with no matching records."""
        with patch('os.path.exists', return_value=True), \
             patch('pandas.read_csv', return_value=pd.DataFrame({
                 'Payee Name of Record': ['Completely Different Company'],
                 'Headquarters Address': ['Different Address']
             })):

            validator = DataValidator(file_config, mock_logger)
            accuracy, validation_df = validator.validate_results(sample_processed_data)

            assert accuracy == 0.0
            assert validation_df.empty
            mock_logger.warning.assert_called_once()

    def test_validate_against_gold_standard_success(self, file_config, mock_logger, sample_processed_data, sample_gold_standard_data, temp_files):
        """Test successful validation against gold standard."""
        results_file, gold_standard_file = temp_files

        # Write test data to files
        sample_processed_data.to_csv(results_file, index=False)
        sample_gold_standard_data.to_csv(gold_standard_file, index=False)

        validator = DataValidator(file_config, mock_logger)

        with patch('headquarters_finder.core.data_validator.pd.read_csv') as mock_read_csv:
            mock_read_csv.return_value = sample_gold_standard_data

            result = validator.validate_against_gold_standard(results_file, gold_standard_file)

            assert result['accuracy'] > 0
            assert result['total_compared'] > 0
            assert result['matches'] > 0
            assert result['mismatches'] == 0
            assert 'error' not in result

    def test_validate_against_gold_standard_gold_file_not_found(self, file_config, mock_logger, temp_files):
        """Test validation when gold standard file doesn't exist."""
        results_file, _ = temp_files

        # Create empty results file
        pd.DataFrame({'test': ['data']}).to_csv(results_file, index=False)

        validator = DataValidator(file_config, mock_logger)
        result = validator.validate_against_gold_standard(results_file, "nonexistent_gold.csv")

        assert result['error'] == 'Gold standard file not found'
        assert result['accuracy'] == 0
        assert result['total_compared'] == 0
        assert result['matches'] == 0
        assert result['mismatches'] == 0

    def test_validate_against_gold_standard_results_file_not_found(self, file_config, mock_logger, temp_files):
        """Test validation when results file doesn't exist."""
        _, gold_standard_file = temp_files

        # Create gold standard file
        pd.DataFrame({'test': ['data']}).to_csv(gold_standard_file, index=False)

        validator = DataValidator(file_config, mock_logger)
        result = validator.validate_against_gold_standard("nonexistent_results.csv", gold_standard_file)

        assert result['error'] == 'Results file not found'
        assert result['accuracy'] == 0
        assert result['total_compared'] == 0
        assert result['matches'] == 0
        assert result['mismatches'] == 0

    def test_validate_against_gold_standard_exception_handling(self, file_config, mock_logger, temp_files):
        """Test validation exception handling."""
        results_file, gold_standard_file = temp_files

        # Create files
        pd.DataFrame({'test': ['data']}).to_csv(results_file, index=False)
        pd.DataFrame({'test': ['data']}).to_csv(gold_standard_file, index=False)

        validator = DataValidator(file_config, mock_logger)

        with patch.object(validator, '_compare_datasets', side_effect=Exception("Test error")):
            result = validator.validate_against_gold_standard(results_file, gold_standard_file)

            assert result['error'] == 'Test error'
            assert result['accuracy'] == 0
            assert result['total_compared'] == 0
            assert result['matches'] == 0
            assert result['mismatches'] == 0

    def test_compare_datasets_with_different_companies(self, file_config, mock_logger):
        """Test dataset comparison with completely different companies."""
        results_df = pd.DataFrame({
            'Payee Name of Record': ['Company A', 'Company B'],
            'HQ_Street_Address': ['Address A', 'Address B'],
            'HQ_City': ['City A', 'City B'],
            'HQ_State': ['State A', 'State B'],
            'HQ_ZIP': ['12345', '67890'],
            'HQ_Country': ['USA', 'USA']
        })

        gold_df = pd.DataFrame({
            'Payee Name of Record': ['Company C', 'Company D'],
            'HQ_Street_Address': ['Address C', 'Address D'],
            'HQ_City': ['City C', 'City D'],
            'HQ_State': ['State C', 'State D'],
            'HQ_ZIP': ['11111', '22222'],
            'HQ_Country': ['USA', 'USA']
        })

        validator = DataValidator(file_config, mock_logger)
        result = validator._compare_datasets(results_df, gold_df)

        assert result['total_compared'] == 0
        assert result['matches'] == 0
        assert result['mismatches'] == 0
        assert result['accuracy'] == 0

    def test_compare_datasets_with_matching_companies(self, file_config, mock_logger):
        """Test dataset comparison with matching companies."""
        results_df = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.', 'Google Inc.'],
            'HQ_Street_Address': ['1 Apple Park Way', '1600 Amphitheatre Parkway'],
            'HQ_City': ['Cupertino', 'Mountain View'],
            'HQ_State': ['CA', 'CA'],
            'HQ_ZIP': ['95014', '94043'],
            'HQ_Country': ['USA', 'USA']
        })

        gold_df = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.', 'Google Inc.'],
            'HQ_Street_Address': ['1 Apple Park Way', '1600 Amphitheatre Parkway'],
            'HQ_City': ['Cupertino', 'Mountain View'],
            'HQ_State': ['CA', 'CA'],
            'HQ_ZIP': ['95014', '94043'],
            'HQ_Country': ['USA', 'USA']
        })

        validator = DataValidator(file_config, mock_logger)
        result = validator._compare_datasets(results_df, gold_df)

        assert result['total_compared'] == 2
        assert result['matches'] == 2
        assert result['mismatches'] == 0
        assert result['accuracy'] == 100.0

    def test_compare_datasets_with_partial_matches(self, file_config, mock_logger):
        """Test dataset comparison with partial matches."""
        results_df = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.', 'Google Inc.'],
            'HQ_Street_Address': ['1 Apple Park Way', '1600 Amphitheatre Parkway'],
            'HQ_City': ['Cupertino', 'Mountain View'],
            'HQ_State': ['CA', 'CA'],
            'HQ_ZIP': ['95014', '94043'],
            'HQ_Country': ['USA', 'USA']
        })

        gold_df = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.', 'Google Inc.'],
            'HQ_Street_Address': ['1 Apple Park Way', '1600 Amphitheatre Pkwy'],  # Slightly different
            'HQ_City': ['Cupertino', 'Mountain View'],
            'HQ_State': ['CA', 'CA'],
            'HQ_ZIP': ['95014', '94043'],
            'HQ_Country': ['USA', 'USA']
        })

        validator = DataValidator(file_config, mock_logger)
        result = validator._compare_datasets(results_df, gold_df)

        # Should still be matches due to high similarity
        assert result['total_compared'] == 2
        assert result['matches'] == 2
        assert result['mismatches'] == 0

    def test_compare_datasets_with_mismatches(self, file_config, mock_logger):
        """Test dataset comparison with clear mismatches."""
        results_df = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.', 'Google Inc.'],
            'HQ_Street_Address': ['Completely Wrong Address', 'Another Wrong Address'],
            'HQ_City': ['Wrong City', 'Wrong City'],
            'HQ_State': ['XX', 'YY'],
            'HQ_ZIP': ['00000', '11111'],
            'HQ_Country': ['Wrong Country', 'Wrong Country']
        })

        gold_df = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.', 'Google Inc.'],
            'HQ_Street_Address': ['1 Apple Park Way', '1600 Amphitheatre Parkway'],
            'HQ_City': ['Cupertino', 'Mountain View'],
            'HQ_State': ['CA', 'CA'],
            'HQ_ZIP': ['95014', '94043'],
            'HQ_Country': ['USA', 'USA']
        })

        validator = DataValidator(file_config, mock_logger)
        result = validator._compare_datasets(results_df, gold_df)

        assert result['total_compared'] == 2
        assert result['matches'] == 0
        assert result['mismatches'] == 2
        assert result['accuracy'] == 0.0

    def test_compare_headquarters_data_exact_match(self, file_config, mock_logger):
        """Test headquarters data comparison with exact match."""
        result_row = pd.Series({
            'HQ_Street_Address': '1 Apple Park Way',
            'HQ_City': 'Cupertino',
            'HQ_State': 'CA',
            'HQ_ZIP': '95014',
            'HQ_Country': 'USA'
        })

        gold_row = pd.Series({
            'HQ_Street_Address': '1 Apple Park Way',
            'HQ_City': 'Cupertino',
            'HQ_State': 'CA',
            'HQ_ZIP': '95014',
            'HQ_Country': 'USA'
        })

        validator = DataValidator(file_config, mock_logger)
        result = validator._compare_headquarters_data(result_row, gold_row)

        assert result['is_match'] == True
        assert result['similarity_score'] == 1.0
        assert len(result['differences']) == 0

    def test_compare_headquarters_data_partial_match(self, file_config, mock_logger):
        """Test headquarters data comparison with partial match."""
        result_row = pd.Series({
            'HQ_Street_Address': '1 Apple Park Way',
            'HQ_City': 'Cupertino',
            'HQ_State': 'CA',
            'HQ_ZIP': '95014',
            'HQ_Country': 'USA'
        })

        gold_row = pd.Series({
            'HQ_Street_Address': '1 Apple Park Way',
            'HQ_City': 'Cupertino',
            'HQ_State': 'CA',
            'HQ_ZIP': '95014',
            'HQ_Country': 'United States'  # Different but similar
        })

        validator = DataValidator(file_config, mock_logger)
        result = validator._compare_headquarters_data(result_row, gold_row)

        assert result['is_match'] == True  # Should still match due to high similarity
        assert result['similarity_score'] >= 0.8

    def test_compare_headquarters_data_no_match(self, file_config, mock_logger):
        """Test headquarters data comparison with no match."""
        result_row = pd.Series({
            'HQ_Street_Address': 'Completely Different Address',
            'HQ_City': 'Different City',
            'HQ_State': 'XX',
            'HQ_ZIP': '00000',
            'HQ_Country': 'Different Country'
        })

        gold_row = pd.Series({
            'HQ_Street_Address': '1 Apple Park Way',
            'HQ_City': 'Cupertino',
            'HQ_State': 'CA',
            'HQ_ZIP': '95014',
            'HQ_Country': 'USA'
        })

        validator = DataValidator(file_config, mock_logger)
        result = validator._compare_headquarters_data(result_row, gold_row)

        assert result['is_match'] == False
        assert result['similarity_score'] < 0.8
        assert len(result['differences']) > 0

    def test_compare_headquarters_data_missing_fields(self, file_config, mock_logger):
        """Test headquarters data comparison with missing fields."""
        result_row = pd.Series({
            'HQ_Street_Address': '',
            'HQ_City': 'Cupertino',
            'HQ_State': 'CA',
            'HQ_ZIP': '95014',
            'HQ_Country': 'USA'
        })

        gold_row = pd.Series({
            'HQ_Street_Address': '1 Apple Park Way',
            'HQ_City': 'Cupertino',
            'HQ_State': 'CA',
            'HQ_ZIP': '95014',
            'HQ_Country': 'USA'
        })

        validator = DataValidator(file_config, mock_logger)
        result = validator._compare_headquarters_data(result_row, gold_row)

        # Should not match due to missing street address
        assert result['is_match'] == False
        assert len(result['differences']) > 0

    def test_generate_validation_report_success(self, file_config, mock_logger, temp_files):
        """Test successful validation report generation."""
        _, output_file = temp_files

        validation_results = {
            'total_compared': 5,
            'matches': 4,
            'mismatches': 1,
            'accuracy': 80.0,
            'detailed_comparisons': [
                {
                    'company_name': 'Apple Inc.',
                    'is_match': True,
                    'similarity_score': 1.0,
                    'differences': [],
                    'result_data': {
                        'street': '1 Apple Park Way',
                        'city': 'Cupertino',
                        'state': 'CA',
                        'zip': '95014',
                        'country': 'USA'
                    },
                    'gold_data': {
                        'street': '1 Apple Park Way',
                        'city': 'Cupertino',
                        'state': 'CA',
                        'zip': '95014',
                        'country': 'USA'
                    }
                }
            ]
        }

        validator = DataValidator(file_config, mock_logger)
        report_file = validator.generate_validation_report(validation_results, output_file)

        assert report_file == output_file
        assert os.path.exists(output_file)

        # Check report content
        with open(output_file, 'r') as f:
            content = f.read()
            assert '# Headquarters Data Validation Report' in content
            assert 'Total Records Compared: 5' in content
            assert 'Accuracy: 80.0%' in content
            assert 'Apple Inc.' in content

    def test_generate_validation_report_exception_handling(self, file_config, mock_logger, temp_files):
        """Test validation report generation exception handling."""
        _, output_file = temp_files

        validation_results = {
            'total_compared': 5,
            'matches': 4,
            'mismatches': 1,
            'accuracy': 80.0
        }

        validator = DataValidator(file_config, mock_logger)

        # Mock file write to raise exception
        with patch('builtins.open', side_effect=Exception("File write error")):
            report_file = validator.generate_validation_report(validation_results, output_file)

            assert report_file == ""
            mock_logger.error.assert_called_once()

    def test_logger_integration_methods(self, file_config, mock_logger, temp_files):
        """Test that logger integration methods are called correctly."""
        results_file, gold_standard_file = temp_files

        # Create test data
        results_df = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.'],
            'HQ_Street_Address': ['1 Apple Park Way'],
            'HQ_City': ['Cupertino'],
            'HQ_State': ['CA'],
            'HQ_ZIP': ['95014'],
            'HQ_Country': ['USA']
        })
        results_df.to_csv(results_file, index=False)

        gold_df = pd.DataFrame({
            'Payee Name of Record': ['Apple Inc.'],
            'HQ_Street_Address': ['1 Apple Park Way'],
            'HQ_City': ['Cupertino'],
            'HQ_State': ['CA'],
            'HQ_ZIP': ['95014'],
            'HQ_Country': ['USA']
        })
        gold_df.to_csv(gold_standard_file, index=False)

        validator = DataValidator(file_config, mock_logger)

        # Mock the logger to track method calls
        with patch.object(validator, '_compare_datasets') as mock_compare:
            mock_compare.return_value = {
                'total_compared': 1,
                'matches': 1,
                'mismatches': 0,
                'accuracy': 100.0,
                'detailed_comparisons': []
            }

            validator.validate_against_gold_standard(results_file, gold_standard_file)

            # Verify logger.log_validation_results was called
            mock_logger.log_validation_results.assert_called_once_with(100.0, 1, 0)

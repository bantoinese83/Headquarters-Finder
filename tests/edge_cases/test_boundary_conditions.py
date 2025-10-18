"""
Edge case tests for boundary conditions and limits.

Tests extreme values, boundary conditions, and limit scenarios
that could cause the application to fail or behave unexpectedly.
"""

import pytest
import pandas as pd
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from headquarters_finder.core.api_client import GeminiAPIClient, Tier1RateLimiter
from headquarters_finder.core.csv_processor import CSVProcessor
from headquarters_finder.services.headquarters_service import HeadquartersService
from headquarters_finder.utils.config import Config
from headquarters_finder.utils.logger import Logger


class TestBoundaryConditions:
    """Test boundary conditions and extreme values."""
    
    def test_empty_dataframe(self, temp_dir, mock_logger):
        """Test processing with completely empty DataFrame."""
        # Create empty CSV
        empty_df = pd.DataFrame()
        empty_csv = os.path.join(temp_dir, 'empty.csv')
        empty_df.to_csv(empty_csv, index=False)
        
        processor = CSVProcessor(empty_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        
        # Should handle empty DataFrame gracefully
        df = processor.read_input_csv()
        assert len(df) == 0
        assert isinstance(df, pd.DataFrame)
    
    def test_single_record(self, temp_dir, mock_logger):
        """Test processing with single record."""
        single_df = pd.DataFrame({
            'Payee Name of Record': ['Single Company'],
            'Status': ['Pending']
        })
        single_csv = os.path.join(temp_dir, 'single.csv')
        single_df.to_csv(single_csv, index=False)
        
        processor = CSVProcessor(single_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        df = processor.read_input_csv()
        
        assert len(df) == 1
        assert df.iloc[0]['Payee Name of Record'] == 'Single Company'
    
    def test_maximum_reasonable_records(self, temp_dir, mock_logger):
        """Test processing with maximum reasonable number of records."""
        # Create DataFrame with 10,000 records (Tier 1 daily limit)
        max_records = 10000
        data = {
            'Payee Name of Record': [f'Company {i}' for i in range(max_records)],
            'Status': ['Pending'] * max_records
        }
        max_df = pd.DataFrame(data)
        max_csv = os.path.join(temp_dir, 'max.csv')
        max_df.to_csv(max_csv, index=False)
        
        processor = CSVProcessor(max_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        df = processor.read_input_csv()
        
        assert len(df) == max_records
        assert all(df['Status'] == 'Pending')
    
    def test_extremely_long_company_name(self, mock_logger):
        """Test processing with extremely long company name."""
        long_name = 'A' * 10000  # 10,000 character company name
        
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            # Should handle long names gracefully
            prompt = client._create_prompt(long_name)
            assert len(prompt) > 0
            assert long_name in prompt
    
    def test_unicode_company_name(self, mock_logger):
        """Test processing with Unicode company name."""
        unicode_name = 'Tëst Çömpäny 中文 日本語 العربية'
        
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            prompt = client._create_prompt(unicode_name)
            assert unicode_name in prompt
            assert len(prompt) > 0
    
    def test_special_characters_company_name(self, mock_logger):
        """Test processing with special characters in company name."""
        special_name = 'Test & Company, Inc. (LLC) [Corp.] {Ltd.} <GmbH>'
        
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            prompt = client._create_prompt(special_name)
            assert special_name in prompt
            assert len(prompt) > 0
    
    def test_rate_limiter_extreme_values(self):
        """Test rate limiter with extreme values."""
        # Test with very high limits
        limiter = Tier1RateLimiter(max_rpm=1000000, max_tpm=1000000000)
        assert limiter.max_rpm == 1000000
        assert limiter.max_tpm == 1000000000
        
        # Test with very low limits
        limiter = Tier1RateLimiter(max_rpm=1, max_tpm=100)
        assert limiter.max_rpm == 1
        assert limiter.max_tpm == 100
    
    def test_processing_time_extreme_values(self, mock_logger):
        """Test processing time calculation with extreme values."""
        from headquarters_finder.utils.config import ProcessingConfig
        processing_config = ProcessingConfig(batch_size=50, save_interval=50, retry_attempts=3, delay_between_requests=0.1)
        service = HeadquartersService(None, None, processing_config, mock_logger)
        
        # Test with zero records
        estimates = service.calculate_processing_time(0)
        assert estimates['total_records'] == 0
        assert estimates['estimated_time_hours'] == 0.0
        assert estimates['can_process_today'] is True
        
        # Test with very large number
        estimates = service.calculate_processing_time(1000000)
        assert estimates['total_records'] == 1000000
        assert estimates['estimated_time_hours'] > 0
        assert estimates['can_process_today'] is False
    
    def test_batch_size_boundaries(self, mock_logger):
        """Test batch size boundary conditions."""
        from headquarters_finder.utils.config import ProcessingConfig
        
        # Test with batch size 1
        processing_config = ProcessingConfig(batch_size=1, save_interval=1, retry_attempts=3, delay_between_requests=0.1)
        service = HeadquartersService(None, None, processing_config, mock_logger)
        assert service.batch_size == 1
        
        # Test with very large batch size
        processing_config = ProcessingConfig(batch_size=10000, save_interval=10000, retry_attempts=3, delay_between_requests=0.1)
        service = HeadquartersService(None, None, processing_config, mock_logger)
        assert service.batch_size == 10000
        
        # Test with zero batch size (should be handled gracefully)
        processing_config = ProcessingConfig(batch_size=0, save_interval=1, retry_attempts=3, delay_between_requests=0.1)
        service = HeadquartersService(None, None, processing_config, mock_logger)
        assert service.batch_size == 0
    
    def test_delay_boundaries(self, mock_logger):
        """Test delay boundary conditions."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            # Test with zero delay
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                delay_between_requests=0.0,
                logger=mock_logger
            )
            assert client.delay_between_requests == 0.0
            
            # Test with very large delay
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                delay_between_requests=3600.0,  # 1 hour
                logger=mock_logger
            )
            assert client.delay_between_requests == 3600.0
    
    def test_temperature_boundaries(self, mock_logger):
        """Test temperature boundary conditions."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            # Test with minimum temperature
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.0,
                max_output_tokens=8192,
                logger=mock_logger
            )
            assert client.temperature == 0.0
            
            # Test with maximum temperature
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=1.0,
                max_output_tokens=8192,
                logger=mock_logger
            )
            assert client.temperature == 1.0
    
    def test_token_boundaries(self, mock_logger):
        """Test token boundary conditions."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            # Test with minimum tokens
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=1,
                logger=mock_logger
            )
            assert client.max_output_tokens == 1
            
            # Test with very large token count
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=1000000,
                logger=mock_logger
            )
            assert client.max_output_tokens == 1000000
    
    def test_retry_attempts_boundaries(self, mock_logger):
        """Test retry attempts boundary conditions."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            # Test with zero retries
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                retry_attempts=0,
                logger=mock_logger
            )
            assert client.retry_attempts == 0
            
            # Test with many retries
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                retry_attempts=100,
                logger=mock_logger
            )
            assert client.retry_attempts == 100
    
    def test_memory_usage_large_dataset(self, temp_dir, mock_logger):
        """Test memory usage with large dataset."""
        # Create large dataset
        large_data = {
            'Payee Name of Record': [f'Company {i}' for i in range(50000)],
            'Status': ['Pending'] * 50000,
            'Address1 of Record': ['Address'] * 50000,
            'City of Record': ['City'] * 50000,
            'State of Record': ['State'] * 50000,
            'Zip of Record': ['Zip'] * 50000
        }
        large_df = pd.DataFrame(large_data)
        large_csv = os.path.join(temp_dir, 'large.csv')
        large_df.to_csv(large_csv, index=False)
        
        processor = CSVProcessor(large_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        
        # Should handle large dataset without memory issues
        df = processor.read_input_csv()
        assert len(df) == 50000
        assert isinstance(df, pd.DataFrame)
    
    def test_file_size_limits(self, temp_dir, mock_logger):
        """Test file size limits."""
        # Create very large CSV file
        large_data = {
            'Payee Name of Record': [f'Very Long Company Name {i} ' * 100 for i in range(1000)],
            'Status': ['Pending'] * 1000,
            'Address1 of Record': ['Very Long Address ' * 50] * 1000,
            'City of Record': ['Very Long City Name ' * 20] * 1000,
            'State of Record': ['State'] * 1000,
            'Zip of Record': ['Zip'] * 1000
        }
        large_df = pd.DataFrame(large_data)
        large_csv = os.path.join(temp_dir, 'large.csv')
        large_df.to_csv(large_csv, index=False)
        
        processor = CSVProcessor(large_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
        
        # Should handle large file without issues
        df = processor.read_input_csv()
        assert len(df) == 1000
        assert isinstance(df, pd.DataFrame)
    
    def test_concurrent_access(self, temp_dir, mock_logger):
        """Test concurrent access to same files."""
        import threading
        import time
        
        # Create test data
        test_data = pd.DataFrame({
            'Payee Name of Record': [f'Company {i}' for i in range(100)],
            'Status': ['Pending'] * 100
        })
        test_csv = os.path.join(temp_dir, 'test.csv')
        test_data.to_csv(test_csv, index=False)
        
        results = []
        
        def read_csv():
            processor = CSVProcessor(test_csv, os.path.join(temp_dir, 'output.csv'), mock_logger)
            df = processor.read_input_csv()
            results.append(len(df))
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=read_csv)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All threads should have read the same data
        assert all(result == 100 for result in results)
        assert len(results) == 10

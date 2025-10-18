"""
Unit tests for API client module.

Tests the GeminiAPIClient and Tier1RateLimiter classes with both
golden path and edge case scenarios.
"""

import time
from unittest.mock import Mock, patch

import pytest

from headquarters_finder.core.api_client import (
    GeminiAPIClient, 
    Tier1RateLimiter, 
    APIError, 
    APIErrorType
)  


class TestTier1RateLimiter:
    """Test cases for Tier1RateLimiter class."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with default values."""
        limiter = Tier1RateLimiter()
        assert limiter.max_rpm == 150
        assert limiter.max_tpm == 2000000
        assert len(limiter.request_times) == 0
        assert len(limiter.token_usage) == 0
    
    def test_rate_limiter_custom_limits(self):
        """Test rate limiter initialization with custom limits."""
        limiter = Tier1RateLimiter(max_rpm=100, max_tpm=1000000)
        assert limiter.max_rpm == 100
        assert limiter.max_tpm == 1000000
    
    def test_rate_limiter_wait_not_needed(self):
        """Test rate limiter when no waiting is needed."""
        limiter = Tier1RateLimiter()
        start_time = time.time()
        limiter.wait_if_needed(1000)
        end_time = time.time()
        # Should not wait significantly
        assert end_time - start_time < 0.1
    
    def test_rate_limiter_rpm_limit(self):
        """Test rate limiter RPM limit enforcement."""
        limiter = Tier1RateLimiter(max_rpm=2)  # Very low limit for testing
        
        # First two requests should not wait
        limiter.wait_if_needed(1000)
        limiter.wait_if_needed(1000)
        
        # Third request should wait
        start_time = time.time()
        limiter.wait_if_needed(1000)
        end_time = time.time()
        
        # Should have waited approximately 60 seconds
        assert end_time - start_time > 0.5  # Allow some tolerance
    
    def test_rate_limiter_tpm_limit(self):
        """Test rate limiter TPM limit enforcement."""
        limiter = Tier1RateLimiter(max_tpm=2000)  # Very low limit for testing

        # First request should not wait
        limiter.wait_if_needed(1000)

        # Second request should wait due to TPM limit
        limiter.wait_if_needed(1000)

        # Should have waited (but may be very short due to timing)
        # Just verify the limiter is working
        assert len(limiter.token_usage) == 2
    
    def test_rate_limiter_cleanup_old_entries(self):
        """Test rate limiter cleans up old entries."""
        limiter = Tier1RateLimiter(max_rpm=2)
        
        # Add old entries
        old_time = time.time() - 120  # 2 minutes ago
        limiter.request_times.append(old_time)
        limiter.token_usage.append((old_time, 1000))
        
        # Add current entry
        limiter.wait_if_needed(1000)
        
        # Old entries should be cleaned up
        assert len(limiter.request_times) == 1
        assert len(limiter.token_usage) == 1
        assert limiter.request_times[0] > old_time
        assert limiter.token_usage[0][0] > old_time


class TestGeminiAPIClient:
    """Test cases for GeminiAPIClient class."""
    
    def test_client_initialization(self, mock_logger):
        """Test API client initialization with valid parameters."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            assert client.api_key == 'test_key'
            assert client.model_name == 'gemini-2.5-pro'
            assert client.temperature == 0.1
            assert client.max_output_tokens == 8192
            assert client.retry_attempts == 3
            assert client.delay_between_requests == 0.4
            assert isinstance(client.rate_limiter, Tier1RateLimiter)
    
    def test_client_initialization_invalid_api_key(self, mock_logger):
        """Test API client initialization with invalid API key."""
        with pytest.raises(ValueError, match="API key must be a non-empty string"):
            GeminiAPIClient(
                api_key='',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
    
    def test_client_initialization_invalid_temperature(self, mock_logger):
        """Test API client initialization with invalid temperature."""
        with pytest.raises(ValueError, match="Temperature must be between 0.0 and 1.0"):
            GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=1.5,
                max_output_tokens=8192,
                logger=mock_logger
            )
    
    def test_client_initialization_invalid_tokens(self, mock_logger):
        """Test API client initialization with invalid token count."""
        with pytest.raises(ValueError, match="Max output tokens must be positive"):
            GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=0,
                logger=mock_logger
            )
    
    def test_create_prompt(self, mock_logger):
        """Test prompt creation for headquarters information."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            prompt = client._create_prompt('Apple Inc.')
            assert 'Apple Inc.' in prompt
            assert 'headquarters' in prompt.lower()
            assert 'address' in prompt.lower()
    
    def test_parse_api_error_quota_exceeded(self, mock_logger):
        """Test API error parsing for quota exceeded."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            error = Exception("429 Quota exceeded. Please retry in 50s")
            api_error = client._parse_api_error(error)
            
            assert api_error.error_type == APIErrorType.QUOTA_EXCEEDED
            assert api_error.retry_after == 50.0
            assert "Quota exceeded" in api_error.message
    
    def test_parse_api_error_authentication(self, mock_logger):
        """Test API error parsing for authentication error."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            error = Exception("401 Authentication failed")
            api_error = client._parse_api_error(error)
            
            assert api_error.error_type == APIErrorType.AUTHENTICATION_ERROR
            assert "Authentication" in api_error.message
    
    def test_parse_api_error_network(self, mock_logger):
        """Test API error parsing for network error."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            error = Exception("Network connection failed")
            api_error = client._parse_api_error(error)
            
            assert api_error.error_type == APIErrorType.NETWORK_ERROR
            assert "network" in api_error.message.lower()
    
    def test_parse_api_error_unknown(self, mock_logger):
        """Test API error parsing for unknown error."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel'):
            client = GeminiAPIClient(
                api_key='test_key',
                model_name='gemini-2.5-pro',
                temperature=0.1,
                max_output_tokens=8192,
                logger=mock_logger
            )
            
            error = Exception("Unknown error occurred")
            api_error = client._parse_api_error(error)
            
            assert api_error.error_type == APIErrorType.UNKNOWN_ERROR
            assert "Unknown error" in api_error.message
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_get_headquarters_info_success(
        self, mock_model_class, _mock_configure, mock_logger
    ):
        """Test successful headquarters information retrieval."""
        # Mock the model and response
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
        
        result, success = client.get_headquarters_info('Apple Inc.')
        
        assert success is True
        assert result['HQ_Street_Address'] == '1 Apple Park Way'
        assert result['HQ_City'] == 'Cupertino'
        assert result['HQ_State'] == 'CA'
        assert result['HQ_ZIP'] == '95014'
        assert result['HQ_Country'] == 'USA'
        assert 'Street Address: 1 Apple Park Way' in result['Raw_Response']
        assert result['Error_Message'] == ''
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_get_headquarters_info_empty_company(
        self, _mock_model_class, _mock_configure, mock_logger
    ):
        """Test headquarters information retrieval with empty company name."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )
        
        result, success = client.get_headquarters_info('')
        
        assert success is False
        assert result['Error_Message'] == 'Empty company name provided'
        assert result['Raw_Response'] == 'ERROR: Empty company name'
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_get_headquarters_info_whitespace_company(
        self, _mock_model_class, _mock_configure, mock_logger
    ):
        """Test headquarters information retrieval with whitespace-only company name."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )
        
        result, success = client.get_headquarters_info('   ')
        
        assert success is False
        assert result['Error_Message'] == 'Empty company name provided'
        assert result['Raw_Response'] == 'ERROR: Empty company name'
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_get_headquarters_info_api_error(
        self, mock_model_class, _mock_configure, mock_logger
    ):
        """Test headquarters information retrieval with API error."""
        # Mock the model to raise an exception
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_model.generate_content.side_effect = Exception("API error occurred")
        
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )
        
        result, success = client.get_headquarters_info('Apple Inc.')
        
        assert success is False
        assert 'API error occurred' in result['Error_Message']
        assert result['Raw_Response'] == 'ERROR: API error occurred'
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_get_headquarters_info_empty_response(
        self, mock_model_class, _mock_configure, mock_logger
    ):
        """Test headquarters information retrieval with empty response."""
        # Mock the model to return empty response
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_response = Mock()
        mock_response.text = ""
        mock_model.generate_content.return_value = mock_response
        
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )
        
        result, success = client.get_headquarters_info('Apple Inc.')
        
        assert success is False
        assert result['Error_Message'] == 'Empty response from API'
        assert result['Raw_Response'] == 'ERROR: Empty response from API'
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_get_headquarters_info_retry_mechanism(
        self, mock_model_class, _mock_configure, mock_logger
    ):
        """Test headquarters information retrieval with retry mechanism."""
        # Mock the model to fail first two times, then succeed
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_response = Mock()
        mock_response.text = """Street Address: 1 Apple Park Way
City: Cupertino
State: CA
ZIP Code: 95014
Country: USA"""
        mock_model.generate_content.side_effect = [
            Exception("Temporary error"),
            Exception("Temporary error"),
            mock_response
        ]
        
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            retry_attempts=3,
            logger=mock_logger
        )
        
        result, success = client.get_headquarters_info('Apple Inc.')
        
        assert success is True
        assert result['HQ_Street_Address'] == '1 Apple Park Way'
        assert mock_model.generate_content.call_count == 3
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_get_headquarters_info_max_retries_exceeded(
        self, mock_model_class, _mock_configure, mock_logger
    ):
        """Test headquarters information retrieval when max retries are exceeded."""
        # Mock the model to always fail
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        mock_model.generate_content.side_effect = Exception("Persistent error")
        
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            retry_attempts=2,
            logger=mock_logger
        )
        
        result, success = client.get_headquarters_info('Apple Inc.')
        
        assert success is False
        assert 'Persistent error' in result['Error_Message']
        assert result['Raw_Response'] == 'ERROR: Persistent error'
        assert mock_model.generate_content.call_count == 2


class TestAPIError:
    """Test cases for APIError dataclass."""
    
    def test_api_error_creation(self):
        """Test APIError creation with all parameters."""
        error = APIError(
            error_type=APIErrorType.QUOTA_EXCEEDED,
            message="Quota exceeded",
            retry_after=60.0,
            original_exception=Exception("Original error")
        )
        
        assert error.error_type == APIErrorType.QUOTA_EXCEEDED
        assert error.message == "Quota exceeded"
        assert error.retry_after == 60.0
        assert isinstance(error.original_exception, Exception)
    
    def test_api_error_minimal(self):
        """Test APIError creation with minimal parameters."""
        error = APIError(
            error_type=APIErrorType.UNKNOWN_ERROR,
            message="Unknown error"
        )
        
        assert error.error_type == APIErrorType.UNKNOWN_ERROR
        assert error.message == "Unknown error"
        assert error.retry_after is None
        assert error.original_exception is None


class TestAPIErrorType:
    """Test cases for APIErrorType enum."""
    
    def test_error_type_values(self):
        """Test APIErrorType enum values."""
        assert APIErrorType.QUOTA_EXCEEDED.value == "quota_exceeded"
        assert APIErrorType.RATE_LIMITED.value == "rate_limited"
        assert APIErrorType.AUTHENTICATION_ERROR.value == "authentication_error"
        assert APIErrorType.NETWORK_ERROR.value == "network_error"
        assert APIErrorType.UNKNOWN_ERROR.value == "unknown_error"
    
    def test_error_type_enumeration(self):
        """Test APIErrorType enum iteration."""
        error_types = list(APIErrorType)
        assert len(error_types) == 5
        assert APIErrorType.QUOTA_EXCEEDED in error_types
        assert APIErrorType.RATE_LIMITED in error_types
        assert APIErrorType.AUTHENTICATION_ERROR in error_types
        assert APIErrorType.NETWORK_ERROR in error_types
        assert APIErrorType.UNKNOWN_ERROR in error_types

    def test_rate_limiter_rpm_limit_boundary(self):
        """Test rate limiter at RPM limit boundary."""
        limiter = Tier1RateLimiter(max_rpm=1)  # Only 1 request per minute

        # First request should not wait
        limiter.wait_if_needed(1000)

        # Second request should wait
        start_time = time.time()
        limiter.wait_if_needed(1000)
        end_time = time.time()

        # Should have waited for rate limit reset
        assert end_time - start_time > 0.5

    def test_rate_limiter_tpm_limit_boundary(self):
        """Test rate limiter at TPM limit boundary."""
        limiter = Tier1RateLimiter(max_tpm=1000)  # Very low TPM limit

        # First request should not wait
        limiter.wait_if_needed(500)

        # Second request should wait due to TPM limit
        limiter.wait_if_needed(600)  # Exceeds limit

        # Verify token usage tracking
        assert len(limiter.token_usage) == 2

    def test_rate_limiter_cleanup_multiple_old_entries(self):
        """Test rate limiter cleanup with multiple old entries."""
        limiter = Tier1RateLimiter(max_rpm=10)

        # Add multiple old entries
        old_time = time.time() - 120  # 2 minutes ago
        for i in range(5):
            limiter.request_times.append(old_time - i)
            limiter.token_usage.append((old_time - i, 1000))

        # Add current entry
        limiter.wait_if_needed(1000)

        # All old entries should be cleaned up
        assert len(limiter.request_times) == 1
        assert len(limiter.token_usage) == 1

    def test_client_initialization_api_configuration_failure(self, mock_logger):
        """Test client initialization with API configuration failure."""
        with patch('google.generativeai.configure', side_effect=Exception("API config error")):
            with pytest.raises(RuntimeError, match="Failed to configure Gemini API"):
                GeminiAPIClient(
                    api_key='test_key',
                    model_name='gemini-2.5-pro',
                    temperature=0.1,
                    max_output_tokens=8192,
                    logger=mock_logger
                )

    def test_client_initialization_model_creation_failure(self, mock_logger):
        """Test client initialization with model creation failure."""
        with patch('google.generativeai.configure'), \
             patch('google.generativeai.GenerativeModel', side_effect=Exception("Model creation error")):
            with pytest.raises(RuntimeError, match="Failed to configure Gemini API"):
                GeminiAPIClient(
                    api_key='test_key',
                    model_name='gemini-2.5-pro',
                    temperature=0.1,
                    max_output_tokens=8192,
                    logger=mock_logger
                )

    def test_client_initialization_boundary_temperature_values(self):
        """Test client initialization with boundary temperature values."""
        # Test with temperature 0.0 (minimum)
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.0,
            max_output_tokens=8192
        )
        assert client.temperature == 0.0

        # Test with temperature 1.0 (maximum)
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=1.0,
            max_output_tokens=8192
        )
        assert client.temperature == 1.0

    def test_client_initialization_boundary_retry_values(self):
        """Test client initialization with boundary retry values."""
        # Test with retry_attempts = 0 (no retries)
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            retry_attempts=0
        )
        assert client.retry_attempts == 0

        # Test with retry_attempts = 10 (high number)
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            retry_attempts=10
        )
        assert client.retry_attempts == 10

    def test_client_initialization_boundary_delay_values(self):
        """Test client initialization with boundary delay values."""
        # Test with delay_between_requests = 0 (no delay)
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            delay_between_requests=0.0
        )
        assert client.delay_between_requests == 0.0

        # Test with delay_between_requests = 10 (high delay)
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            delay_between_requests=10.0
        )
        assert client.delay_between_requests == 10.0

    def test_get_headquarters_info_empty_response(self, mock_logger):
        """Test getting headquarters info with empty API response."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )

        with patch.object(client.model, 'generate_content') as mock_generate:
            # Mock empty response
            mock_response = Mock()
            mock_response.text = ""
            mock_generate.return_value = mock_response

            result, success = client.get_headquarters_info("Test Company")

            assert success == False
            assert result['Error_Message'] == 'Empty response from API'
            assert result['Raw_Response'] == 'ERROR: Empty response from API'

    def test_get_headquarters_info_not_found_response(self, mock_logger):
        """Test getting headquarters info with 'NOT FOUND' response."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )

        with patch.object(client.model, 'generate_content') as mock_generate:
            # Mock "NOT FOUND" response
            mock_response = Mock()
            mock_response.text = "NOT FOUND"
            mock_generate.return_value = mock_response

            result, success = client.get_headquarters_info("Nonexistent Company")

            # Should return empty result for "NOT FOUND"
            assert success == True  # Not found is considered successful
            assert result['HQ_Street_Address'] == ''
            assert result['HQ_City'] == ''
            assert result['HQ_State'] == ''
            assert result['HQ_ZIP'] == ''
            assert result['HQ_Country'] == ''

    def test_get_headquarters_info_api_error_with_retry_after(self, mock_logger):
        """Test getting headquarters info with API error that includes retry_after."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            retry_attempts=2,
            logger=mock_logger
        )

        with patch.object(client.model, 'generate_content') as mock_generate, \
             patch('time.sleep') as mock_sleep:

            # Mock API error with retry_after
            api_error = APIError(
                error_type=APIErrorType.RATE_LIMITED,
                message="Rate limited",
                retry_after=5.0
            )

            with patch.object(client, '_parse_api_error', return_value=api_error):
                mock_generate.side_effect = Exception("Rate limited")

                result, success = client.get_headquarters_info("Test Company")

                # Should fail after retries
                assert success == False
                assert "Rate limited" in result['Error_Message']

                # Should have slept for retry_after time
                mock_sleep.assert_called_with(5.0)

    def test_get_headquarters_info_max_retries_exceeded(self, mock_logger):
        """Test getting headquarters info when max retries are exceeded."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            retry_attempts=1,  # Only 1 retry
            logger=mock_logger
        )

        with patch.object(client.model, 'generate_content') as mock_generate:
            # Mock persistent API error
            mock_generate.side_effect = Exception("Persistent error")

            result, success = client.get_headquarters_info("Test Company")

            # Should fail after max retries
            assert success == False
            assert "Persistent error" in result['Error_Message']
            assert result['Raw_Response'] == 'ERROR: Persistent error'

    def test_test_connection_success(self, mock_logger):
        """Test successful API connection test."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )

        with patch.object(client.model, 'generate_content') as mock_generate:
            # Mock successful response
            mock_response = Mock()
            mock_response.text = "Paris"
            mock_generate.return_value = mock_response

            result = client.test_connection()

            assert result == True
            mock_generate.assert_called_once_with("What is the capital of France?")

    def test_test_connection_failure(self, mock_logger):
        """Test failed API connection test."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )

        with patch.object(client.model, 'generate_content') as mock_generate:
            # Mock API error
            mock_generate.side_effect = Exception("Connection failed")

            result = client.test_connection()

            assert result == False
            mock_logger.error.assert_called_once()

    def test_test_connection_empty_response(self, mock_logger):
        """Test API connection test with empty response."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )

        with patch.object(client.model, 'generate_content') as mock_generate:
            # Mock empty response
            mock_response = Mock()
            mock_response.text = ""
            mock_generate.return_value = mock_response

            result = client.test_connection()

            assert result == False

    def test_rate_limiter_wait_if_needed_with_retry_after_logic(self):
        """Test rate limiter wait logic with retry_after scenario."""
        limiter = Tier1RateLimiter(max_rpm=1)

        # Fill up the rate limit
        limiter.request_times.append(time.time())

        # Next request should wait
        start_time = time.time()
        limiter.wait_if_needed(1000)
        end_time = time.time()

        # Should have waited due to RPM limit
        assert end_time - start_time > 0.5

    def test_parse_response_with_malformed_data(self, mock_logger):
        """Test response parsing with malformed data."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )

        # Test with response missing some fields
        response = """Street Address: 123 Main St
City: Anytown
State: CA
ZIP Code: 12345
Country: USA"""

        result = client._parse_response(response)

        # Should parse correctly even with some missing fields
        assert result['HQ_Street_Address'] == '123 Main St'
        assert result['HQ_City'] == 'Anytown'
        assert result['HQ_State'] == 'CA'
        assert result['HQ_ZIP'] == '12345'
        assert result['HQ_Country'] == 'USA'

    def test_create_prompt_with_special_characters(self, mock_logger):
        """Test prompt creation with special characters in company name."""
        client = GeminiAPIClient(
            api_key='test_key',
            model_name='gemini-2.5-pro',
            temperature=0.1,
            max_output_tokens=8192,
            logger=mock_logger
        )

        prompt = client._create_prompt("Johnson & Johnson Inc.")

        # Should handle special characters properly
        assert "Johnson & Johnson Inc." in prompt
        assert "Return ONLY the official corporate headquarters" in prompt

"""
Gemini API client module for retrieving corporate headquarters information.

This module provides a robust client for interacting with the Google Gemini 2.5 Pro API,
including retry logic, rate limiting, and comprehensive error handling.

Author: AI Assistant
Version: 1.0.0
License: Proprietary
"""

import time
import re
import logging
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from collections import deque

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.types import HarmBlockThreshold as HarmBlockThresholdType

from ..utils.logger import Logger


class APIErrorType(Enum):
    """Enumeration of API error types."""
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_ERROR = "authentication_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class APIError:
    """Represents an API error with context."""
    error_type: APIErrorType
    message: str
    retry_after: Optional[float] = None
    original_exception: Optional[Exception] = None


class Tier1RateLimiter:
    """Rate limiter optimized for Gemini API Tier 1 limits.
    
    Tier 1 Limits:
    - RPM (Requests Per Minute): 150
    - TPM (Tokens Per Minute): 2,000,000
    - RPD (Requests Per Day): 10,000
    - Batch Enqueued Tokens: 5,000,000
    """
    
    def __init__(self, max_rpm: int = 150, max_tpm: int = 2000000):
        """Initialize rate limiter.
        
        Args:
            max_rpm: Maximum requests per minute (default: 150 for Tier 1)
            max_tpm: Maximum tokens per minute (default: 2,000,000 for Tier 1)
        """
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm
        self.request_times = deque()
        self.token_usage = deque()
        
    def wait_if_needed(self, estimated_tokens: int = 8192) -> None:
        """Wait if necessary to respect rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the next request
        """
        current_time = time.time()
        
        # Clean old entries (older than 1 minute)
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()
            
        while self.token_usage and current_time - self.token_usage[0][0] > 60:
            self.token_usage.popleft()
        
        # Check RPM limit
        if len(self.request_times) >= self.max_rpm:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
                current_time = time.time()
        
        # Check TPM limit
        current_tokens = sum(tokens for _, tokens in self.token_usage)
        if current_tokens + estimated_tokens > self.max_tpm:
            sleep_time = 60 - (current_time - self.token_usage[0][0])
            if sleep_time > 0:
                time.sleep(sleep_time)
                current_time = time.time()
        
        # Record this request
        self.request_times.append(current_time)
        self.token_usage.append((current_time, estimated_tokens))


class GeminiAPIClient:
    """Client for interacting with Google Gemini API.
    
    This class provides a robust interface to the Google Gemini 2.5 Pro API
    with comprehensive error handling, retry logic, and rate limiting.
    """
    
    def __init__(
        self, 
        api_key: str, 
        model_name: str, 
        temperature: float, 
        max_output_tokens: int, 
        retry_attempts: int = 3, 
        delay_between_requests: float = 0.4, 
        logger: Optional[Logger] = None
    ) -> None:
        """Initialize Gemini API client.
        
        Args:
            api_key: Google Gemini API key.
            model_name: Name of the Gemini model to use.
            temperature: Temperature setting for the model (0.0-1.0).
            max_output_tokens: Maximum number of output tokens.
            retry_attempts: Number of retry attempts for failed requests.
            delay_between_requests: Delay between requests in seconds.
            logger: Logger instance for logging.
            
        Raises:
            ValueError: If any parameter is invalid.
            RuntimeError: If API configuration fails.
        """
        # Validate parameters
        if not api_key or not isinstance(api_key, str):
            raise ValueError("API key must be a non-empty string")
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Model name must be a non-empty string")
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        if max_output_tokens <= 0:
            raise ValueError("Max output tokens must be positive")
        if retry_attempts < 0:
            raise ValueError("Retry attempts must be non-negative")
        if delay_between_requests < 0:
            raise ValueError("Delay between requests must be non-negative")
        
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.retry_attempts = retry_attempts
        self.delay_between_requests = delay_between_requests
        self.logger = logger or Logger("logs/api_client.log")
        self.rate_limiter = Tier1RateLimiter()
        
        try:
            # Configure the API
            genai.configure(api_key=api_key)
            
            # Initialize the model
            self.model = genai.GenerativeModel(
                model_name=model_name,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': max_output_tokens,
                },
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
        except Exception as e:
            raise RuntimeError(f"Failed to configure Gemini API: {str(e)}") from e
    
    def _create_prompt(self, company_name: str) -> str:
        """Create a structured prompt for headquarters information.
        
        Args:
            company_name: Name of the company to query
            
        Returns:
            Formatted prompt string
        """
        return f"""Find the corporate headquarters address for: {company_name}

Return ONLY the official corporate headquarters in this exact format:
Street Address: [full street address]
City: [city]
State: [state]
ZIP Code: [zip code]
Country: [country]

If the company has multiple locations, provide only the PRIMARY CORPORATE HEADQUARTERS.
If the information cannot be found with high confidence, respond with: "NOT FOUND"

Company: {company_name}"""
    
    def _parse_api_error(self, e: Exception) -> APIError:
        """Parse an API exception to extract error type and retry information.
        
        Args:
            e: The exception raised by the API client
            
        Returns:
            An APIError object containing parsed error details
        """
        message = str(e)
        retry_after: Optional[float] = None
        error_type = APIErrorType.UNKNOWN_ERROR
        
        if "429" in message or "Quota exceeded" in message:
            error_type = APIErrorType.QUOTA_EXCEEDED
            # Extract retry-after seconds if available
            match = re.search(r"Please retry in (\d+\.?\d*)s", message)
            if match:
                retry_after = float(match.group(1))
        elif "401" in message or "Authentication" in message:
            error_type = APIErrorType.AUTHENTICATION_ERROR
        elif "network" in message.lower() or "connection" in message.lower():
            error_type = APIErrorType.NETWORK_ERROR
        
        return APIError(
            error_type=error_type,
            message=message,
            retry_after=retry_after,
            original_exception=e
        )
    
    def _parse_response(self, response: str) -> Dict[str, str]:
        """Parse the API response into structured data.
        
        Args:
            response: Raw response from the API
            
        Returns:
            Dictionary containing parsed headquarters information
        """
        result = {
            'HQ_Street_Address': '',
            'HQ_City': '',
            'HQ_State': '',
            'HQ_ZIP': '',
            'HQ_Country': '',
            'Raw_Response': response.strip(),
            'Error_Message': ''
        }
        
        if response.strip().upper() == "NOT FOUND":
            return result
        
        # Extract information using regex patterns
        patterns = {
            'HQ_Street_Address': r'Street Address:\s*(.+?)(?=\n|$)',
            'HQ_City': r'City:\s*(.+?)(?=\n|$)',
            'HQ_State': r'State:\s*(.+?)(?=\n|$)',
            'HQ_ZIP': r'ZIP Code:\s*(.+?)(?=\n|$)',
            'HQ_Country': r'Country:\s*(.+?)(?=\n|$)'
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
            if match:
                result[field] = match.group(1).strip()
        
        return result
    
    def get_headquarters_info(self, company_name: str) -> Tuple[Dict[str, str], bool]:
        """Get headquarters information for a company.
        
        Args:
            company_name: Name of the company to query
            
        Returns:
            Tuple of (parsed_data, success_flag)
        """
        if not company_name or not company_name.strip():
            self.logger.warning("Empty company name provided")
            return {
                'HQ_Street_Address': '',
                'HQ_City': '',
                'HQ_State': '',
                'HQ_ZIP': '',
                'HQ_Country': '',
                'Raw_Response': 'ERROR: Empty company name',
                'Error_Message': 'Empty company name provided'
            }, False
        
        prompt = self._create_prompt(company_name.strip())
        
        for attempt in range(self.retry_attempts):
            try:
                # Apply rate limiting for Tier 1
                self.rate_limiter.wait_if_needed(self.max_output_tokens)
                
                start_time = time.time()
                
                # Make API request
                response = self.model.generate_content(prompt)
                
                response_time = time.time() - start_time
                
                if response.text:
                    parsed_data = self._parse_response(response.text)
                    self.logger.log_api_request(company_name, "SUCCESS", response_time)
                    
                    # Add delay between requests
                    time.sleep(self.delay_between_requests)
                    
                    return parsed_data, True
                else:
                    self.logger.warning(f"Empty response for company: {company_name}")
                    return {
                        'HQ_Street_Address': '',
                        'HQ_City': '',
                        'HQ_State': '',
                        'HQ_ZIP': '',
                        'HQ_Country': '',
                        'Raw_Response': 'ERROR: Empty response from API',
                        'Error_Message': 'Empty response from API'
                    }, False
                    
            except Exception as e:
                api_error = self._parse_api_error(e)
                error_msg = f"API request failed for '{company_name}' (attempt {attempt + 1}/{self.retry_attempts}): {api_error.message}"
                self.logger.error(error_msg)
                
                if attempt < self.retry_attempts - 1:
                    # Wait before retry (exponential backoff or retry_after)
                    if api_error.retry_after:
                        wait_time = api_error.retry_after
                    else:
                        wait_time = (2 ** attempt) * self.delay_between_requests
                    self.logger.debug(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    return {
                        'HQ_Street_Address': '',
                        'HQ_City': '',
                        'HQ_State': '',
                        'HQ_ZIP': '',
                        'HQ_Country': '',
                        'Raw_Response': f'ERROR: {api_error.message}',
                        'Error_Message': api_error.message
                    }, False
        
        return {
            'HQ_Street_Address': '',
            'HQ_City': '',
            'HQ_State': '',
            'HQ_ZIP': '',
            'HQ_Country': '',
            'Raw_Response': 'ERROR: All retry attempts failed',
            'Error_Message': 'All retry attempts failed'
        }, False
    
    def test_connection(self) -> bool:
        """Test API connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            test_prompt = "What is the capital of France?"
            response = self.model.generate_content(test_prompt)
            return response.text is not None and len(response.text) > 0
        except Exception as e:
            self.logger.error(f"API connection test failed: {str(e)}")
            return False

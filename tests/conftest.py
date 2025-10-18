"""
Pytest configuration and shared fixtures for Headquarters Finder tests.

This module provides common test fixtures and configuration for all test modules.
"""

import pytest
import tempfile
import os
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List

# Add the project root to the Python path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from headquarters_finder.core.api_client import GeminiAPIClient, Tier1RateLimiter
from headquarters_finder.core.csv_processor import CSVProcessor
from headquarters_finder.core.data_validator import DataValidator
from headquarters_finder.services.headquarters_service import HeadquartersService
from headquarters_finder.utils.config import Config
from headquarters_finder.utils.logger import Logger


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return pd.DataFrame({
        'Payee Name of Record': [
            'Apple Inc.',
            'Microsoft Corporation',
            'Google LLC',
            'Amazon.com Inc.',
            'Tesla Inc.'
        ],
        'Address1 of Record': [
            '1 Apple Park Way',
            'One Microsoft Way',
            '1600 Amphitheatre Parkway',
            '410 Terry Avenue North',
            '1 Tesla Road'
        ],
        'City of Record': [
            'Cupertino',
            'Redmond',
            'Mountain View',
            'Seattle',
            'Austin'
        ],
        'State of Record': [
            'CA',
            'WA',
            'CA',
            'WA',
            'TX'
        ],
        'Zip of Record': [
            '95014',
            '98052',
            '94043',
            '98109',
            '78725'
        ],
        'Status': ['Pending', 'Pending', 'Pending', 'Pending', 'Pending'],
        'Headquarters Address': ['', '', '', '', ''],
        'Processed_Timestamp': ['', '', '', '', ''],
        'Error_Message': ['', '', '', '', '']
    })


@pytest.fixture
def sample_gold_standard_data():
    """Sample gold standard data for validation testing."""
    return pd.DataFrame({
        'Payee Name of Record': [
            'Apple Inc.',
            'Microsoft Corporation',
            'Google LLC',
            'Amazon.com Inc.',
            'Tesla Inc.'
        ],
        'Headquarters Address': [
            '1 Apple Park Way, Cupertino, CA 95014, USA',
            'One Microsoft Way, Redmond, WA 98052, USA',
            '1600 Amphitheatre Parkway, Mountain View, CA 94043, USA',
            '410 Terry Avenue North, Seattle, WA 98109, USA',
            '1 Tesla Road, Austin, TX 78725, USA'
        ]
    })


@pytest.fixture
def mock_api_response():
    """Mock API response for testing."""
    return {
        'HQ_Street_Address': '1 Apple Park Way',
        'HQ_City': 'Cupertino',
        'HQ_State': 'CA',
        'HQ_ZIP': '95014',
        'HQ_Country': 'USA',
        'Raw_Response': '1 Apple Park Way, Cupertino, CA 95014, USA',
        'Error_Message': ''
    }


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock()
    config.get_api_config.return_value = Mock(
        api_key='test_api_key',
        model_name='gemini-2.5-pro',
        temperature=0.1,
        max_output_tokens=8192
    )
    config.get_file_config.return_value = Mock(
        input_file='test_input.csv',
        output_file='test_output.csv',
        log_file='test.log',
        gold_standard_file='test_gold.csv'
    )
    config.get_processing_config.return_value = Mock(
        batch_size=50,
        save_interval=50,
        retry_attempts=3,
        delay_between_requests=0.4
    )
    config.get_logging_config.return_value = Mock(
        log_level='INFO',
        max_log_size=10485760,
        backup_count=3
    )
    return config


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def mock_api_client(mock_logger):
    """Mock API client for testing."""
    client = Mock(spec=GeminiAPIClient)
    client.get_headquarters_info.return_value = (
        {
            'HQ_Street_Address': '1 Apple Park Way',
            'HQ_City': 'Cupertino',
            'HQ_State': 'CA',
            'HQ_ZIP': '95014',
            'HQ_Country': 'USA',
            'Raw_Response': '1 Apple Park Way, Cupertino, CA 95014, USA',
            'Error_Message': ''
        },
        True
    )
    client.test_connection.return_value = True
    return client


@pytest.fixture
def edge_case_data():
    """Edge case data for testing boundary conditions."""
    return {
        'empty_string': '',
        'whitespace_only': '   ',
        'very_long_string': 'A' * 10000,
        'special_characters': '!@#$%^&*()_+-=[]{}|;:,.<>?',
        'unicode_string': 'Tëst Çömpäny 中文 日本語',
        'numbers_only': '123456789',
        'mixed_content': 'Test123!@# Company Inc.',
        'newlines': 'Test\nCompany\nInc.',
        'tabs': 'Test\tCompany\tInc.',
        'quotes': 'Test "Company" Inc.',
        'apostrophes': "Test's Company Inc.",
        'parentheses': 'Test (Company) Inc.',
        'brackets': 'Test [Company] Inc.',
        'braces': 'Test {Company} Inc.',
        'angle_brackets': 'Test <Company> Inc.',
        'backslashes': 'Test\\Company\\Inc.',
        'forward_slashes': 'Test/Company/Inc.',
        'question_marks': 'Test?Company?Inc.',
        'exclamation_marks': 'Test!Company!Inc.',
        'at_symbols': 'Test@Company@Inc.',
        'hash_symbols': 'Test#Company#Inc.',
        'dollar_signs': 'Test$Company$Inc.',
        'percent_signs': 'Test%Company%Inc.',
        'ampersands': 'Test&Company&Inc.',
        'asterisks': 'Test*Company*Inc.',
        'plus_signs': 'Test+Company+Inc.',
        'equals_signs': 'Test=Company=Inc.',
        'minus_signs': 'Test-Company-Inc.',
        'underscores': 'Test_Company_Inc.',
        'periods': 'Test.Company.Inc.',
        'commas': 'Test,Company,Inc.',
        'colons': 'Test:Company:Inc.',
        'semicolons': 'Test;Company;Inc.',
        'pipes': 'Test|Company|Inc.',
        'tildes': 'Test~Company~Inc.',
        'backticks': 'Test`Company`Inc.',
        'carets': 'Test^Company^Inc.',
        'spaces': 'Test Company Inc.',
        'multiple_spaces': 'Test   Company   Inc.',
        'leading_spaces': '   Test Company Inc.',
        'trailing_spaces': 'Test Company Inc.   ',
        'leading_trailing_spaces': '   Test Company Inc.   ',
        'null_value': None,
        'boolean_true': True,
        'boolean_false': False,
        'integer_zero': 0,
        'integer_positive': 123,
        'integer_negative': -123,
        'float_zero': 0.0,
        'float_positive': 123.45,
        'float_negative': -123.45,
        'list_empty': [],
        'list_single': ['Test Company'],
        'list_multiple': ['Test Company', 'Inc.', 'LLC'],
        'dict_empty': {},
        'dict_single': {'name': 'Test Company'},
        'dict_multiple': {'name': 'Test Company', 'type': 'Inc.'},
        'tuple_empty': (),
        'tuple_single': ('Test Company',),
        'tuple_multiple': ('Test Company', 'Inc.', 'LLC'),
        'set_empty': set(),
        'set_single': {'Test Company'},
        'set_multiple': {'Test Company', 'Inc.', 'LLC'}
    }


@pytest.fixture
def boundary_test_data():
    """Boundary test data for testing limits."""
    return {
        'min_length': 'A',
        'max_reasonable_length': 'A' * 1000,
        'extreme_length': 'A' * 100000,
        'min_batch_size': 1,
        'max_batch_size': 1000,
        'zero_batch_size': 0,
        'negative_batch_size': -1,
        'min_delay': 0.0,
        'max_delay': 3600.0,
        'negative_delay': -1.0,
        'min_retry_attempts': 0,
        'max_retry_attempts': 10,
        'negative_retry_attempts': -1,
        'min_temperature': 0.0,
        'max_temperature': 1.0,
        'negative_temperature': -0.1,
        'above_max_temperature': 1.1,
        'min_tokens': 1,
        'max_tokens': 1000000,
        'zero_tokens': 0,
        'negative_tokens': -1
    }


@pytest.fixture
def error_scenarios():
    """Error scenarios for testing error handling."""
    return {
        'file_not_found': FileNotFoundError("File not found"),
        'permission_denied': PermissionError("Permission denied"),
        'disk_full': OSError("No space left on device"),
        'network_error': ConnectionError("Network connection failed"),
        'api_quota_exceeded': Exception("429 Quota exceeded"),
        'api_rate_limited': Exception("429 Rate limited"),
        'api_authentication_error': Exception("401 Authentication failed"),
        'api_server_error': Exception("500 Internal server error"),
        'api_timeout': TimeoutError("Request timeout"),
        'invalid_json': ValueError("Invalid JSON response"),
        'empty_response': ValueError("Empty response"),
        'malformed_response': ValueError("Malformed response"),
        'memory_error': MemoryError("Out of memory"),
        'keyboard_interrupt': KeyboardInterrupt("User interrupted"),
        'system_exit': SystemExit("System exit"),
        'base_exception': Exception("Base exception"),
        'runtime_error': RuntimeError("Runtime error"),
        'type_error': TypeError("Type error"),
        'value_error': ValueError("Value error"),
        'attribute_error': AttributeError("Attribute error"),
        'key_error': KeyError("Key error"),
        'index_error': IndexError("Index error"),
        'zero_division_error': ZeroDivisionError("Division by zero"),
        'overflow_error': OverflowError("Overflow error"),
        'arithmetic_error': ArithmeticError("Arithmetic error"),
        'assertion_error': AssertionError("Assertion failed"),
        'not_implemented_error': NotImplementedError("Not implemented"),
        'recursion_error': RecursionError("Maximum recursion depth exceeded"),
        'stop_iteration': StopIteration("Stop iteration"),
        'generator_exit': GeneratorExit("Generator exit"),
        'system_error': SystemError("System error"),
        'os_error': OSError("OS error"),
        'io_error': IOError("IO error"),
        'environment_error': EnvironmentError("Environment error"),
        'windows_error': OSError("Windows error"),
        'blocking_io_error': BlockingIOError("Blocking IO error"),
        'child_process_error': ChildProcessError("Child process error"),
        'connection_error': ConnectionError("Connection error"),
        'broken_pipe_error': BrokenPipeError("Broken pipe"),
        'connection_aborted_error': ConnectionAbortedError("Connection aborted"),
        'connection_refused_error': ConnectionRefusedError("Connection refused"),
        'connection_reset_error': ConnectionResetError("Connection reset"),
        'file_exists_error': FileExistsError("File exists"),
        'file_not_found_error': FileNotFoundError("File not found"),
        'is_a_directory_error': IsADirectoryError("Is a directory"),
        'not_a_directory_error': NotADirectoryError("Not a directory"),
        'permission_error': PermissionError("Permission denied"),
        'process_lookup_error': ProcessLookupError("Process lookup error"),
        'timeout_error': TimeoutError("Timeout error")
    }


@pytest.fixture
def performance_test_data():
    """Performance test data for testing with large datasets."""
    return {
        'small_dataset': 100,
        'medium_dataset': 1000,
        'large_dataset': 10000,
        'very_large_dataset': 100000,
        'extreme_dataset': 1000000
    }


@pytest.fixture
def concurrency_test_data():
    """Concurrency test data for testing parallel processing."""
    return {
        'single_thread': 1,
        'few_threads': 4,
        'many_threads': 16,
        'max_threads': 64,
        'extreme_threads': 256
    }


@pytest.fixture
def memory_test_data():
    """Memory test data for testing memory usage."""
    return {
        'small_memory': 1024,  # 1KB
        'medium_memory': 1024 * 1024,  # 1MB
        'large_memory': 1024 * 1024 * 100,  # 100MB
        'very_large_memory': 1024 * 1024 * 1024,  # 1GB
        'extreme_memory': 1024 * 1024 * 1024 * 10  # 10GB
    }


@pytest.fixture
def network_test_data():
    """Network test data for testing network conditions."""
    return {
        'fast_network': 0.1,  # 100ms latency
        'medium_network': 1.0,  # 1s latency
        'slow_network': 10.0,  # 10s latency
        'very_slow_network': 60.0,  # 60s latency
        'unstable_network': 0.5  # 500ms with random failures
    }


@pytest.fixture
def timezone_test_data():
    """Timezone test data for testing timezone handling."""
    return {
        'utc': 'UTC',
        'est': 'US/Eastern',
        'pst': 'US/Pacific',
        'gmt': 'GMT',
        'jst': 'Asia/Tokyo',
        'cet': 'Europe/Paris',
        'aest': 'Australia/Sydney',
        'invalid': 'Invalid/Timezone'
    }


@pytest.fixture
def locale_test_data():
    """Locale test data for testing internationalization."""
    return {
        'english': 'en_US',
        'spanish': 'es_ES',
        'french': 'fr_FR',
        'german': 'de_DE',
        'japanese': 'ja_JP',
        'chinese': 'zh_CN',
        'arabic': 'ar_SA',
        'russian': 'ru_RU',
        'invalid': 'invalid_locale'
    }


@pytest.fixture
def security_test_data():
    """Security test data for testing security vulnerabilities."""
    return {
        'sql_injection': "'; DROP TABLE users; --",
        'xss_script': '<script>alert("XSS")</script>',
        'path_traversal': '../../../etc/passwd',
        'command_injection': '; rm -rf /',
        'ldap_injection': '*)(uid=*))(|(uid=*',
        'xpath_injection': "' or '1'='1",
        'xml_injection': '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
        'json_injection': '{"malicious": "payload"}',
        'yaml_injection': '!!python/object/apply:os.system ["rm -rf /"]',
        'pickle_injection': 'c__builtin__\neval\np0\n(S\'os.system("rm -rf /")\'\np1\ntp2\nRp3\n.',
        'template_injection': '{{7*7}}',
        'code_injection': '__import__("os").system("rm -rf /")',
        'eval_injection': 'eval("__import__(\'os\').system(\'rm -rf /\')")',
        'exec_injection': 'exec("__import__(\'os\').system(\'rm -rf /\')")',
        'import_injection': '__import__("os").system("rm -rf /")',
        'globals_injection': 'globals()["__import__"]("os").system("rm -rf /")',
        'locals_injection': 'locals()["__import__"]("os").system("rm -rf /")',
        'vars_injection': 'vars()["__import__"]("os").system("rm -rf /")',
        'dir_injection': 'dir()["__import__"]("os").system("rm -rf /")',
        'hasattr_injection': 'hasattr(__import__("os"), "system")',
        'getattr_injection': 'getattr(__import__("os"), "system")("rm -rf /")',
        'setattr_injection': 'setattr(__import__("os"), "system", lambda x: None)',
        'delattr_injection': 'delattr(__import__("os"), "system")',
        'callable_injection': 'callable(__import__("os").system)',
        'isinstance_injection': 'isinstance(__import__("os"), object)',
        'issubclass_injection': 'issubclass(__import__("os").__class__, object)',
        'type_injection': 'type(__import__("os"))',
        'super_injection': 'super().__init__()',
        'property_injection': 'property(__import__("os").system)',
        'staticmethod_injection': 'staticmethod(__import__("os").system)',
        'classmethod_injection': 'classmethod(__import__("os").system)',
        'abstractmethod_injection': 'abstractmethod(__import__("os").system)',
        'final_injection': 'final(__import__("os").system)',
        'overload_injection': 'overload(__import__("os").system)',
        'dataclass_injection': 'dataclass(__import__("os").system)',
        'frozen_injection': 'frozen(__import__("os").system)',
        'field_injection': 'field(__import__("os").system)',
        'init_injection': 'init(__import__("os").system)',
        'repr_injection': 'repr(__import__("os").system)',
        'str_injection': 'str(__import__("os").system)',
        'bytes_injection': 'bytes(__import__("os").system)',
        'bytearray_injection': 'bytearray(__import__("os").system)',
        'memoryview_injection': 'memoryview(__import__("os").system)',
        'slice_injection': 'slice(__import__("os").system)',
        'range_injection': 'range(__import__("os").system)',
        'enumerate_injection': 'enumerate(__import__("os").system)',
        'zip_injection': 'zip(__import__("os").system)',
        'map_injection': 'map(__import__("os").system)',
        'filter_injection': 'filter(__import__("os").system)',
        'reduce_injection': 'reduce(__import__("os").system)',
        'sum_injection': 'sum(__import__("os").system)',
        'min_injection': 'min(__import__("os").system)',
        'max_injection': 'max(__import__("os").system)',
        'abs_injection': 'abs(__import__("os").system)',
        'round_injection': 'round(__import__("os").system)',
        'pow_injection': 'pow(__import__("os").system)',
        'divmod_injection': 'divmod(__import__("os").system)',
        'bin_injection': 'bin(__import__("os").system)',
        'oct_injection': 'oct(__import__("os").system)',
        'hex_injection': 'hex(__import__("os").system)',
        'ord_injection': 'ord(__import__("os").system)',
        'chr_injection': 'chr(__import__("os").system)',
        'ascii_injection': 'ascii(__import__("os").system)',
        'repr_injection': 'repr(__import__("os").system)',
        'str_injection': 'str(__import__("os").system)',
        'bytes_injection': 'bytes(__import__("os").system)',
        'bytearray_injection': 'bytearray(__import__("os").system)',
        'memoryview_injection': 'memoryview(__import__("os").system)',
        'slice_injection': 'slice(__import__("os").system)',
        'range_injection': 'range(__import__("os").system)',
        'enumerate_injection': 'enumerate(__import__("os").system)',
        'zip_injection': 'zip(__import__("os").system)',
        'map_injection': 'map(__import__("os").system)',
        'filter_injection': 'filter(__import__("os").system)',
        'reduce_injection': 'reduce(__import__("os").system)',
        'sum_injection': 'sum(__import__("os").system)',
        'min_injection': 'min(__import__("os").system)',
        'max_injection': 'max(__import__("os").system)',
        'abs_injection': 'abs(__import__("os").system)',
        'round_injection': 'round(__import__("os").system)',
        'pow_injection': 'pow(__import__("os").system)',
        'divmod_injection': 'divmod(__import__("os").system)',
        'bin_injection': 'bin(__import__("os").system)',
        'oct_injection': 'oct(__import__("os").system)',
        'hex_injection': 'hex(__import__("os").system)',
        'ord_injection': 'ord(__import__("os").system)',
        'chr_injection': 'chr(__import__("os").system)',
        'ascii_injection': 'ascii(__import__("os").system)'
    }

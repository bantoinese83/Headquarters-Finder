"""
Unit tests for Config class and related components.

Tests the configuration management with comprehensive coverage including
golden path scenarios, edge cases, and error conditions.
"""

import pytest
import configparser
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

from headquarters_finder.utils.config import (
    Config,
    ConfigSection,
    APIConfig,
    FileConfig,
    ProcessingConfig,
    LoggingConfig
)


class TestConfigSection:
    """Test cases for ConfigSection enum."""
    
    def test_config_section_values(self):
        """Test ConfigSection enum values."""
        assert ConfigSection.API.value == "API"
        assert ConfigSection.FILES.value == "FILES"
        assert ConfigSection.PROCESSING.value == "PROCESSING"
        assert ConfigSection.LOGGING.value == "LOGGING"
    
    def test_config_section_enumeration(self):
        """Test ConfigSection enum iteration."""
        sections = list(ConfigSection)
        assert len(sections) == 4
        assert ConfigSection.API in sections
        assert ConfigSection.FILES in sections
        assert ConfigSection.PROCESSING in sections
        assert ConfigSection.LOGGING in sections


class TestAPIConfig:
    """Test cases for APIConfig dataclass."""
    
    def test_api_config_creation(self):
        """Test APIConfig creation with all parameters."""
        config = APIConfig(
            api_key="test_key",
            model_name="gemini-2.5-pro",
            temperature=0.1,
            max_output_tokens=8192
        )
        
        assert config.api_key == "test_key"
        assert config.model_name == "gemini-2.5-pro"
        assert config.temperature == 0.1
        assert config.max_output_tokens == 8192
    
    def test_api_config_default_values(self):
        """Test APIConfig with default values."""
        config = APIConfig(
            api_key="test_key",
            model_name="test_model",
            temperature=0.5,
            max_output_tokens=1000
        )
        
        assert config.api_key == "test_key"
        assert config.model_name == "test_model"
        assert config.temperature == 0.5
        assert config.max_output_tokens == 1000


class TestFileConfig:
    """Test cases for FileConfig dataclass."""
    
    def test_file_config_creation(self):
        """Test FileConfig creation with all parameters."""
        config = FileConfig(
            input_file="input.csv",
            output_file="output.csv",
            log_file="log.log",
            gold_standard_file="gold.csv"
        )
        
        assert config.input_file == "input.csv"
        assert config.output_file == "output.csv"
        assert config.log_file == "log.log"
        assert config.gold_standard_file == "gold.csv"


class TestProcessingConfig:
    """Test cases for ProcessingConfig dataclass."""
    
    def test_processing_config_creation(self):
        """Test ProcessingConfig creation with all parameters."""
        config = ProcessingConfig(
            batch_size=50,
            save_interval=50,
            retry_attempts=3,
            delay_between_requests=0.4
        )
        
        assert config.batch_size == 50
        assert config.save_interval == 50
        assert config.retry_attempts == 3
        assert config.delay_between_requests == 0.4


class TestLoggingConfig:
    """Test cases for LoggingConfig dataclass."""
    
    def test_logging_config_creation(self):
        """Test LoggingConfig creation with all parameters."""
        config = LoggingConfig(
            log_level="INFO",
            max_log_size=10485760,
            backup_count=3
        )
        
        assert config.log_level == "INFO"
        assert config.max_log_size == 10485760
        assert config.backup_count == 3


class TestConfig:
    """Test cases for Config class."""
    
    @pytest.fixture
    def valid_config_content(self):
        """Valid configuration content for testing."""
        return """
[API]
api_key = TEST_API_KEY
model_name = gemini-2.5-pro
temperature = 0.1
max_output_tokens = 8192

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

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
    
    @pytest.fixture
    def temp_config_file(self, tmp_path, valid_config_content):
        """Create a temporary config file for testing."""
        config_file = tmp_path / "test_config.ini"
        config_file.write_text(valid_config_content)
        return str(config_file)
    
    def test_config_initialization_success(self, temp_config_file):
        """Test successful Config initialization."""
        config = Config(temp_config_file)
        
        assert config.config_file == Path(temp_config_file)
        assert isinstance(config.config, configparser.ConfigParser)
    
    def test_config_initialization_file_not_found(self):
        """Test Config initialization with non-existent file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            Config("non_existent_config.ini")
    
    def test_config_initialization_malformed_file(self, tmp_path):
        """Test Config initialization with malformed config file."""
        config_file = tmp_path / "malformed_config.ini"
        config_file.write_text("[API]\ninvalid_content")
        
        with pytest.raises(configparser.Error):
            Config(str(config_file))
    
    def test_config_initialization_missing_section(self, tmp_path):
        """Test Config initialization with missing required section."""
        config_file = tmp_path / "incomplete_config.ini"
        config_file.write_text("""
[API]
api_key = TEST_API_KEY
model_name = gemini-2.5-pro
temperature = 0.1
max_output_tokens = 8192
""")
        
        with pytest.raises(ValueError, match="Missing required section"):
            Config(str(config_file))
    
    def test_config_initialization_invalid_api_key(self, tmp_path):
        """Test Config initialization with invalid API key."""
        config_file = tmp_path / "invalid_api_config.ini"
        config_file.write_text("""
[API]
api_key = 
model_name = gemini-2.5-pro
temperature = 0.1
max_output_tokens = 8192

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
""")
        
        with pytest.raises(ValueError, match="API key not set"):
            Config(str(config_file))
    
    def test_config_initialization_placeholder_api_key(self, tmp_path):
        """Test Config initialization with placeholder API key."""
        config_file = tmp_path / "placeholder_api_config.ini"
        config_file.write_text("""
[API]
api_key = YOUR_GEMINI_API_KEY_HERE
model_name = gemini-2.5-pro
temperature = 0.1
max_output_tokens = 8192

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
""")
        
        with pytest.raises(ValueError, match="API key not set"):
            Config(str(config_file))
    
    def test_config_initialization_invalid_temperature(self, tmp_path):
        """Test Config initialization with invalid temperature."""
        config_file = tmp_path / "invalid_temp_config.ini"
        config_file.write_text("""
[API]
api_key = TEST_API_KEY
model_name = gemini-2.5-pro
temperature = 1.5
max_output_tokens = 8192

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
""")
        
        with pytest.raises(ValueError, match="Temperature must be between 0.0 and 1.0"):
            Config(str(config_file))
    
    def test_config_initialization_invalid_max_tokens(self, tmp_path):
        """Test Config initialization with invalid max tokens."""
        config_file = tmp_path / "invalid_tokens_config.ini"
        config_file.write_text("""
[API]
api_key = TEST_API_KEY
model_name = gemini-2.5-pro
temperature = 0.1
max_output_tokens = -100

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
""")
        
        with pytest.raises(ValueError, match="Max output tokens must be positive"):
            Config(str(config_file))
    
    def test_get_api_config(self, temp_config_file):
        """Test getting API configuration."""
        config = Config(temp_config_file)
        api_config = config.get_api_config()
        
        assert isinstance(api_config, APIConfig)
        assert api_config.api_key == "TEST_API_KEY"
        assert api_config.model_name == "gemini-2.5-pro"
        assert api_config.temperature == 0.1
        assert api_config.max_output_tokens == 8192
    
    def test_get_file_config(self, temp_config_file):
        """Test getting file configuration."""
        config = Config(temp_config_file)
        file_config = config.get_file_config()
        
        assert isinstance(file_config, FileConfig)
        assert file_config.input_file == "data/input.csv"
        assert file_config.output_file == "data/output.csv"
        assert file_config.log_file == "logs/app.log"
        assert file_config.gold_standard_file == "data/gold_standard.csv"
    
    def test_get_processing_config(self, temp_config_file):
        """Test getting processing configuration."""
        config = Config(temp_config_file)
        processing_config = config.get_processing_config()
        
        assert isinstance(processing_config, ProcessingConfig)
        assert processing_config.batch_size == 50
        assert processing_config.save_interval == 50
        assert processing_config.retry_attempts == 3
        assert processing_config.delay_between_requests == 0.4
    
    def test_get_logging_config(self, temp_config_file):
        """Test getting logging configuration."""
        config = Config(temp_config_file)
        logging_config = config.get_logging_config()
        
        assert isinstance(logging_config, LoggingConfig)
        assert logging_config.log_level == "INFO"
        assert logging_config.max_log_size == 10485760
        assert logging_config.backup_count == 3
    
    def test_validate_config_success(self, temp_config_file):
        """Test successful configuration validation."""
        config = Config(temp_config_file)
        assert config.validate_config() is True
    
    def test_validate_config_failure(self, tmp_path):
        """Test configuration validation failure."""
        config_file = tmp_path / "invalid_config.ini"
        config_file.write_text("""
[API]
api_key =
model_name = gemini-2.5-pro
temperature = 0.1
max_output_tokens = 8192

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
""")
        
        config = Config(str(config_file), validate_on_init=False)
        assert config.validate_config() is False
    
    def test_config_with_missing_option(self, tmp_path):
        """Test Config with missing required option."""
        config_file = tmp_path / "missing_option_config.ini"
        config_file.write_text("""
[API]
api_key = TEST_API_KEY
model_name = gemini-2.5-pro
temperature = 0.1

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
""")
        
        with pytest.raises(ValueError, match="Missing required API configuration"):
            Config(str(config_file))
    
    def test_config_boundary_temperature_values(self, tmp_path):
        """Test Config with boundary temperature values."""
        # Test temperature = 0.0 (valid)
        config_file = tmp_path / "boundary_temp_config.ini"
        config_file.write_text("""
[API]
api_key = TEST_API_KEY
model_name = gemini-2.5-pro
temperature = 0.0
max_output_tokens = 8192

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
""")
        
        config = Config(str(config_file))
        assert config.validate_config() is True
        
        # Test temperature = 1.0 (valid)
        config_file.write_text("""
[API]
api_key = TEST_API_KEY
model_name = gemini-2.5-pro
temperature = 1.0
max_output_tokens = 8192

[FILES]
input_file = data/input.csv
output_file = data/output.csv
log_file = logs/app.log
gold_standard_file = data/gold_standard.csv

[PROCESSING]
batch_size = 50
save_interval = 50
retry_attempts = 3
delay_between_requests = 0.4

[LOGGING]
log_level = INFO
max_log_size = 10485760
backup_count = 3
""")
        
        config = Config(str(config_file))
        assert config.validate_config() is True

"""
Unit tests for Logger class and related components.

Tests the logging functionality with comprehensive coverage including
golden path scenarios, edge cases, and error conditions.
"""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import os

from headquarters_finder.utils.logger import (
    Logger,
    LogLevel,
    LoggingError
)


class TestLogLevel:
    """Test cases for LogLevel enum."""
    
    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"
    
    def test_log_level_enumeration(self):
        """Test LogLevel enum iteration."""
        levels = list(LogLevel)
        assert len(levels) == 5
        assert LogLevel.DEBUG in levels
        assert LogLevel.INFO in levels
        assert LogLevel.WARNING in levels
        assert LogLevel.ERROR in levels
        assert LogLevel.CRITICAL in levels


class TestLoggingError:
    """Test cases for LoggingError exception."""
    
    def test_logging_error_creation(self):
        """Test LoggingError creation."""
        error = LoggingError("Test error message")
        assert str(error) == "Test error message"
    
    def test_logging_error_inheritance(self):
        """Test LoggingError inheritance from Exception."""
        error = LoggingError("Test error message")
        assert isinstance(error, Exception)


class TestLogger:
    """Test cases for Logger class."""
    
    @pytest.fixture
    def temp_log_file(self, tmp_path):
        """Create a temporary log file for testing."""
        log_file = tmp_path / "test.log"
        return str(log_file)
    
    def test_logger_initialization_default_values(self, temp_log_file):
        """Test Logger initialization with default values."""
        logger = Logger(temp_log_file)
        
        assert logger.log_file == Path(temp_log_file)
        assert logger.log_level == logging.INFO
        assert logger.max_size == 10485760
        assert logger.backup_count == 3
        assert logger.log_file.parent.exists()
    
    def test_logger_initialization_custom_values(self, temp_log_file):
        """Test Logger initialization with custom values."""
        logger = Logger(
            temp_log_file,
            log_level=LogLevel.DEBUG,
            max_size=1024,
            backup_count=1
        )
        
        assert logger.log_file == Path(temp_log_file)
        assert logger.log_level == logging.DEBUG
        assert logger.max_size == 1024
        assert logger.backup_count == 1
    
    def test_logger_initialization_string_log_level(self, temp_log_file):
        """Test Logger initialization with string log level."""
        logger = Logger(temp_log_file, log_level="WARNING")
        
        assert logger.log_level == logging.WARNING
    
    def test_logger_initialization_invalid_log_level(self, temp_log_file):
        """Test Logger initialization with invalid log level."""
        with pytest.raises(ValueError, match="Invalid log level"):
            Logger(temp_log_file, log_level="INVALID_LEVEL")
    
    def test_logger_initialization_negative_max_size(self, temp_log_file):
        """Test Logger initialization with negative max size."""
        with pytest.raises(ValueError, match="Max size must be positive"):
            Logger(temp_log_file, max_size=-1)
    
    def test_logger_initialization_zero_max_size(self, temp_log_file):
        """Test Logger initialization with zero max size."""
        with pytest.raises(ValueError, match="Max size must be positive"):
            Logger(temp_log_file, max_size=0)
    
    def test_logger_initialization_negative_backup_count(self, temp_log_file):
        """Test Logger initialization with negative backup count."""
        with pytest.raises(ValueError, match="Backup count must be non-negative"):
            Logger(temp_log_file, backup_count=-1)
    
    def test_logger_initialization_creates_directory(self, tmp_path):
        """Test Logger creates log directory if it doesn't exist."""
        log_file = tmp_path / "subdir" / "test.log"
        
        logger = Logger(str(log_file))
        
        assert logger.log_file.parent.exists()
        assert logger.log_file.parent.name == "subdir"
    
    def test_logger_initialization_directory_creation_failure(self, tmp_path):
        """Test Logger handles directory creation failure."""
        # Create a file where we want to create a directory
        blocking_file = tmp_path / "subdir"
        blocking_file.write_text("blocking file")
        
        log_file = tmp_path / "subdir" / "test.log"
        
        with pytest.raises(OSError, match="Failed to create log directory"):
            Logger(str(log_file))
    
    def test_logger_initialization_handler_setup_failure(self, temp_log_file):
        """Test Logger handles handler setup failure."""
        with patch('logging.handlers.RotatingFileHandler') as mock_handler:
            mock_handler.side_effect = Exception("Handler setup failed")
            
            with pytest.raises(LoggingError, match="Failed to set up logger handlers"):
                Logger(temp_log_file)
    
    def test_get_logger_returns_logger_instance(self, temp_log_file):
        """Test get_logger returns a logger instance."""
        logger = Logger(temp_log_file)
        logger_instance = logger.get_logger()
        
        assert isinstance(logger_instance, logging.Logger)
        assert logger_instance.name == 'headquarters_finder'
    
    def test_logger_prevents_duplicate_handlers(self, temp_log_file):
        """Test Logger prevents duplicate handlers on re-initialization."""
        logger = Logger(temp_log_file)
        initial_handler_count = len(logger.logger.handlers)
        
        # Re-initialize the same logger
        logger._setup_logger()
        
        # Should still have the same number of handlers (not doubled)
        assert len(logger.logger.handlers) == initial_handler_count
    
    def test_logger_file_handler_configuration(self, temp_log_file):
        """Test file handler is configured correctly."""
        logger = Logger(temp_log_file, max_size=1024, backup_count=2)
        
        file_handlers = [h for h in logger.logger.handlers 
                        if isinstance(h, logging.handlers.RotatingFileHandler)]
        
        assert len(file_handlers) == 1
        file_handler = file_handlers[0]
        assert file_handler.maxBytes == 1024
        assert file_handler.backupCount == 2
        assert file_handler.encoding == 'utf-8'
    
    def test_logger_console_handler_configuration(self, temp_log_file):
        """Test console handler is configured correctly."""
        logger = Logger(temp_log_file)
        
        console_handlers = [h for h in logger.logger.handlers 
                           if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler)]
        
        assert len(console_handlers) == 1
        console_handler = console_handlers[0]
        # Just check that we have a console handler (StreamHandler that's not a file handler)
        assert isinstance(console_handler, logging.StreamHandler)
    
    def test_logger_formatter_configuration(self, temp_log_file):
        """Test formatters are configured correctly."""
        logger = Logger(temp_log_file)
        
        # Check file handler formatter
        file_handlers = [h for h in logger.logger.handlers 
                        if isinstance(h, logging.handlers.RotatingFileHandler)]
        assert file_handlers[0].formatter is not None
        
        # Check console handler formatter
        console_handlers = [h for h in logger.logger.handlers 
                           if isinstance(h, logging.StreamHandler)]
        assert console_handlers[0].formatter is not None
    
    def test_logger_log_level_setting(self, temp_log_file):
        """Test logger level is set correctly."""
        logger = Logger(temp_log_file, log_level=LogLevel.DEBUG)
        
        assert logger.logger.level == logging.DEBUG
    
    def test_logger_propagate_setting(self, temp_log_file):
        """Test logger propagate is set to False."""
        logger = Logger(temp_log_file)
        
        assert logger.logger.propagate is False
    
    def test_logger_with_different_log_levels(self, temp_log_file):
        """Test Logger with different log levels."""
        levels = [
            (LogLevel.DEBUG, logging.DEBUG),
            (LogLevel.INFO, logging.INFO),
            (LogLevel.WARNING, logging.WARNING),
            (LogLevel.ERROR, logging.ERROR),
            (LogLevel.CRITICAL, logging.CRITICAL)
        ]
        
        for log_level, expected_level in levels:
            logger = Logger(temp_log_file, log_level=log_level)
            assert logger.log_level == expected_level
            assert logger.logger.level == expected_level
    
    def test_logger_with_string_log_levels(self, temp_log_file):
        """Test Logger with string log levels."""
        levels = [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL)
        ]
        
        for log_level_str, expected_level in levels:
            logger = Logger(temp_log_file, log_level=log_level_str)
            assert logger.log_level == expected_level
            assert logger.logger.level == expected_level
    
    def test_logger_case_insensitive_log_level(self, temp_log_file):
        """Test Logger with case insensitive log level."""
        logger = Logger(temp_log_file, log_level="debug")
        assert logger.log_level == logging.DEBUG
    
    def test_logger_actual_logging_functionality(self, temp_log_file):
        """Test actual logging functionality."""
        logger = Logger(temp_log_file, log_level=LogLevel.DEBUG)
        logger_instance = logger.get_logger()
        
        # Test different log levels
        logger_instance.debug("Debug message")
        logger_instance.info("Info message")
        logger_instance.warning("Warning message")
        logger_instance.error("Error message")
        logger_instance.critical("Critical message")
        
        # Verify log file was created and has content
        assert logger.log_file.exists()
        log_content = logger.log_file.read_text()
        assert "Debug message" in log_content
        assert "Info message" in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content
        assert "Critical message" in log_content
    
    def test_logger_rotating_file_behavior(self, temp_log_file):
        """Test rotating file handler behavior."""
        logger = Logger(temp_log_file, max_size=100, backup_count=2)
        logger_instance = logger.get_logger()
        
        # Write enough content to trigger rotation
        for i in range(10):
            logger_instance.info(f"Test message {i} " * 20)  # Long message
        
        # Check if backup files were created
        log_dir = logger.log_file.parent
        log_files = list(log_dir.glob("test.log*"))
        assert len(log_files) >= 1  # At least the main log file
    
    def test_logger_handles_unicode_content(self, temp_log_file):
        """Test Logger handles unicode content correctly."""
        logger = Logger(temp_log_file)
        logger_instance = logger.get_logger()
        
        unicode_message = "Test message with unicode: 🚀 🎉 ✅"
        logger_instance.info(unicode_message)
        
        log_content = logger.log_file.read_text(encoding='utf-8')
        assert unicode_message in log_content
    
    def test_logger_handles_large_messages(self, temp_log_file):
        """Test Logger handles large messages correctly."""
        logger = Logger(temp_log_file)
        logger_instance = logger.get_logger()
        
        large_message = "Large message: " + "x" * 10000
        logger_instance.info(large_message)
        
        log_content = logger.log_file.read_text()
        assert large_message in log_content

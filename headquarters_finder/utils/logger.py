"""
Logging configuration module for the Headquarters Finder application.

This module provides robust logging functionality with rotating file handlers,
multiple log levels, and comprehensive error handling for the Headquarters Finder.

Author: AI Assistant
Version: 1.0.0
License: Proprietary
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional, Union
from pathlib import Path
from enum import Enum


class LogLevel(Enum):
    """Enumeration of supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingError(Exception):
    """Custom exception for logging errors."""
    pass


class Logger:
    """Centralized logger for the application.
    
    This class provides robust logging functionality with rotating file handlers,
    multiple log levels, and comprehensive error handling.
    """
    
    def __init__(
        self, 
        log_file: str, 
        log_level: Union[str, LogLevel] = LogLevel.INFO, 
        max_size: int = 10485760, 
        backup_count: int = 3
    ) -> None:
        """Initialize logger with rotating file handler.
        
        Args:
            log_file: Path to the log file.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            max_size: Maximum size of log file in bytes (default: 10MB).
            backup_count: Number of backup files to keep.
            
        Raises:
            ValueError: If parameters are invalid.
            OSError: If log directory creation fails.
            LoggingError: If logger setup fails.
        """
        # Validate parameters
        if max_size <= 0:
            raise ValueError("Max size must be positive")
        if backup_count < 0:
            raise ValueError("Backup count must be non-negative")
        
        self.log_file = Path(log_file)
        
        # Handle log level
        if isinstance(log_level, LogLevel):
            self.log_level = getattr(logging, log_level.value)
        else:
            try:
                self.log_level = getattr(logging, log_level.upper())
            except AttributeError:
                raise ValueError(f"Invalid log level: {log_level}")
        
        self.max_size = max_size
        self.backup_count = backup_count
        
        # Create logs directory if it doesn't exist
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create log directory: {e}") from e
        
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Setup logger with rotating file handler."""
        try:
            # Create logger
            self.logger = logging.getLogger('headquarters_finder')
            self.logger.setLevel(self.log_level)
            self.logger.propagate = False  # Prevent duplicate logs from root logger
            
            # Clear any existing handlers
            self.logger.handlers.clear()
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            
            # Create console handler for immediate feedback
            console_handler = logging.StreamHandler(sys.stdout)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Set formatter for handlers
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add handlers to logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        except Exception as e:
            raise LoggingError(f"Failed to set up logger handlers: {e}") from e
    
    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)
    
    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)
    
    def log_batch_progress(self, batch_num: int, total_batches: int, 
                          records_processed: int, total_records: int) -> None:
        """Log batch processing progress.
        
        Args:
            batch_num: Current batch number
            total_batches: Total number of batches
            records_processed: Number of records processed so far
            total_records: Total number of records to process
        """
        progress_percent = (records_processed / total_records) * 100
        self.info(f"Batch {batch_num}/{total_batches} completed. "
                 f"Progress: {records_processed}/{total_records} ({progress_percent:.1f}%)")
    
    def log_api_request(self, company_name: str, status: str, 
                       response_time: Optional[float] = None) -> None:
        """Log API request details.
        
        Args:
            company_name: Name of the company being queried
            status: Status of the request (SUCCESS, FAILED, RETRY)
            response_time: Response time in seconds
        """
        if response_time:
            self.debug(f"API request for '{company_name}': {status} "
                      f"(Response time: {response_time:.2f}s)")
        else:
            self.debug(f"API request for '{company_name}': {status}")
    
    def log_validation_results(self, accuracy: float, total_compared: int, 
                              mismatches: int) -> None:
        """Log validation results.
        
        Args:
            accuracy: Accuracy percentage
            total_compared: Total number of records compared
            mismatches: Number of mismatches found
        """
        self.info(f"Validation complete: {accuracy:.1f}% accuracy "
                 f"({total_compared - mismatches}/{total_compared} correct, "
                 f"{mismatches} mismatches)")
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance.
        
        Returns:
            Configured logging.Logger instance.
        """
        return self.logger


def get_logger(log_file: str, log_level: str = "INFO") -> Logger:
    """Get a configured logger instance.
    
    Args:
        log_file: Path to the log file
        log_level: Logging level
        
    Returns:
        Configured Logger instance
    """
    return Logger(log_file, log_level)

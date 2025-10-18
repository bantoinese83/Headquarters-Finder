#!/usr/bin/env python3
"""
Test script for the Headquarters Finder application.
Tests basic functionality without requiring API key.
"""

import sys
import os
import tempfile
import pandas as pd
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from headquarters_finder.utils.config import Config
from headquarters_finder.utils.logger import Logger
from headquarters_finder.core.csv_processor import CSVProcessor


def test_config_loading():
    """Test configuration loading."""
    print("Testing configuration loading...")
    
    try:
        config = Config("headquarters_finder/config.ini")
        print("✓ Configuration loaded successfully")
        
        # Test individual config sections
        api_config = config.get_api_config()
        file_config = config.get_file_config()
        processing_config = config.get_processing_config()
        logging_config = config.get_logging_config()
        
        print("✓ All configuration sections loaded")
        return True
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False


def test_logger():
    """Test logger functionality."""
    print("Testing logger...")
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            log_file = f.name
        
        logger = Logger(log_file, "INFO")
        logger.info("Test log message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        # Check if log file was created and has content
        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            print("✓ Logger working correctly")
            os.unlink(log_file)
            return True
        else:
            print("✗ Logger failed to create log file")
            return False
    except Exception as e:
        print(f"✗ Logger test failed: {e}")
        return False


def test_csv_processor():
    """Test CSV processor functionality."""
    print("Testing CSV processor...")
    
    try:
        # Create a temporary CSV file for testing
        test_data = {
            'Geographic Location': ['State of California', 'Cook County, Illinois'],
            'Payee Name of Record': ['TEST COMPANY 1', 'TEST COMPANY 2'],
            'Address1 of Record': ['123 Test St', '456 Sample Ave'],
            'City of Record': ['Test City', 'Sample City'],
            'State of Record': ['CA', 'IL'],
            'Zip of Record': ['12345', '67890']
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_input = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_output = f.name
        
        # Create test CSV
        df = pd.DataFrame(test_data)
        df.to_csv(test_input, index=False)
        
        # Test CSV processor
        processor = CSVProcessor(test_input, test_output)
        loaded_df = processor.read_input_csv()
        
        if len(loaded_df) == 2 and 'Status' in loaded_df.columns:
            print("✓ CSV processor working correctly")
            
            # Clean up
            os.unlink(test_input)
            os.unlink(test_output)
            return True
        else:
            print("✗ CSV processor failed to load data correctly")
            return False
    except Exception as e:
        print(f"✗ CSV processor test failed: {e}")
        return False


def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")
    
    try:
        from headquarters_finder.core.api_client import GeminiAPIClient
        from headquarters_finder.core.data_validator import DataValidator
        from headquarters_finder.services.headquarters_service import HeadquartersService
        print("✓ All modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("HEADQUARTERS FINDER - TEST SUITE")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config_loading,
        test_logger,
        test_csv_processor
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("✓ All tests passed! Application is ready to use.")
        print("\nNext steps:")
        print("1. Set your Gemini API key in config.ini")
        print("2. Run: python3 main.py --test")
        print("3. Run: python3 main.py")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Main application entry point for the Headquarters Finder.

This module orchestrates the complete workflow for processing corporate headquarters data
using the Google Gemini 2.5 Pro API. It provides a robust, scalable solution for
automated headquarters information retrieval with high accuracy.

Author: AI Assistant
Version: 1.0.0
License: Proprietary
"""

import sys
import os
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import from the headquarters_finder package
from .utils.config import Config, FileConfig
from .utils.logger import Logger
from .core.api_client import GeminiAPIClient
from .core.csv_processor import CSVProcessor
from .core.data_validator import DataValidator
from .services.headquarters_service import HeadquartersService


class HeadquartersFinderApp:
    """Main application class for headquarters finding.
    
    This class orchestrates the complete workflow for processing corporate
    headquarters data using the Google Gemini 2.5 Pro API.
    """
    
    def __init__(self, config_file: str = "config.ini") -> None:
        """Initialize the application.
        
        Args:
            config_file: Path to configuration file. Defaults to "config.ini".
            
        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config file is invalid.
        """
        self.config_file = Path(config_file)
        self.config: Optional[Config] = None
        self.logger: Optional[Logger] = None
        self.api_client: Optional[GeminiAPIClient] = None
        self.csv_processor: Optional[CSVProcessor] = None
        self.headquarters_service: Optional[HeadquartersService] = None
        self.data_validator: Optional[DataValidator] = None
        self.file_config: Optional[FileConfig] = None
        
        # Validate config file exists
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
    
    def initialize(self) -> bool:
        """Initialize all components.
        
        Returns:
            True if initialization successful, False otherwise
            
        Raises:
            FileNotFoundError: If required files are missing.
            ValueError: If configuration is invalid.
            RuntimeError: If API connection fails.
        """
        try:
            # Load configuration
            self.config = Config(str(self.config_file))
            
            # Validate configuration
            if not self.config.validate_config():
                error_msg = (
                    "Invalid configuration. Please check your config.ini file.\n"
                    "Make sure to set your Gemini API key in the [API] section."
                )
                print(f"ERROR: {error_msg}")
                return False
            
            # Initialize logger
            self.file_config = self.config.get_file_config()
            logging_config = self.config.get_logging_config()
            self.logger = Logger(
                self.file_config.log_file,
                logging_config.log_level
            )
            
            self.logger.info("Headquarters Finder application started")
            
            # Initialize API client
            api_config = self.config.get_api_config()
            processing_config = self.config.get_processing_config()
            
            self.api_client = GeminiAPIClient(
                api_key=api_config.api_key,
                model_name=api_config.model_name,
                temperature=api_config.temperature,
                max_output_tokens=api_config.max_output_tokens,
                retry_attempts=processing_config.retry_attempts,
                delay_between_requests=processing_config.delay_between_requests,
                logger=self.logger
            )
            
            # Test API connection
            if not self.api_client.test_connection():
                self.logger.error("Failed to connect to Gemini API")
                print("ERROR: Failed to connect to Gemini API. Please check your API key.")
                return False
            
            self.logger.info("API connection successful")
            
            # Initialize CSV processor
            self.csv_processor = CSVProcessor(
                self.file_config.input_file,
                self.file_config.output_file,
                self.logger
            )
            
            # Initialize headquarters service
            self.headquarters_service = HeadquartersService(
                self.api_client,
                self.csv_processor,
                processing_config,
                self.logger
            )
            
            # Initialize data validator
            self.data_validator = DataValidator(self.file_config, self.logger)
            
            self.logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize application: {str(e)}"
            print(f"ERROR: {error_msg}")
            if self.logger:
                self.logger.error(f"Initialization failed: {str(e)}")
            return False
    
    def run(self, validate: bool = False) -> Dict[str, Any]:
        """Run the headquarters processing workflow.
        
        Args:
            validate: Whether to validate against gold standard
            
        Returns:
            Dictionary containing processing results
        """
        try:
            self.logger.info("Starting headquarters processing workflow")
            
            # Calculate Tier 1 processing estimates
            input_df = self.csv_processor.read_input_csv()
            pending_records = len(input_df[input_df['Status'].isin(['Pending', 'Error'])])
            
            if pending_records > 0:
                time_estimates = self.headquarters_service.calculate_processing_time(pending_records)
                self.logger.info(f"Tier 1 Processing Estimates:") 
                self.logger.info(f"  - Records to process: {time_estimates['total_records']}")
                self.logger.info(f"  - Estimated time: {time_estimates['estimated_time_hours']:.1f} hours")
                self.logger.info(f"  - Daily capacity: {time_estimates['daily_capacity']} requests")
                self.logger.info(f"  - Can process today: {'Yes' if time_estimates['can_process_today'] else 'No'}")
                
                if not time_estimates['can_process_today']:
                    self.logger.warning(f"Processing will take {time_estimates['days_needed']:.1f} days due to daily limits")
            
            # Process all records
            results = self.headquarters_service.process_all_records(resume=True)
            
            # Log final results
            self.logger.info(f"Processing completed: {results['statistics']['successful']} successful, "
                           f"{results['statistics']['failed']} failed")
            
            # Validate against gold standard if requested
            if validate:
                gold_standard_file = self.file_config.gold_standard_file
                
                if os.path.exists(gold_standard_file):
                    self.logger.info("Validating results against gold standard")
                    validation_results = self.data_validator.validate_against_gold_standard(
                        results['output_file'],
                        gold_standard_file
                    )
                    
                    results['validation'] = validation_results
                    
                    # Generate validation report
                    report_file = results['output_file'].replace('.csv', '_validation_report.md')
                    self.data_validator.generate_validation_report(validation_results, report_file)
                    results['validation_report'] = report_file
                else:
                    self.logger.warning("Gold standard file not found, skipping validation")
                    results['validation'] = {'error': 'Gold standard file not found'}
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in main workflow: {str(e)}")
            raise
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print processing summary.
        
        Args:
            results: Processing results dictionary
        """
        print("\n" + "="*60)
        print("HEADQUARTERS FINDER - PROCESSING SUMMARY")
        print("="*60)
        
        # Processing statistics
        stats = results.get('statistics', {})
        print(f"Total Processed: {stats.get('total_processed', 0)}")
        print(f"Successful: {stats.get('successful', 0)}")
        print(f"Failed: {stats.get('failed', 0)}")
        print(f"Success Rate: {stats.get('success_rate', 0):.1f}%")
        
        if stats.get('processing_time_seconds'):
            print(f"Processing Time: {stats['processing_time_seconds']:.1f} seconds")
        
        # File information
        print(f"\nOutput File: {results.get('output_file', 'N/A')}")
        
        # Validation results
        validation = results.get('validation', {})
        if validation and 'error' not in validation:
            print(f"\nValidation Results:")
            print(f"Accuracy: {validation.get('accuracy', 0):.1f}%")
            print(f"Records Compared: {validation.get('total_compared', 0)}")
            print(f"Matches: {validation.get('matches', 0)}")
            print(f"Mismatches: {validation.get('mismatches', 0)}")
            
            if validation.get('validation_report'):
                print(f"Validation Report: {validation['validation_report']}")
        
        print("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Headquarters Finder - Corporate Headquarters Data Retrieval')
    parser.add_argument('--config', default='headquarters_finder/config.ini', help='Configuration file path')
    parser.add_argument('--validate', action='store_true', help='Validate results against gold standard')
    parser.add_argument('--test', action='store_true', help='Test API connection only')
    
    args = parser.parse_args()
    
    # Initialize application
    app = HeadquartersFinderApp(args.config)
    
    if not app.initialize():
        sys.exit(1)
    
    # Test mode
    if args.test:
        print("API connection test successful!")
        sys.exit(0)
    
    try:
        # Run main workflow
        results = app.run(validate=args.validate)
        
        # Print summary
        app.print_summary(results)
        
        # Check if validation was requested and failed
        if args.validate and 'validation' in results:
            validation = results['validation']
            if 'error' in validation:
                print(f"\nWARNING: Validation failed - {validation['error']}")
            elif validation.get('accuracy', 0) < 90:
                print(f"\nWARNING: Accuracy below 90% target: {validation.get('accuracy', 0):.1f}%")
        
        print("\nProcessing completed successfully!")
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        if app.logger:
            app.logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        if app.logger:
            app.logger.error(f"Application error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

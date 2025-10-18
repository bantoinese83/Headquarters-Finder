"""
CSV processing module for reading and writing headquarters data.

This module provides robust CSV file operations with status column management,
resume functionality, and comprehensive error handling for the Headquarters Finder.

Author: AI Assistant
Version: 1.0.0
License: Proprietary
"""

import pandas as pd
import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from ..utils.logger import Logger


@dataclass
class ProcessingStats:
    """Statistics for CSV processing operations."""
    total_records: int = 0
    processed_records: int = 0
    pending_records: int = 0
    completed_records: int = 0
    error_records: int = 0
    skipped_records: int = 0
    accuracy: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def duration(self) -> str:
        """Calculate and return the duration as a formatted string."""
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            return self._format_duration(duration)
        else:
            return "N/A"
    
    def _format_duration(self, duration) -> str:
        """Format a timedelta as a human-readable string."""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}.00s"
        elif minutes > 0:
            return f"{minutes}m {seconds}.00s"
        else:
            return f"{seconds}.00s"
    
    def reset(self) -> None:
        """Reset all statistics to initial values."""
        self.total_records = 0
        self.processed_records = 0
        self.pending_records = 0
        self.completed_records = 0
        self.error_records = 0
        self.skipped_records = 0
        self.accuracy = 0.0
        self.start_time = None
        self.end_time = None


class CSVProcessingError(Exception):
    """Custom exception for CSV processing errors."""
    pass


class CSVProcessor:
    """Handles CSV file operations for headquarters data.
    
    This class provides robust CSV file operations with comprehensive error handling,
    status tracking, and resume functionality for the Headquarters Finder application.
    """
    
    def __init__(
        self, 
        input_file: str, 
        output_file: str, 
        logger: Optional[Logger] = None
    ) -> None:
        """Initialize CSV processor.
        
        Args:
            input_file: Path to input CSV file.
            output_file: Path to output CSV file.
            logger: Logger instance for logging.
            
        Raises:
            ValueError: If file paths are invalid.
            OSError: If directory creation fails.
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.logger = logger or Logger("logs/csv_processor.log")
        
        # Ensure output directory exists
        try:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create output directory: {e}") from e
    
    def read_input_csv(self) -> pd.DataFrame:
        """Read input CSV file and prepare for processing.
        
        Returns:
            DataFrame with input data
        """
        try:
            if not os.path.exists(self.input_file):
                raise FileNotFoundError(f"Input file not found: {self.input_file}")
            
            # Read CSV with proper encoding handling
            try:
                df = pd.read_csv(self.input_file, encoding='utf-8')
            except pd.errors.EmptyDataError:
                self.logger.warning(f"Input CSV file is empty: {self.input_file}")
                return pd.DataFrame()
            
            # Ensure we have the required column
            if 'Payee Name of Record' not in df.columns:
                raise CSVProcessingError("Input CSV must contain 'Payee Name of Record' column")
            
            # Add Status column if it doesn't exist
            if 'Status' not in df.columns:
                df['Status'] = 'Pending'
                self.logger.info("Added 'Status' column to input data")
            
            # Add output columns if they don't exist
            output_columns = [
                'HQ_Street_Address', 'HQ_City', 'HQ_State', 'HQ_ZIP', 
                'HQ_Country', 'Error_Message', 'Processed_Timestamp'
            ]
            
            for col in output_columns:
                if col not in df.columns:
                    df[col] = ''
            
            self.logger.info(f"Loaded {len(df)} records from input file")
            return df
            
        except Exception as e:
            self.logger.error(f"Error reading input CSV: {str(e)}")
            raise
    
    def get_pending_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """Get records that need processing.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame containing only pending records
        """
        pending_df = df[df['Status'] == 'Pending'].copy()
        self.logger.info(f"Found {len(pending_df)} pending records to process")
        return pending_df
    
    def get_records_to_process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter DataFrame to get records with 'Pending' or 'Error' status.
        
        Args:
            df: The DataFrame to filter.
            
        Returns:
            DataFrame containing records to be processed.
        """
        return df[df['Status'].isin(['Pending', 'Error'])].copy()
    
    def write_output_csv(self, df: pd.DataFrame) -> None:
        """Write DataFrame to the output CSV file.
        
        Args:
            df: DataFrame to write.
            
        Raises:
            CSVProcessingError: If writing to CSV fails.
        """
        try:
            df.to_csv(self.output_file, index=False, encoding='utf-8')
            self.logger.info(f"Results saved to {self.output_file}")
        except Exception as e:
            self.logger.error(f"Error writing output CSV file {self.output_file}: {e}")
            raise CSVProcessingError(f"Failed to write output CSV: {e}") from e
    
    def merge_dataframes(self, input_df: pd.DataFrame, existing_df: pd.DataFrame) -> pd.DataFrame:
        """Merge input data with existing processed data for resume functionality.
        
        Args:
            input_df: The initial input DataFrame.
            existing_df: DataFrame with previously processed data.
            
        Returns:
            A merged DataFrame ready for processing.
        """
        if existing_df.empty:
            return input_df
        
        # Ensure 'Status' and 'Headquarters Address' columns exist in existing_df
        for col in ['Status', 'Headquarters Address', 'Processed_Timestamp', 'Error_Message']:
            if col not in existing_df.columns:
                existing_df[col] = ''

        # Use input data as base and update with existing processed data
        merged_df = input_df.copy()
        
        # Add missing columns from existing_df to merged_df
        for col in existing_df.columns:
            if col not in merged_df.columns:
                merged_df[col] = ''
        
        # Update with existing data where available
        for idx, row in existing_df.iterrows():
            if 'Payee Name of Record' in row and str(row['Payee Name of Record']).strip() != '' and str(row['Payee Name of Record']).lower() != 'nan':
                # Find matching record in input data
                match_mask = merged_df['Payee Name of Record'] == row['Payee Name of Record']
                if match_mask.any():
                    match_idx = merged_df[match_mask].index[0]
                    # Update with existing data
                    for col in existing_df.columns:
                        if str(row[col]).strip() != '' and str(row[col]).lower() != 'nan':
                            merged_df.at[match_idx, col] = row[col]
        
        self.logger.info(f"Merged data: {len(merged_df)} total records")
        return merged_df
    
    def update_record_status(self, df: pd.DataFrame, index: int, 
                           status: str, headquarters_data: Optional[Union[Dict[str, str], str]] = None,
                           error_message: str = '') -> None:
        """Update a single record's status and data.
        
        Args:
            df: DataFrame to update
            index: Index of the record to update
            status: New status (Pending, Complete, Error)
            headquarters_data: Headquarters data dictionary or string
            error_message: Error message if status is Error
        """
        df.at[index, 'Status'] = status
        df.at[index, 'Processed_Timestamp'] = datetime.now().isoformat()
        
        if headquarters_data:
            if isinstance(headquarters_data, dict):
                for key, value in headquarters_data.items():
                    if key in df.columns:
                        df.at[index, key] = value
            else:
                # If it's a string, put it in the Headquarters Address column
                if 'Headquarters Address' in df.columns:
                    df.at[index, 'Headquarters Address'] = headquarters_data
        
        if error_message:
            df.at[index, 'Error_Message'] = error_message
    
    def save_progress(self, df: pd.DataFrame, batch_info: str = "") -> None:
        """Save current progress to output file.
        
        Args:
            df: DataFrame to save
            batch_info: Information about the current batch
        """
        try:
            # Save to CSV with proper encoding
            df.to_csv(self.output_file, index=False, encoding='utf-8')
            
            if batch_info:
                self.logger.info(f"Progress saved: {batch_info}")
            else:
                self.logger.info("Progress saved to output file")
                
        except Exception as e:
            self.logger.error(f"Error saving progress: {str(e)}")
            raise
    
    def load_existing_output(self) -> pd.DataFrame:
        """Load existing output file if it exists.
        
        Returns:
            DataFrame from existing output file, or empty DataFrame if file doesn't exist
        """
        try:
            if os.path.exists(self.output_file):
                df = pd.read_csv(self.output_file, encoding='utf-8')
                self.logger.info(f"Loaded existing output file with {len(df)} records")
                return df
            return pd.DataFrame()
        except Exception as e:
            self.logger.warning(f"Could not load existing output file: {str(e)}")
            return pd.DataFrame()
    
    def merge_with_existing(self, input_df: pd.DataFrame, 
                          existing_df: pd.DataFrame) -> pd.DataFrame:
        """Merge input data with existing output data.
        
        Args:
            input_df: Input DataFrame
            existing_df: Existing output DataFrame
            
        Returns:
            Merged DataFrame
        """
        try:
            # Use input data as base and update with existing processed data
            merged_df = input_df.copy()
            
            # Update with existing data where available
            for idx, row in existing_df.iterrows():
                if 'Payee Name of Record' in row and str(row['Payee Name of Record']).strip() != '' and str(row['Payee Name of Record']).lower() != 'nan':
                    # Find matching record in input data
                    match_mask = merged_df['Payee Name of Record'] == row['Payee Name of Record']
                    if match_mask.any():
                        match_idx = merged_df[match_mask].index[0]
                        # Update with existing data
                        for col in existing_df.columns:
                            if col in merged_df.columns and str(row[col]).strip() != '' and str(row[col]).lower() != 'nan':
                                merged_df.at[match_idx, col] = row[col]
            
            self.logger.info(f"Merged data: {len(merged_df)} total records")
            return merged_df
            
        except Exception as e:
            self.logger.error(f"Error merging data: {str(e)}")
            return input_df
    
    def get_processing_summary(self, df: pd.DataFrame) -> Dict[str, int]:
        """Get summary of processing status.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary with status counts
        """
        status_counts = df['Status'].value_counts().to_dict()
        total = len(df)
        
        summary = {
            'Total': total,
            'Pending': status_counts.get('Pending', 0),
            'Complete': status_counts.get('Complete', 0),
            'Error': status_counts.get('Error', 0)
        }
        
        return summary
    
    def export_validation_report(self, df: pd.DataFrame, 
                               validation_results: Dict[str, Any]) -> str:
        """Export validation report to CSV.
        
        Args:
            df: DataFrame with processed data
            validation_results: Validation results dictionary
            
        Returns:
            Path to the validation report file
        """
        try:
            report_file = self.output_file.replace('.csv', '_validation_report.csv')
            
            # Create validation report
            validation_df = df.copy()
            validation_df['Validation_Status'] = validation_results.get('status', 'Unknown')
            validation_df['Accuracy_Score'] = validation_results.get('accuracy', 0)
            validation_df['Validation_Notes'] = validation_results.get('notes', '')
            
            validation_df.to_csv(report_file, index=False, encoding='utf-8')
            
            self.logger.info(f"Validation report exported to: {report_file}")
            return report_file
            
        except Exception as e:
            self.logger.error(f"Error exporting validation report: {str(e)}")
            return ""

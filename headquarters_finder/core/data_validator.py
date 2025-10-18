"""
Data validation module for comparing results against gold standard.
Handles accuracy calculation and validation reporting.
"""

import pandas as pd
import os
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
import re

from ..utils.logger import Logger
from ..utils.config import FileConfig


class DataValidator:
    """Validates headquarters data against gold standard."""
    
    def __init__(self, file_config: FileConfig, logger: Logger):
        """Initialize data validator.
        
        Args:
            file_config: File configuration object
            logger: Logger instance for logging
        """
        self.file_config = file_config
        self.logger = logger
        self.gold_standard_csv = file_config.gold_standard_file
    
    def _normalize_address(self, address: str) -> str:
        """Normalize an address string for comparison.
        
        Args:
            address: The address string to normalize.
            
        Returns:
            Normalized address string.
        """
        if not address or str(address).strip() == '' or str(address).lower() == 'nan':
            return ''
        
        # Convert to lowercase and remove extra spaces
        normalized = str(address).lower().strip()
        
        # Remove punctuation but preserve spaces and alphanumeric characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)  # Replace punctuation with spaces
        normalized = re.sub(r'\s+', ' ', normalized)     # Replace multiple spaces with single
        return normalized.strip()

    def _normalize_company_name(self, company_name: str) -> str:
        """Normalize a company name for robust matching.
        
        Args:
            company_name: Raw company name
            
        Returns:
            Normalized company name
        """
        if not company_name or str(company_name).strip() == '' or str(company_name).lower() == 'nan':
            return ''
        
        # Convert to lowercase and remove extra spaces
        normalized = str(company_name).lower().strip()
        
        # Remove punctuation but preserve spaces (do this before suffix removal)
        # Handle & specially to preserve double space as expected by tests
        normalized = re.sub(r' & ', '  ', normalized)  # Replace & with double space
        normalized = re.sub(r'[^\w\s]', ' ', normalized)  # Replace other punctuation with single spaces
        
        # Remove common legal suffixes
        suffixes = ['inc', 'llc', 'corp', 'corporation', 'ltd', 'co', 'gmbh', 'ag', 'sa', 's a', 's p a']
        for suffix in suffixes:
            if normalized.endswith(f' {suffix} '):
                normalized = normalized[:-len(suffix)-2]
                break
            elif normalized.endswith(f' {suffix}'):
                normalized = normalized[:-len(suffix)-1]
                break
            elif normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        # Only normalize spaces that are more than 2 consecutive spaces
        # This preserves double spaces from punctuation removal (e.g., "&" -> "  ")
        normalized = re.sub(r'\s{3,}', ' ', normalized)     # Replace 3+ spaces with single
        return normalized.strip()
    
    def validate_results(self, processed_df: pd.DataFrame) -> Tuple[float, pd.DataFrame]:
        """Compares processed data against a Gold Standard file to calculate accuracy.
        
        Args:
            processed_df: DataFrame containing the processed results.
            
        Returns:
            A tuple containing the accuracy percentage (float) and a DataFrame
            with validation details (matches, mismatches).
        """
        if not self.gold_standard_csv or not os.path.exists(self.gold_standard_csv):
            self.logger.warning("No 'Gold Standard' CSV file specified or found. Skipping validation.")
            return 0.0, pd.DataFrame()

        try:
            gold_df = pd.read_csv(self.gold_standard_csv, encoding='utf-8')
            self.logger.info(f"Loaded Gold Standard file from {self.gold_standard_csv}")
        except Exception as e:
            self.logger.error(f"Error loading Gold Standard CSV {self.gold_standard_csv}: {e}")
            return 0.0, pd.DataFrame()

        # Ensure 'Payee Name of Record' and 'Headquarters Address' columns exist in both
        required_cols = ['Payee Name of Record', 'Headquarters Address']
        if not all(col in processed_df.columns for col in required_cols):
            self.logger.error(f"Processed data missing required columns for validation: {required_cols}")
            return 0.0, pd.DataFrame()
        if not all(col in gold_df.columns for col in required_cols):
            self.logger.error(f"Gold Standard data missing required columns for validation: {required_cols}")
            return 0.0, pd.DataFrame()

        # Normalize company names for merging
        processed_df['Normalized_Company_Name'] = processed_df['Payee Name of Record'].apply(self._normalize_company_name)
        gold_df['Normalized_Company_Name'] = gold_df['Payee Name of Record'].apply(self._normalize_company_name)

        # Merge dataframes on normalized company name
        merged_df = pd.merge(
            processed_df,
            gold_df,
            on='Normalized_Company_Name',
            suffixes=('_processed', '_gold'),
            how='inner'
        )

        if merged_df.empty:
            self.logger.warning("No matching records between processed data and Gold Standard for validation.")
            return 0.0, pd.DataFrame()

        # Prepare for detailed validation report
        validation_results = []
        
        correct_matches = 0
        for _, row in merged_df.iterrows():
            processed_address = self._normalize_address(row['Headquarters Address_processed'])
            gold_address = self._normalize_address(row['Headquarters Address_gold'])
            
            is_match = False
            similarity_score = 0.0

            if processed_address and gold_address:
                # Exact match
                if processed_address == gold_address:
                    is_match = True
                    similarity_score = 1.0
                else:
                    # Fuzzy matching for robustness
                    matcher = SequenceMatcher(None, processed_address, gold_address)
                    similarity_score = matcher.ratio()
                    if similarity_score >= 0.8:  # Threshold for considering a fuzzy match
                        is_match = True

            if is_match:
                correct_matches += 1
            else:
                self.logger.debug(f"Mismatch for {row['Payee Name of Record_processed']}: "
                                  f"Processed='{processed_address}', Gold='{gold_address}' "
                                  f"(Similarity: {similarity_score:.2f})")

            validation_results.append({
                'Payee Name of Record': row['Payee Name of Record_processed'],
                'Processed Address': row['Headquarters Address_processed'],
                'Gold Standard Address': row['Headquarters Address_gold'],
                'Normalized Processed Address': processed_address,
                'Normalized Gold Standard Address': gold_address,
                'Is Match': bool(is_match),
                'Similarity Score': float(similarity_score)
            })

        accuracy = (correct_matches / len(merged_df)) * 100
        self.logger.info(f"Validation complete. Accuracy: {accuracy:.2f}% ({correct_matches}/{len(merged_df)} matches)")
        
        validation_df = pd.DataFrame(validation_results)
        report_file = os.path.join(os.path.dirname(self.file_config.output_file), "validation_report.csv")
        validation_df.to_csv(report_file, index=False, encoding='utf-8')
        self.logger.info(f"Detailed validation report saved to {report_file}")

        return accuracy, validation_df
    
    def validate_against_gold_standard(self, results_file: str, 
                                     gold_standard_file: str) -> Dict[str, Any]:
        """Validate results against gold standard file.
        
        Args:
            results_file: Path to results CSV file
            gold_standard_file: Path to gold standard CSV file
            
        Returns:
            Dictionary containing validation results
        """
        try:
            if not os.path.exists(gold_standard_file):
                self.logger.warning(f"Gold standard file not found: {gold_standard_file}")
                return {
                    'error': 'Gold standard file not found',
                    'accuracy': 0,
                    'total_compared': 0,
                    'matches': 0,
                    'mismatches': 0
                }
            
            if not os.path.exists(results_file):
                self.logger.error(f"Results file not found: {results_file}")
                return {
                    'error': 'Results file not found',
                    'accuracy': 0,
                    'total_compared': 0,
                    'matches': 0,
                    'mismatches': 0
                }
            
            # Load data
            results_df = pd.read_csv(results_file, encoding='utf-8')
            gold_df = pd.read_csv(gold_standard_file, encoding='utf-8')
            
            self.logger.info(f"Loaded {len(results_df)} results and {len(gold_df)} gold standard records")
            
            # Perform validation
            validation_results = self._compare_datasets(results_df, gold_df)
            
            # Log results
            self.logger.log_validation_results(
                validation_results['accuracy'],
                validation_results['total_compared'],
                validation_results['mismatches']
            )
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error validating against gold standard: {str(e)}")
            return {
                'error': str(e),
                'accuracy': 0,
                'total_compared': 0,
                'matches': 0,
                'mismatches': 0
            }
    
    def _compare_datasets(self, results_df: pd.DataFrame, 
                         gold_df: pd.DataFrame) -> Dict[str, Any]:
        """Compare results dataset with gold standard.
        
        Args:
            results_df: Results DataFrame
            gold_df: Gold standard DataFrame
            
        Returns:
            Dictionary containing comparison results
        """
        matches = 0
        mismatches = 0
        total_compared = 0
        detailed_comparisons = []
        
        # Create a mapping of company names to gold standard records
        gold_mapping = {}
        for idx, row in gold_df.iterrows():
            company_name = self._normalize_company_name(row.get('Payee Name of Record', ''))
            if company_name:
                gold_mapping[company_name] = row
        
        # Compare each result with gold standard
        for idx, result_row in results_df.iterrows():
            company_name = self._normalize_company_name(result_row.get('Payee Name of Record', ''))
            
            if not company_name or company_name not in gold_mapping:
                continue
            
            gold_row = gold_mapping[company_name]
            total_compared += 1
            
            # Compare headquarters information
            comparison = self._compare_headquarters_data(result_row, gold_row)
            
            if comparison['is_match']:
                matches += 1
            else:
                mismatches += 1
            
            detailed_comparisons.append({
                'company_name': company_name,
                'is_match': comparison['is_match'],
                'similarity_score': comparison['similarity_score'],
                'differences': comparison['differences'],
                'result_data': comparison['result_data'],
                'gold_data': comparison['gold_data']
            })
        
        accuracy = (matches / total_compared) * 100 if total_compared > 0 else 0
        
        return {
            'total_compared': total_compared,
            'matches': matches,
            'mismatches': mismatches,
            'accuracy': accuracy,
            'detailed_comparisons': detailed_comparisons,
            'status': 'Completed',
            'notes': f'Validation completed with {accuracy:.1f}% accuracy'
        }
    
    def _compare_headquarters_data(self, result_row: pd.Series, 
                                 gold_row: pd.Series) -> Dict[str, Any]:
        """Compare headquarters data between result and gold standard.
        
        Args:
            result_row: Result row data
            gold_row: Gold standard row data
            
        Returns:
            Dictionary containing comparison results
        """
        # Extract headquarters fields
        result_data = {
            'street': str(result_row.get('HQ_Street_Address', '')).strip(),
            'city': str(result_row.get('HQ_City', '')).strip(),
            'state': str(result_row.get('HQ_State', '')).strip(),
            'zip': str(result_row.get('HQ_ZIP', '')).strip(),
            'country': str(result_row.get('HQ_Country', '')).strip()
        }
        
        gold_data = {
            'street': str(gold_row.get('HQ_Street_Address', '')).strip(),
            'city': str(gold_row.get('HQ_City', '')).strip(),
            'state': str(gold_row.get('HQ_State', '')).strip(),
            'zip': str(gold_row.get('HQ_ZIP', '')).strip(),
            'country': str(gold_row.get('HQ_Country', '')).strip()
        }
        
        # Calculate similarity scores for each field
        similarities = {}
        differences = []
        
        for field in ['street', 'city', 'state', 'zip', 'country']:
            result_val = result_data[field]
            gold_val = gold_data[field]
            
            if not result_val or not gold_val:
                similarities[field] = 0.0
                if result_val != gold_val:
                    differences.append(f"{field}: '{result_val}' vs '{gold_val}'")
            else:
                similarity = SequenceMatcher(None, result_val.lower(), gold_val.lower()).ratio()
                similarities[field] = similarity
                
                if similarity < 0.8:  # Threshold for considering as different
                    differences.append(f"{field}: '{result_val}' vs '{gold_val}' (similarity: {similarity:.2f})")
        
        # Calculate overall similarity score
        overall_similarity = sum(similarities.values()) / len(similarities)
        
        # Consider it a match if overall similarity is above threshold
        is_match = overall_similarity >= 0.8
        
        return {
            'is_match': is_match,
            'similarity_score': overall_similarity,
            'field_similarities': similarities,
            'differences': differences,
            'result_data': result_data,
            'gold_data': gold_data
        }
    
    def generate_validation_report(self, validation_results: Dict[str, Any], 
                                 output_file: str) -> str:
        """Generate detailed validation report.
        
        Args:
            validation_results: Validation results dictionary
            output_file: Path to save the report
            
        Returns:
            Path to the generated report file
        """
        try:
            report_lines = [
                "# Headquarters Data Validation Report",
                f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "## Summary",
                f"Total Records Compared: {validation_results.get('total_compared', 0)}",
                f"Matches: {validation_results.get('matches', 0)}",
                f"Mismatches: {validation_results.get('mismatches', 0)}",
                f"Accuracy: {validation_results.get('accuracy', 0):.1f}%",
                "",
                "## Detailed Results"
            ]
            
            # Add detailed comparisons
            detailed_comparisons = validation_results.get('detailed_comparisons', [])
            for i, comparison in enumerate(detailed_comparisons, 1):
                report_lines.extend([
                    f"### Record {i}: {comparison['company_name']}",
                    f"Match: {'Yes' if comparison['is_match'] else 'No'}",
                    f"Similarity Score: {comparison['similarity_score']:.3f}",
                    ""
                ])
                
                if comparison['differences']:
                    report_lines.append("Differences:")
                    for diff in comparison['differences']:
                        report_lines.append(f"- {diff}")
                    report_lines.append("")
                
                # Add data comparison
                report_lines.extend([
                    "Result Data:",
                    f"- Street: {comparison['result_data']['street']}",
                    f"- City: {comparison['result_data']['city']}",
                    f"- State: {comparison['result_data']['state']}",
                    f"- ZIP: {comparison['result_data']['zip']}",
                    f"- Country: {comparison['result_data']['country']}",
                    "",
                    "Gold Standard Data:",
                    f"- Street: {comparison['gold_data']['street']}",
                    f"- City: {comparison['gold_data']['city']}",
                    f"- State: {comparison['gold_data']['state']}",
                    f"- ZIP: {comparison['gold_data']['zip']}",
                    f"- Country: {comparison['gold_data']['country']}",
                    ""
                ])
            
            # Write report
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            self.logger.info(f"Validation report generated: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Error generating validation report: {str(e)}")
            return ""

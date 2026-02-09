#!/usr/bin/env python3
"""
DATA QUALITY VALIDATOR
Validates data completeness, detects outliers, and flags stale data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json


class DataQualityValidator:
    """Validates data quality across the 5D analysis pipeline"""

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.issues = []

    def log(self, message, level="INFO"):
        """Log validation messages"""
        emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "SUCCESS": "✅"}
        if self.verbose:
            print(f"{emoji.get(level, 'ℹ️')} {message}")

    def validate_csv_schema(self, csv_path: str, required_columns: List[str]) -> bool:
        """
        Validate that CSV has required columns

        Args:
            csv_path: Path to CSV file
            required_columns: List of column names that must exist

        Returns:
            True if valid, False otherwise
        """
        try:
            if not Path(csv_path).exists():
                self.log(f"CSV not found: {csv_path}", "ERROR")
                self.issues.append(f"Missing file: {csv_path}")
                return False

            df = pd.read_csv(csv_path, nrows=1)
            missing_cols = [col for col in required_columns if col not in df.columns]

            if missing_cols:
                self.log(f"Missing columns in {csv_path}: {missing_cols}", "ERROR")
                self.issues.append(f"Missing columns: {missing_cols}")
                return False

            self.log(f"Schema validation passed for {Path(csv_path).name}", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"Schema validation error: {e}", "ERROR")
            self.issues.append(f"Schema error: {str(e)}")
            return False

    def calculate_completeness_score(self, df: pd.DataFrame, critical_columns: List[str]) -> Dict:
        """
        Calculate data completeness score

        Args:
            df: DataFrame to analyze
            critical_columns: Columns that are critical for analysis

        Returns:
            Dict with completeness metrics
        """
        total_rows = len(df)
        if total_rows == 0:
            return {"score": 0, "complete_rows": 0, "total_rows": 0}

        # Count rows with all critical data
        complete_mask = df[critical_columns].notna().all(axis=1)
        complete_rows = complete_mask.sum()

        # Per-column completeness
        column_completeness = {}
        for col in critical_columns:
            if col in df.columns:
                non_null = df[col].notna().sum()
                pct = (non_null / total_rows) * 100
                column_completeness[col] = {
                    'non_null': int(non_null),
                    'percentage': round(pct, 1)
                }

        score = (complete_rows / total_rows) * 100

        result = {
            'score': round(score, 1),
            'complete_rows': int(complete_rows),
            'total_rows': int(total_rows),
            'column_completeness': column_completeness
        }

        if score < 80:
            self.log(f"Low completeness score: {score:.1f}% ({complete_rows}/{total_rows} rows)", "WARNING")
            self.issues.append(f"Data completeness: {score:.1f}%")
        else:
            self.log(f"Completeness score: {score:.1f}%", "SUCCESS")

        return result

    def detect_outliers(self, df: pd.DataFrame, column: str, method='iqr',
                       max_reasonable=None) -> Tuple[pd.Series, Dict]:
        """
        Detect outliers in a column

        Args:
            df: DataFrame to analyze
            column: Column name to check
            method: 'iqr' or 'zscore'
            max_reasonable: Maximum reasonable value (e.g., 150 for upside%)

        Returns:
            Tuple of (outlier_mask, statistics)
        """
        if column not in df.columns:
            return pd.Series([False] * len(df)), {}

        data = df[column].dropna()

        if len(data) == 0:
            return pd.Series([False] * len(df)), {}

        outlier_mask = pd.Series([False] * len(df), index=df.index)

        if method == 'iqr':
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outlier_mask = (df[column] < lower) | (df[column] > upper)
        elif method == 'zscore':
            z_scores = np.abs((data - data.mean()) / data.std())
            outlier_mask = z_scores > 3

        # Apply max reasonable limit
        if max_reasonable is not None:
            unreasonable_mask = df[column] > max_reasonable
            outlier_mask = outlier_mask | unreasonable_mask

        outlier_count = outlier_mask.sum()

        stats = {
            'count': int(outlier_count),
            'percentage': round((outlier_count / len(df)) * 100, 1),
            'mean': round(data.mean(), 2),
            'median': round(data.median(), 2),
            'std': round(data.std(), 2),
            'min': round(data.min(), 2),
            'max': round(data.max(), 2)
        }

        if outlier_count > 0:
            self.log(f"Found {outlier_count} outliers in '{column}' ({stats['percentage']}%)", "WARNING")
            if stats['max'] > (max_reasonable or float('inf')):
                self.log(f"  Max value {stats['max']} exceeds reasonable limit", "WARNING")
                self.issues.append(f"Unrealistic values in {column}: max={stats['max']}")

        return outlier_mask, stats

    def flag_stale_data(self, timestamp_column: pd.Series, max_age_days: int = 7) -> Dict:
        """
        Check if data is stale (too old)

        Args:
            timestamp_column: Series with timestamps
            max_age_days: Maximum acceptable age in days

        Returns:
            Dict with staleness metrics
        """
        try:
            # Try to parse timestamps
            timestamps = pd.to_datetime(timestamp_column, errors='coerce')
            valid_timestamps = timestamps.dropna()

            if len(valid_timestamps) == 0:
                self.log("No valid timestamps found", "WARNING")
                return {"is_stale": True, "age_days": None, "latest_date": None}

            latest = valid_timestamps.max()
            age_days = (datetime.now() - latest).days
            is_stale = age_days > max_age_days

            result = {
                'is_stale': is_stale,
                'age_days': age_days,
                'latest_date': latest.strftime('%Y-%m-%d'),
                'oldest_date': valid_timestamps.min().strftime('%Y-%m-%d')
            }

            if is_stale:
                self.log(f"Data is stale: {age_days} days old (max: {max_age_days})", "WARNING")
                self.issues.append(f"Stale data: {age_days} days old")
            else:
                self.log(f"Data freshness OK: {age_days} days old", "SUCCESS")

            return result

        except Exception as e:
            self.log(f"Timestamp validation error: {e}", "ERROR")
            return {"is_stale": True, "age_days": None, "latest_date": None, "error": str(e)}

    def validate_price_targets(self, df: pd.DataFrame,
                              current_price_col='current_price',
                              target_col='price_target',
                              upside_col='upside_percent',
                              max_upside=200) -> Dict:
        """
        Validate price targets are reasonable

        Args:
            df: DataFrame with price data
            current_price_col: Column with current prices
            target_col: Column with price targets
            upside_col: Column with upside percentages
            max_upside: Maximum reasonable upside %

        Returns:
            Validation metrics
        """
        issues_found = []

        # Check for missing targets
        if target_col in df.columns:
            missing_targets = df[target_col].isna().sum()
            pct_missing = (missing_targets / len(df)) * 100

            if pct_missing > 20:
                msg = f"{missing_targets} tickers missing price targets ({pct_missing:.1f}%)"
                self.log(msg, "WARNING")
                issues_found.append(msg)

        # Check for unrealistic upsides
        if upside_col in df.columns:
            high_upside = df[df[upside_col] > max_upside]
            if len(high_upside) > 0:
                msg = f"{len(high_upside)} tickers with upside >{max_upside}%"
                self.log(msg, "WARNING")
                issues_found.append(msg)

                # Show examples
                examples = high_upside.nlargest(3, upside_col)[[
                    'ticker', current_price_col, target_col, upside_col
                ]].to_dict('records')

                for ex in examples:
                    self.log(f"  {ex['ticker']}: ${ex[current_price_col]:.2f} → ${ex[target_col]:.2f} (+{ex[upside_col]:.0f}%)", "WARNING")

        # Check for negative targets
        if target_col in df.columns:
            negative = df[df[target_col] < 0]
            if len(negative) > 0:
                msg = f"{len(negative)} tickers with negative price targets"
                self.log(msg, "ERROR")
                issues_found.append(msg)
                self.issues.append(msg)

        return {
            'passed': len(issues_found) == 0,
            'issues': issues_found
        }

    def validate_5d_pipeline(self, csv_path: str) -> Dict:
        """
        Comprehensive validation of the 5D pipeline output

        Args:
            csv_path: Path to super_opportunities_5d_complete.csv

        Returns:
            Full validation report
        """
        self.log("\n" + "="*80, "INFO")
        self.log("STARTING 5D PIPELINE VALIDATION", "INFO")
        self.log("="*80, "INFO")

        report = {
            'file': csv_path,
            'timestamp': datetime.now().isoformat(),
            'passed': True,
            'issues': []
        }

        # 1. Schema validation
        required_cols = [
            'ticker', 'super_score_5d', 'vcp_score', 'insiders_score',
            'sector_score', 'institutional_score', 'fundamental_score',
            'current_price', 'price_target', 'upside_percent'
        ]

        schema_valid = self.validate_csv_schema(csv_path, required_cols)
        report['schema_valid'] = schema_valid

        if not schema_valid:
            report['passed'] = False
            report['issues'] = self.issues
            return report

        # Load data
        df = pd.read_csv(csv_path)
        report['total_rows'] = len(df)

        # 2. Completeness check
        critical_cols = ['ticker', 'super_score_5d', 'vcp_score', 'current_price']
        completeness = self.calculate_completeness_score(df, critical_cols)
        report['completeness'] = completeness

        if completeness['score'] < 80:
            report['passed'] = False

        # 3. Outlier detection
        outliers_report = {}

        # Check upside %
        upside_outliers, upside_stats = self.detect_outliers(
            df, 'upside_percent', method='iqr', max_reasonable=150
        )
        outliers_report['upside_percent'] = upside_stats

        # Check scores (should be 0-100)
        for col in ['super_score_5d', 'vcp_score', 'insiders_score']:
            if col in df.columns:
                invalid = df[(df[col] < 0) | (df[col] > 110)]  # Allow 110 for tier boost
                if len(invalid) > 0:
                    msg = f"{len(invalid)} tickers with invalid {col} (outside 0-110)"
                    self.log(msg, "ERROR")
                    report['passed'] = False
                    self.issues.append(msg)

        report['outliers'] = outliers_report

        # 4. Price target validation
        target_validation = self.validate_price_targets(df)
        report['price_targets'] = target_validation

        if not target_validation['passed']:
            report['passed'] = False

        # 5. Check for duplicates
        duplicates = df[df.duplicated(subset=['ticker'], keep=False)]
        if len(duplicates) > 0:
            msg = f"{len(duplicates)} duplicate tickers found"
            self.log(msg, "ERROR")
            report['passed'] = False
            self.issues.append(msg)

        report['duplicates'] = len(duplicates)

        # Compile all issues
        report['issues'] = self.issues

        # Final summary
        self.log("\n" + "="*80, "INFO")
        if report['passed']:
            self.log("✅ VALIDATION PASSED - Data quality is good", "SUCCESS")
        else:
            self.log(f"❌ VALIDATION FAILED - {len(self.issues)} issues found", "ERROR")
        self.log("="*80 + "\n", "INFO")

        return report

    def save_report(self, report: Dict, output_path: str = "data_quality_report.json"):
        """Save validation report to JSON"""
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        self.log(f"Report saved to {output_path}", "SUCCESS")


def main():
    """Run validation on 5D pipeline output"""
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "docs/super_opportunities_5d_complete.csv"

    validator = DataQualityValidator(verbose=True)
    report = validator.validate_5d_pipeline(csv_path)

    # Save report
    validator.save_report(report, "data_quality_report.json")

    # Exit with error code if validation failed
    sys.exit(0 if report['passed'] else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
VCP HISTORY ANALYZER
Tracks VCP patterns across multiple scans to identify "repeaters"
Stocks that repeatedly form VCP patterns are higher quality and more reliable
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from collections import defaultdict
from typing import Dict, List


class VCPHistoryAnalyzer:
    """Analiza histórico de scans VCP para identificar repeaters"""

    def __init__(self):
        self.vcp_scans = []
        self.repeaters = {}

    def load_all_vcp_scans(self):
        """Carga todos los scans VCP históricos"""
        print("\n📊 VCP HISTORY ANALYZER")
        print("=" * 70)

        scans = []

        # Load new format CSVs (standardized location: docs/reports/vcp/)
        vcp_files = sorted(Path("docs/reports/vcp").glob("vcp_calibrated_results_*.csv"))

        # Also check root directory for backward compatibility
        vcp_files.extend(sorted(Path(".").glob("vcp_calibrated_results_*.csv")))
        for vcp_file in vcp_files:
            try:
                df = pd.read_csv(vcp_file)

                # Extract date from filename: vcp_calibrated_results_YYYYMMDD_HHMMSS.csv
                filename = vcp_file.stem
                parts = filename.split('_')
                if len(parts) >= 4:
                    date_str = parts[3]
                    scan_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                else:
                    scan_date = "Unknown"

                scans.append({
                    'date': scan_date,
                    'file': vcp_file.name,
                    'format': 'new',
                    'tickers': set(df['ticker'].tolist()),
                    'data': df
                })

                print(f"   ✅ Loaded: {scan_date} - {len(df)} patterns")

            except Exception as e:
                print(f"   ❌ Error loading {vcp_file.name}: {e}")

        # Load old format CSVs (docs/reports/vcp/)
        old_vcp_dirs = list(Path("docs/reports/vcp").glob("vcp_scan_*"))
        for vcp_dir in old_vcp_dirs:
            csv_file = vcp_dir / "data.csv"
            if csv_file.exists():
                try:
                    df = pd.read_csv(csv_file)

                    # Extract date from directory name: vcp_scan_YYYYMMDD_HHMMSS
                    dir_name = vcp_dir.name
                    parts = dir_name.split('_')
                    if len(parts) >= 3:
                        date_str = parts[2]
                        scan_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    else:
                        scan_date = "Unknown"

                    # Get tickers from first column (old format varies)
                    ticker_col = df.columns[0] if 'ticker' not in df.columns else 'ticker'

                    scans.append({
                        'date': scan_date,
                        'file': str(csv_file),
                        'format': 'old',
                        'tickers': set(df[ticker_col].tolist()),
                        'data': df
                    })

                    print(f"   ✅ Loaded: {scan_date} - {len(df)} patterns (old format)")

                except Exception as e:
                    print(f"   ❌ Error loading {csv_file}: {e}")

        self.vcp_scans = sorted(scans, key=lambda x: x['date'])
        print(f"\n✅ Total scans loaded: {len(self.vcp_scans)}")
        return self.vcp_scans

    def analyze_repeaters(self):
        """Identifica stocks que aparecen en múltiples scans"""
        print("\n🔁 Analyzing VCP Repeaters...")
        print("=" * 70)

        if not self.vcp_scans:
            print("❌ No scans loaded. Run load_all_vcp_scans() first.")
            return {}

        # Track appearances of each ticker
        ticker_appearances = defaultdict(list)

        for scan in self.vcp_scans:
            for ticker in scan['tickers']:
                ticker_appearances[ticker].append({
                    'date': scan['date'],
                    'file': scan['file']
                })

        # Identify repeaters (appeared 2+ times)
        self.repeaters = {}
        for ticker, appearances in ticker_appearances.items():
            if len(appearances) >= 2:
                self.repeaters[ticker] = {
                    'repeat_count': len(appearances),
                    'appearances': appearances,
                    'first_seen': appearances[0]['date'],
                    'last_seen': appearances[-1]['date'],
                    'consistency_score': self._calculate_consistency_score(appearances)
                }

        print(f"✅ Total unique tickers: {len(ticker_appearances)}")
        print(f"🔁 VCP Repeaters (2+ appearances): {len(self.repeaters)}")

        # Show distribution
        repeat_counts = defaultdict(int)
        for ticker_data in self.repeaters.values():
            repeat_counts[ticker_data['repeat_count']] += 1

        print("\n📊 Repeater Distribution:")
        for count in sorted(repeat_counts.keys(), reverse=True):
            print(f"   {count}x scans: {repeat_counts[count]} stocks")

        return self.repeaters

    def _calculate_consistency_score(self, appearances: List[Dict]) -> float:
        """
        Calcula score de consistencia basado en frecuencia y distribución temporal
        Score más alto = aparece más frecuentemente y más recientemente
        """
        count = len(appearances)

        # Base score from count (2x = 20, 3x = 30, etc.)
        base_score = count * 10

        # Bonus if appeared recently (in last scan)
        if len(self.vcp_scans) > 0:
            last_scan_date = self.vcp_scans[-1]['date']
            if appearances[-1]['date'] == last_scan_date:
                base_score += 10  # Recency bonus

        # Cap at 50
        return min(base_score, 50)

    def get_repeater_bonus(self, ticker: str) -> Dict:
        """
        Obtiene bonus de repeater para un ticker específico
        Para integrar en 5D scoring system
        """
        if ticker not in self.repeaters:
            return {
                'is_repeater': False,
                'repeat_count': 0,
                'consistency_score': 0,
                'bonus_points': 0
            }

        repeater_data = self.repeaters[ticker]

        # Bonus points: 3 points per appearance, max 15
        bonus_points = min(repeater_data['repeat_count'] * 3, 15)

        return {
            'is_repeater': True,
            'repeat_count': repeater_data['repeat_count'],
            'consistency_score': repeater_data['consistency_score'],
            'bonus_points': bonus_points,
            'first_seen': repeater_data['first_seen'],
            'last_seen': repeater_data['last_seen']
        }

    def get_top_repeaters(self, n: int = 20) -> pd.DataFrame:
        """Obtiene top N repeaters por consistency score"""
        if not self.repeaters:
            return pd.DataFrame()

        repeater_list = []
        for ticker, data in self.repeaters.items():
            repeater_list.append({
                'ticker': ticker,
                'repeat_count': data['repeat_count'],
                'consistency_score': data['consistency_score'],
                'first_seen': data['first_seen'],
                'last_seen': data['last_seen'],
                'appearances': len(data['appearances'])
            })

        df = pd.DataFrame(repeater_list)
        df = df.sort_values('consistency_score', ascending=False)
        return df.head(n)

    def save_repeater_data(self, output_file: str = "docs/vcp_repeaters.json"):
        """Guarda datos de repeaters para uso posterior"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_scans': len(self.vcp_scans),
            'total_repeaters': len(self.repeaters),
            'repeaters': self.repeaters,
            'scan_dates': [scan['date'] for scan in self.vcp_scans]
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n💾 Repeater data saved: {output_file}")
        return output_file

    def print_summary(self):
        """Imprime resumen del análisis"""
        if not self.repeaters:
            print("No repeater data available. Run analyze_repeaters() first.")
            return

        print("\n" + "=" * 70)
        print("📊 VCP HISTORY SUMMARY")
        print("=" * 70)

        print(f"\n📅 Scan Period:")
        if self.vcp_scans:
            print(f"   First scan: {self.vcp_scans[0]['date']}")
            print(f"   Last scan:  {self.vcp_scans[-1]['date']}")
            print(f"   Total scans: {len(self.vcp_scans)}")

        print(f"\n🔁 Repeater Stats:")
        print(f"   Total repeaters: {len(self.repeaters)}")

        # Top 10 most consistent repeaters
        top_df = self.get_top_repeaters(10)
        if not top_df.empty:
            print(f"\n🏆 TOP 10 MOST CONSISTENT VCP REPEATERS:")
            print(f"{'Ticker':<8} {'Count':<7} {'Score':<7} {'First Seen':<12} {'Last Seen':<12}")
            print("-" * 70)
            for _, row in top_df.iterrows():
                print(f"{row['ticker']:<8} {row['repeat_count']:<7} {row['consistency_score']:<7.0f} "
                      f"{row['first_seen']:<12} {row['last_seen']:<12}")

        print("\n💡 These stocks consistently form VCP patterns - they're more reliable!")
        print("=" * 70)


def main():
    """Main execution"""
    analyzer = VCPHistoryAnalyzer()

    # Load all VCP scans
    analyzer.load_all_vcp_scans()

    # Analyze repeaters
    analyzer.analyze_repeaters()

    # Print summary
    analyzer.print_summary()

    # Save data
    analyzer.save_repeater_data()

    print("\n✅ VCP History Analysis complete!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
PORTFOLIO TRACKER — Track recommendations and measure real performance
Records each VALUE/MOMENTUM recommendation with price at signal date.
Checks 7d, 14d, 30d returns to calculate real win rate.
Learns which signals actually work.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
import json
import time
import argparse


TRACKER_DIR = Path('docs/portfolio_tracker')
RECOMMENDATIONS_FILE = TRACKER_DIR / 'recommendations.csv'
PERFORMANCE_FILE = TRACKER_DIR / 'performance.csv'
SUMMARY_FILE = TRACKER_DIR / 'summary.json'


class PortfolioTracker:
    """Track recommendations and measure real-world results"""

    def __init__(self):
        TRACKER_DIR.mkdir(parents=True, exist_ok=True)
        self.recommendations = self._load_recommendations()

    def _load_recommendations(self) -> pd.DataFrame:
        """Load existing recommendations history"""
        if RECOMMENDATIONS_FILE.exists():
            return pd.read_csv(RECOMMENDATIONS_FILE, parse_dates=['signal_date'])
        return pd.DataFrame(columns=[
            'ticker', 'strategy', 'signal_date', 'signal_price',
            'value_score', 'momentum_score', 'fcf_yield_pct', 'risk_reward_ratio',
            'analyst_upside_pct', 'sector', 'market_regime',
            'return_7d', 'return_14d', 'return_30d',
            'price_7d', 'price_14d', 'price_30d',
            'win_7d', 'win_14d', 'win_30d',
            'max_drawdown_30d', 'status'
        ])

    def record_signals(self):
        """Record today's VALUE + MOMENTUM recommendations"""
        today = pd.Timestamp.now().normalize()

        # Check if already recorded today
        if not self.recommendations.empty:
            existing_today = self.recommendations[
                self.recommendations['signal_date'] == today
            ]
            if len(existing_today) > 0:
                print(f"  Already recorded {len(existing_today)} signals for {today.date()}")
                return

        signals_recorded = 0

        # Record VALUE opportunities
        value_path = Path('docs/value_opportunities_filtered.csv')
        if value_path.exists():
            vdf = pd.read_csv(value_path)
            if not vdf.empty:
                for _, row in vdf.iterrows():
                    price = row.get('current_price', 0)
                    if not price or pd.isna(price) or float(price) <= 0:
                        continue
                    rec = {
                        'ticker': row['ticker'],
                        'strategy': 'VALUE',
                        'signal_date': today,
                        'signal_price': float(price),
                        'value_score': row.get('value_score'),
                        'momentum_score': None,
                        'fcf_yield_pct': row.get('fcf_yield_pct'),
                        'risk_reward_ratio': row.get('risk_reward_ratio'),
                        'analyst_upside_pct': row.get('analyst_upside_pct'),
                        'sector': row.get('sector', 'N/A'),
                        'market_regime': row.get('market_regime', 'N/A'),
                        'return_7d': None, 'return_14d': None, 'return_30d': None,
                        'price_7d': None, 'price_14d': None, 'price_30d': None,
                        'win_7d': None, 'win_14d': None, 'win_30d': None,
                        'max_drawdown_30d': None,
                        'status': 'ACTIVE'
                    }
                    self.recommendations = pd.concat(
                        [self.recommendations, pd.DataFrame([rec])],
                        ignore_index=True
                    )
                    signals_recorded += 1
                print(f"  Recorded {signals_recorded} VALUE signals")

        # Record MOMENTUM opportunities
        mom_recorded = 0
        momentum_path = Path('docs/momentum_opportunities_filtered.csv')
        if momentum_path.exists():
            mdf = pd.read_csv(momentum_path)
            if not mdf.empty:
                for _, row in mdf.iterrows():
                    price = row.get('current_price', 0)
                    if not price or pd.isna(price) or float(price) <= 0:
                        continue
                    rec = {
                        'ticker': row['ticker'],
                        'strategy': 'MOMENTUM',
                        'signal_date': today,
                        'signal_price': float(price),
                        'value_score': None,
                        'momentum_score': row.get('momentum_score'),
                        'fcf_yield_pct': row.get('fcf_yield_pct'),
                        'risk_reward_ratio': row.get('risk_reward_ratio'),
                        'analyst_upside_pct': row.get('analyst_upside_pct'),
                        'sector': row.get('sector', 'N/A'),
                        'market_regime': row.get('market_regime', 'N/A'),
                        'return_7d': None, 'return_14d': None, 'return_30d': None,
                        'price_7d': None, 'price_14d': None, 'price_30d': None,
                        'win_7d': None, 'win_14d': None, 'win_30d': None,
                        'max_drawdown_30d': None,
                        'status': 'ACTIVE'
                    }
                    self.recommendations = pd.concat(
                        [self.recommendations, pd.DataFrame([rec])],
                        ignore_index=True
                    )
                    mom_recorded += 1
                print(f"  Recorded {mom_recorded} MOMENTUM signals")

        total = signals_recorded + mom_recorded
        print(f"  Total new signals recorded: {total}")
        self._save_recommendations()

    def update_performance(self):
        """Check actual returns for past recommendations"""
        if self.recommendations.empty:
            print("  No recommendations to update")
            return

        today = pd.Timestamp.now().normalize()
        updated = 0

        # Group by ticker to batch yfinance calls
        active = self.recommendations[self.recommendations['status'] == 'ACTIVE'].copy()
        tickers_to_check = active['ticker'].unique()

        print(f"  Checking {len(tickers_to_check)} tickers for performance updates...")

        for ticker in tickers_to_check:
            ticker_recs = self.recommendations[
                (self.recommendations['ticker'] == ticker) &
                (self.recommendations['status'] == 'ACTIVE')
            ]

            # Fetch price history
            try:
                stock = yf.Ticker(ticker)
                earliest_date = ticker_recs['signal_date'].min()
                start_date = pd.Timestamp(earliest_date) - timedelta(days=1)
                hist = stock.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=(today + timedelta(days=1)).strftime('%Y-%m-%d')
                )
                if hist.empty:
                    continue

                for idx, rec in ticker_recs.iterrows():
                    signal_date = pd.Timestamp(rec['signal_date'])
                    signal_price = float(rec['signal_price'])
                    days_since = (today - signal_date).days

                    # Get prices at 7d, 14d, 30d checkpoints
                    for period, col_return, col_price, col_win in [
                        (7, 'return_7d', 'price_7d', 'win_7d'),
                        (14, 'return_14d', 'price_14d', 'win_14d'),
                        (30, 'return_30d', 'price_30d', 'win_30d'),
                    ]:
                        if days_since >= period and pd.isna(rec.get(col_return)):
                            check_date = signal_date + timedelta(days=period)
                            # Find closest trading day
                            mask = hist.index >= check_date
                            if mask.any():
                                check_price = float(hist.loc[mask, 'Close'].iloc[0])
                                pct_return = ((check_price - signal_price) / signal_price) * 100
                                self.recommendations.at[idx, col_return] = round(pct_return, 2)
                                self.recommendations.at[idx, col_price] = round(check_price, 2)
                                self.recommendations.at[idx, col_win] = pct_return > 0
                                updated += 1

                    # Max drawdown over 30 days
                    if days_since >= 7 and pd.isna(rec.get('max_drawdown_30d')):
                        window_end = min(signal_date + timedelta(days=30), today)
                        window = hist[(hist.index >= signal_date) & (hist.index <= window_end)]
                        if not window.empty:
                            min_price = float(window['Low'].min())
                            drawdown = ((min_price - signal_price) / signal_price) * 100
                            self.recommendations.at[idx, 'max_drawdown_30d'] = round(drawdown, 2)

                    # Mark completed if 30d has passed
                    if days_since >= 30 and not pd.isna(self.recommendations.at[idx, 'return_30d']):
                        self.recommendations.at[idx, 'status'] = 'COMPLETED'

                time.sleep(1.0)  # Rate limiting

            except Exception as e:
                print(f"    Error checking {ticker}: {e}")
                continue

        print(f"  Updated {updated} performance checkpoints")
        self._save_recommendations()

    def generate_summary(self) -> dict:
        """Generate performance summary statistics"""
        if self.recommendations.empty:
            summary = {
                'total_signals': 0,
                'message': 'No recommendations tracked yet',
                'generated_at': datetime.now().isoformat()
            }
            self._save_summary(summary)
            return summary

        df = self.recommendations

        # Overall stats
        total = len(df)
        unique_tickers = df['ticker'].nunique()
        date_range = f"{df['signal_date'].min().date()} to {df['signal_date'].max().date()}"

        # Win rates by period
        def win_stats(col_return, col_win):
            valid = df[df[col_return].notna()]
            if valid.empty:
                return {'count': 0, 'win_rate': None, 'avg_return': None,
                        'median_return': None, 'best': None, 'worst': None}
            wins = valid[valid[col_win] == True]
            return {
                'count': len(valid),
                'win_rate': round(len(wins) / len(valid) * 100, 1),
                'avg_return': round(valid[col_return].mean(), 2),
                'median_return': round(valid[col_return].median(), 2),
                'best': round(valid[col_return].max(), 2),
                'worst': round(valid[col_return].min(), 2),
            }

        # By strategy
        value_df = df[df['strategy'] == 'VALUE']
        mom_df = df[df['strategy'] == 'MOMENTUM']

        # Sector analysis
        sector_perf = {}
        for sector in df['sector'].unique():
            sdf = df[(df['sector'] == sector) & df['return_14d'].notna()]
            if len(sdf) >= 2:
                sector_perf[sector] = {
                    'count': len(sdf),
                    'avg_14d': round(sdf['return_14d'].mean(), 2),
                    'win_rate_14d': round((sdf['win_14d'] == True).sum() / len(sdf) * 100, 1)
                }

        # Score correlation — do higher scores = better returns?
        score_corr = None
        if not value_df.empty and value_df['return_14d'].notna().sum() >= 5:
            valid = value_df[value_df['return_14d'].notna() & value_df['value_score'].notna()]
            if len(valid) >= 5:
                score_corr = round(valid['value_score'].corr(valid['return_14d']), 3)

        # Top/Bottom performers
        if df['return_14d'].notna().sum() > 0:
            sorted_df = df[df['return_14d'].notna()].sort_values('return_14d', ascending=False)
            top5 = sorted_df.head(5)[['ticker', 'strategy', 'signal_date', 'signal_price', 'return_14d']].to_dict('records')
            bottom5 = sorted_df.tail(5)[['ticker', 'strategy', 'signal_date', 'signal_price', 'return_14d']].to_dict('records')
        else:
            top5 = []
            bottom5 = []

        summary = {
            'total_signals': total,
            'unique_tickers': unique_tickers,
            'date_range': date_range,
            'active_signals': int((df['status'] == 'ACTIVE').sum()),
            'completed_signals': int((df['status'] == 'COMPLETED').sum()),

            'overall': {
                '7d': win_stats('return_7d', 'win_7d'),
                '14d': win_stats('return_14d', 'win_14d'),
                '30d': win_stats('return_30d', 'win_30d'),
            },

            'value_strategy': {
                'count': len(value_df),
                '7d': win_stats('return_7d', 'win_7d') if not value_df.empty else {},
                '14d': win_stats('return_14d', 'win_14d') if not value_df.empty else {},
                '30d': win_stats('return_30d', 'win_30d') if not value_df.empty else {},
            },

            'momentum_strategy': {
                'count': len(mom_df),
                '7d': win_stats('return_7d', 'win_7d') if not mom_df.empty else {},
                '14d': win_stats('return_14d', 'win_14d') if not mom_df.empty else {},
                '30d': win_stats('return_30d', 'win_30d') if not mom_df.empty else {},
            },

            'sector_performance': sector_perf,
            'score_correlation': score_corr,
            'top_performers': top5,
            'worst_performers': bottom5,

            'avg_max_drawdown': round(df['max_drawdown_30d'].mean(), 2) if df['max_drawdown_30d'].notna().sum() > 0 else None,

            'generated_at': datetime.now().isoformat()
        }

        self._save_summary(summary)
        return summary

    def print_report(self, summary: dict):
        """Print formatted performance report"""
        print("\n" + "=" * 80)
        print("PORTFOLIO TRACKER — PERFORMANCE REPORT")
        print("=" * 80)

        print(f"\n  Total signals tracked: {summary['total_signals']}")
        print(f"  Unique tickers: {summary.get('unique_tickers', 'N/A')}")
        print(f"  Period: {summary.get('date_range', 'N/A')}")
        print(f"  Active: {summary.get('active_signals', 0)} | Completed: {summary.get('completed_signals', 0)}")

        for label, key in [('OVERALL', 'overall'), ('VALUE', 'value_strategy'), ('MOMENTUM', 'momentum_strategy')]:
            data = summary.get(key, {})
            if not data:
                continue
            print(f"\n  --- {label} ---")
            for period in ['7d', '14d', '30d']:
                stats = data.get(period, {})
                if not stats or stats.get('count', 0) == 0:
                    continue
                wr = stats.get('win_rate')
                avg = stats.get('avg_return')
                n = stats.get('count')
                wr_str = f"{wr}%" if wr is not None else "N/A"
                avg_str = f"{avg:+.2f}%" if avg is not None else "N/A"
                print(f"    {period}: Win Rate {wr_str} | Avg {avg_str} | n={n}")

        # Score correlation
        corr = summary.get('score_correlation')
        if corr is not None:
            direction = "POSITIVE" if corr > 0.1 else ("NEGATIVE" if corr < -0.1 else "WEAK")
            print(f"\n  Score → Return correlation: {corr} ({direction})")
            if corr > 0.1:
                print("    Higher scores DO predict better returns")
            elif corr < -0.1:
                print("    WARNING: Higher scores predict WORSE returns!")

        # Top/Bottom
        top = summary.get('top_performers', [])
        if top:
            print(f"\n  TOP 5 PERFORMERS:")
            for t in top:
                sig_date = str(t.get('signal_date', ''))[:10]
                print(f"    {t['ticker']:6} {t['strategy']:8} {sig_date} ${t.get('signal_price', 0):>8.2f} → {t['return_14d']:+.1f}%")

        bottom = summary.get('worst_performers', [])
        if bottom:
            print(f"\n  WORST 5 PERFORMERS:")
            for t in bottom:
                sig_date = str(t.get('signal_date', ''))[:10]
                print(f"    {t['ticker']:6} {t['strategy']:8} {sig_date} ${t.get('signal_price', 0):>8.2f} → {t['return_14d']:+.1f}%")

        dd = summary.get('avg_max_drawdown')
        if dd is not None:
            print(f"\n  Average Max Drawdown (30d): {dd:.1f}%")

        print("\n" + "=" * 80)

    def _save_recommendations(self):
        """Save recommendations to CSV"""
        self.recommendations.to_csv(RECOMMENDATIONS_FILE, index=False)

    def _save_summary(self, summary: dict):
        """Save summary to JSON"""
        # Convert Timestamps to strings for JSON
        def convert(obj):
            if isinstance(obj, (pd.Timestamp, datetime)):
                return str(obj)
            if isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(i) for i in obj]
            if pd.isna(obj) if isinstance(obj, float) else False:
                return None
            return obj

        with open(SUMMARY_FILE, 'w') as f:
            json.dump(convert(summary), f, indent=2, default=str)
        print(f"  Summary saved: {SUMMARY_FILE}")


def main():
    parser = argparse.ArgumentParser(description='Portfolio Tracker')
    parser.add_argument('--record', action='store_true', help='Record today\'s signals')
    parser.add_argument('--update', action='store_true', help='Update performance for past signals')
    parser.add_argument('--report', action='store_true', help='Generate and print performance report')
    parser.add_argument('--all', action='store_true', help='Record + Update + Report')
    args = parser.parse_args()

    if not any([args.record, args.update, args.report, args.all]):
        args.all = True

    tracker = PortfolioTracker()

    print("\n" + "=" * 80)
    print("PORTFOLIO TRACKER")
    print("=" * 80)

    if args.record or args.all:
        print("\n1. RECORDING TODAY'S SIGNALS")
        print("-" * 40)
        tracker.record_signals()

    if args.update or args.all:
        print("\n2. UPDATING PERFORMANCE")
        print("-" * 40)
        tracker.update_performance()

    if args.report or args.all:
        print("\n3. GENERATING REPORT")
        print("-" * 40)
        summary = tracker.generate_summary()
        tracker.print_report(summary)

    print("\nDone!")


if __name__ == '__main__':
    main()

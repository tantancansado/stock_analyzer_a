#!/usr/bin/env python3
"""
Apply valuation filters to existing value_opportunities.csv
"""
import pandas as pd
from pathlib import Path

def main():
    print("=" * 80)
    print("APPLYING VALUATION FILTERS TO VALUE OPPORTUNITIES")
    print("=" * 80)

    # Load existing value opportunities
    value_path = Path('docs/value_opportunities.csv')
    if not value_path.exists():
        print("❌ value_opportunities.csv not found")
        return

    df = pd.read_csv(value_path)
    print(f"\n📊 Original count: {len(df)} opportunities")
    print(f"   Average value_score: {df['value_score'].mean():.1f}")

    # FILTER 1: Reject stocks with negative analyst upside (overvalued)
    if 'analyst_upside_pct' in df.columns and 'value_score' in df.columns:
        overvalued = df['analyst_upside_pct'].notna() & (df['analyst_upside_pct'] < 0)
        overvalued_count = overvalued.sum()

        if overvalued_count > 0:
            overvalued_tickers = df[overvalued][['ticker', 'value_score', 'analyst_upside_pct']].copy()
            print(f"\n🚫 REJECTING {overvalued_count} stocks with negative analyst upside:")
            for _, row in overvalued_tickers.iterrows():
                print(f"   {row['ticker']:<6} value_score={row['value_score']:.1f} → upside={row['analyst_upside_pct']:.1f}%")

            # Zero out value_score for overvalued stocks
            df.loc[overvalued, 'value_score'] = 0.0

    # FILTER 2: Penalize stocks without analyst coverage
    if 'analyst_count' in df.columns:
        no_coverage = df['analyst_count'].isna() | (df['analyst_count'] == 0)
        no_cov_count = no_coverage.sum()

        if no_cov_count > 0:
            print(f"\n⚠️  {no_cov_count} stocks have no analyst coverage")
            print("   Applying -15% penalty to value_score")

            # Apply 15% penalty
            df.loc[no_coverage, 'value_score'] = df.loc[no_coverage, 'value_score'] * 0.85

    # Filter out value_score == 0 (rejected stocks)
    df_filtered = df[df['value_score'] > 0].copy()
    rejected_count = len(df) - len(df_filtered)

    print(f"\n📊 After valuation filters:")
    print(f"   Remaining: {len(df_filtered)} opportunities")
    print(f"   Rejected: {rejected_count}")
    print(f"   Average value_score: {df_filtered['value_score'].mean():.1f}")

    # Sort by value_score
    df_filtered = df_filtered.sort_values('value_score', ascending=False)

    # Save updated file
    output_path = Path('docs/value_opportunities.csv')
    df_filtered.to_csv(output_path, index=False)
    print(f"\n✅ Saved to: {output_path}")

    # Show top 10
    print(f"\n🎯 TOP 10 VALUE OPPORTUNITIES (after filters):")
    top10 = df_filtered.head(10)[['ticker', 'company_name', 'value_score',
                                    'analyst_upside_pct', 'analyst_count',
                                    'target_price_analyst', 'current_price']]

    for i, (_, row) in enumerate(top10.iterrows(), 1):
        ticker = row['ticker']
        score = row['value_score']
        upside = row['analyst_upside_pct']
        count = row['analyst_count']
        target = row['target_price_analyst']
        price = row['current_price']

        upside_str = f"+{upside:.1f}%" if pd.notna(upside) else "N/A"
        target_str = f"${target:.2f}" if pd.notna(target) else "N/A"
        count_str = f"({int(count)})" if pd.notna(count) else "(0)"

        print(f"  {i:2}. {ticker:<6} score={score:5.1f}  upside={upside_str:>8} {count_str:>4}  target={target_str:>8}  price=${price:.2f}")

if __name__ == '__main__':
    main()

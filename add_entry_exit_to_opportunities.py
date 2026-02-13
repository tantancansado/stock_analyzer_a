#!/usr/bin/env python3
"""
ADD ENTRY/EXIT TO OPPORTUNITIES
Añade precios de entrada/salida a las oportunidades del super score

Lee: docs/super_scores_ultimate.csv
Añade: entry_price, stop_loss, exit_price, risk_reward
Guarda: docs/super_opportunities_with_prices.csv
"""

import pandas as pd
import sys
from pathlib import Path
from entry_exit_calculator import EntryExitCalculator
from seeking_alpha_client import SeekingAlphaClient

def add_entry_exit_prices(input_file: str = None, output_file: str = None):
    """
    Añade entry/exit prices a todas las oportunidades

    Args:
        input_file: CSV con oportunidades (default: docs/super_scores_ultimate.csv)
        output_file: CSV output (default: docs/super_opportunities_with_prices.csv)
    """
    if not input_file:
        input_file = 'docs/super_scores_ultimate.csv'
    if not output_file:
        output_file = 'docs/super_opportunities_with_prices.csv'

    print(f"\n{'='*80}")
    print("📊 ADDING ENTRY/EXIT PRICES TO OPPORTUNITIES")
    print(f"{'='*80}\n")

    # Load opportunities
    if not Path(input_file).exists():
        print(f"❌ File not found: {input_file}")
        return

    df = pd.read_csv(input_file)
    print(f"✅ Loaded {len(df)} opportunities from {input_file}")

    # Initialize calculators
    calc = EntryExitCalculator()
    sa_client = SeekingAlphaClient()

    # Process each opportunity
    results = []

    for idx, row in df.head(50).iterrows():  # Process top 50
        ticker = row['ticker']
        print(f"\n[{idx+1}/50] Processing {ticker}...")

        try:
            # Get ticker data
            ticker_data = sa_client.get_ticker_data(ticker)
            if not ticker_data or 'historical' not in ticker_data:
                print(f"   ⚠️  No data for {ticker}")
                continue

            # Convert hist dict to DataFrame if needed
            hist = ticker_data.get('historical')
            if isinstance(hist, dict):
                hist = pd.DataFrame(hist)
                hist.set_index('Date', inplace=True)

            current_price = ticker_data.get('current_price', 0)
            if current_price == 0:
                current_price = hist['Close'].iloc[-1] if not hist.empty else 0

            # Prepare VCP analysis from row data
            vcp_analysis = {
                'score': row.get('vcp_score', 0),
                'pattern_detected': row.get('vcp_ready_to_buy', False)
            }

            # Prepare fundamental data
            fundamental_data = {
                'pe_ratio': row.get('pe_ratio'),
                'peg_ratio': row.get('peg_ratio'),
            }

            # Prepare validation
            # Estimate ATH from 52-week high if available
            year_high = ticker_data.get('52_week_high') or ticker_data.get('fifty_two_week_high')
            if year_high:
                price_vs_ath = ((current_price - year_high) / year_high) * 100
            else:
                price_vs_ath = None

            validation = {
                'price_vs_ath': price_vs_ath
            }

            # Calculate entry/exit
            entry_exit = calc.calculate_entry_exit(
                ticker=ticker,
                current_price=current_price,
                hist=hist,
                vcp_analysis=vcp_analysis,
                fundamental_data=fundamental_data,
                validation=validation
            )

            # Add to row
            result = row.to_dict()
            result.update({
                'current_price': entry_exit['current_price'],
                'entry_price': entry_exit['entry_price'],
                'entry_range': f"${entry_exit['entry_range_low']}-${entry_exit['entry_range_high']}",
                'stop_loss': entry_exit['stop_loss'],
                'exit_price': entry_exit['exit_price'],
                'exit_range': f"${entry_exit['exit_range_low']}-${entry_exit['exit_range_high']}",
                'risk_reward': entry_exit['risk_reward_ratio'],
                'risk_pct': entry_exit['risk_pct'],
                'reward_pct': entry_exit['reward_pct'],
                'entry_timing': entry_exit['entry_timing'],
                'meets_risk_reward': entry_exit['meets_criteria']
            })

            results.append(result)

            print(f"   ✅ ${entry_exit['current_price']} → Entry: ${entry_exit['entry_price']} | Stop: ${entry_exit['stop_loss']} | Target: ${entry_exit['exit_price']} (R/R: {entry_exit['risk_reward_ratio']}:1)")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            continue

    # Create DataFrame and save
    if results:
        result_df = pd.DataFrame(results)

        # Reorder columns to show prices first
        price_cols = ['ticker', 'current_price', 'entry_price', 'entry_range', 'stop_loss',
                      'exit_price', 'exit_range', 'risk_reward', 'risk_pct', 'reward_pct',
                      'entry_timing', 'meets_risk_reward']

        other_cols = [col for col in result_df.columns if col not in price_cols]
        result_df = result_df[price_cols + other_cols]

        # Save
        result_df.to_csv(output_file, index=False)

        print(f"\n{'='*80}")
        print(f"✅ SAVED {len(result_df)} opportunities with entry/exit prices")
        print(f"📁 Output: {output_file}")
        print(f"{'='*80}\n")

        # Show summary
        print("\n📊 SUMMARY:")
        print(f"   Average R/R Ratio: {result_df['risk_reward'].mean():.2f}:1")
        print(f"   Meets Criteria (3:1): {result_df['meets_risk_reward'].sum()}/{len(result_df)}")
        print(f"   Average Risk: {result_df['risk_pct'].mean():.1f}%")
        print(f"   Average Reward: {result_df['reward_pct'].mean():.1f}%")

        # Show top 10
        print(f"\n🏆 TOP 10 BY RISK/REWARD:")
        top_10 = result_df.nlargest(10, 'risk_reward')[['ticker', 'current_price', 'entry_price', 'exit_price', 'risk_reward', 'entry_timing']]
        print(top_10.to_string(index=False))

    else:
        print("\n❌ No opportunities processed successfully")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Add entry/exit prices to opportunities')
    parser.add_argument('--input', type=str, help='Input CSV file')
    parser.add_argument('--output', type=str, help='Output CSV file')
    args = parser.parse_args()

    add_entry_exit_prices(args.input, args.output)

#!/usr/bin/env python3
"""
ADD ENTRY/EXIT TO OPPORTUNITIES
Añade precios de entrada/salida a las oportunidades del super score

Lee: docs/super_scores_ultimate.csv
Añade: entry_price, stop_loss, exit_price, risk_reward
Guarda: docs/super_opportunities_with_prices.csv

Data source: yfinance (no Seeking Alpha cookies needed)
"""

import pandas as pd
import numpy as np
import time
import sys
from pathlib import Path
from entry_exit_calculator import EntryExitCalculator

# Rate limiting config
YF_DELAY_BETWEEN_TICKERS = 2.0  # seconds between tickers
YF_DELAY_ON_ERROR = 10.0        # seconds after a rate limit error
YF_MAX_RETRIES = 3


def fetch_ticker_yfinance(ticker: str, attempt: int = 1) -> dict:
    """
    Fetch ticker data from yfinance with retry logic.
    Returns dict with current_price, hist (DataFrame), 52w high/low.
    """
    import yfinance as yf

    try:
        stock = yf.Ticker(ticker)

        # Get historical data (200+ days for SMA calculations)
        hist = stock.history(period='1y')

        if hist.empty:
            print(f"   ⚠️  No historical data from yfinance")
            return None

        # Get current price from latest close
        current_price = float(hist['Close'].iloc[-1])

        # 52-week high/low from historical
        week_52_high = float(hist['High'].max())
        week_52_low = float(hist['Low'].min())

        return {
            'current_price': current_price,
            'hist': hist,
            '52_week_high': week_52_high,
            '52_week_low': week_52_low,
        }

    except Exception as e:
        error_msg = str(e).lower()

        # Rate limit detection
        if '429' in str(e) or 'too many requests' in error_msg or 'rate' in error_msg:
            if attempt < YF_MAX_RETRIES:
                wait = YF_DELAY_ON_ERROR * attempt
                print(f"   ⏳ Rate limited, waiting {wait:.0f}s (attempt {attempt}/{YF_MAX_RETRIES})...")
                time.sleep(wait)
                return fetch_ticker_yfinance(ticker, attempt + 1)

        print(f"   ⚠️  yfinance error: {str(e)[:80]}")
        return None


def add_entry_exit_prices(input_file: str = None, output_file: str = None):
    """
    Añade entry/exit prices a todas las oportunidades usando yfinance
    """
    if not input_file:
        input_file = 'docs/super_scores_ultimate.csv'
    if not output_file:
        output_file = 'docs/super_opportunities_with_prices.csv'

    print(f"\n{'='*80}")
    print("📊 ADDING ENTRY/EXIT PRICES TO OPPORTUNITIES")
    print(f"{'='*80}")
    print(f"📡 Data source: yfinance (with rate limiting)\n")

    # Load opportunities
    if not Path(input_file).exists():
        print(f"❌ File not found: {input_file}")
        return

    df = pd.read_csv(input_file)
    total = min(len(df), 50)
    print(f"✅ Loaded {len(df)} opportunities from {input_file}")
    print(f"📋 Processing top {total}...\n")

    # Initialize calculator
    calc = EntryExitCalculator()

    results = []
    failed = []

    for idx, row in df.head(total).iterrows():
        ticker = row['ticker']
        print(f"[{idx+1}/{total}] Processing {ticker}...")

        # Rate limiting between tickers
        if idx > 0:
            time.sleep(YF_DELAY_BETWEEN_TICKERS)

        try:
            # Fetch from yfinance
            data = fetch_ticker_yfinance(ticker)
            if not data:
                failed.append(ticker)
                continue

            hist = data['hist']
            current_price = data['current_price']

            # Normalize columns to lowercase
            hist.columns = [col.lower() for col in hist.columns]

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

            # Price vs ATH
            year_high = data.get('52_week_high')
            if year_high and year_high > 0:
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
            print(f"   ✅ ${entry_exit['current_price']:.2f} → Entry: ${entry_exit['entry_price']:.2f} | Stop: ${entry_exit['stop_loss']:.2f} | Target: ${entry_exit['exit_price']:.2f} (R/R: {entry_exit['risk_reward_ratio']:.1f}:1)")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            failed.append(ticker)
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
        if failed:
            print(f"⚠️  Failed ({len(failed)}): {', '.join(failed)}")
        print(f"{'='*80}\n")

        # Show summary
        print("📊 SUMMARY:")
        print(f"   Processed: {len(result_df)}/{total}")
        print(f"   Average R/R Ratio: {result_df['risk_reward'].mean():.2f}:1")
        print(f"   Meets Criteria (3:1): {result_df['meets_risk_reward'].sum()}/{len(result_df)}")
        print(f"   Average Risk: {result_df['risk_pct'].mean():.1f}%")
        print(f"   Average Reward: {result_df['reward_pct'].mean():.1f}%")

        # Show top 10
        print(f"\n🏆 TOP 10 BY RISK/REWARD:")
        top_10 = result_df.nlargest(10, 'risk_reward')[['ticker', 'current_price', 'entry_price', 'exit_price', 'risk_reward', 'entry_timing']]
        print(top_10.to_string(index=False))

    else:
        print(f"\n❌ No opportunities processed successfully")
        if failed:
            print(f"   Failed tickers: {', '.join(failed)}")


def _enrich_csv_with_entry_exit(input_file: str):
    """
    Enrich a CSV in-place with entry/exit columns.
    Reads the file, adds entry/exit data, writes back to same file.
    Only updates rows where entry/exit was successfully calculated.
    Preserves ALL original rows (doesn't drop any).
    """
    p = Path(input_file)
    if not p.exists():
        return
    df = pd.read_csv(input_file)
    if df.empty:
        print(f"  {input_file} is empty, skipping")
        return

    print(f"\n📊 Enriching {input_file} with entry/exit ({len(df)} tickers)")
    calc = EntryExitCalculator()

    for idx, row in df.head(50).iterrows():
        ticker = row['ticker']
        if idx > 0:
            time.sleep(YF_DELAY_BETWEEN_TICKERS)
        try:
            data = fetch_ticker_yfinance(ticker)
            if not data:
                continue
            hist = data['hist']
            hist.columns = [col.lower() for col in hist.columns]
            current_price = data['current_price']

            vcp_analysis = {'score': row.get('vcp_score', 0), 'pattern_detected': False}
            fundamental_data = {'pe_ratio': row.get('pe_ratio'), 'peg_ratio': row.get('peg_ratio')}
            year_high = data.get('52_week_high')
            price_vs_ath = ((current_price - year_high) / year_high * 100) if year_high and year_high > 0 else None

            entry_exit = calc.calculate_entry_exit(
                ticker=ticker, current_price=current_price, hist=hist,
                vcp_analysis=vcp_analysis, fundamental_data=fundamental_data,
                validation={'price_vs_ath': price_vs_ath}
            )

            df.at[idx, 'entry_price'] = entry_exit['entry_price']
            df.at[idx, 'stop_loss'] = entry_exit['stop_loss']
            df.at[idx, 'exit_price'] = entry_exit['exit_price']
            df.at[idx, 'risk_pct'] = entry_exit['risk_pct']
            df.at[idx, 'reward_pct'] = entry_exit['reward_pct']
            df.at[idx, 'entry_timing'] = entry_exit['entry_timing']
            print(f"  [{idx+1}] {ticker}: Entry ${entry_exit['entry_price']:.2f} → Target ${entry_exit['exit_price']:.2f}")

        except Exception as e:
            print(f"  [{idx+1}] {ticker}: Error {str(e)[:60]}")
            continue

    # Save back — ALL rows preserved, entry/exit columns added where available
    df.to_csv(input_file, index=False)
    print(f"  Saved {input_file}")


def add_entry_exit_all():
    """Run entry/exit for all opportunity types: momentum, US VALUE, EU VALUE"""
    # 1. Momentum (original behavior — separate output file)
    add_entry_exit_prices()

    # 2. US VALUE — enrich in-place (preserves all rows)
    for vf in ['docs/value_opportunities_filtered.csv', 'docs/value_opportunities.csv']:
        if Path(vf).exists() and pd.read_csv(vf).shape[0] > 0:
            _enrich_csv_with_entry_exit(vf)
            break

    # 3. EU VALUE — enrich in-place (preserves all rows)
    for ef in ['docs/european_value_opportunities_filtered.csv', 'docs/european_value_opportunities.csv']:
        if Path(ef).exists() and pd.read_csv(ef).shape[0] > 0:
            _enrich_csv_with_entry_exit(ef)
            break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Add entry/exit prices to opportunities')
    parser.add_argument('--input', type=str, help='Input CSV file')
    parser.add_argument('--output', type=str, help='Output CSV file')
    parser.add_argument('--all', action='store_true', help='Process all opportunity types (momentum + VALUE + EU)')
    args = parser.parse_args()

    if args.all:
        add_entry_exit_all()
    else:
        add_entry_exit_prices(args.input, args.output)

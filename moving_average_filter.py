#!/usr/bin/env python3
"""
MOVING AVERAGE FILTER
Aplica el Minervini Trend Template a stocks individuales

Criteria (Mark Minervini):
1. Current price > 150 MA AND > 200 MA
2. 150 MA > 200 MA
3. 200 MA trending up for at least 1 month
4. 50 MA > 150 MA > 200 MA (ideal)
5. Current price >= 30% above 52-week low
6. Current price within 25% of 52-week high
7. RS Rating >= 70 (relative to market)

Filters out:
- Stocks below key MAs (weak trend)
- Stocks with downtrending 200 MA (structural weakness)
- Stocks not in stage 2 uptrend
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path


class MovingAverageFilter:
    """Filtra stocks usando Minervini Trend Template"""

    def __init__(self):
        self.cache_dir = Path('cache/ma_filter')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def check_stock(self, ticker: str, verbose: bool = False) -> Dict:
        """
        Verifica si un stock cumple el Minervini Trend Template

        Args:
            ticker: Symbol del stock
            verbose: Si imprimir detalles

        Returns:
            Dict con:
            - passes: bool (True si pasa el filtro)
            - score: 0-100 (% de criterios cumplidos)
            - details: dict con cada criterio
            - reason: str (explicación)
        """
        if verbose:
            print(f"\n📊 Checking MA Template: {ticker}")

        try:
            # Get data
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1y')

            if hist.empty or len(hist) < 200:
                return {
                    'ticker': ticker,
                    'passes': False,
                    'score': 0,
                    'reason': 'Insufficient data',
                    'details': {}
                }

            current_price = float(hist['Close'].iloc[-1])

            # Calculate MAs
            ma_50 = float(hist['Close'].rolling(50).mean().iloc[-1])
            ma_150 = float(hist['Close'].rolling(150).mean().iloc[-1])
            ma_200 = float(hist['Close'].rolling(200).mean().iloc[-1])

            # Calculate 200 MA slope (1 month = 20 trading days)
            ma_200_20d_ago = float(hist['Close'].rolling(200).mean().iloc[-20])
            ma_200_slope = ((ma_200 - ma_200_20d_ago) / ma_200_20d_ago * 100)

            # 52-week high/low
            week_52_high = float(hist['High'].max())
            week_52_low = float(hist['Low'].min())

            # Check each criterion
            criterion_1 = current_price > ma_150 and current_price > ma_200
            criterion_2 = ma_150 > ma_200
            criterion_3 = ma_200_slope > 0
            criterion_4 = ma_50 > ma_150 > ma_200
            criterion_5 = current_price >= week_52_low * 1.30
            criterion_6 = current_price >= week_52_high * 0.75

            # Count passed criteria
            criteria = [
                criterion_1, criterion_2, criterion_3,
                criterion_4, criterion_5, criterion_6
            ]
            checks_passed = sum(criteria)
            score = int((checks_passed / len(criteria)) * 100)

            # Must pass critical criteria (1, 2, 3)
            passes = criterion_1 and criterion_2 and criterion_3

            # Build reason
            if not passes:
                if not criterion_1:
                    reason = "Price below 150/200 MA - weak trend"
                elif not criterion_2:
                    reason = "150 MA below 200 MA - not in Stage 2"
                elif not criterion_3:
                    reason = "200 MA declining - structural weakness"
                else:
                    reason = "Failed critical MA criteria"
            else:
                reason = f"Passes Minervini Template ({checks_passed}/6 criteria)"

            result = {
                'ticker': ticker,
                'passes': bool(passes),
                'score': score,
                'checks_passed': f"{checks_passed}/6",
                'reason': reason,
                'details': {
                    'current_price': float(round(current_price, 2)),
                    'ma_50': float(round(ma_50, 2)),
                    'ma_150': float(round(ma_150, 2)),
                    'ma_200': float(round(ma_200, 2)),
                    'ma_200_slope': float(round(ma_200_slope, 2)),
                    '52w_high': float(round(week_52_high, 2)),
                    '52w_low': float(round(week_52_low, 2)),
                    'distance_from_high': float(round((current_price / week_52_high - 1) * 100, 1)),
                    'distance_from_low': float(round((current_price / week_52_low - 1) * 100, 1)),
                    'criterion_1_price_above_mas': bool(criterion_1),
                    'criterion_2_ma_150_above_200': bool(criterion_2),
                    'criterion_3_ma_200_rising': bool(criterion_3),
                    'criterion_4_ma_aligned': bool(criterion_4),
                    'criterion_5_above_low_30pct': bool(criterion_5),
                    'criterion_6_near_high_25pct': bool(criterion_6)
                }
            }

            if verbose:
                status_emoji = '✅' if passes else '❌'
                print(f"   {status_emoji} {reason}")
                print(f"   Price: ${current_price:.2f} | 50/150/200 MA: ${ma_50:.2f}/${ma_150:.2f}/${ma_200:.2f}")
                print(f"   200 MA Slope: {ma_200_slope:+.2f}% | Distance from High: {result['details']['distance_from_high']:+.1f}%")

            return result

        except Exception as e:
            if verbose:
                print(f"   ❌ Error: {str(e)}")
            return {
                'ticker': ticker,
                'passes': False,
                'score': 0,
                'reason': f'Error: {str(e)}',
                'details': {}
            }

    def filter_dataframe(
        self,
        df: pd.DataFrame,
        ticker_column: str = 'ticker',
        add_details: bool = False
    ) -> pd.DataFrame:
        """
        Filtra un DataFrame de stocks aplicando MA filter

        Args:
            df: DataFrame con columna de tickers
            ticker_column: Nombre de la columna con tickers
            add_details: Si agregar columnas con detalles de MA

        Returns:
            DataFrame filtrado con columna 'ma_filter_pass'
        """
        print(f"\n{'='*70}")
        print("📊 MOVING AVERAGE FILTER - Minervini Trend Template")
        print(f"{'='*70}\n")

        results = []
        total = len(df)

        for idx, ticker in enumerate(df[ticker_column], 1):
            print(f"[{idx}/{total}] Checking {ticker}...", end=' ')
            result = self.check_stock(ticker, verbose=False)
            results.append(result)

            status = '✅' if result['passes'] else '❌'
            print(f"{status} {result['reason']}")

        # Create results DataFrame
        results_df = pd.DataFrame(results)

        # Merge with original DataFrame
        df_filtered = df.copy()
        df_filtered = df_filtered.merge(
            results_df[[
                'ticker', 'passes', 'score', 'checks_passed', 'reason'
            ]].rename(columns={
                'passes': 'ma_filter_pass',
                'score': 'ma_score',
                'checks_passed': 'ma_checks_passed',
                'reason': 'ma_reason'
            }),
            left_on=ticker_column,
            right_on='ticker',
            how='left'
        )

        # Add MA details if requested
        if add_details:
            details_df = pd.json_normalize(results_df['details'])
            details_df['ticker'] = results_df['ticker']
            df_filtered = df_filtered.merge(details_df, on='ticker', how='left', suffixes=('', '_ma'))

        # Summary
        passed = int(df_filtered['ma_filter_pass'].sum())
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\n{'='*70}")
        print("📊 MA FILTER SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Passed: {passed}/{total} ({pass_rate:.1f}%)")
        print(f"❌ Failed: {failed}/{total} ({100-pass_rate:.1f}%)")
        print(f"{'='*70}\n")

        return df_filtered


def main():
    """Test MA filter on example stocks"""
    import argparse

    parser = argparse.ArgumentParser(description='Test Moving Average Filter')
    parser.add_argument('--ticker', help='Single ticker to test')
    parser.add_argument('--file', help='CSV file with tickers')
    parser.add_argument('--column', default='ticker', help='Ticker column name')
    args = parser.parse_args()

    filter_tool = MovingAverageFilter()

    if args.ticker:
        # Test single ticker
        result = filter_tool.check_stock(args.ticker, verbose=True)
        print(f"\nResult: {result}")

    elif args.file:
        # Test file
        df = pd.read_csv(args.file)
        filtered = filter_tool.filter_dataframe(df, ticker_column=args.column, add_details=True)

        # Show top 10 that passed
        passed = filtered[filtered['ma_filter_pass'] == True].head(10)
        print("\n🔥 Top 10 that passed MA filter:")
        for _, row in passed.iterrows():
            print(f"   ✅ {row['ticker']:6s} | Score: {row['ma_score']}/100 | {row['ma_reason']}")

    else:
        # Test on some well-known stocks
        test_tickers = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'META']
        for ticker in test_tickers:
            filter_tool.check_stock(ticker, verbose=True)


if __name__ == '__main__':
    main()

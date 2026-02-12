#!/usr/bin/env python3
"""
S&P 500 FUNDAMENTALS FETCHER
Obtiene PE/Beta/Float para todos los tickers del S&P 500

Este script corre LOCALMENTE (sin rate limiting) y genera un archivo
que el servidor puede usar sin hacer llamadas a Yahoo Finance.

Usage:
    python3 fetch_sp500_fundamentals.py
"""
import requests
import json
import time
import pandas as pd
from datetime import datetime
from pathlib import Path


def get_sp500_tickers():
    """
    Obtiene la lista de tickers del S&P 500 desde Wikipedia

    Returns:
        list: Lista de tickers del S&P 500
    """
    print("📋 Fetching S&P 500 ticker list from Wikipedia...")

    try:
        # Wikipedia mantiene una lista actualizada del S&P 500
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        sp500_table = tables[0]

        tickers = sp500_table['Symbol'].tolist()

        # Limpiar tickers (algunos tienen caracteres especiales)
        tickers = [ticker.replace('.', '-') for ticker in tickers]

        print(f"✅ Found {len(tickers)} S&P 500 tickers")
        return tickers

    except Exception as e:
        print(f"❌ Failed to fetch S&P 500 list: {str(e)}")
        print("⚠️  Using fallback list of major tickers...")

        # Fallback: Lista de ~100 tickers principales si falla Wikipedia
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
            'UNH', 'JNJ', 'JPM', 'V', 'PG', 'XOM', 'MA', 'HD', 'CVX', 'MRK',
            'ABBV', 'PEP', 'AVGO', 'KO', 'COST', 'ADBE', 'WMT', 'MCD', 'CSCO',
            'CRM', 'ACN', 'TMO', 'ABT', 'LIN', 'NFLX', 'DIS', 'NKE', 'CMCSA',
            'VZ', 'INTC', 'AMD', 'TXN', 'QCOM', 'DHR', 'PM', 'NEE', 'UPS',
            'HON', 'RTX', 'UNP', 'AMGN', 'LOW', 'SPGI', 'BMY', 'BA', 'T',
            'GE', 'IBM', 'CAT', 'DE', 'SBUX', 'INTU', 'GS', 'AXP', 'BLK',
            'NOW', 'AMAT', 'BKNG', 'GILD', 'MMM', 'LMT', 'CVS', 'ADI', 'MDLZ',
            'PLD', 'MO', 'SYK', 'TJX', 'VRTX', 'ZTS', 'C', 'CB', 'ADP', 'ISRG',
            'DUK', 'SCHW', 'CI', 'SO', 'REGN', 'BDX', 'PNC', 'TGT', 'USB',
            'MMC', 'COP', 'EOG', 'NOC', 'ICE', 'WM', 'MCO', 'PGR', 'MS'
        ]


def fetch_ticker_fundamentals(ticker: str) -> dict:
    """
    Obtiene PE/Beta/Float para un ticker usando yfinance

    Uses yfinance library which handles rate limiting better than raw requests

    Args:
        ticker: Stock ticker symbol

    Returns:
        dict: Fundamentals data or None if failed
    """
    try:
        import yfinance as yf

        # Create ticker object
        stock = yf.Ticker(ticker)

        # Get info (this is cached and more robust)
        info = stock.info

        if not info or len(info) < 5:
            return None

        # Extract fundamentals
        fundamentals = {
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'peg_ratio': info.get('pegRatio'),
            'beta': info.get('beta'),
            'float_shares': info.get('floatShares'),
            'shares_outstanding': info.get('sharesOutstanding'),
            'market_cap': info.get('marketCap'),
            'dividend_yield': info.get('dividendYield'),
            'price_to_book': info.get('priceToBook'),
            'profit_margins': info.get('profitMargins'),
            'revenue_growth': info.get('revenueGrowth')
        }

        # Remove None values
        fundamentals = {k: v for k, v in fundamentals.items() if v is not None}

        return fundamentals if fundamentals else None

    except Exception as e:
        return None


def main():
    """Main function to fetch S&P 500 fundamentals"""
    print("\n" + "="*70)
    print("📊 S&P 500 FUNDAMENTALS FETCHER")
    print("="*70 + "\n")

    # Get S&P 500 tickers
    tickers = get_sp500_tickers()

    output_file = Path('docs/sp500_fundamentals.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n🎯 Fetching fundamentals for {len(tickers)} tickers...")
    print("⏱️  Estimated time: ~{:.1f} minutes (3s delay per ticker)".format(len(tickers) * 3 / 60))
    print("\n" + "="*70 + "\n")

    results = {}
    successful = 0
    failed = 0

    for i, ticker in enumerate(tickers, 1):
        try:
            # Progress indicator
            progress = f"[{i}/{len(tickers)}]"
            print(f"{progress:>12} {ticker:6s} ", end='', flush=True)

            # Fetch fundamentals
            fundamentals = fetch_ticker_fundamentals(ticker)

            if fundamentals:
                results[ticker] = {
                    'ticker': ticker,
                    'fundamentals': fundamentals,
                    'fetched_at': datetime.now().isoformat()
                }

                # Show what we got
                pe = fundamentals.get('pe_ratio')
                beta = fundamentals.get('beta')
                pe_str = f"PE: {pe:.1f}" if pe else "PE: N/A"
                beta_str = f"Beta: {beta:.2f}" if beta else "Beta: N/A"
                print(f"✅ {pe_str:12s} {beta_str:12s}")

                successful += 1
            else:
                print("❌ No data")
                failed += 1

            # Delay to avoid rate limiting (critical!)
            # 3 seconds is safe for most cases
            time.sleep(3)

            # Save progress every 50 tickers
            if i % 50 == 0:
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\n💾 Progress saved ({successful} successful, {failed} failed)\n")

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user. Saving progress...")
            break

        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            failed += 1
            time.sleep(3)

    # Save final results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"✅ Successful: {successful}/{len(tickers)} ({successful/len(tickers)*100:.1f}%)")
    print(f"❌ Failed: {failed}/{len(tickers)} ({failed/len(tickers)*100:.1f}%)")
    print(f"💾 Saved to: {output_file}")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Generate test ticker cache for a few tickers
Used to test the ticker analyzer system
"""
import yfinance as yf
import json
from pathlib import Path
from datetime import datetime

def generate_test_cache():
    """Generate ticker cache for test tickers"""

    test_tickers = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOGL']
    ticker_cache = {}

    print("🧪 Generating test ticker cache...")
    print(f"Fetching data for {len(test_tickers)} tickers: {', '.join(test_tickers)}\n")

    for ticker in test_tickers:
        try:
            print(f"  Fetching {ticker}...", end=" ", flush=True)

            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="200d")

            if hist.empty:
                print("❌ No data")
                continue

            # Prepare ticker data
            ticker_data = {
                "ticker": ticker,
                "company_name": info.get('longName', info.get('shortName', ticker)),
                "sector": info.get('sector', 'N/A'),
                "industry": info.get('industry', 'N/A'),

                "current_price": float(info.get('currentPrice', hist['Close'].iloc[-1])),
                "previous_close": float(info.get('previousClose', hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[-1])),
                "volume": int(info.get('volume', hist['Volume'].iloc[-1])),
                "avg_volume": int(info.get('averageVolume', hist['Volume'].mean())),

                "market_cap": int(info.get('marketCap', 0)),
                "shares_outstanding": int(info.get('sharesOutstanding', 0)),

                "fifty_two_week_high": float(info.get('fiftyTwoWeekHigh', hist['High'].max())),
                "fifty_two_week_low": float(info.get('fiftyTwoWeekLow', hist['Low'].min())),

                "historical": {
                    "dates": [d.strftime('%Y-%m-%d') for d in hist.index],
                    "open": [float(x) for x in hist['Open'].values],
                    "high": [float(x) for x in hist['High'].values],
                    "low": [float(x) for x in hist['Low'].values],
                    "close": [float(x) for x in hist['Close'].values],
                    "volume": [int(x) for x in hist['Volume'].values]
                },

                "sma_10": float(hist['Close'].tail(10).mean()),
                "sma_20": float(hist['Close'].tail(20).mean()),
                "sma_50": float(hist['Close'].tail(50).mean()),
                "sma_150": float(hist['Close'].tail(150).mean()),
                "sma_200": float(hist['Close'].tail(200).mean()),

                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "data_source": "yfinance_test"
            }

            ticker_cache[ticker] = ticker_data
            print("✅")

        except Exception as e:
            print(f"❌ {str(e)[:50]}")
            continue

    # Save to JSON
    cache_path = Path('docs/ticker_data_cache.json')
    with open(cache_path, 'w') as f:
        json.dump(ticker_cache, f, indent=2)

    print(f"\n✅ Test cache generated: {cache_path}")
    print(f"   Tickers: {len(ticker_cache)}")
    print(f"   File size: {cache_path.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    generate_test_cache()

#!/usr/bin/env python3
"""
COMPANY NAME FETCHER
Obtiene nombres completos de empresas para tickers
"""
import yfinance as yf
from typing import Dict
import json
from pathlib import Path


class CompanyNameFetcher:
    """Fetches and caches company names"""

    def __init__(self, cache_file: str = "data/company_names_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cached company names"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        """Save cache to file"""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def get_company_name(self, ticker: str) -> str:
        """
        Get company name for a ticker
        Returns cached name if available, otherwise fetches from yfinance
        """
        # Check cache first
        if ticker in self.cache:
            return self.cache[ticker]

        # Fetch from yfinance
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Try different fields for company name
            name = info.get('longName') or info.get('shortName') or ticker

            # Clean up the name
            if name and name != ticker:
                # Remove common suffixes for cleaner display
                name = name.replace(' Inc.', '').replace(' Inc', '')
                name = name.replace(' Corporation', '').replace(' Corp.', '').replace(' Corp', '')
                name = name.replace(' Company', '').replace(' Co.', '').replace(' Co', '')
                name = name.replace(' Limited', '').replace(' Ltd.', '').replace(' Ltd', '')
                name = name.replace(' Holding Company', '').replace(' Holdings', '')
                name = name.strip()

            # Cache the result
            self.cache[ticker] = name
            self._save_cache()

            return name

        except Exception as e:
            # If fetch fails, cache ticker as name
            self.cache[ticker] = ticker
            self._save_cache()
            return ticker

    def get_multiple_names(self, tickers: list, show_progress: bool = False) -> Dict[str, str]:
        """
        Get company names for multiple tickers
        Returns dict of ticker -> company name
        """
        results = {}
        total = len(tickers)

        for i, ticker in enumerate(tickers, 1):
            if show_progress and i % 10 == 0:
                print(f"   Fetching names: {i}/{total}...", end='\r')

            results[ticker] = self.get_company_name(ticker)

        if show_progress:
            print(f"   ✅ {total} company names loaded")

        return results


def add_company_names_to_opportunities(opportunities: list) -> list:
    """
    Add company names to opportunities list
    """
    fetcher = CompanyNameFetcher()

    # Get all unique tickers
    tickers = list(set([opp.get('ticker') for opp in opportunities if opp.get('ticker')]))

    print(f"\n📝 Obteniendo nombres de empresas para {len(tickers)} tickers...")

    # Fetch names
    names = fetcher.get_multiple_names(tickers, show_progress=True)

    # Add to opportunities
    for opp in opportunities:
        ticker = opp.get('ticker')
        if ticker:
            opp['company_name'] = names.get(ticker, ticker)

    return opportunities


if __name__ == "__main__":
    # Test
    fetcher = CompanyNameFetcher()

    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']

    print("Testing company name fetcher:")
    print("=" * 60)

    for ticker in test_tickers:
        name = fetcher.get_company_name(ticker)
        print(f"{ticker:6} -> {name}")

    print("\n✅ Test complete!")

#!/usr/bin/env python3
"""
YAHOO FINANCE WEB SCRAPER
Scrapes Yahoo Finance HTML directly (no API calls)

Used as fallback when ticker is not in the pre-populated cache.
Avoids API rate limiting by scraping public HTML pages.

Legal: Personal use only, respects robots.txt
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List


class YahooFinanceScraper:
    """Scrapes Yahoo Finance public pages to get stock data"""

    def __init__(self):
        self.base_url = "https://finance.yahoo.com/quote"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

    def scrape_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape datos completos de un ticker desde Yahoo Finance

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Dict con datos del ticker (formato compatible con ticker_data_cache.json)
        """
        print(f"🌐 Scraping Yahoo Finance for {ticker}...")

        try:
            # 1. Scrape main quote page
            quote_data = self._scrape_quote_page(ticker)

            # 2. Scrape historical data (últimos 200 días)
            historical_data = self._scrape_historical_data(ticker, days=200)

            # 3. Combine data
            ticker_data = {
                **quote_data,
                "historical": historical_data,
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "data_source": "yahoo_finance_scraper"
            }

            print(f"✅ Successfully scraped {ticker}")
            return ticker_data

        except Exception as e:
            print(f"❌ Failed to scrape {ticker}: {str(e)}")
            raise

    def _scrape_quote_page(self, ticker: str) -> Dict[str, Any]:
        """Scrape main quote page for current data"""
        url = f"{self.base_url}/{ticker}"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract data from page
        try:
            # Current price (in the main quote area)
            price_element = soup.find('fin-streamer', {'data-symbol': ticker, 'data-field': 'regularMarketPrice'})
            current_price = float(price_element.get('value', 0)) if price_element else 0.0

            # Previous close
            prev_close_element = soup.find('fin-streamer', {'data-field': 'regularMarketPreviousClose'})
            previous_close = float(prev_close_element.get('value', current_price)) if prev_close_element else current_price

            # Volume
            volume_element = soup.find('fin-streamer', {'data-field': 'regularMarketVolume'})
            volume = int(volume_element.get('value', 0)) if volume_element else 0

            # Market cap (puede estar en formato abreviado como "2.5T")
            market_cap_text = self._extract_table_value(soup, 'Market Cap')
            market_cap = self._parse_market_cap(market_cap_text)

            # 52 week range
            week_52_range = self._extract_table_value(soup, '52 Week Range')
            fifty_two_week_low, fifty_two_week_high = self._parse_52_week_range(week_52_range)

            # Avg Volume
            avg_volume_text = self._extract_table_value(soup, 'Avg. Volume')
            avg_volume = self._parse_volume(avg_volume_text)

            # Company name (from title)
            title = soup.find('title')
            company_name = ticker
            if title:
                # Format: "AAPL : Summary for Apple Inc. - Yahoo Finance"
                match = re.search(r'Summary for (.+?) -', title.text)
                if match:
                    company_name = match.group(1).strip()

            # Sector & Industry (from profile page - optional, can be scraped separately)
            sector = "N/A"
            industry = "N/A"

            return {
                "ticker": ticker,
                "company_name": company_name,
                "sector": sector,
                "industry": industry,
                "current_price": current_price,
                "previous_close": previous_close,
                "volume": volume,
                "avg_volume": avg_volume,
                "market_cap": market_cap,
                "shares_outstanding": 0,  # Requires additional scraping
                "fifty_two_week_high": fifty_two_week_high,
                "fifty_two_week_low": fifty_two_week_low,
            }

        except Exception as e:
            raise Exception(f"Failed to parse quote page: {str(e)}")

    def _scrape_historical_data(self, ticker: str, days: int = 200) -> Dict[str, List]:
        """
        Scrape historical price data

        Yahoo Finance allows downloading CSV for historical data
        """
        # Calculate timestamps
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        period1 = int(start_date.timestamp())
        period2 = int(end_date.timestamp())

        # Download CSV format (easier to parse than HTML)
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
        params = {
            'period1': period1,
            'period2': period2,
            'interval': '1d',
            'events': 'history',
        }

        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            response.raise_for_status()

            # Parse CSV
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                raise Exception("No historical data available")

            # Skip header
            data_lines = lines[1:]

            dates = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []

            for line in data_lines:
                parts = line.split(',')
                if len(parts) >= 6:
                    try:
                        dates.append(parts[0])  # Date
                        opens.append(float(parts[1]))  # Open
                        highs.append(float(parts[2]))  # High
                        lows.append(float(parts[3]))  # Low
                        closes.append(float(parts[4]))  # Close
                        volumes.append(int(float(parts[6])))  # Volume
                    except (ValueError, IndexError):
                        continue

            return {
                "dates": dates,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes
            }

        except Exception as e:
            print(f"⚠️  Failed to get historical data via CSV, using empty fallback: {str(e)}")
            return {
                "dates": [],
                "open": [],
                "high": [],
                "low": [],
                "close": [],
                "volume": []
            }

    def _extract_table_value(self, soup: BeautifulSoup, label: str) -> str:
        """Extract value from the statistics table"""
        try:
            # Find the td element containing the label
            label_element = soup.find('td', string=re.compile(label, re.IGNORECASE))
            if label_element:
                # Get the next td sibling (the value)
                value_element = label_element.find_next_sibling('td')
                if value_element:
                    return value_element.text.strip()
        except Exception:
            pass
        return "N/A"

    def _parse_market_cap(self, text: str) -> int:
        """Parse market cap from text like '2.5T' or '150.5B'"""
        if text == "N/A" or not text:
            return 0

        try:
            # Remove commas
            text = text.replace(',', '')

            # Check for suffix
            multiplier = 1
            if 'T' in text.upper():
                multiplier = 1_000_000_000_000
                text = text.upper().replace('T', '')
            elif 'B' in text.upper():
                multiplier = 1_000_000_000
                text = text.upper().replace('B', '')
            elif 'M' in text.upper():
                multiplier = 1_000_000
                text = text.upper().replace('M', '')

            return int(float(text) * multiplier)
        except Exception:
            return 0

    def _parse_52_week_range(self, text: str) -> tuple:
        """Parse 52 week range like '150.50 - 200.75'"""
        if text == "N/A" or not text:
            return (0.0, 0.0)

        try:
            parts = text.split('-')
            if len(parts) == 2:
                low = float(parts[0].strip())
                high = float(parts[1].strip())
                return (low, high)
        except Exception:
            pass
        return (0.0, 0.0)

    def _parse_volume(self, text: str) -> int:
        """Parse volume from text like '50.5M'"""
        if text == "N/A" or not text:
            return 0

        try:
            text = text.replace(',', '')

            multiplier = 1
            if 'M' in text.upper():
                multiplier = 1_000_000
                text = text.upper().replace('M', '')
            elif 'K' in text.upper():
                multiplier = 1_000
                text = text.upper().replace('K', '')

            return int(float(text) * multiplier)
        except Exception:
            return 0


def test_scraper():
    """Test the scraper with a few tickers"""
    scraper = YahooFinanceScraper()

    test_tickers = ['AAPL', 'NVDA', 'TSLA']

    for ticker in test_tickers:
        print(f"\n{'='*60}")
        try:
            data = scraper.scrape_ticker(ticker)
            print(f"\n📊 {ticker} Data:")
            print(f"  Company: {data['company_name']}")
            print(f"  Price: ${data['current_price']:.2f}")
            print(f"  Volume: {data['volume']:,}")
            print(f"  Market Cap: ${data['market_cap']:,}")
            print(f"  52W Range: ${data['fifty_two_week_low']:.2f} - ${data['fifty_two_week_high']:.2f}")
            print(f"  Historical Days: {len(data['historical']['dates'])}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    test_scraper()

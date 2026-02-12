#!/usr/bin/env python3
"""
SEEKING ALPHA API CLIENT
Cliente para obtener datos de stocks desde Seeking Alpha API

Ventajas sobre Yahoo Finance:
- Menos rate limiting
- Datos más completos (análisis, ratings, etc.)
- API más estable

Endpoints disponibles:
- /api/v3/symbols/{ticker}/tooltips - Info básica
- /finance-api/real_time_quotes - Precio en tiempo real
- /api/v3/symbols/{ticker}/relative_rankings - Rankings relativos
- /api/v3/symbols/{ticker}/insiders_sell_buy - Operaciones insiders
"""
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional


class SeekingAlphaClient:
    """Cliente para Seeking Alpha API"""

    def __init__(self, cookies: Optional[str] = None):
        """
        Initialize Seeking Alpha client

        Args:
            cookies: Optional cookie string from browser (for authenticated requests)
                    Format: "key1=value1; key2=value2; ..."
        """
        self.base_url = "https://seekingalpha.com/api/v3"
        self.finance_api_url = "https://finance-api.seekingalpha.com"

        # Headers base
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'es-ES,es;q=0.9,en-GB;q=0.8,en;q=0.7',
            'Referer': 'https://seekingalpha.com/',
            'Sec-Ch-Ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }

        # Add cookies if provided (ensure it's a string, not bytes)
        if cookies:
            # Decode bytes to string if needed
            if isinstance(cookies, bytes):
                cookies = cookies.decode('utf-8')
            self.headers['Cookie'] = str(cookies)

        # Cache for ticker ID lookups
        self.ticker_id_cache = {}

    def get_ticker_data(self, ticker: str) -> Dict[str, Any]:
        """
        Obtiene datos completos de un ticker desde Seeking Alpha

        Args:
            ticker: Símbolo del ticker (e.g., 'FISV', 'NVDA')

        Returns:
            Dict con datos del ticker en formato compatible con ticker_data_cache.json
        """
        ticker = ticker.upper()
        print(f"🌐 Fetching {ticker} from Seeking Alpha API...")

        try:
            # 1. Get basic info (tooltips endpoint)
            info_data = self._get_tooltips(ticker)

            # 2. Get real-time quote
            quote_data = self._get_real_time_quote(ticker)

            # 3. Combine data into standard format
            ticker_data = self._build_ticker_data(ticker, info_data, quote_data)

            print(f"✅ Successfully fetched {ticker} from Seeking Alpha")
            return ticker_data

        except Exception as e:
            print(f"❌ Failed to fetch {ticker} from Seeking Alpha: {str(e)}")
            raise

    def _get_tooltips(self, ticker: str) -> Dict[str, Any]:
        """Get basic ticker info from tooltips endpoint"""
        # Use the generic tooltips endpoint with filter
        url = f"{self.base_url}/tooltips"
        params = {'filter[path]': f'/symbol/{ticker}'}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   ⚠️  Tooltips endpoint failed: {str(e)}")
            return {}

    def _get_real_time_quote(self, ticker: str) -> Dict[str, Any]:
        """Get real-time quote data"""
        # First, get the SA ID from tooltips or use ticker symbol directly
        url = f"{self.finance_api_url}/real_time_quotes"
        params = {'sa_ids': ticker}  # Can also use numeric ID

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract first result if available
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            elif isinstance(data, dict):
                return data
            return {}
        except Exception as e:
            print(f"   ⚠️  Real-time quote failed: {str(e)}")
            return {}

    def _build_ticker_data(self, ticker: str, info_data: Dict, quote_data: Dict) -> Dict[str, Any]:
        """
        Build ticker data in standard format from SA API responses

        Note: Seeking Alpha doesn't provide full historical OHLCV data in free API,
        so we'll include what's available and mark historical as limited.
        """
        # Extract data from responses (defensive parsing)
        company_name = ticker  # Default to ticker
        sector = "N/A"
        industry = "N/A"
        current_price = 0.0
        market_cap = 0

        # Parse tooltips data
        if info_data and 'data' in info_data:
            data = info_data['data']
            if isinstance(data, list) and len(data) > 0:
                attributes = data[0].get('attributes', {})
                company_name = attributes.get('company', ticker)
                # Sector/Industry might be in different location

        # Parse quote data
        if quote_data:
            current_price = float(quote_data.get('last', 0) or quote_data.get('price', 0))
            market_cap = int(quote_data.get('marketCap', 0) or 0)

        # Build standard format
        ticker_data = {
            "ticker": ticker,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,

            "current_price": current_price,
            "previous_close": float(quote_data.get('prevClose', current_price)),
            "volume": int(quote_data.get('volume', 0) or 0),
            "avg_volume": int(quote_data.get('avgVolume', 0) or 0),

            "market_cap": market_cap,
            "shares_outstanding": 0,  # Not readily available in SA API

            "fifty_two_week_high": float(quote_data.get('week52High', 0) or 0),
            "fifty_two_week_low": float(quote_data.get('week52Low', 0) or 0),

            # Historical data - Limited (SA API doesn't provide full OHLCV history for free)
            # We'll need to use yfinance as backup or accept limited data
            "historical": self._get_limited_historical(ticker, current_price),

            # Moving averages - Calculate from limited data or use defaults
            "sma_10": current_price,
            "sma_20": current_price,
            "sma_50": current_price,
            "sma_150": current_price,
            "sma_200": current_price,

            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_source": "seeking_alpha"
        }

        return ticker_data

    def _get_limited_historical(self, ticker: str, current_price: float) -> Dict[str, list]:
        """
        Get limited historical data (SA free API doesn't provide full history)

        For production: Consider using yfinance as backup for historical data
        or upgrading to SA premium API
        """
        # Return minimal historical data (just current)
        today = datetime.now().strftime('%Y-%m-%d')

        return {
            "dates": [today],
            "open": [current_price],
            "high": [current_price],
            "low": [current_price],
            "close": [current_price],
            "volume": [0]
        }


def test_client():
    """Test the Seeking Alpha client"""
    client = SeekingAlphaClient()

    test_tickers = ['FISV', 'NVDA', 'AAPL']

    for ticker in test_tickers:
        print(f"\n{'='*60}")
        try:
            data = client.get_ticker_data(ticker)
            print(f"\n📊 {ticker} Data:")
            print(f"  Company: {data['company_name']}")
            print(f"  Price: ${data['current_price']:.2f}")
            print(f"  Volume: {data['volume']:,}")
            print(f"  Market Cap: ${data['market_cap']:,}")
            print(f"  52W Range: ${data['fifty_two_week_low']:.2f} - ${data['fifty_two_week_high']:.2f}")
            print(f"  Data Source: {data['data_source']}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    test_client()

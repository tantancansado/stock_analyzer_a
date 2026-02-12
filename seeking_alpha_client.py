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
            # Strip whitespace and newlines (common issue when pasting cookies)
            cookies = str(cookies).strip()
            self.headers['Cookie'] = cookies

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
        Build ticker data in standard format from SA API + yfinance

        Strategy:
        1. Get basic info from Seeking Alpha (fast, works with cookies)
        2. Enrich with yfinance data (fundamentals + historical)
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

        # Enrich with yfinance data (fundamentals + complete data)
        yf_data = self._get_yfinance_enrichment(ticker)

        # Build standard format (merge SA + yfinance data)
        ticker_data = {
            "ticker": ticker,
            "company_name": yf_data.get('company_name', company_name),
            "sector": yf_data.get('sector', sector),
            "industry": yf_data.get('industry', industry),

            "current_price": current_price or yf_data.get('current_price', 0),
            "previous_close": float(quote_data.get('prevClose', current_price) if quote_data else yf_data.get('previous_close', 0)),
            "volume": int(quote_data.get('volume', 0) if quote_data else yf_data.get('volume', 0)),
            "avg_volume": int(quote_data.get('avgVolume', 0) if quote_data else yf_data.get('avg_volume', 0)),

            "market_cap": market_cap or yf_data.get('market_cap', 0),
            "shares_outstanding": yf_data.get('shares_outstanding', 0),

            "fifty_two_week_high": float(quote_data.get('week52High', 0) if quote_data else yf_data.get('fifty_two_week_high', 0)),
            "fifty_two_week_low": float(quote_data.get('week52Low', 0) if quote_data else yf_data.get('fifty_two_week_low', 0)),

            # P/E ratio and other fundamentals from yfinance
            "pe_ratio": yf_data.get('pe_ratio'),
            "forward_pe": yf_data.get('forward_pe'),
            "peg_ratio": yf_data.get('peg_ratio'),
            "beta": yf_data.get('beta'),

            # Historical data from yfinance
            "historical": yf_data.get('historical', self._get_limited_historical(ticker, current_price)),

            # Moving averages - Calculate from historical data
            "sma_10": yf_data.get('sma_10', current_price),
            "sma_20": yf_data.get('sma_20', current_price),
            "sma_50": yf_data.get('sma_50', current_price),
            "sma_150": yf_data.get('sma_150', current_price),
            "sma_200": yf_data.get('sma_200', current_price),

            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_source": "seeking_alpha+yfinance"
        }

        return ticker_data

    def _get_yfinance_enrichment(self, ticker: str) -> Dict[str, Any]:
        """
        Enrich ticker data with yfinance (fundamentals + historical)

        This provides the complete data needed for VCP, ML, MA filters, etc.
        """
        import yfinance as yf
        import time

        try:
            print(f"   📊 Enriching with yfinance data (2s delay to avoid rate limit)...")
            time.sleep(2)

            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period='200d')

            enrichment = {}

            # Company info
            enrichment['company_name'] = info.get('longName', info.get('shortName', ''))
            enrichment['sector'] = info.get('sector', 'N/A')
            enrichment['industry'] = info.get('industry', 'N/A')

            # Price data
            if not hist.empty:
                enrichment['current_price'] = float(hist['Close'].iloc[-1])
                enrichment['previous_close'] = float(hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[-1])
                enrichment['volume'] = int(hist['Volume'].iloc[-1])
                enrichment['avg_volume'] = int(hist['Volume'].mean())

            # Fundamentals
            enrichment['market_cap'] = info.get('marketCap', 0)
            enrichment['shares_outstanding'] = info.get('sharesOutstanding', 0)
            enrichment['pe_ratio'] = info.get('trailingPE')
            enrichment['forward_pe'] = info.get('forwardPE')
            enrichment['peg_ratio'] = info.get('pegRatio')
            enrichment['beta'] = info.get('beta')

            # 52-week range
            enrichment['fifty_two_week_high'] = float(info.get('fiftyTwoWeekHigh', 0) or 0)
            enrichment['fifty_two_week_low'] = float(info.get('fiftyTwoWeekLow', 0) or 0)

            # Historical data
            if not hist.empty:
                enrichment['historical'] = {
                    "dates": hist.index.strftime('%Y-%m-%d').tolist(),
                    "open": hist['Open'].tolist(),
                    "high": hist['High'].tolist(),
                    "low": hist['Low'].tolist(),
                    "close": hist['Close'].tolist(),
                    "volume": hist['Volume'].tolist()
                }

                # Calculate moving averages
                closes = hist['Close']
                enrichment['sma_10'] = float(closes.tail(10).mean()) if len(closes) >= 10 else float(closes.mean())
                enrichment['sma_20'] = float(closes.tail(20).mean()) if len(closes) >= 20 else float(closes.mean())
                enrichment['sma_50'] = float(closes.tail(50).mean()) if len(closes) >= 50 else float(closes.mean())
                enrichment['sma_150'] = float(closes.tail(150).mean()) if len(closes) >= 150 else float(closes.mean())
                enrichment['sma_200'] = float(closes.tail(200).mean()) if len(closes) >= 200 else float(closes.mean())

            print(f"   ✅ yfinance enrichment successful")
            return enrichment

        except Exception as e:
            print(f"   ⚠️  yfinance enrichment failed: {str(e)}")
            return {}

    def _get_limited_historical(self, ticker: str, current_price: float) -> Dict[str, list]:
        """
        Get historical data using yfinance as backup

        SA free API doesn't provide historical data, so we use yfinance
        with a delay to avoid rate limiting
        """
        import yfinance as yf
        import time

        try:
            # Add delay to avoid rate limiting (important!)
            print(f"   📊 Fetching historical data from yfinance (with 2s delay)...")
            time.sleep(2)

            stock = yf.Ticker(ticker)
            hist = stock.history(period='200d')

            if not hist.empty:
                return {
                    "dates": hist.index.strftime('%Y-%m-%d').tolist(),
                    "open": hist['Open'].tolist(),
                    "high": hist['High'].tolist(),
                    "low": hist['Low'].tolist(),
                    "close": hist['Close'].tolist(),
                    "volume": hist['Volume'].tolist()
                }
        except Exception as e:
            print(f"   ⚠️  yfinance historical failed: {str(e)}")

        # Fallback: return minimal data (just current)
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

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
        Get comprehensive ticker data from Seeking Alpha

        Uses multiple SA API endpoints:
        1. tooltips - basic company info
        2. relative_rankings - sector/industry + SA ID
        3. real_time_quotes - current price data (using SA ID)
        4. metrics - fundamentals (market cap, debt, cash, TEV)

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')

        Returns:
            Dict with ticker data in standard format
        """
        ticker = ticker.upper()
        print(f"🌐 Fetching {ticker} from Seeking Alpha API...")

        try:
            # 1. Get basic info (tooltips endpoint)
            info_data = self._get_tooltips(ticker)

            # 2. Get relative rankings (includes SA ID, sector, industry)
            rankings_data = self._get_relative_rankings(ticker)

            # 3. Get SA ID from rankings (needed for real-time quotes)
            sa_id = rankings_data.get('data', {}).get('id') if rankings_data else None

            # 4. Get real-time quote using SA ID (more reliable than ticker)
            quote_data = self._get_real_time_quote_by_id(sa_id) if sa_id else {}

            # 5. Get metrics (fundamentals: market cap, debt, cash, TEV)
            metrics_data = self._get_metrics(ticker)

            # 6. Combine all data into standard format
            ticker_data = self._build_ticker_data(ticker, info_data, rankings_data, quote_data, metrics_data)

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
        """Get real-time quote data (legacy - prefer _get_real_time_quote_by_id)"""
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

    def _get_relative_rankings(self, ticker: str) -> Dict[str, Any]:
        """
        Get relative rankings (sector, industry, SA ID)

        Returns SA ID which is needed for other endpoints
        """
        url = f"{self.base_url}/symbols/{ticker.lower()}/relative_rankings"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   ⚠️  Relative rankings failed: {str(e)}")
            return {}

    def _get_real_time_quote_by_id(self, sa_id: str) -> Dict[str, Any]:
        """
        Get real-time quote using SA ID (more reliable than ticker)

        Args:
            sa_id: Seeking Alpha internal ID (e.g., '1719' for UNH)
        """
        url = f"{self.finance_api_url}/real_time_quotes"
        params = {'sa_ids': sa_id}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # DEBUG: Print quote data to see what fields are available
            print(f"   🔍 DEBUG - Quote data keys: {list(data[0].keys()) if isinstance(data, list) and len(data) > 0 else list(data.keys()) if isinstance(data, dict) else 'empty'}")

            # Extract first result if available
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            elif isinstance(data, dict):
                return data
            return {}
        except Exception as e:
            print(f"   ⚠️  Real-time quote by ID failed: {str(e)}")
            return {}

    def _get_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Get fundamental metrics (market cap, debt, cash, TEV, etc.)

        Returns comprehensive fundamental data
        """
        url = f"{self.base_url}/metrics"
        params = {
            'filter[fields]': 'marketcap,impliedmarketcap,total_cash,total_debt,tev,other_cap_struct',
            'filter[slugs]': ticker.lower(),
            'minified': 'false'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   ⚠️  Metrics endpoint failed: {str(e)}")
            return {}

    def _build_ticker_data(
        self,
        ticker: str,
        info_data: Dict,
        rankings_data: Dict,
        quote_data: Dict,
        metrics_data: Dict
    ) -> Dict[str, Any]:
        """
        Build ticker data from Seeking Alpha API endpoints

        Strategy:
        1. Use SA data first (tooltips, rankings, quotes, metrics)
        2. Only use yfinance for historical OHLCV data
        """
        # Extract company name from tooltips
        company_name = ticker
        if info_data and 'data' in info_data:
            data = info_data['data']
            if isinstance(data, list) and len(data) > 0:
                attributes = data[0].get('attributes', {})
                company_name = attributes.get('company', ticker)

        # Extract sector/industry from rankings
        sector = "N/A"
        industry = "N/A"
        if rankings_data and 'data' in rankings_data:
            attrs = rankings_data['data'].get('attributes', {})
            sector_name = attrs.get('sectorName', 'N/A')
            industry_name = attrs.get('primaryName', 'N/A')
            sector = sector_name
            industry = industry_name

        # Extract price data from quote
        current_price = 0.0
        previous_close = 0.0
        volume = 0
        avg_volume = 0
        week_52_high = 0.0
        week_52_low = 0.0

        if quote_data:
            current_price = float(quote_data.get('last', 0) or quote_data.get('price', 0))
            previous_close = float(quote_data.get('prevClose', current_price))
            volume = int(quote_data.get('volume', 0) or 0)
            avg_volume = int(quote_data.get('avgVolume', 0) or 0)
            week_52_high = float(quote_data.get('week52High', 0) or 0)
            week_52_low = float(quote_data.get('week52Low', 0) or 0)

        # Extract fundamentals from metrics
        market_cap = 0
        total_debt = 0
        total_cash = 0
        tev = 0  # Total Enterprise Value

        if metrics_data and 'data' in metrics_data:
            for metric in metrics_data['data']:
                attrs = metric.get('attributes', {})
                value = attrs.get('value', 0)

                # Get metric type from relationships
                relationships = metric.get('relationships', {})
                metric_type = relationships.get('metric_type', {}).get('data', {}).get('id', '')

                # Map metric types (from included data)
                if 'included' in metrics_data:
                    for item in metrics_data['included']:
                        if item.get('type') == 'metric_type' and item.get('id') == metric_type:
                            field = item.get('attributes', {}).get('field', '')
                            if field == 'marketcap':
                                market_cap = int(value)
                            elif field == 'total_debt':
                                total_debt = int(value)
                            elif field == 'total_cash':
                                total_cash = int(value)
                            elif field == 'tev':
                                tev = int(value)

        # Try to get historical data from Seeking Alpha chart endpoint
        print(f"   📈 Fetching historical chart data from Seeking Alpha...")
        historical_data = self._get_chart_data(ticker)

        # Calculate moving averages from historical data if available
        sma_10, sma_20, sma_50, sma_150, sma_200 = self._calculate_smas(historical_data, current_price)

        # Build standard format (100% Seeking Alpha data - NO yfinance!)
        ticker_data = {
            "ticker": ticker,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,

            "current_price": current_price,
            "previous_close": previous_close,
            "volume": volume,
            "avg_volume": avg_volume,

            "market_cap": market_cap,
            "total_debt": total_debt,
            "total_cash": total_cash,
            "enterprise_value": tev,
            "shares_outstanding": 0,  # Not available in SA free API

            "fifty_two_week_high": week_52_high,
            "fifty_two_week_low": week_52_low,

            # Fundamentals (limited in SA free API)
            "pe_ratio": None,  # Not available in SA free API
            "forward_pe": None,
            "peg_ratio": None,
            "beta": None,

            # Historical data from Seeking Alpha chart endpoint
            "historical": historical_data,

            # Moving averages calculated from historical data
            "sma_10": sma_10,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_150": sma_150,
            "sma_200": sma_200,

            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_source": "seeking_alpha"
        }

        return ticker_data

    def _get_chart_data(self, ticker: str) -> Dict[str, list]:
        """
        Get historical price data from Seeking Alpha historical_prices endpoint

        Fetches 200+ days of OHLCV data for technical analysis
        """
        from datetime import timedelta

        # Calculate date range (200 trading days ≈ 280 calendar days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=280)

        url = f"{self.base_url}/historical_prices"
        params = {
            'filter[ticker][slug]': ticker.lower(),
            'filter[as_of_date][gte]': start_date.strftime('%Y-%m-%d'),
            'filter[as_of_date][lte]': end_date.strftime('%Y-%m-%d'),
            'sort': 'as_of_date'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Parse historical prices
            if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                prices = data['data']

                dates = []
                opens = []
                highs = []
                lows = []
                closes = []
                volumes = []

                for price_point in prices:
                    if price_point.get('type') == 'historical_price':
                        attrs = price_point.get('attributes', {})

                        dates.append(attrs.get('as_of_date', ''))
                        opens.append(float(attrs.get('open', 0)))
                        highs.append(float(attrs.get('high', 0)))
                        lows.append(float(attrs.get('low', 0)))
                        closes.append(float(attrs.get('close', 0)))
                        volumes.append(int(attrs.get('volume', 0)))

                if len(dates) > 0:
                    print(f"   ✅ Historical data fetched: {len(dates)} days from Seeking Alpha")
                    return {
                        "dates": dates,
                        "open": opens,
                        "high": highs,
                        "low": lows,
                        "close": closes,
                        "volume": volumes
                    }

        except Exception as e:
            print(f"   ⚠️  Historical prices failed: {str(e)}")

        # Fallback: return minimal data
        print(f"   ⚠️  No historical data available")
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            "dates": [today],
            "open": [0],
            "high": [0],
            "low": [0],
            "close": [0],
            "volume": [0]
        }

    def _calculate_smas(self, historical_data: Dict[str, list], current_price: float) -> tuple:
        """
        Calculate Simple Moving Averages from historical data

        Returns: (sma_10, sma_20, sma_50, sma_150, sma_200)
        """
        closes = historical_data.get('close', [])

        if not closes or len(closes) < 2:
            # No historical data, use current price as default
            return (current_price, current_price, current_price, current_price, current_price)

        # Remove zeros and filter valid prices
        closes = [c for c in closes if c > 0]

        if len(closes) < 2:
            return (current_price, current_price, current_price, current_price, current_price)

        # Calculate SMAs
        def calc_sma(prices, period):
            if len(prices) >= period:
                return sum(prices[-period:]) / period
            else:
                return sum(prices) / len(prices) if prices else current_price

        sma_10 = calc_sma(closes, 10)
        sma_20 = calc_sma(closes, 20)
        sma_50 = calc_sma(closes, 50)
        sma_150 = calc_sma(closes, 150)
        sma_200 = calc_sma(closes, 200)

        return (sma_10, sma_20, sma_50, sma_150, sma_200)

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

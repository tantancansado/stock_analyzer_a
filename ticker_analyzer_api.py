#!/usr/bin/env python3
"""
TICKER ANALYZER API
Flask backend para analizar cualquier ticker con todo el pipeline

Ejecuta:
- VCP Analysis
- ML Scoring
- Fundamental Scoring
- Advanced Filters (MA, A/D, Float, Market Regime)
- Web Validation
- Investment Thesis Generation

Usage:
    python3 ticker_analyzer_api.py

API Endpoints:
    GET /api/analyze/<ticker>
    GET /api/health
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback
import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import finnhub (optional, fallback to yfinance if not available)
try:
    import finnhub
    FINNHUB_AVAILABLE = True
except ImportError:
    FINNHUB_AVAILABLE = False
    print("⚠️  Finnhub not installed. Using yfinance only.")

# Import our analysis modules
from moving_average_filter import MovingAverageFilter
from accumulation_distribution_filter import AccumulationDistributionFilter
from float_filter import FloatFilter
from market_regime_detector import MarketRegimeDetector
from opportunity_validator import OpportunityValidator

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Global cache for stock data (in-memory)
DATA_CACHE = {}
CACHE_DURATION = timedelta(minutes=10)  # Cache for 10 minutes

# Initialize Finnhub client if available
FINNHUB_CLIENT = None
FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
if FINNHUB_AVAILABLE and FINNHUB_API_KEY:
    FINNHUB_CLIENT = finnhub.Client(api_key=FINNHUB_API_KEY)
    print("✅ Finnhub client initialized")
else:
    print("⚠️  Finnhub not configured. Set FINNHUB_API_KEY in .env file")


def get_stock_data_from_finnhub(ticker: str) -> tuple:
    """
    Fetch stock data from Finnhub API

    Returns:
        tuple: (info_dict, history_dataframe, source='finnhub')
    """
    if not FINNHUB_CLIENT:
        raise ValueError("Finnhub client not initialized")

    print(f"📡 Fetching {ticker} from Finnhub...")

    # Get company profile
    profile = FINNHUB_CLIENT.company_profile2(symbol=ticker)

    # Get quote (current price)
    quote = FINNHUB_CLIENT.quote(ticker)

    # Get historical data (1 year of daily candles)
    end_date = int(datetime.now().timestamp())
    start_date = int((datetime.now() - timedelta(days=365)).timestamp())
    candles = FINNHUB_CLIENT.stock_candles(ticker, 'D', start_date, end_date)

    # Convert to pandas DataFrame (similar format to yfinance)
    if candles['s'] == 'ok':
        hist = pd.DataFrame({
            'Close': candles['c'],
            'High': candles['h'],
            'Low': candles['l'],
            'Open': candles['o'],
            'Volume': candles['v']
        }, index=pd.to_datetime(candles['t'], unit='s'))
    else:
        raise ValueError(f"No historical data from Finnhub for {ticker}")

    # Build info dict (similar format to yfinance)
    info = {
        'longName': profile.get('name', ticker),
        'symbol': ticker,
        'sector': profile.get('finnhubIndustry', 'N/A'),
        'industry': profile.get('finnhubIndustry', 'N/A'),
        'currentPrice': quote.get('c'),
        'previousClose': quote.get('pc'),
        'marketCap': profile.get('marketCapitalization', 0) * 1_000_000,  # Finnhub returns in millions
        'sharesOutstanding': profile.get('shareOutstanding', 0) * 1_000_000,
        'country': profile.get('country', 'US'),
        'currency': profile.get('currency', 'USD'),
        'exchange': profile.get('exchange', 'NASDAQ'),
        'website': profile.get('weburl', ''),
        'logo': profile.get('logo', ''),
        'longBusinessSummary': f"{profile.get('name', ticker)} - {profile.get('finnhubIndustry', 'N/A')}",
    }

    print(f"✅ Successfully fetched {ticker} from Finnhub")
    return (None, info, hist, 'finnhub')


def get_stock_data_from_yfinance(ticker: str, max_retries: int = 3) -> tuple:
    """
    Fetch stock data from yfinance (with retry logic)

    Returns:
        tuple: (stock_object, info_dict, history_dataframe, source='yfinance')
    """
    for attempt in range(max_retries):
        try:
            print(f"📡 Fetching {ticker} from yfinance (attempt {attempt + 1}/{max_retries})")

            # Add delay to avoid rate limiting
            if attempt > 0:
                delay = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                print(f"⏳ Waiting {delay}s before retry...")
                time.sleep(delay)

            # Fetch all data in ONE go
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period='1y')

            # Validate data
            if not info or hist.empty:
                raise ValueError(f"No data available for {ticker}")

            print(f"✅ Successfully fetched {ticker} from yfinance")
            return (stock, info, hist, 'yfinance')

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"❌ Error fetching {ticker}: {str(e)}, retrying...")
                continue
            else:
                print(f"❌ Failed to fetch {ticker} from yfinance after {max_retries} attempts")
                raise


def get_cached_stock_data(ticker: str, max_retries: int = 3):
    """
    Get stock data with caching and hybrid provider fallback

    Tries providers in order:
    1. Finnhub (if configured) - 60 calls/minute, reliable
    2. yfinance (fallback) - free but rate limited

    Returns:
        tuple: (stock_object_or_None, info_dict, history_dataframe, source)
    """
    cache_key = f"{ticker}_data"

    # Check cache first
    if cache_key in DATA_CACHE:
        cached_data, timestamp = DATA_CACHE[cache_key]
        if datetime.now() - timestamp < CACHE_DURATION:
            print(f"✓ Using cached data for {ticker} (source: {cached_data[3]})")
            return cached_data
        else:
            print(f"⚠️  Cache expired for {ticker}, fetching fresh data")

    # Try providers in order of preference
    errors = []

    # 1. Try Finnhub first (if configured)
    if FINNHUB_CLIENT:
        try:
            data = get_stock_data_from_finnhub(ticker)
            DATA_CACHE[cache_key] = (data, datetime.now())
            return data
        except Exception as e:
            error_msg = f"Finnhub failed: {str(e)}"
            print(f"⚠️  {error_msg}")
            errors.append(error_msg)

    # 2. Fallback to yfinance
    try:
        data = get_stock_data_from_yfinance(ticker, max_retries)
        DATA_CACHE[cache_key] = (data, datetime.now())
        return data
    except Exception as e:
        error_msg = f"yfinance failed: {str(e)}"
        print(f"❌ {error_msg}")
        errors.append(error_msg)

    # All providers failed
    raise ValueError(f"Failed to fetch {ticker} from all providers. Errors: {'; '.join(errors)}")


class TickerAnalyzer:
    """Comprehensive ticker analysis using all our systems"""

    def __init__(self):
        self.ma_filter = MovingAverageFilter()
        self.ad_filter = AccumulationDistributionFilter()
        self.float_filter = FloatFilter()
        self.market_detector = MarketRegimeDetector()
        self.validator = OpportunityValidator()

    def analyze(self, ticker: str) -> dict:
        """
        Run complete analysis on a ticker

        Returns:
            dict with complete analysis + investment thesis
        """
        print(f"\n{'='*70}")
        print(f"🎯 ANALYZING {ticker.upper()}")
        print(f"{'='*70}\n")

        ticker = ticker.upper()

        try:
            # ✨ GET ALL DATA ONCE (with caching + retry + hybrid providers)
            stock, info, hist, source = get_cached_stock_data(ticker)

            # Extract stock info (no extra API calls)
            stock_info = self._extract_stock_info(info, hist)
            stock_info['data_source'] = source  # Track which provider was used

            # Run market regime check (cached separately)
            market_regime = self.market_detector.detect_regime(save_report=False)

            # Run VCP analysis (reuses hist data)
            vcp_analysis = self._analyze_vcp_pattern_cached(hist)

            # Run ML scoring (reuses hist data)
            ml_score = self._calculate_ml_score_cached(hist)

            # Run fundamental analysis (reuses info data)
            fundamental_analysis = self._analyze_fundamentals(ticker, stock_info)

            # Run advanced filters (using cached data - NO API CALLS)
            ma_result = self._check_ma_filter_cached(ticker, hist)
            ad_result = self._check_ad_filter_cached(ticker, hist)
            float_result = self._check_float_filter_cached(ticker, info)

            # Run web validation (reuses stock_info)
            validation_result = self._run_validation(ticker, stock_info)

            # Calculate final score
            final_score = self._calculate_final_score(
                vcp_analysis, ml_score, fundamental_analysis,
                ma_result, ad_result, market_regime
            )

            # Generate investment thesis
            thesis = self._generate_investment_thesis(
                ticker, stock_info, vcp_analysis, ml_score,
                fundamental_analysis, ma_result, ad_result,
                float_result, market_regime, validation_result,
                final_score
            )

            # Build complete report
            report = {
                'ticker': ticker,
                'company_name': stock_info.get('company_name', ticker),
                'sector': stock_info.get('sector', 'N/A'),
                'current_price': stock_info.get('current_price'),
                'analyzed_at': datetime.now().isoformat(),

                # Final recommendation
                'final_score': final_score,
                'recommendation': thesis['recommendation'],
                'confidence': thesis['confidence'],

                # Investment thesis
                'thesis': thesis,

                # Component scores
                'vcp_analysis': vcp_analysis,
                'ml_score': ml_score,
                'fundamental_analysis': fundamental_analysis,

                # Filters
                'market_regime': {
                    'regime': market_regime['regime'],
                    'recommendation': market_regime['recommendation'],
                    'explanation': market_regime['explanation']
                },
                'ma_filter': ma_result,
                'ad_filter': ad_result,
                'float_filter': float_result,

                # Validation
                'validation': validation_result,

                # Stock info
                'stock_info': stock_info
            }

            print(f"\n✅ Analysis complete for {ticker}")
            return report

        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {str(e)}")
            traceback.print_exc()
            return {
                'ticker': ticker,
                'error': str(e),
                'traceback': traceback.format_exc()
            }

    def _get_stock_info(self, ticker: str) -> dict:
        """Get basic stock information from yfinance (OLD - uses extra API calls)"""
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period='1y')

        if hist.empty:
            raise ValueError(f"No data available for {ticker}")

        current_price = info.get('currentPrice') or hist['Close'].iloc[-1]

        return {
            'company_name': info.get('longName', ticker),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'current_price': float(round(current_price, 2)),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'peg_ratio': info.get('pegRatio'),
            'price_to_book': info.get('priceToBook'),
            'dividend_yield': info.get('dividendYield'),
            'beta': info.get('beta'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'avg_volume': info.get('averageVolume'),
            'description': info.get('longBusinessSummary', '')[:500]  # First 500 chars
        }

    def _extract_stock_info(self, info: dict, hist: pd.DataFrame) -> dict:
        """Extract stock info from already-fetched data (OPTIMIZED - no API calls)"""
        if hist.empty:
            raise ValueError("No historical data available")

        current_price = info.get('currentPrice') or hist['Close'].iloc[-1]

        return {
            'company_name': info.get('longName', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'current_price': float(round(current_price, 2)),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'peg_ratio': info.get('pegRatio'),
            'price_to_book': info.get('priceToBook'),
            'dividend_yield': info.get('dividendYield'),
            'beta': info.get('beta'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'avg_volume': info.get('averageVolume'),
            'description': info.get('longBusinessSummary', '')[:500]
        }

    def _analyze_vcp_pattern_cached(self, hist: pd.DataFrame) -> dict:
        """VCP analysis using cached historical data (OPTIMIZED - no API calls)"""
        try:
            if hist.empty or len(hist) < 200:
                return {'score': 50, 'pattern_detected': False, 'reason': 'Insufficient data'}

            # Simple volatility contraction check
            recent_vol = hist['Close'].tail(20).std()
            older_vol = hist['Close'].head(20).std()
            vol_ratio = recent_vol / older_vol if older_vol > 0 else 1.0

            # Check for consolidation
            recent_high = hist['High'].tail(50).max()
            recent_low = hist['Low'].tail(50).min()
            consolidation_range = (recent_high - recent_low) / recent_low * 100

            # Simple scoring
            score = 50
            if vol_ratio < 0.7:
                score += 20
            if consolidation_range < 30:
                score += 15
            if hist['Close'].iloc[-1] > hist['Close'].iloc[-20]:
                score += 15

            return {
                'score': int(min(100, score)),
                'pattern_detected': score >= 70,
                'vol_ratio': float(round(vol_ratio, 2)),
                'consolidation_range': float(round(consolidation_range, 1)),
                'reason': 'VCP-like pattern detected' if score >= 70 else 'No clear VCP pattern'
            }
        except Exception as e:
            return {'score': 50, 'pattern_detected': False, 'reason': f'Error: {str(e)}'}

    def _calculate_ml_score_cached(self, hist: pd.DataFrame) -> dict:
        """ML scoring using cached historical data (OPTIMIZED - no API calls)"""
        try:
            if hist.empty or len(hist) < 50:
                return {'score': 50, 'reason': 'Insufficient data'}

            close = hist['Close']

            # Price momentum (20-day)
            momentum_20d = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) >= 20 else 0

            # Trend strength (50-day MA)
            ma_50 = close.rolling(50).mean()
            above_ma_50 = close.iloc[-1] > ma_50.iloc[-1] if len(ma_50) >= 50 else False

            # Volume trend
            vol = hist['Volume']
            recent_vol = vol.tail(10).mean()
            baseline_vol = vol.mean()
            vol_ratio = recent_vol / baseline_vol if baseline_vol > 0 else 1.0

            # Calculate score
            score = 50
            if momentum_20d > 10:
                score += 20
            elif momentum_20d > 5:
                score += 10

            if above_ma_50:
                score += 15

            if vol_ratio > 1.2:
                score += 15

            return {
                'score': int(min(100, max(0, score))),
                'momentum_20d': float(round(momentum_20d, 1)),
                'above_ma_50': bool(above_ma_50),
                'volume_ratio': float(round(vol_ratio, 2)),
                'reason': 'Strong momentum' if score >= 70 else 'Weak momentum'
            }
        except Exception as e:
            return {'score': 50, 'reason': f'Error: {str(e)}'}

    def _check_ma_filter_cached(self, ticker: str, hist: pd.DataFrame) -> dict:
        """MA Filter using cached data (OPTIMIZED - no API calls)"""
        try:
            if hist.empty or len(hist) < 200:
                return {'ticker': ticker, 'passes': False, 'score': 0, 'reason': 'Insufficient data', 'details': {}}

            current_price = float(hist['Close'].iloc[-1])
            ma_50 = float(hist['Close'].rolling(50).mean().iloc[-1])
            ma_150 = float(hist['Close'].rolling(150).mean().iloc[-1])
            ma_200 = float(hist['Close'].rolling(200).mean().iloc[-1])
            ma_200_20d_ago = float(hist['Close'].rolling(200).mean().iloc[-20])
            ma_200_slope = ((ma_200 - ma_200_20d_ago) / ma_200_20d_ago * 100)

            week_52_high = float(hist['High'].max())
            week_52_low = float(hist['Low'].min())

            criterion_1 = current_price > ma_150 and current_price > ma_200
            criterion_2 = ma_150 > ma_200
            criterion_3 = ma_200_slope > 0
            criterion_4 = ma_50 > ma_150 > ma_200
            criterion_5 = current_price >= week_52_low * 1.30
            criterion_6 = current_price >= week_52_high * 0.75

            checks_passed = sum([criterion_1, criterion_2, criterion_3, criterion_4, criterion_5, criterion_6])
            score = int((checks_passed / 6) * 100)
            passes = criterion_1 and criterion_2 and criterion_3

            if not passes:
                reason = "Price below 150/200 MA" if not criterion_1 else "150 MA below 200 MA" if not criterion_2 else "200 MA declining"
            else:
                reason = f"Passes Minervini Template ({checks_passed}/6)"

            return {'ticker': ticker, 'passes': bool(passes), 'score': score, 'checks_passed': f"{checks_passed}/6", 'reason': reason}
        except Exception as e:
            return {'ticker': ticker, 'passes': False, 'score': 0, 'reason': f'Error: {str(e)}'}

    def _check_ad_filter_cached(self, ticker: str, hist: pd.DataFrame) -> dict:
        """A/D Filter using cached data (OPTIMIZED - no API calls)"""
        try:
            period_days = min(50, len(hist))
            if period_days < 20:
                return {'ticker': ticker, 'signal': 'UNKNOWN', 'score': 50, 'reason': 'Insufficient data'}

            df = hist.tail(period_days).copy()
            df['price_change'] = df['Close'].diff()
            df['is_up_day'] = df['price_change'] > 0
            df['is_down_day'] = df['price_change'] < 0

            up_days_volume = df[df['is_up_day']]['Volume'].sum()
            down_days_volume = df[df['is_down_day']]['Volume'].sum()
            total_volume = df['Volume'].sum()

            volume_ratio = up_days_volume / down_days_volume if down_days_volume > 0 else 10.0
            up_volume_pct = (up_days_volume / total_volume * 100) if total_volume > 0 else 50

            # Determine signal
            score = 50
            if volume_ratio >= 2.0:
                score += 30
                signal = 'STRONG_ACCUMULATION'
            elif volume_ratio >= 1.5:
                score += 20
                signal = 'ACCUMULATION'
            elif volume_ratio >= 1.0:
                score += 10
                signal = 'ACCUMULATION'
            elif volume_ratio >= 0.7:
                score -= 10
                signal = 'NEUTRAL'
            elif volume_ratio >= 0.5:
                score -= 20
                signal = 'DISTRIBUTION'
            else:
                score -= 30
                signal = 'STRONG_DISTRIBUTION'

            if up_volume_pct >= 65:
                score += 15
            elif up_volume_pct <= 35:
                score -= 15

            score = max(0, min(100, score))
            reason = f"{signal} ({volume_ratio:.1f}x ratio, {up_volume_pct:.0f}% up volume)"

            return {'ticker': ticker, 'signal': signal, 'score': int(score), 'reason': reason}
        except Exception as e:
            return {'ticker': ticker, 'signal': 'UNKNOWN', 'score': 50, 'reason': f'Error: {str(e)}'}

    def _check_float_filter_cached(self, ticker: str, info: dict) -> dict:
        """Float Filter using cached info (OPTIMIZED - no API calls)"""
        try:
            shares_outstanding = info.get('sharesOutstanding')
            float_shares = info.get('floatShares')
            shares = float_shares if float_shares else shares_outstanding

            if not shares or shares == 0:
                return {'ticker': ticker, 'passes': False, 'float_category': 'UNKNOWN', 'score': 50, 'reason': 'Float data not available'}

            shares_millions = shares / 1_000_000

            if shares_millions < 10:
                category, score, passes = 'MICRO_FLOAT', 85, True
            elif shares_millions < 25:
                category, score, passes = 'LOW_FLOAT', 100, True
            elif shares_millions < 50:
                category, score, passes = 'MEDIUM_FLOAT', 90, True
            elif shares_millions < 200:
                category, score, passes = 'HIGH_FLOAT', 60, False
            else:
                category, score, passes = 'MEGA_FLOAT', 30, False

            market_cap = info.get('marketCap')
            market_cap_billions = market_cap / 1_000_000_000 if market_cap else None

            return {
                'ticker': ticker,
                'passes': bool(passes),
                'float_category': category,
                'shares_outstanding': float(shares),
                'shares_outstanding_millions': float(round(shares_millions, 1)),
                'market_cap': float(market_cap) if market_cap else None,
                'market_cap_billions': float(round(market_cap_billions, 2)) if market_cap_billions else None,
                'score': int(score),
                'reason': f"{shares_millions:.1f}M shares - {category.replace('_', ' ').title()}"
            }
        except Exception as e:
            return {'ticker': ticker, 'passes': False, 'float_category': 'UNKNOWN', 'score': 50, 'reason': f'Error: {str(e)}'}

    def _analyze_vcp_pattern(self, ticker: str) -> dict:
        """Simplified VCP pattern analysis"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='6mo')

            if hist.empty:
                return {'score': 50, 'pattern_detected': False, 'reason': 'No data'}

            # Simple volatility contraction check
            recent_vol = hist['Close'].tail(20).std()
            older_vol = hist['Close'].head(20).std()

            vol_ratio = recent_vol / older_vol if older_vol > 0 else 1.0

            # Check for consolidation
            recent_high = hist['High'].tail(50).max()
            recent_low = hist['Low'].tail(50).min()
            consolidation_range = (recent_high - recent_low) / recent_low * 100

            # Simple scoring
            score = 50
            if vol_ratio < 0.7:
                score += 20  # Volatility contracting
            if consolidation_range < 30:
                score += 15  # Tight consolidation
            if hist['Close'].iloc[-1] > hist['Close'].iloc[-20]:
                score += 15  # Recent uptrend

            return {
                'score': int(min(100, score)),
                'pattern_detected': score >= 70,
                'vol_ratio': float(round(vol_ratio, 2)),
                'consolidation_range': float(round(consolidation_range, 1)),
                'reason': 'VCP-like pattern detected' if score >= 70 else 'No clear VCP pattern'
            }

        except Exception as e:
            return {'score': 50, 'pattern_detected': False, 'reason': f'Error: {str(e)}'}

    def _calculate_ml_score(self, ticker: str) -> dict:
        """Simplified ML scoring based on momentum/trend"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='3mo')

            if hist.empty:
                return {'score': 50, 'reason': 'No data'}

            # Calculate momentum indicators
            close = hist['Close']

            # Price momentum (20-day)
            momentum_20d = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) >= 20 else 0

            # Trend strength (50-day MA)
            ma_50 = close.rolling(50).mean()
            above_ma_50 = close.iloc[-1] > ma_50.iloc[-1] if len(ma_50) >= 50 else False

            # Volume trend
            vol = hist['Volume']
            recent_vol = vol.tail(10).mean()
            baseline_vol = vol.mean()
            vol_ratio = recent_vol / baseline_vol if baseline_vol > 0 else 1.0

            # Calculate score
            score = 50
            if momentum_20d > 10:
                score += 20
            elif momentum_20d > 5:
                score += 10

            if above_ma_50:
                score += 15

            if vol_ratio > 1.2:
                score += 15

            return {
                'score': int(min(100, max(0, score))),
                'momentum_20d': float(round(momentum_20d, 1)),
                'above_ma_50': bool(above_ma_50),
                'volume_ratio': float(round(vol_ratio, 2)),
                'reason': 'Strong momentum' if score >= 70 else 'Weak momentum'
            }

        except Exception as e:
            return {'score': 50, 'reason': f'Error: {str(e)}'}

    def _analyze_fundamentals(self, ticker: str, stock_info: dict) -> dict:
        """Analyze fundamental metrics"""
        score = 50
        reasons = []

        # P/E ratio check
        pe = stock_info.get('pe_ratio')
        if pe:
            if pe < 20:
                score += 10
                reasons.append('Low P/E ratio')
            elif pe > 40:
                score -= 10
                reasons.append('High P/E ratio')

        # PEG ratio check
        peg = stock_info.get('peg_ratio')
        if peg:
            if peg < 1.5:
                score += 10
                reasons.append('Good PEG ratio')
            elif peg > 2.5:
                score -= 10
                reasons.append('High PEG ratio')

        # Market cap check
        mcap = stock_info.get('market_cap')
        if mcap:
            if mcap > 10_000_000_000:  # >10B
                score += 5
                reasons.append('Large cap stability')

        return {
            'score': int(min(100, max(0, score))),
            'pe_ratio': pe,
            'peg_ratio': peg,
            'market_cap': mcap,
            'reasons': reasons
        }

    def _run_validation(self, ticker: str, stock_info: dict) -> dict:
        """Run web validation checks"""
        try:
            # Create minimal DataFrame for validator
            df = pd.DataFrame([{
                'ticker': ticker,
                'super_score_5d': 70,  # Dummy score
                'company_name': stock_info.get('company_name', ticker),
                'sector': stock_info.get('sector', 'N/A')
            }])

            validated = self.validator.validate_opportunities(df, top_n=1, save_report=False)

            if len(validated) > 0:
                result = validated.iloc[0]
                return {
                    'status': result.get('validation_status', 'UNKNOWN'),
                    'score': int(result.get('validation_score', 50)),
                    'reason': result.get('validation_reason', 'N/A'),
                    'price_vs_ath': result.get('price_vs_ath'),
                    'analyst_consensus': result.get('analyst_consensus', 'N/A')
                }
            else:
                return {'status': 'UNKNOWN', 'score': 50, 'reason': 'Validation failed'}

        except Exception as e:
            return {'status': 'ERROR', 'score': 50, 'reason': str(e)}

    def _calculate_final_score(self, vcp, ml, fundamental, ma, ad, market_regime) -> float:
        """Calculate final weighted score"""
        # Base score (VCP 40%, ML 30%, Fundamental 30%)
        base_score = (
            vcp['score'] * 0.40 +
            ml['score'] * 0.30 +
            fundamental['score'] * 0.30
        )

        # Apply filter penalties
        penalty = 0

        # Market regime penalty
        if market_regime['recommendation'] == 'AVOID':
            penalty += 15
        elif market_regime['recommendation'] == 'CAUTION':
            penalty += 5

        # MA filter penalty
        if not ma.get('passes', False):
            penalty += 20

        # A/D filter penalty
        ad_signal = ad.get('signal', 'NEUTRAL')
        if ad_signal == 'STRONG_DISTRIBUTION':
            penalty += 15
        elif ad_signal == 'DISTRIBUTION':
            penalty += 10

        final_score = max(0, base_score - penalty)
        return round(final_score, 1)

    def _generate_investment_thesis(self, ticker, stock_info, vcp, ml, fundamental,
                                    ma, ad, float_filter, market_regime, validation, final_score) -> dict:
        """Generate comprehensive investment thesis"""

        # Determine recommendation
        if final_score >= 70 and validation['status'] == 'BUY':
            recommendation = 'BUY'
            confidence = 'HIGH'
        elif final_score >= 60 and validation['status'] in ['BUY', 'HOLD']:
            recommendation = 'HOLD'
            confidence = 'MEDIUM'
        elif final_score >= 50:
            recommendation = 'HOLD'
            confidence = 'LOW'
        else:
            recommendation = 'AVOID'
            confidence = 'HIGH' if final_score < 40 else 'MEDIUM'

        # Build thesis narrative
        strengths = []
        weaknesses = []

        # Market regime
        if market_regime['recommendation'] == 'TRADE':
            strengths.append(f"Market in confirmed uptrend ({market_regime['regime']})")
        else:
            weaknesses.append(f"Market showing weakness ({market_regime['regime']})")

        # MA filter
        if ma.get('passes', False):
            strengths.append(f"Passes Minervini Trend Template ({ma.get('checks_passed', 'N/A')})")
        else:
            weaknesses.append(f"Fails MA filter: {ma.get('reason', 'Unknown')}")

        # A/D signal
        ad_signal = ad.get('signal', 'NEUTRAL')
        if ad_signal in ['STRONG_ACCUMULATION', 'ACCUMULATION']:
            strengths.append(f"Institutional accumulation detected ({ad_signal})")
        elif ad_signal in ['DISTRIBUTION', 'STRONG_DISTRIBUTION']:
            weaknesses.append(f"Institutional distribution detected ({ad_signal})")

        # Validation
        price_vs_ath = validation.get('price_vs_ath')
        if price_vs_ath and price_vs_ath < -15:
            strengths.append(f"Good pullback from ATH ({price_vs_ath:+.1f}%)")
        elif price_vs_ath and price_vs_ath > -5:
            weaknesses.append(f"Too close to ATH ({price_vs_ath:+.1f}%) - poor entry")

        # P/E ratio
        pe = stock_info.get('pe_ratio')
        if pe and pe < 25:
            strengths.append(f"Reasonable valuation (P/E: {pe:.1f})")
        elif pe and pe > 40:
            weaknesses.append(f"High valuation risk (P/E: {pe:.1f})")

        # Float
        float_cat = float_filter.get('float_category', 'UNKNOWN')
        if float_cat in ['LOW_FLOAT', 'MEDIUM_FLOAT']:
            strengths.append(f"Good float for momentum ({float_cat})")

        # Summary statement
        if recommendation == 'BUY':
            summary = f"{ticker} shows strong technical setup with {len(strengths)} positive factors. The stock passes professional trading criteria and appears well-positioned for upside."
        elif recommendation == 'HOLD':
            summary = f"{ticker} shows mixed signals. While there are {len(strengths)} positive factors, {len(weaknesses)} concerns suggest waiting for better entry or confirmation."
        else:
            summary = f"{ticker} currently fails key trading criteria with {len(weaknesses)} concerns. Risk/reward ratio is unfavorable at this time."

        return {
            'recommendation': recommendation,
            'confidence': confidence,
            'summary': summary,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'entry_timing': 'Good entry point' if validation['status'] == 'BUY' else 'Wait for pullback',
            'risk_level': 'LOW' if final_score >= 70 else 'MEDIUM' if final_score >= 50 else 'HIGH'
        }


# Flask API endpoints
analyzer = TickerAnalyzer()


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/api/analyze/<ticker>', methods=['GET'])
def analyze_ticker(ticker):
    """Analyze a ticker and return complete report"""
    try:
        print(f"\n🔍 API Request: Analyze {ticker.upper()}")
        report = analyzer.analyze(ticker)

        if 'error' in report:
            return jsonify({'error': report['error']}), 500

        return jsonify(report)

    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/')
def index():
    """Redirect to frontend"""
    return """
    <html>
        <head><title>Ticker Analyzer API</title></head>
        <body style="font-family: Arial; padding: 40px;">
            <h1>🎯 Ticker Analyzer API</h1>
            <p>Flask backend running successfully!</p>
            <h2>Endpoints:</h2>
            <ul>
                <li><code>GET /api/health</code> - Health check</li>
                <li><code>GET /api/analyze/&lt;ticker&gt;</code> - Analyze a ticker</li>
            </ul>
            <h2>Example:</h2>
            <a href="http://localhost:5001/api/analyze/NVDA" target="_blank">http://localhost:5001/api/analyze/NVDA</a>
            <p><strong>Frontend:</strong> Open <code>docs/ticker_analyzer.html</code> in your browser</p>
        </body>
    </html>
    """


def main():
    """Run Flask server"""
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'True') == 'True'

    print("\n" + "="*70)
    print("🚀 TICKER ANALYZER API SERVER")
    print("="*70)
    print("\n📡 Starting Flask server...")
    print("🌐 Frontend: Open docs/ticker_analyzer.html in your browser")
    print(f"🔧 API: http://localhost:{port}")
    print(f"🔧 Debug mode: {debug}")
    print("\n" + "="*70 + "\n")

    app.run(debug=debug, host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()

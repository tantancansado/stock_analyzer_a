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
from datetime import datetime
import traceback
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our analysis modules
from moving_average_filter import MovingAverageFilter
from accumulation_distribution_filter import AccumulationDistributionFilter
from float_filter import FloatFilter
from market_regime_detector import MarketRegimeDetector
from opportunity_validator import OpportunityValidator

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend


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
            # Get basic stock info
            stock_info = self._get_stock_info(ticker)

            # Run market regime check
            market_regime = self.market_detector.detect_regime(save_report=False)

            # Run VCP analysis (simplified - we don't have full VCP scanner access here)
            vcp_analysis = self._analyze_vcp_pattern(ticker)

            # Run ML scoring (simplified)
            ml_score = self._calculate_ml_score(ticker)

            # Run fundamental analysis
            fundamental_analysis = self._analyze_fundamentals(ticker, stock_info)

            # Run advanced filters
            ma_result = self.ma_filter.check_stock(ticker, verbose=True)
            ad_result = self.ad_filter.analyze_stock(ticker, verbose=True)
            float_result = self.float_filter.check_stock(ticker, verbose=True)

            # Run web validation
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
        """Get basic stock information from yfinance"""
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

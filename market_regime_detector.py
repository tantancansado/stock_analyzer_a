#!/usr/bin/env python3
"""
MARKET REGIME DETECTOR
Detecta la tendencia del mercado general (SPY/QQQ) para evitar operar contra corriente

Basado en CAN SLIM: "3 de cada 4 stocks siguen la dirección del mercado"

Regímenes:
- CONFIRMED_UPTREND: Mercado alcista confirmado (operar)
- UPTREND_PRESSURE: Tendencia bajo presión (precaución)
- CORRECTION: Mercado en corrección (evitar nuevas posiciones)
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import time


class MarketRegimeDetector:
    """Detecta régimen del mercado basado en SPY/QQQ"""

    def __init__(self):
        self.cache_dir = Path('cache/market_regime')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load ticker cache if available (for Railway deployment)
        self.ticker_cache = {}
        self._load_ticker_cache()

    def _load_ticker_cache(self):
        """Load ticker cache from JSON (optional, for Railway)"""
        cache_path = Path('docs/ticker_data_cache.json')
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    self.ticker_cache = json.load(f)
            except Exception:
                pass  # Silently fail, will use yfinance fallback

    def _get_historical_data(self, symbol: str) -> pd.DataFrame:
        """
        Get historical data from cache or yfinance

        Args:
            symbol: Ticker symbol (e.g., 'SPY', 'QQQ', '^VIX')

        Returns:
            DataFrame with OHLCV data or None
        """
        # 1. Try cache first (fast, no API calls)
        if symbol in self.ticker_cache:
            try:
                ticker_data = self.ticker_cache[symbol]
                historical = ticker_data.get('historical', {})

                if historical and historical.get('dates'):
                    hist = pd.DataFrame({
                        'Open': historical['open'],
                        'High': historical['high'],
                        'Low': historical['low'],
                        'Close': historical['close'],
                        'Volume': historical['volume']
                    }, index=pd.to_datetime(historical['dates']))
                    return hist
            except Exception:
                pass  # Fall through to yfinance

        # 2. Fallback to yfinance (may fail with rate limiting)
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1y')
            return hist if not hist.empty else None
        except Exception as e:
            print(f"   ⚠️  Failed to fetch {symbol}: {str(e)[:60]}")
            return None

    def detect_regime(self, save_report: bool = True) -> dict:
        """
        Detecta el régimen actual del mercado

        Returns:
            dict con:
            - regime: CONFIRMED_UPTREND | UPTREND_PRESSURE | CORRECTION
            - spy_status: análisis de SPY
            - qqq_status: análisis de QQQ
            - vix_level: nivel de VIX
            - recommendation: TRADE | CAUTION | AVOID
        """
        print("\n" + "="*70)
        print("📈 MARKET REGIME DETECTOR")
        print("="*70 + "\n")

        # Analyze SPY (S&P 500)
        spy_status = self._analyze_index('SPY', 'S&P 500')
        time.sleep(1)

        # Analyze QQQ (Nasdaq 100)
        qqq_status = self._analyze_index('QQQ', 'Nasdaq 100')
        time.sleep(1)

        # Analyze VIX (volatility)
        vix_level = self._analyze_vix()

        # Determine overall regime
        regime = self._determine_regime(spy_status, qqq_status, vix_level)

        result = {
            'detected_at': datetime.now().isoformat(),
            'regime': regime['regime'],
            'recommendation': regime['recommendation'],
            'confidence': regime['confidence'],
            'spy_status': spy_status,
            'qqq_status': qqq_status,
            'vix_level': vix_level,
            'explanation': regime['explanation']
        }

        if save_report:
            self._save_report(result)

        # Print summary
        self._print_summary(result)

        return result

    def _analyze_index(self, symbol: str, name: str) -> dict:
        """
        Analiza un índice (SPY o QQQ)

        Checks:
        - Price above 50/150/200 day MA
        - MA alignment (50 > 150 > 200)
        - 200 MA slope (trending up)
        - Recent price action
        """
        print(f"📊 Analyzing {name} ({symbol})...")

        try:
            # Try to get data from cache first
            hist = self._get_historical_data(symbol)

            if hist is None or hist.empty:
                return {'status': 'ERROR', 'reason': 'No data'}

            current_price = hist['Close'].iloc[-1]

            # Calculate MAs
            ma_50 = hist['Close'].rolling(50).mean().iloc[-1]
            ma_150 = hist['Close'].rolling(150).mean().iloc[-1]
            ma_200 = hist['Close'].rolling(200).mean().iloc[-1]

            # Calculate 200 MA slope (20-day change)
            ma_200_20d_ago = hist['Close'].rolling(200).mean().iloc[-20]
            ma_200_slope = ((ma_200 - ma_200_20d_ago) / ma_200_20d_ago * 100)

            # Data-quality gate: if price/MAs are NaN (partial or rate-limited
            # yfinance data), DO NOT invent a CORRECTION verdict from NaN — every
            # `price > ma` comparison silently becomes False, faking 0/5 checks.
            # Per CLAUDE.md: missing data → no score, never a fabricated number.
            import math
            if any(math.isnan(x) for x in (current_price, ma_50, ma_150, ma_200, ma_200_slope)):
                print(f"   ⚠️  {symbol}: precio/MAs NaN (datos insuficientes o rate-limit) — sin veredicto")
                return {'status': 'ERROR', 'reason': 'NaN in price/MA data'}

            # Check criteria
            above_50 = current_price > ma_50
            above_150 = current_price > ma_150
            above_200 = current_price > ma_200
            ma_aligned = ma_50 > ma_150 > ma_200
            ma_200_rising = ma_200_slope > 0

            # Calculate distance from 200 MA
            distance_200 = ((current_price - ma_200) / ma_200 * 100)

            # Determine status
            checks_passed = sum([above_50, above_150, above_200, ma_aligned, ma_200_rising])

            if checks_passed >= 4:
                status = 'STRONG_UPTREND'
            elif checks_passed >= 3:
                status = 'UPTREND'
            elif checks_passed >= 2:
                status = 'WEAK_UPTREND'
            else:
                status = 'CORRECTION'

            result = {
                'status': status,
                'current_price': float(round(current_price, 2)),
                'ma_50': float(round(ma_50, 2)),
                'ma_150': float(round(ma_150, 2)),
                'ma_200': float(round(ma_200, 2)),
                'above_50': bool(above_50),
                'above_150': bool(above_150),
                'above_200': bool(above_200),
                'ma_aligned': bool(ma_aligned),
                'ma_200_slope': float(round(ma_200_slope, 2)),
                'ma_200_rising': bool(ma_200_rising),
                'distance_from_200ma': float(round(distance_200, 2)),
                'checks_passed': f"{checks_passed}/5"
            }

            # Print details
            status_emoji = {'STRONG_UPTREND': '🟢', 'UPTREND': '🟡', 'WEAK_UPTREND': '🟠', 'CORRECTION': '🔴'}.get(status, '⚪')
            print(f"   {status_emoji} {status} ({checks_passed}/5 checks passed)")
            print(f"   Price: ${current_price:.2f} | 200 MA: ${ma_200:.2f} ({distance_200:+.1f}%)")
            print(f"   MA Slope: {ma_200_slope:+.2f}% | Aligned: {'✅' if ma_aligned else '❌'}")

            return result

        except Exception as e:
            print(f"   ❌ Error analyzing {symbol}: {str(e)}")
            return {'status': 'ERROR', 'reason': str(e)}

    def _analyze_vix(self) -> dict:
        """Analiza el VIX (volatility index)"""
        print("\n📊 Analyzing VIX (Volatility Index)...")

        try:
            # Try to get data from cache first
            hist = self._get_historical_data('^VIX')

            if hist is None or hist.empty:
                return {'level': 'UNKNOWN', 'value': None}

            current_vix = hist['Close'].iloc[-1]
            avg_vix_30d = hist['Close'].tail(30).mean()

            # VIX interpretation
            if current_vix < 15:
                level = 'LOW'  # Complacency
                interpretation = 'Low fear, market complacent'
            elif current_vix < 20:
                level = 'NORMAL'  # Healthy market
                interpretation = 'Normal volatility'
            elif current_vix < 30:
                level = 'ELEVATED'  # Caution
                interpretation = 'Elevated fear, use caution'
            else:
                level = 'HIGH'  # Panic
                interpretation = 'High fear, market stress'

            result = {
                'level': level,
                'value': round(current_vix, 2),
                'avg_30d': round(avg_vix_30d, 2),
                'interpretation': interpretation
            }

            level_emoji = {'LOW': '🟢', 'NORMAL': '🟡', 'ELEVATED': '🟠', 'HIGH': '🔴'}.get(level, '⚪')
            print(f"   {level_emoji} VIX: {current_vix:.2f} ({level}) - {interpretation}")

            return result

        except Exception as e:
            print(f"   ⚠️  Could not fetch VIX: {str(e)}")
            return {'level': 'UNKNOWN', 'value': None}

    def _determine_regime(self, spy_status: dict, qqq_status: dict, vix_level: dict) -> dict:
        """
        Determina el régimen general del mercado

        Logic:
        - CONFIRMED_UPTREND: Ambos índices STRONG/UPTREND + VIX < 30
        - UPTREND_PRESSURE: Uno débil o VIX elevado
        - CORRECTION: Ambos débiles o VIX alto
        """
        spy = spy_status.get('status', 'ERROR')
        qqq = qqq_status.get('status', 'ERROR')
        vix_value = vix_level.get('value')
        # Handle None case (VIX data not available)
        if vix_value is None:
            vix_value = 20  # Assume normal volatility if no data

        # Count strong uptrends
        strong_count = sum([
            spy in ['STRONG_UPTREND', 'UPTREND'],
            qqq in ['STRONG_UPTREND', 'UPTREND']
        ])

        # Check for corrections
        correction_count = sum([
            spy == 'CORRECTION',
            qqq == 'CORRECTION'
        ])

        # Data-quality gate: if BOTH indices failed to produce a verdict (ERROR),
        # we have no basis to call the regime. Report UNKNOWN rather than faking a
        # CORRECTION out of missing data — and never let that abort the pipeline.
        if spy == 'ERROR' and qqq == 'ERROR':
            return {
                'regime': 'UNKNOWN',
                'recommendation': 'CAUTION',
                'confidence': 'NONE',
                'explanation': 'No se pudieron obtener datos de SPY/QQQ (rate-limit o fallo de red). Régimen indeterminado — no se asume corrección.'
            }

        # Determine regime
        if strong_count == 2 and vix_value < 30:
            regime = 'CONFIRMED_UPTREND'
            recommendation = 'TRADE'
            confidence = 'HIGH'
            explanation = 'Both indices in uptrend, low volatility. Safe to trade.'

        elif strong_count >= 1 and correction_count == 0:
            regime = 'UPTREND_PRESSURE'
            recommendation = 'CAUTION'
            confidence = 'MEDIUM'
            explanation = 'Market showing some weakness. Be selective with new trades.'

        else:
            regime = 'CORRECTION'
            recommendation = 'AVOID'
            confidence = 'HIGH'
            explanation = 'Market in correction. Avoid new positions, protect capital.'

        # VIX override
        if vix_value > 30 and regime != 'CORRECTION':
            regime = 'UPTREND_PRESSURE'
            recommendation = 'CAUTION'
            explanation += ' High volatility detected.'

        return {
            'regime': regime,
            'recommendation': recommendation,
            'confidence': confidence,
            'explanation': explanation
        }

    def _save_report(self, result: dict):
        """Guarda reporte de régimen del mercado"""
        output_file = Path("docs/market_regime.json")

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n✅ Market regime report saved: {output_file}")

    def _print_summary(self, result: dict):
        """Imprime resumen del régimen detectado"""
        print("\n" + "="*70)
        print("📊 MARKET REGIME SUMMARY")
        print("="*70)

        regime = result['regime']
        recommendation = result['recommendation']

        regime_emoji = {
            'CONFIRMED_UPTREND': '🟢',
            'UPTREND_PRESSURE': '🟡',
            'CORRECTION': '🔴'
        }.get(regime, '⚪')

        rec_emoji = {
            'TRADE': '✅',
            'CAUTION': '⚠️',
            'AVOID': '❌'
        }.get(recommendation, '❓')

        print(f"\n{regime_emoji} Market Regime: {regime}")
        print(f"{rec_emoji} Recommendation: {recommendation}")
        print(f"📝 {result['explanation']}")
        print("\n" + "="*70)


def main():
    """Run standalone market regime detection.

    This step is INFORMATIONAL: it writes docs/market_regime.json and the
    recommendation gates signals downstream. It must never abort the pipeline —
    "AVOID" is a verdict to act on, not a build failure. Always exit 0; a non-zero
    exit only signals an actual crash (unhandled exception).
    """
    detector = MarketRegimeDetector()
    regime = detector.detect_regime()

    rec = regime['recommendation']
    if rec == 'AVOID':
        print("\n⚠️  WARNING: Market in correction - avoid new trades")
    elif rec == 'CAUTION':
        print("\n⚠️  CAUTION: Market under pressure - be selective")
    else:
        print("\n✅ GREEN LIGHT: Market in confirmed uptrend - safe to trade")
    return 0


if __name__ == '__main__':
    exit(main())

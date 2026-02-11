#!/usr/bin/env python3
"""
MARKET REGIME DETECTOR - Detecta Bull/Bear/Choppy markets
Ajusta scoring dinámicamente según condiciones del mercado
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Tuple
import json
from pathlib import Path


class MarketRegimeDetector:
    """Detecta el régimen actual del mercado"""

    def __init__(self):
        self.spy = yf.Ticker("SPY")
        self.vix = yf.Ticker("^VIX")
        self.cache_file = Path("data/market_regime_cache.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

    def get_market_regime(self, as_of_date: str = None) -> Dict:
        """
        Detecta el régimen del mercado en una fecha específica

        Args:
            as_of_date: Fecha para detectar régimen (YYYY-MM-DD). None = hoy

        Returns:
            Dict con régimen, indicators, y scoring weights
        """
        # Parse date
        if as_of_date:
            ref_date = pd.to_datetime(as_of_date)
        else:
            ref_date = pd.Timestamp.now()

        # Check cache
        cache = self._load_cache()
        cache_key = ref_date.strftime('%Y-%m-%d')

        if cache_key in cache:
            print(f"📂 Usando régimen cacheado para {cache_key}")
            return cache[cache_key]

        # Fetch SPY data (últimos 100 días para calcular SMA)
        start_date = (ref_date - timedelta(days=100)).strftime('%Y-%m-%d')
        end_date = ref_date.strftime('%Y-%m-%d')

        print(f"📊 Detectando régimen del mercado ({cache_key})...")

        try:
            # Get SPY data
            spy_data = yf.download("SPY", start=start_date, end=end_date, progress=False)

            if spy_data.empty:
                print("⚠️  No se pudo obtener datos de SPY")
                return self._get_default_regime()

            # Flatten multi-index if present
            if isinstance(spy_data.columns, pd.MultiIndex):
                spy_data.columns = spy_data.columns.get_level_values(0)

            # Calculate 50-day SMA
            spy_data['SMA50'] = spy_data['Close'].rolling(window=50).mean()

            # Get latest values
            latest = spy_data.iloc[-1]
            spy_price = latest['Close']
            spy_sma50 = latest['SMA50']

            # Get VIX
            vix_data = yf.download("^VIX", start=start_date, end=end_date, progress=False)

            if vix_data.empty:
                vix_value = 20  # Default
            else:
                if isinstance(vix_data.columns, pd.MultiIndex):
                    vix_data.columns = vix_data.columns.get_level_values(0)
                vix_value = vix_data['Close'].iloc[-1]

            # Detect regime
            regime_data = self._classify_regime(spy_price, spy_sma50, vix_value, ref_date)

            # Cache it
            cache[cache_key] = regime_data
            self._save_cache(cache)

            return regime_data

        except Exception as e:
            print(f"⚠️  Error detectando régimen: {e}")
            return self._get_default_regime()

    def _classify_regime(self, spy_price: float, spy_sma50: float, vix: float, date: pd.Timestamp) -> Dict:
        """Clasifica el régimen del mercado"""

        above_sma = spy_price > spy_sma50
        pct_above_sma = ((spy_price - spy_sma50) / spy_sma50) * 100

        # Classification logic
        if above_sma and vix < 20:
            regime = "BULL"
            confidence = "HIGH" if pct_above_sma > 2 and vix < 15 else "MEDIUM"
            weights = {'vcp': 50, 'ml': 30, 'fundamental': 20}
            color = "🟢"

        elif not above_sma and vix > 30:
            regime = "BEAR"
            confidence = "HIGH" if pct_above_sma < -2 and vix > 35 else "MEDIUM"
            weights = {'vcp': 20, 'ml': 30, 'fundamental': 50}
            color = "🔴"

        elif above_sma and vix >= 20 and vix <= 30:
            regime = "CAUTIOUS_BULL"
            confidence = "MEDIUM"
            weights = {'vcp': 40, 'ml': 35, 'fundamental': 25}
            color = "🟡"

        elif not above_sma and vix <= 30:
            regime = "CHOPPY"
            confidence = "MEDIUM"
            weights = {'vcp': 30, 'ml': 50, 'fundamental': 20}
            color = "🟠"

        else:
            regime = "CHOPPY"
            confidence = "LOW"
            weights = {'vcp': 33, 'ml': 34, 'fundamental': 33}
            color = "⚪"

        return {
            'regime': regime,
            'confidence': confidence,
            'date': date.strftime('%Y-%m-%d'),
            'indicators': {
                'spy_price': round(spy_price, 2),
                'spy_sma50': round(spy_sma50, 2),
                'pct_above_sma': round(pct_above_sma, 2),
                'vix': round(vix, 2),
            },
            'weights': weights,
            'emoji': color,
            'description': self._get_regime_description(regime)
        }

    def _get_regime_description(self, regime: str) -> str:
        """Descripción del régimen"""
        descriptions = {
            'BULL': 'Mercado alcista - Favorece VCP breakouts y momentum',
            'BEAR': 'Mercado bajista - Favorece fundamentales sólidos',
            'CAUTIOUS_BULL': 'Alcista con cautela - Volatilidad moderada',
            'CHOPPY': 'Mercado lateral - Favorece ML predictions y selectividad'
        }
        return descriptions.get(regime, 'Régimen desconocido')

    def _get_default_regime(self) -> Dict:
        """Régimen por defecto si no se puede detectar"""
        return {
            'regime': 'UNKNOWN',
            'confidence': 'LOW',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'indicators': {
                'spy_price': 0,
                'spy_sma50': 0,
                'pct_above_sma': 0,
                'vix': 20,
            },
            'weights': {'vcp': 40, 'ml': 30, 'fundamental': 30},  # Default weights
            'emoji': '⚪',
            'description': 'No se pudo detectar régimen - usando defaults'
        }

    def _load_cache(self) -> Dict:
        """Carga cache de regímenes"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self, cache: Dict):
        """Guarda cache de regímenes"""
        with open(self.cache_file, 'w') as f:
            json.dump(cache, f, indent=2)

    def print_regime_summary(self, regime_data: Dict):
        """Imprime resumen del régimen"""
        print("\n" + "=" * 80)
        print(f"{regime_data['emoji']} MARKET REGIME: {regime_data['regime']}")
        print("=" * 80)
        print(f"📅 Date: {regime_data['date']}")
        print(f"🎯 Confidence: {regime_data['confidence']}")
        print(f"📝 {regime_data['description']}")
        print(f"\n📊 Indicators:")
        for key, value in regime_data['indicators'].items():
            print(f"   {key}: {value}")
        print(f"\n⚖️  Scoring Weights:")
        for key, value in regime_data['weights'].items():
            print(f"   {key}: {value}%")
        print("=" * 80)


def main():
    """Test regime detection"""
    detector = MarketRegimeDetector()

    # Test today
    print("\n🔍 Detectando régimen ACTUAL:")
    regime_today = detector.get_market_regime()
    detector.print_regime_summary(regime_today)

    # Test historical dates
    test_dates = [
        "2025-11-13",  # 3 meses atrás
        "2025-08-15",  # 6 meses atrás
        "2025-02-11",  # 1 año atrás
    ]

    for date in test_dates:
        print(f"\n🔍 Detectando régimen para {date}:")
        regime = detector.get_market_regime(as_of_date=date)
        detector.print_regime_summary(regime)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
SECTOR ROTATION DETECTOR
Detecta rotaciones sectoriales en tiempo real para timing optimal de entrada/salida
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
from collections import defaultdict


class SectorRotationDetector:
    """Detector de rotaciones sectoriales en tiempo real"""

    def __init__(self, lookback_days: int = 90):
        """
        Args:
            lookback_days: Días hacia atrás para analizar momentum (default: 90)
        """
        self.lookback_days = lookback_days
        self.sectors_data = {}
        self.rotation_signals = []
        self.cache_dir = Path("data/sector_rotation_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # DJ Sectorial tickers
        self.dj_sectors = self._load_dj_sectors()

    def _load_dj_sectors(self) -> Dict:
        """Carga mapeo de sectores usando SPDR Sector ETFs"""
        # SPDR Sector ETFs - líquidos y accesibles vía yfinance
        sectors = {
            'XLK': 'Technology',
            'XLF': 'Financials',
            'XLV': 'Healthcare',
            'XLY': 'Consumer Discretionary',
            'XLI': 'Industrials',
            'XLE': 'Energy',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLU': 'Utilities',
            'XLC': 'Communication Services',
            'XLP': 'Consumer Staples'
        }
        return sectors

    def get_sector_price_history(self, ticker: str, days: int = None) -> pd.DataFrame:
        """
        Obtiene histórico de precios para sector DJ

        Args:
            ticker: DJ sector ticker (ej: DJUSTC)
            days: Días de histórico (None = usar lookback_days)

        Returns:
            DataFrame con precios OHLCV
        """
        if days is None:
            days = self.lookback_days

        cache_file = self.cache_dir / f"{ticker}_{days}d.csv"

        # Check cache (válido por 1 día)
        if cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age.total_seconds() < 86400:  # 24 horas
                return pd.read_csv(cache_file, index_col=0, parse_dates=True)

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # +10 margen

            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if not df.empty:
                # Handle MultiIndex columns (yfinance sometimes returns ticker in column names)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                df.index.name = 'Date'
                df.to_csv(cache_file)
                return df
        except Exception as e:
            print(f"   ⚠️  Error descargando {ticker}: {e}")

        return pd.DataFrame()

    def calculate_momentum_velocity(self, prices: pd.DataFrame,
                                   short_period: int = 10,
                                   long_period: int = 50) -> float:
        """
        Calcula velocidad de momentum (rate of change del momentum)

        Args:
            prices: DataFrame con precios
            short_period: Período corto para momentum
            long_period: Período largo para momentum

        Returns:
            Momentum velocity (-100 a +100)
        """
        if len(prices) < long_period:
            return 0.0

        closes = prices['Close']

        # Momentum short term (10 días)
        momentum_short = ((float(closes.iloc[-1]) - float(closes.iloc[-short_period])) /
                         float(closes.iloc[-short_period])) * 100

        # Momentum long term (50 días)
        momentum_long = ((float(closes.iloc[-1]) - float(closes.iloc[-long_period])) /
                        float(closes.iloc[-long_period])) * 100

        # Velocity = diferencia de momentums (aceleración)
        velocity = momentum_short - momentum_long

        return float(velocity)

    def calculate_relative_strength(self, sector_prices: pd.DataFrame,
                                   market_prices: pd.DataFrame) -> float:
        """
        Calcula relative strength vs market (SPY)

        Args:
            sector_prices: Precios del sector
            market_prices: Precios del market (SPY)

        Returns:
            Relative strength score (0-100)
        """
        if sector_prices.empty or market_prices.empty:
            return 50.0

        # Align dates
        common_dates = sector_prices.index.intersection(market_prices.index)
        if len(common_dates) < 20:
            return 50.0

        sector_aligned = sector_prices.loc[common_dates, 'Close']
        market_aligned = market_prices.loc[common_dates, 'Close']

        # Calcular returns
        sector_return = ((float(sector_aligned.iloc[-1]) - float(sector_aligned.iloc[0])) /
                        float(sector_aligned.iloc[0])) * 100
        market_return = ((float(market_aligned.iloc[-1]) - float(market_aligned.iloc[0])) /
                        float(market_aligned.iloc[0])) * 100

        # Relative strength
        if market_return != 0:
            relative_strength = (sector_return / market_return) * 50 + 50
        else:
            relative_strength = 50.0

        # Clamp 0-100
        return max(0, min(100, relative_strength))

    def detect_momentum_change(self, current_velocity: float,
                               previous_velocity: float,
                               threshold: float = 2.0) -> str:
        """
        Detecta cambio de momentum

        Args:
            current_velocity: Velocity actual
            previous_velocity: Velocity previa
            threshold: Umbral para considerar cambio significativo

        Returns:
            'accelerating', 'decelerating', 'stable'
        """
        delta = current_velocity - previous_velocity

        if abs(delta) < threshold:
            return 'stable'
        elif delta > 0:
            return 'accelerating'
        else:
            return 'decelerating'

    def classify_rotation_status(self, velocity: float,
                                relative_strength: float) -> Dict:
        """
        Clasifica estado de rotación del sector

        Args:
            velocity: Momentum velocity
            relative_strength: RS vs market

        Returns:
            Dict con status y señales
        """
        # Quadrant analysis (Mark Minervini style)
        # RS > 50 = Outperforming market
        # Velocity > 0 = Accelerating momentum

        if relative_strength > 60 and velocity > 3:
            status = 'LEADING'
            signal = 'BUY'
            strength = 'STRONG'
        elif relative_strength > 50 and velocity > 0:
            status = 'IMPROVING'
            signal = 'ACCUMULATE'
            strength = 'MODERATE'
        elif relative_strength < 40 and velocity < -3:
            status = 'LAGGING'
            signal = 'AVOID'
            strength = 'WEAK'
        elif relative_strength < 50 and velocity < 0:
            status = 'WEAKENING'
            signal = 'REDUCE'
            strength = 'MODERATE'
        else:
            status = 'NEUTRAL'
            signal = 'HOLD'
            strength = 'NEUTRAL'

        return {
            'status': status,
            'signal': signal,
            'strength': strength,
            'velocity': velocity,
            'relative_strength': relative_strength
        }

    def scan_all_sectors(self) -> List[Dict]:
        """
        Escanea todos los sectores DJ y detecta rotaciones

        Returns:
            Lista de sectores con datos de rotación
        """
        print("\n🔄 SECTOR ROTATION SCAN")
        print("=" * 70)

        # Get market benchmark (SPY)
        print("   📊 Descargando benchmark (SPY)...")
        market_prices = self.get_sector_price_history('SPY', days=self.lookback_days)

        results = []

        for dj_ticker, sector_name in self.dj_sectors.items():
            print(f"   Analizando {sector_name} ({dj_ticker})...", end='\r')

            # Get sector prices
            sector_prices = self.get_sector_price_history(dj_ticker)

            if sector_prices.empty:
                continue

            # Calculate current metrics
            current_velocity = self.calculate_momentum_velocity(sector_prices)

            # Calculate previous velocity (7 días atrás)
            if len(sector_prices) > 7:
                prev_prices = sector_prices.iloc[:-7]
                previous_velocity = self.calculate_momentum_velocity(prev_prices)
            else:
                previous_velocity = current_velocity

            # Relative strength
            relative_strength = self.calculate_relative_strength(sector_prices, market_prices)

            # Momentum change
            momentum_change = self.detect_momentum_change(current_velocity, previous_velocity)

            # Rotation status
            rotation = self.classify_rotation_status(current_velocity, relative_strength)

            # Recent performance
            recent_return = ((float(sector_prices['Close'].iloc[-1]) -
                            float(sector_prices['Close'].iloc[-30])) /
                           float(sector_prices['Close'].iloc[-30])) * 100 if len(sector_prices) >= 30 else 0

            result = {
                'sector': sector_name,
                'dj_ticker': dj_ticker,
                'status': rotation['status'],
                'signal': rotation['signal'],
                'strength': rotation['strength'],
                'velocity': round(current_velocity, 2),
                'relative_strength': round(relative_strength, 1),
                'momentum_change': momentum_change,
                'recent_return_30d': round(recent_return, 2),
                'current_price': round(float(sector_prices['Close'].iloc[-1]), 2),
                'timestamp': datetime.now().isoformat()
            }

            results.append(result)

        print(f"\n   ✅ {len(results)} sectores analizados")

        return results

    def identify_rotation_opportunities(self, results: List[Dict]) -> Dict:
        """
        Identifica oportunidades de rotación

        Args:
            results: Lista de resultados del scan

        Returns:
            Dict con oportunidades clasificadas
        """
        opportunities = {
            'leaders': [],      # Sectores LEADING - máxima prioridad
            'emerging': [],     # Sectores IMPROVING - entrando en fortaleza
            'weakening': [],    # Sectores WEAKENING - considerar salida
            'laggards': []      # Sectores LAGGING - evitar
        }

        for sector in results:
            if sector['status'] == 'LEADING':
                opportunities['leaders'].append(sector)
            elif sector['status'] == 'IMPROVING':
                opportunities['emerging'].append(sector)
            elif sector['status'] == 'WEAKENING':
                opportunities['weakening'].append(sector)
            elif sector['status'] == 'LAGGING':
                opportunities['laggards'].append(sector)

        # Sort by velocity
        opportunities['leaders'].sort(key=lambda x: x['velocity'], reverse=True)
        opportunities['emerging'].sort(key=lambda x: x['velocity'], reverse=True)
        opportunities['weakening'].sort(key=lambda x: x['velocity'])
        opportunities['laggards'].sort(key=lambda x: x['velocity'])

        return opportunities

    def generate_rotation_alerts(self, results: List[Dict]) -> List[Dict]:
        """
        Genera alertas de rotación sectorial

        Args:
            results: Lista de resultados del scan

        Returns:
            Lista de alertas
        """
        alerts = []

        for sector in results:
            alert = None

            # Alert: Sector acelerando fuerte
            if sector['momentum_change'] == 'accelerating' and sector['velocity'] > 5:
                alert = {
                    'type': 'ROTATION_IN',
                    'severity': 'HIGH',
                    'sector': sector['sector'],
                    'message': f"💚 {sector['sector']} acelerando fuerte (velocity: {sector['velocity']})",
                    'action': 'CONSIDERAR ENTRADA en tickers de este sector'
                }

            # Alert: Sector desacelerando
            elif sector['momentum_change'] == 'decelerating' and sector['velocity'] < -3:
                alert = {
                    'type': 'ROTATION_OUT',
                    'severity': 'MEDIUM',
                    'sector': sector['sector'],
                    'message': f"🔴 {sector['sector']} perdiendo momentum (velocity: {sector['velocity']})",
                    'action': 'CONSIDERAR SALIDA de posiciones en este sector'
                }

            # Alert: Sector emergiendo desde weakness
            elif (sector['status'] == 'IMPROVING' and
                  sector['momentum_change'] == 'accelerating'):
                alert = {
                    'type': 'EARLY_ROTATION',
                    'severity': 'MEDIUM',
                    'sector': sector['sector'],
                    'message': f"⚡ {sector['sector']} emergiendo (RS: {sector['relative_strength']})",
                    'action': 'EARLY ENTRY OPPORTUNITY - sector saliendo de debilidad'
                }

            if alert:
                alert['timestamp'] = sector['timestamp']
                alerts.append(alert)

        return alerts

    def save_results(self, results: List[Dict], opportunities: Dict,
                    alerts: List[Dict], output_dir: str = "docs/sector_rotation"):
        """
        Guarda resultados del scan

        Args:
            results: Resultados completos
            opportunities: Oportunidades clasificadas
            alerts: Alertas generadas
            output_dir: Directorio de salida
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save full results
        results_file = output_path / f"scan_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'results': results,
                'opportunities': opportunities,
                'alerts': alerts
            }, f, indent=2)

        # Save CSV
        df = pd.DataFrame(results)
        csv_file = output_path / f"scan_{timestamp}.csv"
        df.to_csv(csv_file, index=False)

        # Save latest (overwrite)
        latest_file = output_path / "latest_scan.json"
        with open(latest_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'results': results,
                'opportunities': opportunities,
                'alerts': alerts
            }, f, indent=2)

        print(f"\n💾 Resultados guardados:")
        print(f"   JSON: {results_file}")
        print(f"   CSV: {csv_file}")
        print(f"   Latest: {latest_file}")

    def print_summary(self, results: List[Dict], opportunities: Dict,
                     alerts: List[Dict]):
        """Imprime resumen de rotaciones"""
        print("\n📊 SECTOR ROTATION SUMMARY")
        print("=" * 70)

        print(f"\n🏆 LEADING SECTORS ({len(opportunities['leaders'])}):")
        for sector in opportunities['leaders']:
            print(f"   ✅ {sector['sector']:25} | "
                  f"Velocity: {sector['velocity']:+6.2f} | "
                  f"RS: {sector['relative_strength']:5.1f} | "
                  f"30D: {sector['recent_return_30d']:+6.2f}%")

        print(f"\n⚡ EMERGING SECTORS ({len(opportunities['emerging'])}):")
        for sector in opportunities['emerging']:
            print(f"   📈 {sector['sector']:25} | "
                  f"Velocity: {sector['velocity']:+6.2f} | "
                  f"RS: {sector['relative_strength']:5.1f} | "
                  f"30D: {sector['recent_return_30d']:+6.2f}%")

        print(f"\n⚠️  WEAKENING SECTORS ({len(opportunities['weakening'])}):")
        for sector in opportunities['weakening']:
            print(f"   📉 {sector['sector']:25} | "
                  f"Velocity: {sector['velocity']:+6.2f} | "
                  f"RS: {sector['relative_strength']:5.1f} | "
                  f"30D: {sector['recent_return_30d']:+6.2f}%")

        if alerts:
            print(f"\n🚨 ROTATION ALERTS ({len(alerts)}):")
            for alert in alerts:
                icon = '💚' if alert['type'] == 'ROTATION_IN' else '🔴' if alert['type'] == 'ROTATION_OUT' else '⚡'
                print(f"   {icon} {alert['message']}")
                print(f"      → {alert['action']}")


def main():
    """Main execution"""
    detector = SectorRotationDetector(lookback_days=90)

    print("🔄 SECTOR ROTATION DETECTOR - Real-time Analysis")
    print("=" * 70)

    # Scan all sectors
    results = detector.scan_all_sectors()

    # Identify opportunities
    opportunities = detector.identify_rotation_opportunities(results)

    # Generate alerts
    alerts = detector.generate_rotation_alerts(results)

    # Print summary
    detector.print_summary(results, opportunities, alerts)

    # Save results
    detector.save_results(results, opportunities, alerts)

    print("\n✅ Sector rotation scan completado!")


if __name__ == "__main__":
    main()

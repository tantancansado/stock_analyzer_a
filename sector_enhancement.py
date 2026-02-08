#!/usr/bin/env python3
"""
SECTOR ENHANCEMENT SYSTEM
Smart integration con DJ Sectorial para mejorar el scoring 4D

Features:
- Sector momentum detection
- Tier boost para sectores fuertes
- Diversificación automática
- Mapeo de tickers a sectores
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
import json

SECTOR_CACHE_FILE = Path("data/sector_cache.json")

# Mapeo de sectores Yahoo Finance → ticker DJ Sectorial
# Verificado contra reports/dj_sectorial_analysis.csv
DJ_SECTOR_MAP = {
    'Technology': 'DJUSTC',           # Dow Jones U.S. Technology Index
    'Financial Services': 'DJUSFI',   # Dow Jones U.S. Financial Services Index
    'Healthcare': 'DJUSHC',           # Dow Jones U.S. Health Care Index
    'Consumer Cyclical': 'DJUSGT',    # Dow Jones U.S. General Retailers Index
    'Communication Services': 'DJUSTL',  # Dow Jones U.S. Telecommunications Index
    'Industrials': 'DJUSIG',          # Dow Jones U.S. Industrial Goods & Services Index
    'Consumer Defensive': 'DJUSFB',   # Dow Jones U.S. Food & Beverage Index
    'Energy': 'DJUSEN',               # Dow Jones U.S. Oil & Gas Index
    'Real Estate': 'DJUSRE',          # Dow Jones U.S. Real Estate Index
    'Basic Materials': 'DJUSBS',      # Dow Jones U.S. Basic Resources Index
    'Utilities': 'DJUSUT',            # Dow Jones U.S. Utilities Index
}


class SectorEnhancement:
    """Sistema de mejora sectorial inteligente"""

    def __init__(self):
        self.sector_data = None
        self.sector_rankings = {}
        self.ticker_to_sector = {}
        self._load_sector_cache()

    def _load_sector_cache(self):
        """Carga caché de ticker→sector desde disco y re-aplica el mapa actualizado"""
        if SECTOR_CACHE_FILE.exists():
            with open(SECTOR_CACHE_FILE, 'r') as f:
                self.ticker_to_sector = json.load(f)
            # Re-mapear dj_ticker con el mapa actual (corrige entradas desactualizadas)
            updated = False
            for ticker, info in self.ticker_to_sector.items():
                sector = info.get('sector', '')
                correct_dj = DJ_SECTOR_MAP.get(sector)
                if info.get('dj_ticker') != correct_dj:
                    info['dj_ticker'] = correct_dj
                    updated = True
            if updated:
                self._save_sector_cache()

    def _save_sector_cache(self):
        """Guarda caché de ticker→sector en disco"""
        SECTOR_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SECTOR_CACHE_FILE, 'w') as f:
            json.dump(self.ticker_to_sector, f)

    def prefetch_sectors(self, tickers, batch_size=20, delay=1.0):
        """
        Pre-carga sectores para una lista de tickers en lotes
        Solo consulta los que no están en caché
        """
        import time
        missing = [t for t in tickers if t not in self.ticker_to_sector]

        if not missing:
            print(f"✅ Todos los sectores en caché ({len(tickers)} tickers)")
            return

        print(f"📡 Descargando sectores para {len(missing)} tickers (en lotes de {batch_size})...")
        for i in range(0, len(missing), batch_size):
            batch = missing[i:i + batch_size]
            for ticker in batch:
                try:
                    info = yf.Ticker(ticker).info
                    sector = info.get('sector', '')
                    industry = info.get('industry', '')
                    self.ticker_to_sector[ticker] = {
                        'sector': sector,
                        'industry': industry,
                        'dj_ticker': DJ_SECTOR_MAP.get(sector)
                    }
                except Exception:  # noqa: BLE001
                    self.ticker_to_sector[ticker] = {'sector': '', 'industry': '', 'dj_ticker': None}
            print(f"   Lote {i//batch_size + 1}/{(len(missing)-1)//batch_size + 1} completado")
            if i + batch_size < len(missing):
                time.sleep(delay)

        self._save_sector_cache()
        print("✅ Sectores descargados y guardados en caché")

    def load_dj_sectorial(self):
        """Carga análisis DJ Sectorial"""
        sector_file = Path("reports/dj_sectorial_analysis.csv")

        if not sector_file.exists():
            print("⚠️  DJ Sectorial no encontrado")
            return False

        self.sector_data = pd.read_csv(sector_file)
        print(f"✅ DJ Sectorial cargado: {len(self.sector_data)} sectores")

        # Crear ranking por fortaleza
        # Mejores sectores = más lejos del mínimo + RSI fuerte
        self.sector_data['strength_score'] = (
            self.sector_data['DistanceFromMin'] * 0.6 +
            self.sector_data['RSI'] * 0.4
        )

        # Ranking (1 = mejor, 140 = peor)
        self.sector_data = self.sector_data.sort_values('strength_score', ascending=False)
        self.sector_data['ranking'] = range(1, len(self.sector_data) + 1)

        # Guardar en dict para lookup rápido
        for _, row in self.sector_data.iterrows():
            ticker = row['Ticker']
            self.sector_rankings[ticker] = {
                'name': row['Sector'],
                'ranking': row['ranking'],
                'strength_score': row['strength_score'],
                'rsi': row['RSI'],
                'estado': row['Estado'],
                'classification': row['Classification']
            }

        return True

    def map_ticker_to_sector(self, ticker):
        """Mapea ticker a sector DJ, usando caché si está disponible"""
        if ticker in self.ticker_to_sector:
            return self.ticker_to_sector[ticker].get('dj_ticker')

        try:
            info = yf.Ticker(ticker).info
            sector = info.get('sector', '')
            self.ticker_to_sector[ticker] = {
                'sector': sector,
                'industry': info.get('industry', ''),
                'dj_ticker': DJ_SECTOR_MAP.get(sector)
            }
            self._save_sector_cache()
            return self.ticker_to_sector[ticker]['dj_ticker']
        except Exception:
            self.ticker_to_sector[ticker] = {'sector': '', 'industry': '', 'dj_ticker': None}
            return None

    def calculate_sector_score(self, ticker, use_cache=True):
        """
        Calcula sector score dinámico (0-100) basado en DJ Sectorial

        Score components:
        - Ranking del sector (50%): Top 10 = 100, Bottom 10 = 0
        - RSI del sector (30%): RSI alto = oportunidad
        - Estado del sector (20%): FUERTE > CERCA > OPORTUNIDAD
        """
        # Mapear ticker a sector DJ
        if ticker not in self.ticker_to_sector or not use_cache:
            dj_ticker = self.map_ticker_to_sector(ticker)
        else:
            dj_ticker = self.ticker_to_sector[ticker]['dj_ticker']

        if not dj_ticker or dj_ticker not in self.sector_rankings:
            # Sin datos sectoriales, score neutral
            return 50

        sector = self.sector_rankings[dj_ticker]

        # Componente 1: Ranking (top sectores = mejor score)
        total_sectors = len(self.sector_rankings)
        ranking = sector['ranking']
        ranking_score = 100 * (1 - (ranking - 1) / total_sectors)

        # Componente 2: RSI (normalizado 0-100)
        rsi_score = sector['rsi']

        # Componente 3: Estado
        estado_scores = {
            '🔴': 80,  # FUERTE - sector en uptrend
            '🟡': 60,  # CERCA - neutral
            '🟢': 40   # OPORTUNIDAD - en mínimos (puede rebotar pero riesgoso)
        }
        estado_score = estado_scores.get(sector['estado'], 50)

        # Score final ponderado
        final_score = (
            ranking_score * 0.50 +
            rsi_score * 0.30 +
            estado_score * 0.20
        )

        return round(final_score, 2)

    def get_sector_momentum(self, ticker):
        """
        Detecta si el sector está ganando o perdiendo momentum

        Compara ranking actual vs hace 1 semana (si disponible)
        Returns: 'improving', 'declining', 'stable'
        """
        # TODO: Implementar cuando tengamos histórico de rankings
        # Por ahora, basado en RSI y Distance

        dj_ticker = self.ticker_to_sector.get(ticker, {}).get('dj_ticker')
        if not dj_ticker or dj_ticker not in self.sector_rankings:
            return 'stable'

        sector = self.sector_rankings[dj_ticker]
        rsi = sector['rsi']

        # RSI > 70 = overbought (declining momentum)
        # RSI < 30 = oversold (improving momentum)
        # 50-70 = improving
        # 30-50 = stable

        if rsi > 70:
            return 'declining'
        elif rsi > 50:
            return 'improving'
        elif rsi < 30:
            return 'improving'  # Oversold bounce
        else:
            return 'stable'

    def calculate_tier_boost(self, sector_score, momentum):
        """
        Calcula boost adicional al score 4D por sector fuerte

        Boost máximo: +10 puntos
        - Sector Top 10 + Momentum improving: +10
        - Sector Top 25 + Momentum stable: +5
        - Sector Top 50: +3
        """
        boost = 0

        # Boost por score sectorial
        if sector_score >= 90:  # Top 10
            boost += 7
            if momentum == 'improving':
                boost += 3  # Total: +10
        elif sector_score >= 80:  # Top 25
            boost += 5
            if momentum == 'improving':
                boost += 2  # Total: +7
        elif sector_score >= 70:  # Top 50
            boost += 3

        return boost

    def diversify_opportunities(self, opportunities, max_per_sector=3):
        """
        Evita concentración excesiva en un solo sector

        Limita el número de oportunidades del mismo sector en el Top N
        """
        sector_count = {}
        diversified = []

        for opp in opportunities:
            ticker = opp['ticker']

            # Obtener sector
            dj_ticker = self.ticker_to_sector.get(ticker, {}).get('dj_ticker', 'UNKNOWN')

            # Contar por sector
            current_count = sector_count.get(dj_ticker, 0)

            if current_count < max_per_sector:
                diversified.append(opp)
                sector_count[dj_ticker] = current_count + 1
            else:
                # Saltar esta oportunidad (ya tenemos suficientes del mismo sector)
                continue

        return diversified

    def get_sector_stats(self):
        """Retorna estadísticas de los sectores"""
        if self.sector_data is None:
            return None

        stats = {
            'total_sectors': len(self.sector_data),
            'top_10': self.sector_data.head(10)['Sector'].tolist(),
            'bottom_10': self.sector_data.tail(10)['Sector'].tolist(),
            'avg_rsi': self.sector_data['RSI'].mean(),
            'strong_sectors': len(self.sector_data[self.sector_data['Estado'] == '🔴']),
            'weak_sectors': len(self.sector_data[self.sector_data['Estado'] == '🟢']),
        }

        return stats


def main():
    """Test del sistema"""
    print("🔍 SECTOR ENHANCEMENT SYSTEM - TEST")
    print("=" * 80)

    enhancer = SectorEnhancement()

    # Cargar DJ Sectorial
    if not enhancer.load_dj_sectorial():
        print("❌ Error cargando DJ Sectorial")
        return

    # Stats generales
    stats = enhancer.get_sector_stats()
    print(f"\n📊 Stats Sectoriales:")
    print(f"   Total sectores: {stats['total_sectors']}")
    print(f"   Sectores fuertes (🔴): {stats['strong_sectors']}")
    print(f"   Sectores débiles (🟢): {stats['weak_sectors']}")
    print(f"   RSI promedio: {stats['avg_rsi']:.1f}")

    print(f"\n🏆 Top 10 Sectores:")
    for i, sector in enumerate(stats['top_10'], 1):
        print(f"   {i:2}. {sector}")

    # Test con algunos tickers
    test_tickers = ['AAPL', 'MSFT', 'NVDA', 'JPM', 'XOM']

    print(f"\n🧪 Test con tickers:")
    for ticker in test_tickers:
        score = enhancer.calculate_sector_score(ticker)
        momentum = enhancer.get_sector_momentum(ticker)
        boost = enhancer.calculate_tier_boost(score, momentum)

        sector_info = enhancer.ticker_to_sector.get(ticker, {})
        print(f"\n   {ticker}:")
        print(f"      Sector: {sector_info.get('sector', 'N/A')}")
        print(f"      Sector Score: {score}/100")
        print(f"      Momentum: {momentum}")
        print(f"      Tier Boost: +{boost} puntos")


if __name__ == "__main__":
    main()

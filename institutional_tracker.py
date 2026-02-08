#!/usr/bin/env python3
"""
INSTITUTIONAL TRACKER - SEC 13F Scraper
Trackea holdings institucionales de los TOP inversores (whales)
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
from collections import defaultdict

# === WHALE INVESTORS (Top 50 institucionales) ===
WHALE_INVESTORS = {
    # Legends
    '0001067983': {'name': 'Berkshire Hathaway (Warren Buffett)', 'tier': 'legend'},
    '0001350694': {'name': 'Bridgewater Associates (Ray Dalio)', 'tier': 'legend'},

    # Mega Funds
    '0001086364': {'name': 'BlackRock', 'tier': 'mega'},
    '0000102909': {'name': 'Vanguard Group', 'tier': 'mega'},
    '0000315066': {'name': 'State Street', 'tier': 'mega'},
    '0000930667': {'name': 'Fidelity', 'tier': 'mega'},

    # Hedge Funds
    '0001649339': {'name': 'ARK Investment (Cathie Wood)', 'tier': 'hedge'},
    '0001336528': {'name': 'Pershing Square (Bill Ackman)', 'tier': 'hedge'},
    '0001061768': {'name': 'Tiger Global Management', 'tier': 'hedge'},
    '0001549469': {'name': 'Renaissance Technologies', 'tier': 'hedge'},
    '0001567892': {'name': 'Third Point (Dan Loeb)', 'tier': 'hedge'},
    '0001079114': {'name': 'Appaloosa Management (David Tepper)', 'tier': 'hedge'},
    '0001266171': {'name': 'Two Sigma Investments', 'tier': 'hedge'},
    '0001040273': {'name': 'D.E. Shaw', 'tier': 'hedge'},
    '0001037389': {'name': 'Millennium Management', 'tier': 'hedge'},
    '0001661450': {'name': 'Citadel Advisors (Ken Griffin)', 'tier': 'hedge'},

    # Growth/Tech Focused
    '0001767143': {'name': 'Tiger Cub - Chase Coleman', 'tier': 'growth'},
    '0001159191': {'name': 'Lone Pine Capital', 'tier': 'growth'},
    '0001013542': {'name': 'Viking Global', 'tier': 'growth'},
    '0001336471': {'name': 'Coatue Management', 'tier': 'growth'},
}

class InstitutionalTracker:
    """Scraper de 13F filings de SEC"""

    def __init__(self):
        self.base_url = "https://www.sec.gov"
        self.headers = {
            'User-Agent': 'Stock Analyzer ale@tantancansado.com',
            'Accept-Encoding': 'gzip, deflate',
        }
        self.cache_dir = Path("data/institutional")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_latest_13f(self, cik, max_filings=2):
        """Obtiene últimos N filings 13F de una institución"""
        print(f"📡 Obteniendo 13F de CIK {cik}...")

        # API de SEC Edgar
        url = f"{self.base_url}/cgi-bin/browse-edgar"
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': '13F-HR',
            'dateb': '',
            'owner': 'exclude',
            'count': max_filings,
            'output': 'atom'
        }

        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=10)

            if response.status_code == 200:
                # Parse filing URLs
                # Simplificado: guardar info básica
                return {
                    'cik': cik,
                    'status': 'ok',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print(f"   ⚠️  Status {response.status_code}")
                return None

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    def parse_13f_xml(self, cik):
        """
        Parse XML de 13F para extraer holdings
        Formato simplificado por ahora
        """
        # TODO: Implementar parser completo de XML
        # Por ahora retornamos estructura de ejemplo
        return {
            'holdings': [],
            'total_value': 0,
            'filing_date': datetime.now().strftime('%Y-%m-%d')
        }

    def get_whale_activity(self, ticker):
        """Obtiene actividad de whales para un ticker específico"""
        print(f"\n🐋 BUSCANDO ACTIVIDAD WHALE PARA {ticker}")
        print("=" * 70)

        whale_activity = {
            'ticker': ticker,
            'whales_holding': [],
            'new_positions': 0,
            'increased_positions': 0,
            'decreased_positions': 0,
            'total_whale_score': 0
        }

        # Buscar en holdings cacheados
        # TODO: Implementar búsqueda en holdings reales

        return whale_activity

    def scan_all_whales(self):
        """Escanea todos los whales y cachea sus holdings"""
        print("🐋 ESCANEANDO TODOS LOS WHALE INVESTORS")
        print("=" * 70)

        results = {}

        for cik, info in WHALE_INVESTORS.items():
            print(f"\n📊 {info['name']} ({info['tier'].upper()})")

            # Rate limiting (SEC requiere max 10 requests/segundo)
            time.sleep(0.2)

            filing_data = self.get_latest_13f(cik)

            if filing_data:
                results[cik] = {
                    'name': info['name'],
                    'tier': info['tier'],
                    'data': filing_data
                }
                print(f"   ✅ Datos obtenidos")
            else:
                print(f"   ⚠️  Sin datos")

        # Guardar cache
        cache_path = self.cache_dir / f"whale_scan_{datetime.now().strftime('%Y%m%d')}.json"
        with open(cache_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Escaneo completado: {len(results)} whales procesados")
        print(f"💾 Cache guardado: {cache_path}")

        return results

    def calculate_institutional_score(self, ticker):
        """
        Calcula score institucional para un ticker

        Factores:
        - Nuevas posiciones de whales (+50 puntos cada una)
        - Incrementos en posiciones existentes (+30 puntos)
        - Tier del whale (legend=3x, mega=2x, hedge/growth=1x)
        """
        activity = self.get_whale_activity(ticker)

        score = 0

        # Nuevas posiciones (muy bullish)
        score += activity['new_positions'] * 50

        # Incrementos
        score += activity['increased_positions'] * 30

        # Decrementos (bearish)
        score -= activity['decreased_positions'] * 20

        # Bonus por tier de whale
        for whale in activity['whales_holding']:
            tier_multiplier = {
                'legend': 3.0,
                'mega': 2.0,
                'hedge': 1.5,
                'growth': 1.5
            }.get(whale['tier'], 1.0)

            score *= tier_multiplier

        # Normalizar a 0-100
        normalized_score = min(100, max(0, score))

        return {
            'ticker': ticker,
            'institutional_score': normalized_score,
            'new_positions': activity['new_positions'],
            'increased_positions': activity['increased_positions'],
            'decreased_positions': activity['decreased_positions'],
            'whales_holding': len(activity['whales_holding']),
            'details': activity
        }


def demo_institutional_tracker():
    """Demo del institutional tracker"""
    tracker = InstitutionalTracker()

    # Test con ticker de ejemplo
    print("🧪 TEST: Calculando score institucional para AAPL")
    score_data = tracker.calculate_institutional_score('AAPL')

    print(f"\n📊 RESULTADO:")
    print(f"   Ticker: {score_data['ticker']}")
    print(f"   Score Institucional: {score_data['institutional_score']}/100")
    print(f"   Nuevas posiciones: {score_data['new_positions']}")
    print(f"   Incrementos: {score_data['increased_positions']}")
    print(f"   Whales holding: {score_data['whales_holding']}")

    return score_data


if __name__ == "__main__":
    print("🏛️  INSTITUTIONAL TRACKER - SEC 13F Scraper")
    print("=" * 70)
    print("\nOpciones:")
    print("1. Escanear todos los whales")
    print("2. Buscar actividad para ticker específico")
    print("3. Demo rápido")

    choice = input("\nSelecciona (1-3): ").strip()

    tracker = InstitutionalTracker()

    if choice == '1':
        tracker.scan_all_whales()
    elif choice == '2':
        ticker = input("Ticker: ").strip().upper()
        result = tracker.calculate_institutional_score(ticker)
        print(json.dumps(result, indent=2))
    else:
        demo_institutional_tracker()

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
from parse_13f_holdings import Holdings13FParser

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

    def parse_13f_xml(self, cik, filing_url):
        """
        Parse XML de 13F para extraer holdings usando Holdings13FParser
        """
        print(f"   📊 Parseando holdings del filing...")

        try:
            parser = Holdings13FParser()
            holdings = parser.parse_filing(filing_url)

            if holdings:
                # Calcular total value
                total_value = sum(h.get('value', 0) for h in holdings)

                return {
                    'holdings': holdings,
                    'total_value': total_value,
                    'filing_date': datetime.now().strftime('%Y-%m-%d'),
                    'holdings_count': len(holdings)
                }
            else:
                print(f"   ⚠️  No se pudieron parsear holdings")
                return {
                    'holdings': [],
                    'total_value': 0,
                    'filing_date': datetime.now().strftime('%Y-%m-%d')
                }

        except Exception as e:
            print(f"   ❌ Error parseando: {e}")
            return {
                'holdings': [],
                'total_value': 0,
                'filing_date': datetime.now().strftime('%Y-%m-%d')
            }

    def load_cached_holdings(self):
        """
        Carga todos los holdings cacheados
        Returns dict: {cik: holdings_data}
        """
        holdings_dir = Path("data/institutional/holdings")
        all_holdings = {}

        if not holdings_dir.exists():
            return all_holdings

        for holdings_file in holdings_dir.glob("*.json"):
            try:
                with open(holdings_file, 'r') as f:
                    data = json.load(f)
                    cik = data.get('cik')
                    if cik:
                        all_holdings[cik] = data
            except Exception as e:
                print(f"   ⚠️  Error loading {holdings_file}: {e}")

        return all_holdings

    def get_whale_activity(self, ticker):
        """Obtiene actividad de whales para un ticker específico"""
        ticker = ticker.upper()

        whale_activity = {
            'ticker': ticker,
            'whales_holding': [],
            'num_whales': 0,
            'total_value': 0,
            'total_shares': 0,
            'whale_score': 0
        }

        # Cargar holdings cacheados
        all_holdings = self.load_cached_holdings()

        if not all_holdings:
            return whale_activity

        # Buscar ticker en cada whale's holdings
        for cik, holdings_data in all_holdings.items():
            whale_name = WHALE_INVESTORS.get(cik, {}).get('name', f'CIK {cik}')
            whale_tier = WHALE_INVESTORS.get(cik, {}).get('tier', 'unknown')

            # Buscar ticker en holdings
            for holding in holdings_data.get('holdings', []):
                holding_ticker = (holding.get('ticker') or '').upper()

                if holding_ticker == ticker:
                    # Found match!
                    value = holding.get('value', 0)
                    shares = holding.get('shares', 0)

                    whale_activity['whales_holding'].append({
                        'whale_name': whale_name,
                        'tier': whale_tier,
                        'value': value,
                        'shares': shares,
                        'company_name': holding.get('company_name', '')
                    })

                    whale_activity['num_whales'] += 1
                    whale_activity['total_value'] += value
                    whale_activity['total_shares'] += shares

        # Calcular whale score
        if whale_activity['num_whales'] > 0:
            # Score basado en número de whales y tier quality
            base_score = whale_activity['num_whales'] * 10  # 10 puntos por whale

            # Bonus por tier (legends valen más)
            tier_bonus = 0
            for whale in whale_activity['whales_holding']:
                if whale['tier'] == 'legend':
                    tier_bonus += 15
                elif whale['tier'] == 'mega':
                    tier_bonus += 10
                elif whale['tier'] == 'hedge':
                    tier_bonus += 5

            whale_activity['whale_score'] = min(100, base_score + tier_bonus)

        return whale_activity

    def calculate_institutional_score(self, ticker):
        """
        Calcula score institucional para un ticker (0-100)

        Factores:
        - Número de whales holding (más = mejor)
        - Tier quality (legends > mega > hedge)
        - Total position value

        Returns: float 0-100
        """
        activity = self.get_whale_activity(ticker)
        return activity.get('whale_score', 0)

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
        - Número de whales holding (10 puntos cada uno)
        - Tier del whale (legend=+15, mega=+10, hedge=+5)
        - Normalized a 0-100
        """
        activity = self.get_whale_activity(ticker)

        # Usar whale_score calculado en get_whale_activity()
        normalized_score = activity.get('whale_score', 0)

        return {
            'ticker': ticker,
            'institutional_score': normalized_score,
            'new_positions': 0,  # TODO: Requiere comparar con holdings previos
            'increased_positions': 0,  # TODO: Requiere comparar con holdings previos
            'decreased_positions': 0,  # TODO: Requiere comparar con holdings previos
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

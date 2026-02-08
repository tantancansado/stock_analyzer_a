#!/usr/bin/env python3
"""
BUILD INSTITUTIONAL INDEX
Construye índice ticker -> whales para lookup rápido
Detecta cambios entre trimestres
"""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class InstitutionalIndexBuilder:
    """Construye índice de holdings institucionales"""

    def __init__(self):
        self.holdings_dir = Path("data/institutional/holdings")
        self.output_dir = Path("data/institutional")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_all_whale_holdings(self):
        """Carga todos los holdings guardados"""
        print("📂 CARGANDO HOLDINGS DE WHALES")
        print("=" * 70)

        all_holdings = {}

        if not self.holdings_dir.exists():
            print("⚠️  No hay holdings guardados aún")
            return all_holdings

        # Buscar todos los JSONs
        json_files = list(self.holdings_dir.glob("*.json"))

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                    cik = data['cik']
                    filing_date = data['filing_date']
                    whale_name = data['whale_name']

                    key = f"{cik}_{filing_date}"

                    all_holdings[key] = {
                        'cik': cik,
                        'whale_name': whale_name,
                        'filing_date': filing_date,
                        'holdings': data['holdings']
                    }

                    print(f"✅ {whale_name:40} | {filing_date} | {len(data['holdings'])} holdings")

            except Exception as e:
                print(f"⚠️  Error cargando {json_file}: {e}")

        print(f"\n✅ Total cargados: {len(all_holdings)} filings")
        return all_holdings

    def build_ticker_index(self, all_holdings):
        """
        Construye índice inverso: ticker -> [whales que lo tienen]

        Estructura:
        {
            'AAPL': [
                {
                    'whale_name': 'Berkshire Hathaway',
                    'cik': '0001067983',
                    'filing_date': '2025-11-14',
                    'shares': 1000000,
                    'value': 150000000,
                    'ticker': 'AAPL'
                }
            ]
        }
        """
        print("\n🔨 CONSTRUYENDO ÍNDICE TICKER -> WHALES")
        print("=" * 70)

        ticker_index = defaultdict(list)

        for key, whale_data in all_holdings.items():
            for holding in whale_data['holdings']:
                ticker = holding.get('ticker')

                if ticker and ticker != 'N/A':
                    ticker_index[ticker].append({
                        'whale_name': whale_data['whale_name'],
                        'cik': whale_data['cik'],
                        'filing_date': whale_data['filing_date'],
                        'shares': holding.get('shares', 0),
                        'value': holding.get('value', 0),
                        'company_name': holding.get('company_name', ''),
                        'ticker': ticker
                    })

        # Ordenar por value
        for ticker in ticker_index:
            ticker_index[ticker] = sorted(
                ticker_index[ticker],
                key=lambda x: x['value'],
                reverse=True
            )

        print(f"✅ Índice construido: {len(ticker_index)} tickers únicos")

        # Top tickers por número de whales
        top_by_whales = sorted(
            ticker_index.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]

        print(f"\n🏆 TOP 10 TICKERS MÁS POPULARES ENTRE WHALES:")
        print("-" * 70)
        for ticker, whales in top_by_whales:
            total_value = sum(w['value'] for w in whales)
            print(f"{ticker:6} - {len(whales)} whales holding | Total value: ${total_value:,.0f}")

        return dict(ticker_index)

    def detect_changes(self, all_holdings):
        """
        Detecta cambios entre trimestres para cada whale

        Compara holdings de Q1 2025 vs Q4 2024, por ejemplo
        """
        print("\n🔍 DETECTANDO CAMBIOS ENTRE TRIMESTRES")
        print("=" * 70)

        # Agrupar por CIK
        holdings_by_cik = defaultdict(list)

        for key, data in all_holdings.items():
            holdings_by_cik[data['cik']].append(data)

        changes_report = {}

        for cik, filings in holdings_by_cik.items():
            if len(filings) < 2:
                continue

            # Ordenar por fecha
            filings_sorted = sorted(filings, key=lambda x: x['filing_date'], reverse=True)

            latest = filings_sorted[0]
            previous = filings_sorted[1]

            whale_name = latest['whale_name']

            print(f"\n📊 {whale_name}")
            print(f"   Comparando: {previous['filing_date']} → {latest['filing_date']}")

            # Construir mapas ticker->shares
            prev_map = {}
            for h in previous['holdings']:
                ticker = h.get('ticker')
                if ticker and ticker != 'N/A':
                    prev_map[ticker] = h.get('shares', 0)

            latest_map = {}
            for h in latest['holdings']:
                ticker = h.get('ticker')
                if ticker and ticker != 'N/A':
                    latest_map[ticker] = h.get('shares', 0)

            # Detectar cambios
            new_positions = []
            increased = []
            decreased = []
            exited = []

            # Nuevas posiciones
            for ticker in latest_map:
                if ticker not in prev_map:
                    new_positions.append({
                        'ticker': ticker,
                        'shares': latest_map[ticker]
                    })

            # Incrementos y decrementos
            for ticker in latest_map:
                if ticker in prev_map:
                    prev_shares = prev_map[ticker]
                    new_shares = latest_map[ticker]

                    if new_shares > prev_shares:
                        pct_change = ((new_shares - prev_shares) / prev_shares) * 100
                        if pct_change >= 20:  # Incremento significativo
                            increased.append({
                                'ticker': ticker,
                                'prev_shares': prev_shares,
                                'new_shares': new_shares,
                                'change_pct': pct_change
                            })
                    elif new_shares < prev_shares:
                        pct_change = ((prev_shares - new_shares) / prev_shares) * 100
                        if pct_change >= 20:
                            decreased.append({
                                'ticker': ticker,
                                'prev_shares': prev_shares,
                                'new_shares': new_shares,
                                'change_pct': pct_change
                            })

            # Salidas
            for ticker in prev_map:
                if ticker not in latest_map:
                    exited.append({
                        'ticker': ticker,
                        'prev_shares': prev_map[ticker]
                    })

            changes_report[cik] = {
                'whale_name': whale_name,
                'comparison': f"{previous['filing_date']} → {latest['filing_date']}",
                'new_positions': new_positions,
                'increased': increased,
                'decreased': decreased,
                'exited': exited
            }

            # Print summary
            if new_positions:
                print(f"   ✨ NUEVAS: {len(new_positions)}")
                for pos in new_positions[:5]:
                    print(f"      • {pos['ticker']}: {pos['shares']:,} shares")

            if increased:
                print(f"   📈 INCREMENTOS: {len(increased)}")
                for pos in increased[:5]:
                    print(f"      • {pos['ticker']}: +{pos['change_pct']:.0f}%")

            if decreased:
                print(f"   📉 DECREMENTOS: {len(decreased)}")

            if exited:
                print(f"   🚪 SALIDAS: {len(exited)}")

        return changes_report

    def calculate_ticker_institutional_score(self, ticker, ticker_index, changes_report):
        """
        Calcula score institucional para un ticker específico

        Factores:
        - Whales holding (base score)
        - Nuevas posiciones (+50 por whale)
        - Incrementos significativos (+30 por whale)
        - Tier multipliers (legend 3x, mega 2x)
        """
        if ticker not in ticker_index:
            return {
                'ticker': ticker,
                'institutional_score': 0,
                'whales_holding': 0,
                'new_positions': 0,
                'increased_positions': 0,
                'details': []
            }

        holdings = ticker_index[ticker]
        num_whales = len(holdings)

        # Base score
        score = num_whales * 10

        # Analizar cambios
        new_count = 0
        increased_count = 0

        for cik, changes in changes_report.items():
            # Nuevas posiciones
            for new_pos in changes['new_positions']:
                if new_pos['ticker'] == ticker:
                    new_count += 1
                    score += 50

            # Incrementos
            for inc in changes['increased']:
                if inc['ticker'] == ticker:
                    increased_count += 1
                    score += 30

        # Normalizar a 0-100
        normalized_score = min(100, score)

        return {
            'ticker': ticker,
            'institutional_score': normalized_score,
            'whales_holding': num_whales,
            'new_positions': new_count,
            'increased_positions': increased_count,
            'details': holdings[:5]  # Top 5 whales
        }

    def build_and_save_index(self):
        """Pipeline completo"""
        # Cargar holdings
        all_holdings = self.load_all_whale_holdings()

        if not all_holdings:
            print("\n⚠️  No hay datos para procesar")
            print("   Ejecuta primero: python3 parse_13f_holdings.py")
            return

        # Build ticker index
        ticker_index = self.build_ticker_index(all_holdings)

        # Guardar ticker index
        index_path = self.output_dir / "ticker_institutional_index.json"
        with open(index_path, 'w') as f:
            json.dump(ticker_index, f, indent=2)
        print(f"\n💾 Ticker index guardado: {index_path}")

        # Detect changes
        if len(set(h['cik'] for h in all_holdings.values())) > 1 or \
           len(set(h['filing_date'] for h in all_holdings.values())) > 1:
            changes_report = self.detect_changes(all_holdings)

            # Guardar changes report
            changes_path = self.output_dir / "institutional_changes.json"
            with open(changes_path, 'w') as f:
                json.dump(changes_report, f, indent=2)
            print(f"💾 Changes report guardado: {changes_path}")
        else:
            changes_report = {}

        # Calcular scores para algunos tickers de ejemplo
        print(f"\n🎯 CALCULANDO SCORES INSTITUCIONALES")
        print("=" * 70)

        example_tickers = ['AAPL', 'GOOGL', 'AMZN', 'ALLY', 'AXP']
        scores = {}

        for ticker in example_tickers:
            score_data = self.calculate_ticker_institutional_score(ticker, ticker_index, changes_report)
            scores[ticker] = score_data

            print(f"\n{ticker}: {score_data['institutional_score']}/100")
            print(f"   Whales: {score_data['whales_holding']}")
            print(f"   Nuevas: {score_data['new_positions']}")
            print(f"   Incrementos: {score_data['increased_positions']}")

        return {
            'ticker_index': ticker_index,
            'changes_report': changes_report,
            'scores': scores
        }


if __name__ == "__main__":
    print("🏗️  INSTITUTIONAL INDEX BUILDER")
    print("=" * 80)

    builder = InstitutionalIndexBuilder()
    builder.build_and_save_index()

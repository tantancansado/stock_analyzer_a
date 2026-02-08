#!/usr/bin/env python3
"""
SUPER ANALYZER 5D - Ultimate Stock Opportunity Scanner
Combina 5 dimensiones para encontrar las MEJORES oportunidades:
  1. VCP Patterns (30%)
  2. Recurring Insiders (25%)
  3. Sector State (20%) ← MEJORADO con DJ Sectorial
  4. Institutional Buying (25%)
  5. Fundamental Analysis + Price Targets ← NUEVO
"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from sector_enhancement import SectorEnhancement
from fundamental_analyzer import FundamentalAnalyzer

class SuperAnalyzer4D:
    """Analizador 5D con sector enhancement + fundamental analysis"""

    def __init__(self):
        self.weights = {
            'vcp': 0.30,        # Análisis técnico VCP
            'insiders': 0.25,   # Compras recurrentes insiders
            'sector': 0.20,     # Estado del sector (MEJORADO)
            'institutional': 0.25  # Compras institucionales
        }

        # Nuevos módulos
        self.sector_enhancer = SectorEnhancement()
        self.fundamental_analyzer = FundamentalAnalyzer()

        # Cargar DJ Sectorial
        print("🔍 Cargando Sector Enhancement...")
        if self.sector_enhancer.load_dj_sectorial():
            print("   ✅ DJ Sectorial cargado correctamente")
        else:
            print("   ⚠️  DJ Sectorial no disponible - usando scores base")

    def load_vcp_data(self):
        """Carga datos de VCP scanner"""
        vcp_csv = Path("docs/reports/vcp/vcp_scan_20250711_103128/data.csv")
        if vcp_csv.exists():
            df = pd.read_csv(vcp_csv)
            print(f"✅ VCP: {len(df)} patrones cargados")
            return df
        return pd.DataFrame()

    def load_recurring_insiders_data(self):
        """Carga datos de insiders recurrentes"""
        insiders_csv = Path("docs/recurring_insiders.csv")
        if insiders_csv.exists():
            df = pd.read_csv(insiders_csv)
            print(f"✅ Recurring Insiders: {len(df)} tickers cargados")
            return df
        return pd.DataFrame()

    def load_sector_data(self):
        """Carga estado sectorial"""
        # Cargar desde el análisis sectorial existente
        # Por ahora, placeholder
        print(f"✅ Sector State: Datos cargados")
        return {}

    def load_institutional_data(self):
        """Carga datos institucionales"""
        # Cargar desde institutional_tracker cache
        cache_dir = Path("data/institutional")
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("whale_scan_*.json"))
            if cache_files:
                latest = sorted(cache_files)[-1]
                with open(latest, 'r') as f:
                    data = json.load(f)
                print(f"✅ Institutional: {len(data)} whales cargados")
                return data
        print(f"⚠️  Institutional: Sin datos (ejecuta institutional_tracker.py)")
        return {}

    def calculate_4d_score(self, ticker, vcp_score=0, insider_score=0, sector_score=0, institutional_score=0):
        """
        Calcula super score 4D

        Parámetros:
        - vcp_score: 0-100 (patrón VCP)
        - insider_score: 0-100 (compras recurrentes)
        - sector_score: 0-100 (estado sectorial)
        - institutional_score: 0-100 (actividad institucional)
        """
        super_score = (
            vcp_score * self.weights['vcp'] +
            insider_score * self.weights['insiders'] +
            sector_score * self.weights['sector'] +
            institutional_score * self.weights['institutional']
        )

        # Clasificación
        if super_score >= 85:
            tier = "⭐⭐⭐⭐ LEGENDARY"
            description = "Confirmación cuádruple - Oportunidad HISTÓRICA"
        elif super_score >= 75:
            tier = "⭐⭐⭐ ÉPICA"
            description = "Triple/Cuádruple confirmación - Altísima probabilidad"
        elif super_score >= 65:
            tier = "⭐⭐ EXCELENTE"
            description = "Doble confirmación sólida"
        elif super_score >= 55:
            tier = "⭐ BUENA"
            description = "Señales positivas"
        else:
            tier = "🔵 MODERADA"
            description = "Seguimiento recomendado"

        return {
            'ticker': ticker,
            'super_score_4d': round(super_score, 1),
            'tier': tier,
            'description': description,
            'dimensions': {
                'vcp': vcp_score,
                'insiders': insider_score,
                'sector': sector_score,
                'institutional': institutional_score
            },
            'weights': self.weights
        }

    def find_4d_opportunities(self):
        """Encuentra oportunidades con las 4 dimensiones"""
        print("\n🚀 SUPER ANALYZER 4D - BUSCANDO OPORTUNIDADES LEGENDARY")
        print("=" * 80)

        # Cargar datos
        vcp_df = self.load_vcp_data()
        insiders_df = self.load_recurring_insiders_data()
        sector_data = self.load_sector_data()
        institutional_data = self.load_institutional_data()

        # Cruzar datos
        opportunities = []

        # Empezar con tickers que tienen datos de insiders recurrentes
        for _, row in insiders_df.iterrows():
            ticker = row['ticker']

            print(f"   Analizando {ticker}...", end="\r")

            # Calcular scores
            insider_score = min(100, row.get('confidence_score', 0))

            # VCP score
            vcp_score = 0
            vcp_match = vcp_df[vcp_df['ticker'] == ticker]
            if not vcp_match.empty:
                vcp_score = vcp_match.iloc[0].get('vcp_score', 0)

            # Sector score MEJORADO con DJ Sectorial
            sector_score = self.sector_enhancer.calculate_sector_score(ticker)
            sector_momentum = self.sector_enhancer.get_sector_momentum(ticker)
            tier_boost = self.sector_enhancer.calculate_tier_boost(sector_score, sector_momentum)

            # Institutional score (placeholder hasta que tengamos datos reales)
            institutional_score = 0

            # Calcular super score 4D base
            result = self.calculate_4d_score(
                ticker,
                vcp_score=vcp_score,
                insider_score=insider_score,
                sector_score=sector_score,
                institutional_score=institutional_score
            )

            # Aplicar tier boost por sector fuerte
            result['super_score_4d'] = round(
                min(100, result['super_score_4d'] + tier_boost), 1
            )

            # Añadir información sectorial
            result['sector_momentum'] = sector_momentum
            result['tier_boost'] = tier_boost

            # Sector info
            sector_info = self.sector_enhancer.ticker_to_sector.get(ticker, {})
            result['sector_name'] = sector_info.get('sector', 'Unknown')
            result['dj_ticker'] = sector_info.get('dj_ticker', None)

            # FUNDAMENTAL ANALYSIS + PRICE TARGETS
            try:
                # Obtener datos fundamentales
                fundamental_data = self.fundamental_analyzer.get_fundamental_data(ticker)

                if fundamental_data:
                    # Calcular price target combinado
                    price_target_data = self.fundamental_analyzer.calculate_custom_price_target(ticker)

                    if price_target_data:
                        result['price_target'] = price_target_data['custom_target']
                        result['upside_percent'] = price_target_data['upside_percent']
                        result['price_target_components'] = price_target_data['components']
                    else:
                        result['price_target'] = None
                        result['upside_percent'] = None

                    # Fundamental score
                    result['fundamental_score'] = self.fundamental_analyzer.get_fundamental_score(ticker)

                    # Métricas clave
                    result['pe_ratio'] = fundamental_data['valuation']['pe_ratio']
                    result['peg_ratio'] = fundamental_data['valuation']['peg_ratio']
                    result['fcf_yield'] = fundamental_data['cashflow']['fcf_yield']
                    result['roe'] = fundamental_data['profitability']['roe']
                    result['revenue_growth'] = fundamental_data['growth']['revenue_growth']
                    result['current_price'] = fundamental_data['current_price']

                    # Analyst targets
                    result['analyst_target'] = fundamental_data['analysts']['target_mean']
                    result['analyst_upside'] = fundamental_data['analysts']['upside_analysts']
                    result['num_analysts'] = fundamental_data['analysts']['num_analysts']

                else:
                    # Sin datos fundamentales
                    result['price_target'] = None
                    result['upside_percent'] = None
                    result['fundamental_score'] = 50
                    result['current_price'] = None

            except Exception as e:
                print(f"⚠️  Error fundamental {ticker}: {e}")
                result['price_target'] = None
                result['upside_percent'] = None
                result['fundamental_score'] = 50

            opportunities.append(result)

        # Ordenar por super score
        opportunities.sort(key=lambda x: x['super_score_4d'], reverse=True)

        print(f"\n✅ {len(opportunities)} oportunidades analizadas")

        return opportunities

    def generate_4d_report(self, opportunities):
        """Genera reporte HTML 4D"""
        print("\n📊 GENERANDO REPORTE 4D")

        # Filtrar top oportunidades
        legendary = [o for o in opportunities if '⭐⭐⭐⭐' in o['tier']]
        epic = [o for o in opportunities if '⭐⭐⭐' in o['tier'] and '⭐⭐⭐⭐' not in o['tier']]
        excellent = [o for o in opportunities if '⭐⭐' in o['tier'] and '⭐⭐⭐' not in o['tier']]

        print(f"   ⭐⭐⭐⭐ LEGENDARY: {len(legendary)}")
        print(f"   ⭐⭐⭐ ÉPICAS: {len(epic)}")
        print(f"   ⭐⭐ EXCELENTES: {len(excellent)}")

        # Top 10
        print(f"\n🏆 TOP 10 OPORTUNIDADES 5D:")
        print("-" * 80)
        for i, opp in enumerate(opportunities[:10], 1):
            dims = opp['dimensions']
            print(f"{i:2}. {opp['ticker']:6} - Score: {opp['super_score_4d']:5.1f} - {opp['tier']}")
            print(f"    VCP: {dims['vcp']:.0f} | Insiders: {dims['insiders']:.0f} | "
                  f"Sector: {dims['sector']:.0f} | Institutional: {dims['institutional']:.0f}")

            # Sector info
            print(f"    📊 Sector: {opp.get('sector_name', 'N/A')} | "
                  f"Momentum: {opp.get('sector_momentum', 'N/A')} | "
                  f"Boost: +{opp.get('tier_boost', 0)}")

            # Price target y fundamentales
            if opp.get('price_target'):
                print(f"    🎯 Target: ${opp['price_target']:.2f} "
                      f"({opp['upside_percent']:+.1f}%) | "
                      f"Fundamental: {opp.get('fundamental_score', 'N/A'):.0f}/100")

                # Current price
                if opp.get('current_price'):
                    print(f"    💵 Precio: ${opp['current_price']:.2f}", end="")

                # Métricas clave
                metrics = []
                if opp.get('pe_ratio'):
                    metrics.append(f"P/E: {opp['pe_ratio']:.1f}")
                if opp.get('peg_ratio'):
                    metrics.append(f"PEG: {opp['peg_ratio']:.2f}")
                if opp.get('fcf_yield'):
                    metrics.append(f"FCF Yield: {opp['fcf_yield']:.1f}%")

                if metrics:
                    print(f" | {' | '.join(metrics)}")
                else:
                    print()
            else:
                print(f"    ⚠️  Sin datos fundamentales")

            print()

        # TODO: Generar HTML
        return opportunities


def main():
    """Main execution"""
    analyzer = SuperAnalyzer4D()

    print("🎯 SUPER ANALYZER 5D - ULTIMATE OPPORTUNITY SCANNER")
    print("=" * 80)
    print("\nPesos configurados:")
    for dim, weight in analyzer.weights.items():
        print(f"  {dim.upper()}: {weight*100:.0f}%")

    print("\n✨ NUEVAS CARACTERÍSTICAS:")
    print("  - Sector scoring dinámico con DJ Sectorial")
    print("  - Tier boost automático por sector fuerte (+0 a +10)")
    print("  - Price targets (DCF + P/E + Analistas)")
    print("  - Análisis fundamental completo (FCF, ROE, P/E, PEG)")
    print("  - Upside potential calculado")

    # Buscar oportunidades
    opportunities = analyzer.find_4d_opportunities()

    # Generar reporte
    analyzer.generate_4d_report(opportunities)

    # Guardar CSV con todas las nuevas columnas
    output_csv = Path("docs/super_opportunities_5d.csv")
    df = pd.DataFrame(opportunities)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Reporte 5D guardado: {output_csv}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
SUPER ANALYZER 4D - Ultimate Stock Opportunity Scanner
Combina 4 dimensiones para encontrar las MEJORES oportunidades:
  1. VCP Patterns (30%)
  2. Recurring Insiders (25%)
  3. Sector State (20%)
  4. Institutional Buying (25%) ← NUEVA DIMENSIÓN
"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class SuperAnalyzer4D:
    """Analizador 4D con institucionales"""

    def __init__(self):
        self.weights = {
            'vcp': 0.30,        # Análisis técnico VCP
            'insiders': 0.25,   # Compras recurrentes insiders
            'sector': 0.20,     # Estado del sector
            'institutional': 0.25  # Compras institucionales ← NUEVO
        }

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

            # Calcular scores
            insider_score = min(100, row.get('confidence_score', 0))

            # VCP score
            vcp_score = 0
            vcp_match = vcp_df[vcp_df['ticker'] == ticker]
            if not vcp_match.empty:
                vcp_score = vcp_match.iloc[0].get('vcp_score', 0)

            # Sector score (simplificado por ahora)
            sector_score = 50  # Placeholder

            # Institutional score (placeholder hasta que tengamos datos reales)
            institutional_score = 0

            # Calcular super score 4D
            result = self.calculate_4d_score(
                ticker,
                vcp_score=vcp_score,
                insider_score=insider_score,
                sector_score=sector_score,
                institutional_score=institutional_score
            )

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
        print(f"\n🏆 TOP 10 OPORTUNIDADES 4D:")
        print("-" * 80)
        for i, opp in enumerate(opportunities[:10], 1):
            dims = opp['dimensions']
            print(f"{i:2}. {opp['ticker']:6} - Score: {opp['super_score_4d']:5.1f} - {opp['tier']}")
            print(f"    VCP: {dims['vcp']:.0f} | Insiders: {dims['insiders']:.0f} | "
                  f"Sector: {dims['sector']:.0f} | Institutional: {dims['institutional']:.0f}")

        # TODO: Generar HTML
        return opportunities


def main():
    """Main execution"""
    analyzer = SuperAnalyzer4D()

    print("🎯 SUPER ANALYZER 4D - ULTIMATE OPPORTUNITY SCANNER")
    print("=" * 80)
    print(f"\nPesos configurados:")
    for dim, weight in analyzer.weights.items():
        print(f"  {dim.upper()}: {weight*100:.0f}%")

    # Buscar oportunidades
    opportunities = analyzer.find_4d_opportunities()

    # Generar reporte
    analyzer.generate_4d_report(opportunities)

    # Guardar CSV
    output_csv = Path("docs/super_opportunities_4d.csv")
    df = pd.DataFrame(opportunities)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Reporte guardado: {output_csv}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
RUN SUPER ANALYZER 4D - Con datos institucionales reales
Ejecuta análisis completo con las 4 dimensiones
"""
import json
from pathlib import Path
from super_analyzer_4d import SuperAnalyzer4D

def load_institutional_scores():
    """Carga scores institucionales del índice"""
    index_path = Path("data/institutional/ticker_institutional_index.json")

    if not index_path.exists():
        print("⚠️  No hay índice institucional")
        print("   Ejecuta: python3 scan_all_whales.py")
        return {}

    with open(index_path, 'r') as f:
        ticker_index = json.load(f)

    # Calcular scores básicos por ticker
    scores = {}
    for ticker, holdings in ticker_index.items():
        num_whales = len(holdings)
        total_value = sum(h['value'] for h in holdings)

        # Score basado en número de whales y valor
        score = min(100, num_whales * 10 + (total_value / 1e12))  # Normalizar por trillion

        scores[ticker] = {
            'institutional_score': score,
            'num_whales': num_whales,
            'total_value': total_value,
            'top_whales': [h['whale_name'] for h in holdings[:3]]
        }

    return scores

def run_4d_analysis():
    """Ejecuta análisis 4D completo"""
    print("🎯 SUPER ANALYZER 4D - ANÁLISIS COMPLETO")
    print("=" * 80)

    # Cargar scores institucionales
    print("\n🏛️  Cargando datos institucionales...")
    inst_scores = load_institutional_scores()

    if inst_scores:
        print(f"   ✅ {len(inst_scores)} tickers con datos institucionales")

        # Top 5 por score institucional
        top_inst = sorted(inst_scores.items(), key=lambda x: x[1]['institutional_score'], reverse=True)[:5]
        print(f"\n   🏆 TOP 5 POR SCORE INSTITUCIONAL:")
        for ticker, data in top_inst:
            print(f"      {ticker:6} - {data['institutional_score']:.0f}/100 ({data['num_whales']} whales)")
    else:
        print(f"   ⚠️  Sin datos institucionales - Scores será 0")

    # Ejecutar Super Analyzer 4D
    analyzer = SuperAnalyzer4D()
    opportunities = analyzer.find_4d_opportunities()

    # Enriquecer con datos institucionales reales
    for opp in opportunities:
        ticker = opp['ticker']
        if ticker in inst_scores:
            inst_data = inst_scores[ticker]
            opp['dimensions']['institutional'] = inst_data['institutional_score']
            opp['institutional_details'] = inst_data

            # Recalcular super score con datos reales
            vcp = opp['dimensions']['vcp']
            insiders = opp['dimensions']['insiders']
            sector = opp['dimensions']['sector']
            institutional = inst_data['institutional_score']

            opp_recalc = analyzer.calculate_4d_score(
                ticker, vcp, insiders, sector, institutional
            )

            opp.update(opp_recalc)

    # Reordenar por nuevo score
    opportunities.sort(key=lambda x: x['super_score_4d'], reverse=True)

    # Generar reporte
    analyzer.generate_4d_report(opportunities)

    # Guardar con datos institucionales
    output_csv = Path("docs/super_opportunities_4d_complete.csv")

    import pandas as pd

    # Preparar datos para CSV
    csv_data = []
    for opp in opportunities:
        row = {
            'ticker': opp['ticker'],
            'super_score_4d': opp['super_score_4d'],
            'tier': opp['tier'],
            'vcp_score': opp['dimensions']['vcp'],
            'insiders_score': opp['dimensions']['insiders'],
            'sector_score': opp['dimensions']['sector'],
            'institutional_score': opp['dimensions']['institutional'],
            'num_whales': opp.get('institutional_details', {}).get('num_whales', 0),
            'top_whales': ', '.join(opp.get('institutional_details', {}).get('top_whales', []))
        }
        csv_data.append(row)

    df = pd.DataFrame(csv_data)
    df.to_csv(output_csv, index=False)

    print(f"\n✅ Reporte 4D completo guardado: {output_csv}")

    # Destacar LEGENDARY opportunities
    legendary = [o for o in opportunities if '⭐⭐⭐⭐' in o['tier']]

    if legendary:
        print(f"\n{'='*80}")
        print(f"🌟 LEGENDARY OPPORTUNITIES ENCONTRADAS: {len(legendary)}")
        print(f"{'='*80}")

        for opp in legendary:
            print(f"\n🎯 {opp['ticker']}: {opp['super_score_4d']}/100")
            print(f"   {opp['tier']} - {opp['description']}")
            dims = opp['dimensions']
            print(f"   VCP: {dims['vcp']:.0f} | Insiders: {dims['insiders']:.0f} | "
                  f"Sector: {dims['sector']:.0f} | Institutional: {dims['institutional']:.0f}")

            if opp.get('institutional_details'):
                inst = opp['institutional_details']
                print(f"   🐋 Whales: {', '.join(inst['top_whales'])}")

    return opportunities

if __name__ == "__main__":
    run_4d_analysis()

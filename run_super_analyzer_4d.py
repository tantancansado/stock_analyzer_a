#!/usr/bin/env python3
"""
RUN SUPER ANALYZER 5D - Sistema completo
Ejecuta análisis con 5 dimensiones:
  1. VCP Patterns
  2. Recurring Insiders
  3. Sector Enhancement (DJ Sectorial)
  4. Institutional Buying
  5. Fundamental Analysis + Price Targets
"""
import json
from pathlib import Path
from super_analyzer_4d import SuperAnalyzer4D
from investment_thesis_generator import add_thesis_to_opportunities
from company_name_fetcher import add_company_names_to_opportunities

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

def load_vcp_repeaters():
    """Carga datos de VCP repeaters históricos"""
    repeater_path = Path("docs/vcp_repeaters.json")

    if not repeater_path.exists():
        print("⚠️  No hay datos de VCP repeaters")
        print("   Ejecuta: python3 vcp_history_analyzer.py")
        return {}

    with open(repeater_path, 'r') as f:
        repeater_data = json.load(f)

    return repeater_data.get('repeaters', {})

def run_4d_analysis():
    """Ejecuta análisis 5D completo"""
    print("🎯 SUPER ANALYZER 5D - ANÁLISIS COMPLETO")
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

    # Cargar VCP Repeaters
    print("\n🔁 Cargando VCP Repeaters históricos...")
    vcp_repeaters = load_vcp_repeaters()

    if vcp_repeaters:
        print(f"   ✅ {len(vcp_repeaters)} VCP Repeaters identificados")

        # Top 5 por consistency score
        top_repeaters = sorted(vcp_repeaters.items(),
                             key=lambda x: x[1]['consistency_score'],
                             reverse=True)[:5]
        print(f"\n   🏆 TOP 5 REPEATERS MÁS CONSISTENTES:")
        for ticker, data in top_repeaters:
            print(f"      {ticker:6} - {data['repeat_count']}x apariciones | "
                  f"Score: {data['consistency_score']:.0f}/50")
    else:
        print(f"   ⚠️  Sin datos de repeaters - Bonus será 0")

    # Ejecutar Super Analyzer 5D
    # (incluye sector enhancement + fundamental analysis automáticamente)
    analyzer = SuperAnalyzer4D()
    opportunities = analyzer.find_4d_opportunities()

    # Enriquecer con datos institucionales reales y VCP repeaters
    for opp in opportunities:
        ticker = opp['ticker']

        # Datos institucionales
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

        # VCP Repeater bonus
        if ticker in vcp_repeaters:
            repeater_data = vcp_repeaters[ticker]

            # Add repeater info
            opp['vcp_repeater'] = True
            opp['repeat_count'] = repeater_data['repeat_count']
            opp['consistency_score'] = repeater_data['consistency_score']

            # Calculate bonus: 3 points per appearance, max 15
            repeater_bonus = min(repeater_data['repeat_count'] * 3, 15)
            opp['repeater_bonus'] = repeater_bonus

            # Add bonus to super score
            opp['super_score_4d'] = opp.get('super_score_4d', 0) + repeater_bonus

            # Update tier if needed
            new_score = opp['super_score_4d']
            if new_score >= 80:
                opp['tier'] = '⭐⭐⭐⭐ LEGENDARY'
            elif new_score >= 70:
                opp['tier'] = '⭐⭐⭐ EXCELENTE'
            elif new_score >= 60:
                opp['tier'] = '⭐⭐ BUENA'
            elif new_score >= 50:
                opp['tier'] = '⭐ BUENA'
        else:
            opp['vcp_repeater'] = False
            opp['repeat_count'] = 0
            opp['consistency_score'] = 0
            opp['repeater_bonus'] = 0

    # Reordenar por nuevo score
    opportunities.sort(key=lambda x: x['super_score_4d'], reverse=True)

    # Generar Investment Thesis para cada opportunity
    print("\n📝 Generando Investment Thesis...")
    opportunities = add_thesis_to_opportunities(opportunities)
    print(f"   ✅ Thesis generadas para {len(opportunities)} opportunities")

    # Obtener nombres de empresas
    print("\n🏢 Obteniendo nombres de empresas...")
    opportunities = add_company_names_to_opportunities(opportunities)

    # Generar reporte
    analyzer.generate_4d_report(opportunities)

    # Guardar con datos institucionales + sector + fundamentales
    output_csv = Path("docs/super_opportunities_5d_complete.csv")

    import pandas as pd

    # Preparar datos para CSV con TODAS las columnas 5D
    csv_data = []
    for opp in opportunities:
        row = {
            # Core
            'ticker': opp['ticker'],
            'company_name': opp.get('company_name', opp['ticker']),
            'super_score_5d': opp['super_score_4d'],
            'tier': opp['tier'],
            'description': opp['description'],

            # 4 Dimensiones base
            'vcp_score': opp['dimensions']['vcp'],
            'insiders_score': opp['dimensions']['insiders'],
            'sector_score': opp['dimensions']['sector'],
            'institutional_score': opp['dimensions']['institutional'],

            # Sector Enhancement
            'sector_name': opp.get('sector_name', 'Unknown'),
            'sector_momentum': opp.get('sector_momentum', 'stable'),
            'tier_boost': opp.get('tier_boost', 0),
            'dj_ticker': opp.get('dj_ticker', ''),

            # Timing Convergence (VCP + Insider timing)
            'timing_convergence': opp.get('timing_convergence', False),
            'timing_bonus': opp.get('timing_bonus', 0),
            'timing_reason': opp.get('timing_reason', ''),

            # Price Targets
            'current_price': opp.get('current_price'),
            'price_target': opp.get('price_target'),
            'upside_percent': opp.get('upside_percent'),
            'analyst_target': opp.get('analyst_target'),
            'analyst_upside': opp.get('analyst_upside'),
            'num_analysts': opp.get('num_analysts', 0),

            # Fundamentales
            'fundamental_score': opp.get('fundamental_score', 50),
            'pe_ratio': opp.get('pe_ratio'),
            'peg_ratio': opp.get('peg_ratio'),
            'fcf_yield': opp.get('fcf_yield'),
            'roe': opp.get('roe'),
            'revenue_growth': opp.get('revenue_growth'),

            # Institucionales
            'num_whales': opp.get('institutional_details', {}).get('num_whales', 0),
            'top_whales': ', '.join(opp.get('institutional_details', {}).get('top_whales', [])),

            # VCP Repeaters
            'vcp_repeater': opp.get('vcp_repeater', False),
            'repeat_count': opp.get('repeat_count', 0),
            'consistency_score': opp.get('consistency_score', 0),
            'repeater_bonus': opp.get('repeater_bonus', 0),

            # Investment Thesis
            'thesis_short': opp.get('thesis_short', ''),
            'investment_thesis': opp.get('investment_thesis', '')
        }
        csv_data.append(row)

    df = pd.DataFrame(csv_data)
    df.to_csv(output_csv, index=False)

    print(f"\n✅ Reporte 5D completo guardado: {output_csv}")
    print(f"   📊 {len(csv_data)} oportunidades con datos completos:")
    print(f"      - Sector Enhancement (DJ Sectorial)")
    print(f"      - Price Targets (DCF + P/E + Analistas)")
    print(f"      - Fundamental Scores (FCF, ROE, P/E, PEG)")
    print(f"      - Institutional Holdings")

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

            # Sector info
            print(f"   📊 {opp.get('sector_name', 'N/A')} | "
                  f"Momentum: {opp.get('sector_momentum', 'N/A')} | "
                  f"Boost: +{opp.get('tier_boost', 0)}")

            # Price targets
            if opp.get('price_target'):
                print(f"   🎯 Target: ${opp['price_target']:.2f} ({opp['upside_percent']:+.1f}%) | "
                      f"Fundamental: {opp.get('fundamental_score', 50):.0f}/100")

            if opp.get('institutional_details'):
                inst = opp['institutional_details']
                if inst.get('top_whales'):
                    print(f"   🐋 Whales: {', '.join(inst['top_whales'])}")

    # DATA QUALITY VALIDATION
    print(f"\n{'='*80}")
    print("🔍 VALIDANDO CALIDAD DE DATOS")
    print(f"{'='*80}\n")

    from validators.data_quality import DataQualityValidator

    validator = DataQualityValidator(verbose=True)
    validation_report = validator.validate_5d_pipeline(str(output_csv))

    # Save validation report
    validator.save_report(validation_report, "data_quality_report.json")

    if not validation_report['passed']:
        print(f"\n⚠️  ADVERTENCIA: Se encontraron {len(validation_report['issues'])} problemas de calidad")
        print("   Ver data_quality_report.json para detalles")
        print("\n   Principales problemas:")
        for issue in validation_report['issues'][:5]:
            print(f"   - {issue}")
    else:
        print("\n✅ Validación de calidad PASSED - Datos listos para producción")

    return opportunities

if __name__ == "__main__":
    run_4d_analysis()

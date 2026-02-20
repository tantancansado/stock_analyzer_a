#!/usr/bin/env python3
"""
Deep analysis of VALUE opportunities with AI-powered fair value estimation
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json

def calculate_fair_value(row):
    """
    Calculate AI-estimated fair value for stocks without analyst coverage
    Based on:
    - P/E vs industry average
    - PEG ratio (growth-adjusted)
    - DCF-based estimate
    - Peer comparison
    """
    ticker = row['ticker']
    price = row.get('current_price', 0)

    # If we have analyst target, trust it
    if pd.notna(row.get('target_price_analyst')) and row.get('analyst_count', 0) > 0:
        return None  # Use analyst target

    # Estimate fair value based on available metrics
    estimates = []

    # 1. P/E based (if we have forward PE estimate)
    target_pe = row.get('target_price_pe')
    if pd.notna(target_pe):
        estimates.append(('PE-based', target_pe))

    # 2. DCF based
    target_dcf = row.get('target_price_dcf')
    if pd.notna(target_dcf):
        estimates.append(('DCF-based', target_dcf))

    # 3. Revenue growth multiple (simple heuristic)
    rev_growth = row.get('rev_growth_yoy', 0)
    profit_margin = 15  # Assume 15% default

    # Try to extract profit margin from earnings_details
    earnings_details = row.get('earnings_details', '{}')
    if isinstance(earnings_details, str):
        try:
            ed = eval(earnings_details)
            profit_margin = ed.get('profit_margin_pct', 15)
        except:
            pass

    if pd.notna(rev_growth) and rev_growth > 0:
        # Growth stocks: P/S ratio based on growth
        # High growth (>30%) = 3-5x P/S, Moderate (15-30%) = 2-3x P/S
        if rev_growth > 30:
            ps_multiple = 4.0
        elif rev_growth > 15:
            ps_multiple = 2.5
        else:
            ps_multiple = 1.5

        market_cap = row.get('market_cap', 0)
        if market_cap > 0 and profit_margin > 0:
            # Estimate revenue from market cap
            estimated_revenue = market_cap / ps_multiple
            # Fair value = revenue * margin improvement
            growth_premium = 1 + (rev_growth / 100) * 0.5  # 50% of growth
            fair_value = price * growth_premium
            estimates.append(('Growth-adjusted', fair_value))

    if not estimates:
        return None

    # Average the estimates
    avg_estimate = np.mean([est[1] for est in estimates])
    return avg_estimate

def analyze_opportunity(row):
    """
    Deep analysis of each opportunity
    Returns: (verdict, confidence, reasoning)
    """
    ticker = row['ticker']
    price = row['current_price']
    target = row.get('target_price_analyst')
    analyst_count = row.get('analyst_count', 0)
    upside = row.get('analyst_upside_pct', 0)

    # Fundamental metrics
    roe = None
    debt_to_equity = None
    profit_margin = None
    rev_growth = row.get('rev_growth_yoy', 0)

    # Extract from health_details
    health_details = row.get('health_details', '{}')
    if isinstance(health_details, str):
        try:
            hd = eval(health_details)
            roe = hd.get('roe_pct')
            debt_to_equity = hd.get('debt_to_equity')
        except:
            pass

    # Extract from earnings_details
    earnings_details = row.get('earnings_details', '{}')
    if isinstance(earnings_details, str):
        try:
            ed = eval(earnings_details)
            profit_margin = ed.get('profit_margin_pct')
        except:
            pass

    fundamental_score = row.get('fundamental_score', 50)
    value_score = row.get('value_score', 0)

    # ANALYSIS
    concerns = []
    strengths = []
    verdict = "HOLD"
    confidence = 50

    # 1. Analyst coverage
    if pd.notna(analyst_count) and analyst_count >= 10:
        strengths.append(f"Alta cobertura de analistas ({int(analyst_count)})")
        confidence += 10
    elif pd.notna(analyst_count) and analyst_count >= 3:
        strengths.append(f"Cobertura moderada ({int(analyst_count)} analistas)")
        confidence += 5
    elif analyst_count == 0 or pd.isna(analyst_count):
        concerns.append("Sin cobertura de analistas - alta incertidumbre")
        confidence -= 20

    # 2. Upside
    if pd.notna(upside):
        if upside > 20:
            strengths.append(f"Upside excepcional (+{upside:.1f}%)")
            confidence += 15
        elif upside > 10:
            strengths.append(f"Buen upside (+{upside:.1f}%)")
            confidence += 10
        elif upside > 5:
            strengths.append(f"Upside moderado (+{upside:.1f}%)")
            confidence += 5
        else:
            concerns.append(f"Upside bajo (+{upside:.1f}%) - poco margen")
            confidence -= 10
    else:
        concerns.append("Sin precio objetivo - difícil valorar")
        confidence -= 15

    # 3. Profitability
    if pd.notna(profit_margin):
        if profit_margin > 20:
            strengths.append(f"Alta rentabilidad (margen {profit_margin:.1f}%)")
            confidence += 10
        elif profit_margin > 10:
            strengths.append(f"Rentabilidad sólida (margen {profit_margin:.1f}%)")
            confidence += 5
        elif profit_margin < 0:
            concerns.append(f"NO RENTABLE (margen {profit_margin:.1f}%)")
            confidence -= 20

    # 4. ROE
    if pd.notna(roe):
        if roe > 15:
            strengths.append(f"ROE excelente ({roe:.1f}%)")
            confidence += 10
        elif roe > 10:
            strengths.append(f"ROE sólido ({roe:.1f}%)")
            confidence += 5
        elif roe < 0:
            concerns.append(f"ROE negativo ({roe:.1f}%) - destruye valor")
            confidence -= 20
        elif roe < 5:
            concerns.append(f"ROE bajo ({roe:.1f}%) - poca rentabilidad")
            confidence -= 10

    # 5. Debt
    if pd.notna(debt_to_equity):
        if debt_to_equity > 2.0:
            concerns.append(f"Alta deuda (D/E {debt_to_equity:.2f})")
            confidence -= 10
        elif debt_to_equity < 0.5:
            strengths.append(f"Balance limpio (D/E {debt_to_equity:.2f})")
            confidence += 5

    # 6. Growth
    if pd.notna(rev_growth):
        if rev_growth > 30:
            strengths.append(f"Crecimiento fuerte ({rev_growth:.1f}%)")
            confidence += 10
        elif rev_growth > 15:
            strengths.append(f"Crecimiento sólido ({rev_growth:.1f}%)")
            confidence += 5
        elif rev_growth < 0:
            concerns.append(f"Ingresos en caída ({rev_growth:.1f}%)")
            confidence -= 15

    # 7. Extreme upside check (suspicious)
    if pd.notna(upside) and upside > 100:
        concerns.append(f"⚠️ Upside extremo ({upside:.1f}%) - poco realista")
        confidence -= 25

    # VERDICT
    if confidence >= 70:
        verdict = "BUY"
    elif confidence >= 50:
        verdict = "HOLD"
    else:
        verdict = "AVOID"

    return {
        'verdict': verdict,
        'confidence': confidence,
        'strengths': strengths,
        'concerns': concerns,
        'roe': roe,
        'profit_margin': profit_margin,
        'debt_to_equity': debt_to_equity,
        'rev_growth': rev_growth
    }

def main():
    print("=" * 100)
    print("DEEP ANALYSIS OF VALUE OPPORTUNITIES")
    print("=" * 100)

    # Load data
    fund_path = Path('docs/fundamental_scores.csv')
    value_path = Path('docs/value_opportunities.csv')

    fund_df = pd.read_csv(fund_path)
    value_df = pd.read_csv(value_path)

    # Merge
    df = value_df.merge(
        fund_df[['ticker', 'health_details', 'earnings_details', 'fundamental_score']],
        on='ticker',
        how='left',
        suffixes=('', '_fund')
    )

    # Filter top opportunities
    top = df.head(15).copy()

    # Calculate fair value for stocks without analysts
    top['ai_fair_value'] = top.apply(calculate_fair_value, axis=1)

    # Analyze each
    analyses = []
    for idx, row in top.iterrows():
        analysis = analyze_opportunity(row)
        analysis['ticker'] = row['ticker']
        analysis['company_name'] = row['company_name']
        analysis['price'] = row['current_price']
        analysis['target'] = row.get('target_price_analyst')
        analysis['ai_target'] = row.get('ai_fair_value')
        analysis['analyst_count'] = row.get('analyst_count', 0)
        analysis['upside'] = row.get('analyst_upside_pct')
        analysis['value_score'] = row['value_score']
        analysis['sector'] = row['sector']
        analyses.append(analysis)

    # Sort by confidence
    analyses = sorted(analyses, key=lambda x: x['confidence'], reverse=True)

    # Print results
    print("\n" + "=" * 100)
    print("RANKING BY CONFIDENCE (AI + FUNDAMENTAL ANALYSIS)")
    print("=" * 100)

    for i, a in enumerate(analyses, 1):
        print(f"\n{'=' * 100}")
        print(f"#{i}. {a['ticker']} - {a['company_name'][:40]}")
        print(f"{'=' * 100}")
        print(f"💰 Precio: ${a['price']:.2f}")

        if pd.notna(a['target']):
            print(f"🎯 Target analistas: ${a['target']:.2f} ({int(a['analyst_count'])} analistas)")
        elif pd.notna(a['ai_target']):
            print(f"🤖 Target estimado (IA): ${a['ai_target']:.2f}")
        else:
            print(f"🎯 Target: N/A")

        if pd.notna(a['upside']):
            print(f"📈 Upside: +{a['upside']:.1f}%")

        print(f"⭐ Value Score: {a['value_score']:.1f}/100")
        print(f"🏢 Sector: {a['sector']}")

        print(f"\n🔍 VEREDICTO: {a['verdict']} (Confianza: {a['confidence']}/100)")

        if a['strengths']:
            print(f"\n✅ FORTALEZAS:")
            for s in a['strengths']:
                print(f"   • {s}")

        if a['concerns']:
            print(f"\n⚠️  PREOCUPACIONES:")
            for c in a['concerns']:
                print(f"   • {c}")

        # Fundamentals summary
        print(f"\n📊 FUNDAMENTALES:")
        if pd.notna(a['roe']):
            print(f"   ROE: {a['roe']:.1f}%")
        if pd.notna(a['profit_margin']):
            print(f"   Margen: {a['profit_margin']:.1f}%")
        if pd.notna(a['debt_to_equity']):
            print(f"   Deuda/Equity: {a['debt_to_equity']:.2f}x")
        if pd.notna(a['rev_growth']):
            print(f"   Crecimiento: {a['rev_growth']:.1f}%")

    # Summary
    print("\n" + "=" * 100)
    print("RESUMEN")
    print("=" * 100)

    buys = [a for a in analyses if a['verdict'] == 'BUY']
    holds = [a for a in analyses if a['verdict'] == 'HOLD']
    avoids = [a for a in analyses if a['verdict'] == 'AVOID']

    print(f"\n🟢 BUY (alta confianza): {len(buys)}")
    for a in buys:
        upside_str = f"+{a['upside']:.1f}%" if pd.notna(a['upside']) else "N/A"
        print(f"   {a['ticker']:<6} ${a['price']:>8.2f} → upside {upside_str:>8} (confianza {a['confidence']})")

    print(f"\n🟡 HOLD (confianza media): {len(holds)}")
    for a in holds:
        upside_str = f"+{a['upside']:.1f}%" if pd.notna(a['upside']) else "N/A"
        print(f"   {a['ticker']:<6} ${a['price']:>8.2f} → upside {upside_str:>8} (confianza {a['confidence']})")

    print(f"\n🔴 AVOID (baja confianza): {len(avoids)}")
    for a in avoids:
        upside_str = f"+{a['upside']:.1f}%" if pd.notna(a['upside']) else "N/A"
        print(f"   {a['ticker']:<6} ${a['price']:>8.2f} → upside {upside_str:>8} (confianza {a['confidence']})")

if __name__ == '__main__':
    main()

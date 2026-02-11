#!/usr/bin/env python3
"""
INVESTMENT THESIS GENERATOR
Genera narrativas de inversión explicando el "WHY" detrás de cada opportunity
"""
from typing import Dict, List


class InvestmentThesisGenerator:
    """Genera tesis de inversión basadas en scores 5D"""

    @staticmethod
    def generate_thesis(opportunity: Dict) -> str:
        """
        Genera investment thesis completa explicando por qué es una buena opportunity

        Args:
            opportunity: Dict con todos los datos del 5D analyzer

        Returns:
            String con la tesis de inversión narrativa
        """
        thesis_parts = []
        ticker = opportunity.get('ticker', 'Unknown')

        # 1. VCP Analysis
        vcp_score = opportunity.get('vcp_score', 0)
        if vcp_score >= 85:
            thesis_parts.append(f"📈 STRONG VCP: Patrón de alta calidad ({vcp_score:.0f}/100) indicando consolidación saludable y potencial breakout")
        elif vcp_score >= 70:
            thesis_parts.append(f"📊 SOLID VCP: Patrón bien formado ({vcp_score:.0f}/100) con contracciones progresivas")

        # 2. Insider Buying
        insiders_score = opportunity.get('insiders_score', 0)
        timing_conv = opportunity.get('timing_convergence', False)

        if insiders_score >= 90:
            if timing_conv:
                timing_reason = opportunity.get('timing_reason', '')
                thesis_parts.append(f"🔥 TIMING PERFECTO: {timing_reason}")
            else:
                thesis_parts.append(f"👔 HIGH INSIDER CONVICTION: Compras recurrentes de insiders ({insiders_score:.0f}/100) señalando fuerte convicción interna")
        elif insiders_score >= 70:
            thesis_parts.append(f"✅ INSIDER SUPPORT: Actividad positiva de insiders ({insiders_score:.0f}/100)")

        # 3. Sector Momentum
        sector_name = opportunity.get('sector_name', 'Unknown')
        sector_momentum = opportunity.get('sector_momentum', 'stable')
        sector_score = opportunity.get('sector_score', 0)

        if sector_momentum == 'leading':
            thesis_parts.append(f"🚀 SECTOR LEADING: {sector_name} en momentum ascendente - rotación favorable ({sector_score:.0f}/100)")
        elif sector_momentum == 'improving':
            thesis_parts.append(f"📈 SECTOR IMPROVING: {sector_name} saliendo de debilidad ({sector_score:.0f}/100)")
        elif sector_score >= 70:
            thesis_parts.append(f"✅ SECTOR STABLE: {sector_name} con momentum sólido ({sector_score:.0f}/100)")

        # 4. Institutional Support
        num_whales = opportunity.get('num_whales', 0)
        top_whales = opportunity.get('top_whales', '')
        inst_score = opportunity.get('institutional_score', 0)

        if num_whales >= 5:
            thesis_parts.append(f"🐋 INSTITUTIONAL SUPPORT: {num_whales} whales con posiciones activas ({inst_score:.0f}/100)")
            if top_whales:
                whale_list = top_whales.split(', ')[:2]  # Top 2
                thesis_parts.append(f"   Incluye: {', '.join(whale_list)}")
        elif num_whales > 0:
            thesis_parts.append(f"🏛️ Institutional holdings: {num_whales} fondos institucionales")

        # 5. VCP Repeater Bonus
        is_repeater = opportunity.get('vcp_repeater', False)
        if is_repeater:
            repeat_count = opportunity.get('repeat_count', 0)
            repeater_bonus = opportunity.get('repeater_bonus', 0)
            thesis_parts.append(f"🔁 VCP REPEATER: Stock formó VCP patterns {repeat_count}x históricamente - track record comprobado (+{repeater_bonus} bonus)")

        # 6. Fundamentals & Price Targets
        upside = opportunity.get('upside_percent')
        price_target = opportunity.get('price_target')
        fundamental_score = opportunity.get('fundamental_score', 50)

        if upside and upside > 20:
            thesis_parts.append(f"💰 UPSIDE POTENTIAL: {upside:.0f}% hasta precio objetivo ${price_target:.2f}")

        # Fundamental highlights
        fund_highlights = []
        fcf_yield = opportunity.get('fcf_yield')
        roe = opportunity.get('roe')
        revenue_growth = opportunity.get('revenue_growth')

        if fcf_yield and fcf_yield > 5:
            fund_highlights.append(f"FCF yield {fcf_yield:.1f}%")
        if roe and roe > 15:
            fund_highlights.append(f"ROE {roe*100:.0f}%")
        if revenue_growth and revenue_growth > 15:
            fund_highlights.append(f"Revenue growth {revenue_growth*100:.0f}%")

        if fund_highlights:
            thesis_parts.append(f"📊 FUNDAMENTALS: {', '.join(fund_highlights)} (Score: {fundamental_score:.0f}/100)")

        # 7. Overall Conviction
        super_score = opportunity.get('super_score_5d', 0)
        tier = opportunity.get('tier', '')

        if super_score >= 80:
            conviction = "🌟 HIGHEST CONVICTION"
        elif super_score >= 70:
            conviction = "💎 HIGH CONVICTION"
        elif super_score >= 60:
            conviction = "✅ GOOD CONVICTION"
        else:
            conviction = "⚡ MODERATE"

        # Compose final thesis
        thesis = f"{conviction} ({super_score:.1f}/100 - {tier})\n\n"
        thesis += "\n".join([f"• {part}" for part in thesis_parts])

        return thesis

    @staticmethod
    def generate_short_thesis(opportunity: Dict) -> str:
        """
        Genera versión corta de la tesis (1-2 líneas) para CSV
        """
        parts = []

        # Key signals
        vcp_score = opportunity.get('vcp_score', 0)
        if vcp_score >= 85:
            parts.append(f"Strong VCP ({vcp_score:.0f})")

        if opportunity.get('timing_convergence'):
            parts.append("Perfect Timing")
        elif opportunity.get('insiders_score', 0) >= 90:
            parts.append("High Insider Activity")

        if opportunity.get('sector_momentum') == 'leading':
            parts.append(f"{opportunity.get('sector_name', '')} LEADING")

        if opportunity.get('vcp_repeater'):
            count = opportunity.get('repeat_count', 0)
            parts.append(f"Repeater {count}x")

        if opportunity.get('upside_percent', 0) > 25:
            parts.append(f"{opportunity.get('upside_percent', 0):.0f}% upside")

        return " | ".join(parts) if parts else "Multiple signals converging"


def add_thesis_to_opportunities(opportunities: List[Dict]) -> List[Dict]:
    """
    Añade investment thesis a cada opportunity

    Args:
        opportunities: Lista de opportunities del 5D analyzer

    Returns:
        Lista de opportunities con thesis añadidas
    """
    generator = InvestmentThesisGenerator()

    for opp in opportunities:
        opp['investment_thesis'] = generator.generate_thesis(opp)
        opp['thesis_short'] = generator.generate_short_thesis(opp)

    return opportunities


if __name__ == "__main__":
    # Test con opportunity de ejemplo
    test_opp = {
        'ticker': 'CPAY',
        'super_score_5d': 89.1,
        'tier': '⭐⭐⭐ EXCELENTE',
        'vcp_score': 90.29,
        'insiders_score': 90,
        'sector_score': 72.4,
        'institutional_score': 45,
        'sector_name': 'Technology',
        'sector_momentum': 'leading',
        'timing_convergence': True,
        'timing_reason': '🔥 TIMING PERFECTO: 4 compras de insiders durante VCP base (3 días)',
        'vcp_repeater': True,
        'repeat_count': 2,
        'repeater_bonus': 6,
        'upside_percent': 31.3,
        'price_target': 467.98,
        'fundamental_score': 55,
        'fcf_yield': 7.74,
        'roe': 0.29,
        'revenue_growth': 0.207,
        'num_whales': 3,
        'top_whales': 'Vanguard, Blackrock, State Street'
    }

    generator = InvestmentThesisGenerator()

    print("=" * 80)
    print(f"INVESTMENT THESIS: {test_opp['ticker']}")
    print("=" * 80)
    print()
    print(generator.generate_thesis(test_opp))
    print()
    print("=" * 80)
    print("SHORT THESIS:")
    print(generator.generate_short_thesis(test_opp))
    print("=" * 80)

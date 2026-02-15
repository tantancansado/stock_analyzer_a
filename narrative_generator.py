#!/usr/bin/env python3
"""
NARRATIVE GENERATOR
Genera narrativas de inversión explicando por qué una empresa es oportunidad

Analiza:
- Fundamentales (FCF, deuda, márgenes, growth)
- Contexto del sector
- Razón de la bajada actual
- Por qué es oportunidad vs red flag
"""

import pandas as pd
from typing import Dict, Optional
from seeking_alpha_client import SeekingAlphaClient


class NarrativeGenerator:
    """Genera narrativas de inversión basadas en análisis fundamental"""

    def __init__(self):
        self.sa_client = SeekingAlphaClient()

    def generate_narrative(self, ticker: str, opportunity_data: Dict) -> Dict:
        """
        Genera narrativa completa de inversión

        Args:
            ticker: Ticker symbol
            opportunity_data: Data from super_opportunities CSV

        Returns:
            Dict con narrativa estructurada
        """
        # Get fundamental data
        fundamental_analysis = self._analyze_fundamentals(ticker, opportunity_data)

        # Get sector context
        sector_context = self._analyze_sector_context(opportunity_data)

        # Analyze price action reason
        price_action = self._analyze_price_action(opportunity_data)

        # Generate investment thesis
        thesis = self._generate_thesis(
            ticker,
            fundamental_analysis,
            sector_context,
            price_action,
            opportunity_data
        )

        return {
            'ticker': ticker,
            'thesis': thesis,
            'fundamental_highlights': fundamental_analysis['highlights'],
            'risks': fundamental_analysis['risks'],
            'sector_tailwinds': sector_context['tailwinds'],
            'price_action_reason': price_action['reason'],
            'opportunity_type': price_action['opportunity_type']
        }

    def _analyze_fundamentals(self, ticker: str, data: Dict) -> Dict:
        """Analiza salud fundamental de la empresa"""
        highlights = []
        risks = []

        # Revenue Growth
        growth = data.get('revenue_growth_yoy', 0) or data.get('growth_acceleration_score', 0)
        if growth > 15:
            highlights.append(f"Strong revenue growth ({growth:.0f}%+ YoY)")
        elif growth < 5:
            risks.append(f"Slow revenue growth ({growth:.0f}% YoY)")

        # Profitability (PE ratio analysis)
        pe = data.get('pe_ratio')
        if pe and pe > 0:
            if pe < 15:
                highlights.append(f"Undervalued (PE: {pe:.1f})")
            elif pe > 40:
                risks.append(f"High valuation (PE: {pe:.1f})")

        # Earnings Quality
        earnings_quality = data.get('earnings_quality_score', 0)
        if earnings_quality >= 70:
            highlights.append("High earnings quality")
        elif earnings_quality < 40:
            risks.append("Weak earnings quality")

        # Financial Health
        financial_health = data.get('financial_health_score', 0)
        if financial_health >= 70:
            highlights.append("Strong balance sheet")
        elif financial_health < 40:
            risks.append("Balance sheet concerns")

        # Relative Strength
        rs_score = data.get('relative_strength_score', 0)
        if rs_score >= 80:
            highlights.append(f"Outperforming market (RS: {rs_score:.0f})")
        elif rs_score < 40:
            risks.append(f"Underperforming market (RS: {rs_score:.0f})")

        return {
            'highlights': highlights,
            'risks': risks
        }

    def _analyze_sector_context(self, data: Dict) -> Dict:
        """Analiza contexto del sector"""
        sector = data.get('sector', '')

        # Sector-specific analysis
        sector_insights = {
            'Technology': {
                'tailwinds': ['AI adoption', 'Cloud migration', 'Digital transformation'],
                'headwinds': ['High interest rates', 'Competition']
            },
            'Healthcare': {
                'tailwinds': ['Aging population', 'Innovation', 'Biotech advances'],
                'headwinds': ['Regulation', 'Drug pricing pressure']
            },
            'Energy': {
                'tailwinds': ['Energy transition', 'Supply constraints'],
                'headwinds': ['Volatility', 'Climate concerns']
            },
            'Financial': {
                'tailwinds': ['Higher rates benefit', 'Economic growth'],
                'headwinds': ['Recession risk', 'Credit concerns']
            },
            'Consumer': {
                'tailwinds': ['Brand loyalty', 'Pricing power'],
                'headwinds': ['Consumer weakness', 'Inflation']
            },
            'Industrial': {
                'tailwinds': ['Infrastructure spending', 'Manufacturing reshoring'],
                'headwinds': ['Economic slowdown']
            },
            'Real Estate': {
                'tailwinds': ['Supply constraints', 'Demographics'],
                'headwinds': ['High interest rates', 'Office weakness']
            }
        }

        context = sector_insights.get(sector, {
            'tailwinds': ['Sector-specific opportunities'],
            'headwinds': ['Market risks']
        })

        return context

    def _analyze_price_action(self, data: Dict) -> Dict:
        """Analiza razón de movimiento de precio y si es oportunidad"""
        price_vs_ath = data.get('price_vs_ath', 0)
        vcp_score = data.get('vcp_score', 0)
        validation_status = data.get('validation_status', '')

        # Determine reason for price movement
        if price_vs_ath and price_vs_ath < -20:
            reason = f"Price pulled back {abs(price_vs_ath):.1f}% from ATH"

            # Is this a buying opportunity or red flag?
            if vcp_score >= 80:
                opportunity_type = "HEALTHY_PULLBACK"
                explanation = "Pullback with strong accumulation pattern (VCP) - institutions buying the dip"
            elif data.get('fundamental_score', 0) >= 60:
                opportunity_type = "FUNDAMENTAL_OPPORTUNITY"
                explanation = "Fundamentals remain strong despite price weakness - market overreaction"
            else:
                opportunity_type = "RISKY_FALLING_KNIFE"
                explanation = "⚠️ Price weakness may reflect underlying issues"

        elif price_vs_ath and price_vs_ath > -5:
            reason = f"Near all-time high (only {abs(price_vs_ath):.1f}% below)"
            if vcp_score >= 85:
                opportunity_type = "BREAKOUT_SETUP"
                explanation = "Strong base near highs - ready for new breakout"
            else:
                opportunity_type = "MOMENTUM_PLAY"
                explanation = "Extended move - wait for better entry or use tight stop"

        else:
            reason = f"Moderate pullback ({abs(price_vs_ath):.1f}% from high)"
            opportunity_type = "BALANCED_SETUP"
            explanation = "Healthy consolidation after run-up"

        return {
            'reason': reason,
            'opportunity_type': opportunity_type,
            'explanation': explanation
        }

    def _generate_thesis(
        self,
        ticker: str,
        fundamentals: Dict,
        sector: Dict,
        price_action: Dict,
        data: Dict
    ) -> str:
        """Genera tesis de inversión narrativa"""

        company_name = data.get('company_name', ticker)
        sector_name = data.get('sector', 'its sector')

        # Opening
        thesis = f"**{company_name} ({ticker})** is presenting a {price_action['opportunity_type'].lower().replace('_', ' ')} opportunity. "

        # Price action context
        thesis += f"{price_action['reason']}. {price_action['explanation']}.\n\n"

        # Fundamental strengths
        if fundamentals['highlights']:
            thesis += "**Fundamental Strengths:**\n"
            for highlight in fundamentals['highlights']:
                thesis += f"- {highlight}\n"
            thesis += "\n"

        # Sector context
        if sector['tailwinds']:
            thesis += f"**{sector_name} Tailwinds:**\n"
            for tailwind in sector['tailwinds'][:3]:  # Top 3
                thesis += f"- {tailwind}\n"
            thesis += "\n"

        # Risks
        if fundamentals['risks']:
            thesis += "**Key Risks:**\n"
            for risk in fundamentals['risks']:
                thesis += f"- {risk}\n"
            thesis += "\n"

        # Target price reasoning
        entry = data.get('entry_price', 0)
        target = data.get('exit_price', 0)
        if entry and target:
            upside = ((target - entry) / entry) * 100
            thesis += f"**Price Target:** ${target:.2f} ({upside:.0f}% upside from entry)\n"
            thesis += "Target based on:\n"
            thesis += "- Fair value analysis (PE multiple expansion)\n"
            thesis += "- Technical resistance levels (prior highs)\n"
            thesis += "- Sector peer valuation comparison\n"

        return thesis


def add_narratives_to_opportunities(
    input_file: str = 'docs/super_opportunities_with_prices.csv',
    output_file: str = 'docs/super_opportunities_with_narratives.csv'
):
    """Añade narrativas a las oportunidades"""

    print("\n" + "="*80)
    print("📝 ADDING INVESTMENT NARRATIVES")
    print("="*80 + "\n")

    df = pd.read_csv(input_file)
    print(f"✅ Loaded {len(df)} opportunities")

    generator = NarrativeGenerator()

    # Add narratives to top 10
    narratives = []
    for idx, row in df.head(10).iterrows():
        ticker = row['ticker']
        print(f"\n[{idx+1}/10] Generating narrative for {ticker}...")

        try:
            narrative = generator.generate_narrative(ticker, row.to_dict())

            result = row.to_dict()
            result['investment_thesis'] = narrative['thesis']
            result['opportunity_type'] = narrative['opportunity_type']
            result['price_action_reason'] = narrative['price_action_reason']

            narratives.append(result)

            print(f"   ✅ Generated ({narrative['opportunity_type']})")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            continue

    if narratives:
        result_df = pd.DataFrame(narratives)
        result_df.to_csv(output_file, index=False)

        print(f"\n{'='*80}")
        print(f"✅ SAVED {len(result_df)} opportunities with narratives")
        print(f"📁 Output: {output_file}")
        print(f"{'='*80}\n")
    else:
        print("\n❌ No narratives generated")


if __name__ == "__main__":
    add_narratives_to_opportunities()

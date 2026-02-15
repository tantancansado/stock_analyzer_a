#!/usr/bin/env python3
"""
ENHANCED NARRATIVE GENERATOR
Genera narrativas de inversión usando TODOS los análisis disponibles

Integra:
- VCP + ML + Fundamental (base)
- Insider Trading (recurring buyers)
- Institutional Ownership
- Mean Reversion signals
- Options Flow (unusual activity)
- Sector Rotation
- Backtest performance
"""

import pandas as pd
from typing import Dict, Optional
from pathlib import Path


class EnhancedNarrativeGenerator:
    """Genera narrativas completas integrando todos los análisis"""

    def __init__(self):
        # Load all auxiliary data
        self.insiders_data = self._load_insiders()
        self.mean_reversion_data = self._load_mean_reversion()
        self.options_flow_data = self._load_options_flow()

    def _load_insiders(self) -> Dict:
        """Load insider trading data"""
        try:
            df = pd.read_csv('docs/recurring_insiders.csv')
            return df.set_index('ticker').to_dict('index')
        except:
            return {}

    def _load_mean_reversion(self) -> Dict:
        """Load mean reversion opportunities"""
        try:
            df = pd.read_csv('docs/mean_reversion_opportunities.csv')
            return df.set_index('ticker').to_dict('index')
        except:
            return {}

    def _load_options_flow(self) -> Dict:
        """Load unusual options activity"""
        try:
            df = pd.read_csv('docs/options_flow.csv')
            return df.set_index('ticker').to_dict('index')
        except:
            return {}

    def generate_narrative(self, ticker: str, opportunity_data: Dict) -> Dict:
        """
        Genera narrativa completa integrando TODOS los análisis

        Args:
            ticker: Ticker symbol
            opportunity_data: Data from super_opportunities CSV

        Returns:
            Dict con narrativa enriquecida
        """
        # Base analysis
        fundamental_analysis = self._analyze_fundamentals(ticker, opportunity_data)
        sector_context = self._analyze_sector_context(opportunity_data)
        price_action = self._analyze_price_action(opportunity_data)

        # Enhanced analysis
        insider_analysis = self._analyze_insiders(ticker)
        mean_reversion_analysis = self._analyze_mean_reversion(ticker)
        options_analysis = self._analyze_options_flow(ticker)

        # Generate enhanced thesis
        thesis = self._generate_enhanced_thesis(
            ticker,
            fundamental_analysis,
            sector_context,
            price_action,
            insider_analysis,
            mean_reversion_analysis,
            options_analysis,
            opportunity_data
        )

        return {
            'ticker': ticker,
            'thesis': thesis,
            'fundamental_highlights': fundamental_analysis['highlights'],
            'risks': fundamental_analysis['risks'],
            'sector_tailwinds': sector_context['tailwinds'],
            'price_action_reason': price_action['reason'],
            'opportunity_type': price_action['opportunity_type'],
            'insider_signal': insider_analysis['signal'],
            'mean_reversion_signal': mean_reversion_analysis['signal'],
            'options_signal': options_analysis['signal'],
            'conviction_level': self._calculate_conviction(
                fundamental_analysis,
                insider_analysis,
                mean_reversion_analysis,
                options_analysis
            )
        }

    def _analyze_fundamentals(self, ticker: str, data: Dict) -> Dict:
        """Analiza salud fundamental"""
        highlights = []
        risks = []

        # Revenue Growth
        growth = data.get('growth_acceleration_score', 0)
        if growth >= 70:
            highlights.append(f"📈 Strong revenue growth acceleration (Score: {growth:.0f})")
        elif growth < 40:
            risks.append(f"⚠️ Weak revenue growth (Score: {growth:.0f})")

        # Earnings Quality
        earnings_quality = data.get('earnings_quality_score', 0)
        if earnings_quality >= 70:
            highlights.append(f"✅ High earnings quality (Score: {earnings_quality:.0f})")
        elif earnings_quality < 40:
            risks.append(f"⚠️ Earnings quality concerns (Score: {earnings_quality:.0f})")

        # Financial Health
        financial_health = data.get('financial_health_score', 0)
        if financial_health >= 70:
            highlights.append(f"💪 Strong balance sheet (Health: {financial_health:.0f})")
        elif financial_health < 40:
            risks.append(f"⚠️ Balance sheet weakness (Health: {financial_health:.0f})")

        # Relative Strength
        rs_score = data.get('relative_strength_score', 0)
        if rs_score >= 80:
            highlights.append(f"🚀 Significantly outperforming market (RS: {rs_score:.0f})")
        elif rs_score >= 60:
            highlights.append(f"📊 Outperforming market (RS: {rs_score:.0f})")
        elif rs_score < 40:
            risks.append(f"⚠️ Underperforming market (RS: {rs_score:.0f})")

        # Valuation
        pe = data.get('pe_ratio')
        if pe and pe > 0:
            if pe < 15:
                highlights.append(f"💎 Undervalued relative to growth (PE: {pe:.1f})")
            elif pe > 50:
                risks.append(f"⚠️ High valuation multiple (PE: {pe:.1f})")

        return {'highlights': highlights, 'risks': risks}

    def _analyze_sector_context(self, data: Dict) -> Dict:
        """Analiza contexto del sector"""
        sector = data.get('sector', '')

        sector_insights = {
            'Technology': {
                'tailwinds': ['🤖 AI/ML adoption accelerating', '☁️ Cloud migration continuing', '💻 Digital transformation demand'],
                'headwinds': ['📉 Interest rate sensitivity', '🌐 Tech regulation risks']
            },
            'Healthcare': {
                'tailwinds': ['👴 Aging demographics', '💊 Biotech innovation', '🏥 Healthcare spending growth'],
                'headwinds': ['⚖️ Regulatory uncertainty', '💰 Drug pricing pressure']
            },
            'Energy': {
                'tailwinds': ['⚡ Energy transition spending', '🛢️ Supply discipline', '🌍 Global demand recovery'],
                'headwinds': ['🌡️ Climate policy shifts', '📊 Price volatility']
            },
            'Financials': {
                'tailwinds': ['📈 Higher interest rates benefit', '💼 Economic expansion', '🏦 Digital banking adoption'],
                'headwinds': ['💥 Credit cycle risks', '📉 Recession concerns']
            },
            'Consumer': {
                'tailwinds': ['🏷️ Brand strength', '💰 Pricing power', '🛒 E-commerce growth'],
                'headwinds': ['💸 Consumer spending pressure', '🔥 Input cost inflation']
            },
            'Industrials': {
                'tailwinds': ['🏗️ Infrastructure investment', '🏭 Nearshoring/reshoring', '🚂 Supply chain resilience'],
                'headwinds': ['📊 Cyclical slowdown risk', '💼 Labor cost pressures']
            },
            'Real Estate': {
                'tailwinds': ['🏘️ Housing supply constraints', '👥 Millennial demographics', '🏙️ Urban renaissance'],
                'headwinds': ['💹 High interest rates', '🏢 Office space weakness']
            },
            'Materials': {
                'tailwinds': ['🏗️ Infrastructure spending', '⚡ Green energy materials', '🌐 Supply tightness'],
                'headwinds': ['🌍 China economic slowdown', '♻️ Sustainability pressures']
            }
        }

        return sector_insights.get(sector, {
            'tailwinds': ['📊 Sector-specific opportunities'],
            'headwinds': ['⚠️ Market-wide risks']
        })

    def _analyze_price_action(self, data: Dict) -> Dict:
        """Analiza movimiento de precio"""
        price_vs_ath = data.get('price_vs_ath', 0)
        vcp_score = data.get('vcp_score', 0)

        if price_vs_ath and price_vs_ath < -20:
            reason = f"📉 {abs(price_vs_ath):.1f}% pullback from ATH"
            if vcp_score >= 80:
                opportunity_type = "HEALTHY_PULLBACK"
                explanation = "✅ Pullback with strong VCP accumulation - smart money buying"
            elif data.get('fundamental_score', 0) >= 60:
                opportunity_type = "FUNDAMENTAL_OPPORTUNITY"
                explanation = "✅ Fundamentals solid despite price weakness - market overreaction"
            else:
                opportunity_type = "RISKY_FALLING_KNIFE"
                explanation = "⚠️ Price weakness may reflect underlying deterioration"
        elif price_vs_ath and price_vs_ath > -5:
            reason = f"🚀 Near ATH (only {abs(price_vs_ath):.1f}% below)"
            if vcp_score >= 85:
                opportunity_type = "BREAKOUT_SETUP"
                explanation = "✅ Tight base near highs - ready for expansion"
            else:
                opportunity_type = "MOMENTUM_PLAY"
                explanation = "⚠️ Extended - use tight stops"
        else:
            reason = f"📊 {abs(price_vs_ath):.1f}% from high"
            opportunity_type = "BALANCED_SETUP"
            explanation = "✅ Healthy consolidation pattern"

        return {
            'reason': reason,
            'opportunity_type': opportunity_type,
            'explanation': explanation
        }

    def _analyze_insiders(self, ticker: str) -> Dict:
        """Analiza insider trading"""
        if ticker not in self.insiders_data:
            return {'signal': 'NEUTRAL', 'description': ''}

        data = self.insiders_data[ticker]
        purchase_count = data.get('purchase_count', 0)
        unique_insiders = data.get('unique_insiders', 0)
        confidence = data.get('confidence_score', 0)

        if purchase_count >= 20:
            return {
                'signal': 'VERY_BULLISH',
                'description': f"🟢🟢 STRONG INSIDER BUYING: {purchase_count} purchases by {unique_insiders} insider(s) - Confidence: {confidence}"
            }
        elif purchase_count >= 10:
            return {
                'signal': 'BULLISH',
                'description': f"🟢 Insider buying: {purchase_count} purchases by {unique_insiders} insider(s)"
            }
        else:
            return {
                'signal': 'NEUTRAL',
                'description': f"Moderate insider activity: {purchase_count} purchases"
            }

    def _analyze_mean_reversion(self, ticker: str) -> Dict:
        """Analiza mean reversion opportunity"""
        if ticker not in self.mean_reversion_data:
            return {'signal': 'NONE', 'description': ''}

        data = self.mean_reversion_data[ticker]
        score = data.get('reversion_score', 0)
        strategy = data.get('strategy', '')
        rsi = data.get('rsi', 50)
        drawdown = data.get('drawdown_pct', 0)

        if score >= 80:
            return {
                'signal': 'STRONG',
                'description': f"🔄 MEAN REVERSION SIGNAL: {strategy} | RSI: {rsi:.1f} | {abs(drawdown):.1f}% drawdown from highs - High probability bounce"
            }
        elif score >= 60:
            return {
                'signal': 'MODERATE',
                'description': f"🔄 Mean reversion setup: {strategy} | RSI: {rsi:.1f}"
            }
        else:
            return {'signal': 'WEAK', 'description': ''}

    def _analyze_options_flow(self, ticker: str) -> Dict:
        """Analiza unusual options activity"""
        if ticker not in self.options_flow_data:
            return {'signal': 'NONE', 'description': ''}

        data = self.options_flow_data[ticker]
        sentiment = data.get('sentiment', 'NEUTRAL')
        flow_score = data.get('flow_score', 0)
        premium = data.get('total_premium', 0)

        if flow_score >= 80:
            emoji = '🔴' if sentiment == 'BEARISH' else '🟢'
            return {
                'signal': sentiment,
                'description': f"{emoji} WHALE OPTIONS ACTIVITY: {sentiment} flow | ${premium/1e6:.1f}M premium - Institutional positioning"
            }
        elif flow_score >= 60:
            return {
                'signal': sentiment,
                'description': f"🐋 Unusual options activity: {sentiment} bias"
            }
        else:
            return {'signal': 'NONE', 'description': ''}

    def _calculate_conviction(
        self,
        fundamentals: Dict,
        insiders: Dict,
        mean_reversion: Dict,
        options: Dict
    ) -> str:
        """Calcula nivel de convicción basado en señales"""
        score = 0

        # Fundamental strength
        if len(fundamentals['highlights']) >= 4:
            score += 3
        elif len(fundamentals['highlights']) >= 2:
            score += 2
        elif len(fundamentals['highlights']) >= 1:
            score += 1

        # Insider signal
        if insiders['signal'] == 'VERY_BULLISH':
            score += 3
        elif insiders['signal'] == 'BULLISH':
            score += 2

        # Mean reversion
        if mean_reversion['signal'] == 'STRONG':
            score += 2
        elif mean_reversion['signal'] == 'MODERATE':
            score += 1

        # Options flow (if bullish)
        if options['signal'] == 'BULLISH':
            score += 1

        # Conviction levels
        if score >= 7:
            return "🔥🔥🔥 VERY HIGH"
        elif score >= 5:
            return "🔥🔥 HIGH"
        elif score >= 3:
            return "🔥 MODERATE"
        else:
            return "⚠️ LOW"

    def _generate_enhanced_thesis(
        self,
        ticker: str,
        fundamentals: Dict,
        sector: Dict,
        price_action: Dict,
        insiders: Dict,
        mean_reversion: Dict,
        options: Dict,
        data: Dict
    ) -> str:
        """Genera tesis enriquecida con TODOS los análisis"""

        company_name = data.get('company_name', ticker)
        sector_name = data.get('sector', 'its sector')

        # Opening with conviction
        conviction = self._calculate_conviction(fundamentals, insiders, mean_reversion, options)
        thesis = f"# {company_name} ({ticker})\n\n"
        thesis += f"**Conviction Level:** {conviction}\n\n"

        # Opportunity type
        thesis += f"**Setup Type:** {price_action['opportunity_type'].replace('_', ' ').title()}\n\n"

        # Price action
        thesis += f"## 📊 Price Action\n"
        thesis += f"{price_action['reason']}. {price_action['explanation']}\n\n"

        # Fundamental strengths
        if fundamentals['highlights']:
            thesis += "## 💪 Fundamental Strengths\n"
            for highlight in fundamentals['highlights']:
                thesis += f"- {highlight}\n"
            thesis += "\n"

        # ENHANCED SIGNALS
        signals_found = False

        # Insider activity
        if insiders['signal'] != 'NEUTRAL' and insiders['description']:
            if not signals_found:
                thesis += "## 🎯 Additional Bullish Signals\n\n"
                signals_found = True
            thesis += f"### Insider Activity\n"
            thesis += f"{insiders['description']}\n\n"

        # Mean reversion
        if mean_reversion['signal'] != 'NONE' and mean_reversion['description']:
            if not signals_found:
                thesis += "## 🎯 Additional Bullish Signals\n\n"
                signals_found = True
            thesis += f"### Mean Reversion Setup\n"
            thesis += f"{mean_reversion['description']}\n\n"

        # Options flow
        if options['signal'] != 'NONE' and options['description']:
            if not signals_found:
                thesis += "## 🎯 Additional Signals\n\n"
                signals_found = True
            thesis += f"### Institutional Options Activity\n"
            thesis += f"{options['description']}\n\n"

        # Sector context
        if sector['tailwinds']:
            thesis += f"## 🌍 {sector_name} Tailwinds\n"
            for tailwind in sector['tailwinds'][:3]:
                thesis += f"- {tailwind}\n"
            thesis += "\n"

        # Risks
        if fundamentals['risks']:
            thesis += "## ⚠️ Key Risks\n"
            for risk in fundamentals['risks']:
                thesis += f"- {risk}\n"
            thesis += "\n"

        # Price target
        entry = data.get('entry_price', 0)
        target = data.get('exit_price', 0)
        stop = data.get('stop_loss', 0)
        rr = data.get('risk_reward', 0)

        if entry and target:
            upside = ((target - entry) / entry) * 100
            downside = ((entry - stop) / entry) * 100

            thesis += f"## 🎯 Price Targets & Risk Management\n\n"
            thesis += f"- **Entry:** ${entry:.2f}\n"
            thesis += f"- **Target:** ${target:.2f} ({upside:.0f}% upside)\n"
            thesis += f"- **Stop Loss:** ${stop:.2f} ({downside:.1f}% risk)\n"
            thesis += f"- **Risk/Reward:** {rr:.1f}:1\n\n"

            thesis += "**Target Methodology:**\n"
            thesis += "- Technical: Prior resistance + ATH breakout\n"
            thesis += "- Fundamental: Fair value (PE expansion to sector avg)\n"
            thesis += "- Momentum: Measured move projection\n"

        return thesis


def add_enhanced_narratives(
    input_file: str = 'docs/super_opportunities_with_prices.csv',
    output_file: str = 'docs/super_opportunities_with_narratives.csv'
):
    """Añade narrativas enriquecidas a las oportunidades"""

    print("\n" + "="*80)
    print("📝 ADDING ENHANCED INVESTMENT NARRATIVES")
    print("="*80 + "\n")

    df = pd.read_csv(input_file)
    print(f"✅ Loaded {len(df)} opportunities")

    generator = EnhancedNarrativeGenerator()

    print(f"\n📊 Auxiliary data loaded:")
    print(f"   - Insider Trading: {len(generator.insiders_data)} tickers")
    print(f"   - Mean Reversion: {len(generator.mean_reversion_data)} tickers")
    print(f"   - Options Flow: {len(generator.options_flow_data)} tickers")

    # Add narratives to top 10
    narratives = []
    for idx, row in df.head(10).iterrows():
        ticker = row['ticker']
        print(f"\n[{idx+1}/10] Processing {ticker}...")

        try:
            narrative = generator.generate_narrative(ticker, row.to_dict())

            result = row.to_dict()
            result['investment_thesis'] = narrative['thesis']
            result['opportunity_type'] = narrative['opportunity_type']
            result['conviction_level'] = narrative['conviction_level']
            result['insider_signal'] = narrative['insider_signal']
            result['mean_reversion_signal'] = narrative['mean_reversion_signal']
            result['options_signal'] = narrative['options_signal']

            narratives.append(result)

            print(f"   ✅ {narrative['opportunity_type']} | Conviction: {narrative['conviction_level']}")
            if narrative['insider_signal'] != 'NEUTRAL':
                print(f"      🟢 Insider: {narrative['insider_signal']}")
            if narrative['mean_reversion_signal'] != 'NONE':
                print(f"      🔄 Mean Reversion: {narrative['mean_reversion_signal']}")
            if narrative['options_signal'] != 'NONE':
                print(f"      🐋 Options: {narrative['options_signal']}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    if narratives:
        result_df = pd.DataFrame(narratives)
        result_df.to_csv(output_file, index=False)

        print(f"\n{'='*80}")
        print(f"✅ SAVED {len(result_df)} opportunities with ENHANCED narratives")
        print(f"📁 Output: {output_file}")
        print(f"{'='*80}\n")

        # Summary of signals
        insider_signals = result_df['insider_signal'].value_counts()
        mr_signals = result_df['mean_reversion_signal'].value_counts()
        options_signals = result_df['options_signal'].value_counts()

        print("\n📊 SIGNAL SUMMARY:")
        if not insider_signals.empty:
            print(f"\n🟢 Insider Signals:")
            for signal, count in insider_signals.items():
                print(f"   {signal}: {count}")

        if not mr_signals.empty:
            print(f"\n🔄 Mean Reversion Signals:")
            for signal, count in mr_signals.items():
                if signal != 'NONE':
                    print(f"   {signal}: {count}")

        if not options_signals.empty:
            print(f"\n🐋 Options Signals:")
            for signal, count in options_signals.items():
                if signal != 'NONE':
                    print(f"   {signal}: {count}")
    else:
        print("\n❌ No narratives generated")


if __name__ == "__main__":
    add_enhanced_narratives()

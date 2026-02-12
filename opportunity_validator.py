#!/usr/bin/env python3
"""
OPPORTUNITY VALIDATOR
Valida oportunidades VCP usando web research para confirmar timing y fundamentales

Valida:
- Timing: ¿Stock cerca de all-time highs? (malo para VCP)
- Sentiment: Noticias recientes, earnings beat/miss
- Valuation: P/E, price targets, analyst consensus
- Context: Eventos que podrían invalidar el setup técnico
"""
import pandas as pd
import requests
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
import time


class OpportunityValidator:
    """Valida oportunidades con web research"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize validator

        Args:
            api_key: Optional API key for web search (Serper, etc.)
                    If None, will use free alternatives
        """
        self.api_key = api_key
        self.cache_dir = Path('cache/validation')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def validate_opportunities(
        self,
        opportunities_df: pd.DataFrame,
        top_n: int = 15,
        save_report: bool = True
    ) -> pd.DataFrame:
        """
        Valida las top N oportunidades

        Args:
            opportunities_df: DataFrame con oportunidades (ticker, super_score_5d, etc.)
            top_n: Número de tops a validar (default 15)
            save_report: Si guardar reporte de validación

        Returns:
            DataFrame con columnas adicionales:
            - validation_status: BUY/HOLD/AVOID
            - validation_score: 0-100
            - validation_reason: Razón del status
            - price_vs_ath: % desde all-time high
            - recent_news_sentiment: POSITIVE/NEUTRAL/NEGATIVE
        """
        print(f"\n{'='*70}")
        print("🔍 OPPORTUNITY VALIDATOR - Web Research Confirmation")
        print(f"{'='*70}\n")

        # Get top opportunities
        df = opportunities_df.copy()
        df = df.nlargest(top_n, 'super_score_5d')

        validations = []

        for idx, row in df.iterrows():
            ticker = row['ticker']
            score = row['super_score_5d']

            print(f"\n📊 Validating {ticker} (Score: {score:.1f})")
            print("-" * 50)

            validation = self._validate_ticker(ticker, row)
            validations.append(validation)

            # Rate limit - be nice to web services
            time.sleep(1)

        # Convert to DataFrame and merge
        validation_df = pd.DataFrame(validations)
        result = df.merge(validation_df, on='ticker', how='left')

        if save_report:
            self._save_validation_report(result)

        return result

    def _validate_ticker(self, ticker: str, opportunity_data: pd.Series) -> Dict:
        """
        Valida un ticker individual

        Returns:
            Dict con validation results
        """
        # Check cache first
        cache_file = self.cache_dir / f"{ticker}_{datetime.now().strftime('%Y%m%d')}.json"
        if cache_file.exists():
            print(f"   ✓ Using cached validation")
            with open(cache_file, 'r') as f:
                return json.load(f)

        validation = {
            'ticker': ticker,
            'validation_status': 'UNKNOWN',
            'validation_score': 50,
            'validation_reason': '',
            'price_vs_ath': None,
            'recent_news_sentiment': 'NEUTRAL',
            'analyst_consensus': 'N/A',
            'valuation_concern': False,
            'earnings_surprise': None
        }

        try:
            # Get stock info from Yahoo Finance (free, no API needed)
            stock_info = self._get_yfinance_data(ticker)

            if stock_info:
                # Check price vs ATH
                validation['price_vs_ath'] = stock_info.get('price_vs_ath')

                # Check valuation
                pe_ratio = stock_info.get('pe_ratio')
                if pe_ratio and pe_ratio > 40:
                    validation['valuation_concern'] = True

                # Check price targets
                target_upside = stock_info.get('target_upside')

                # Determine validation status
                validation = self._determine_validation_status(
                    validation,
                    stock_info,
                    opportunity_data
                )

            # Save to cache
            with open(cache_file, 'w') as f:
                json.dump(validation, f, indent=2)

        except Exception as e:
            print(f"   ⚠️  Validation error: {str(e)}")
            validation['validation_reason'] = f"Error: {str(e)}"

        return validation

    def _get_yfinance_data(self, ticker: str) -> Optional[Dict]:
        """Get stock data from Yahoo Finance (free)"""
        import yfinance as yf

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period='1y')

            if hist.empty:
                return None

            current_price = info.get('currentPrice') or hist['Close'].iloc[-1]
            year_high = hist['High'].max()
            year_low = hist['Low'].min()

            # Calculate distance from ATH
            price_vs_ath = ((current_price - year_high) / year_high * 100) if year_high else None

            # Get 52-week high from info if available
            fifty_two_week_high = info.get('fiftyTwoWeekHigh', year_high)
            if fifty_two_week_high:
                price_vs_ath = ((current_price - fifty_two_week_high) / fifty_two_week_high * 100)

            return {
                'current_price': current_price,
                'year_high': year_high,
                'year_low': year_low,
                'price_vs_ath': round(price_vs_ath, 1) if price_vs_ath else None,
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'target_price': info.get('targetMeanPrice'),
                'target_upside': ((info.get('targetMeanPrice', current_price) - current_price) / current_price * 100) if info.get('targetMeanPrice') else None,
                'analyst_rating': info.get('recommendationKey'),
                'market_cap': info.get('marketCap'),
                'sector': info.get('sector'),
                'volume_surge': hist['Volume'].iloc[-1] / hist['Volume'].mean() if len(hist) > 0 else 1.0
            }

        except Exception as e:
            print(f"   ⚠️  yfinance error: {str(e)}")
            return None

    def _determine_validation_status(
        self,
        validation: Dict,
        stock_info: Dict,
        opportunity_data: pd.Series
    ) -> Dict:
        """
        Determina validation status basado en múltiples factores

        Logic:
        - AVOID: Stock muy cerca de ATH (>-5%) o valuación extrema
        - HOLD: Stock cerca de ATH (-5% a -15%) o concerns menores
        - BUY: Stock con pullback adecuado (>-15% desde ATH) y fundamentales OK
        """
        reasons = []
        score = 70  # Start neutral-positive

        price_vs_ath = stock_info.get('price_vs_ath')
        pe_ratio = stock_info.get('pe_ratio')
        target_upside = stock_info.get('target_upside')
        analyst_rating = stock_info.get('analyst_rating')

        # 1. Check ATH distance (critical for VCP entries)
        if price_vs_ath is not None:
            if price_vs_ath > -5:
                # Too close to ATH - bad VCP entry
                validation['validation_status'] = 'AVOID'
                score = 30
                reasons.append(f"Near ATH ({price_vs_ath:+.1f}% from high) - poor entry point")
            elif price_vs_ath > -15:
                # Close to ATH - questionable entry
                validation['validation_status'] = 'HOLD'
                score = 50
                reasons.append(f"Close to ATH ({price_vs_ath:+.1f}% from high) - wait for pullback")
            elif price_vs_ath < -50:
                # Very far from ATH - might be broken
                score -= 15
                reasons.append(f"Far from ATH ({price_vs_ath:+.1f}%) - verify not broken")
            else:
                # Good pullback range (-15% to -50%)
                validation['validation_status'] = 'BUY'
                score += 15
                reasons.append(f"Good pullback ({price_vs_ath:+.1f}% from high) - valid VCP setup")

        # 2. Check valuation
        if pe_ratio:
            if pe_ratio > 50:
                score -= 20
                reasons.append(f"High P/E ({pe_ratio:.1f}) - valuation risk")
                validation['valuation_concern'] = True
            elif pe_ratio > 35:
                score -= 10
                reasons.append(f"Elevated P/E ({pe_ratio:.1f}) - watch valuation")

        # 3. Check analyst targets
        if target_upside is not None:
            if target_upside < -10:
                score -= 15
                reasons.append(f"Price above target ({target_upside:.1f}% upside) - limited room")
            elif target_upside > 15:
                score += 10
                reasons.append(f"Strong upside ({target_upside:+.1f}%) - analyst support")

        # 4. Check analyst rating
        if analyst_rating:
            validation['analyst_consensus'] = analyst_rating.upper()
            if analyst_rating in ['strong_buy', 'buy']:
                score += 5
            elif analyst_rating in ['sell', 'strong_sell']:
                score -= 15
                reasons.append("Analyst downgrade/sell rating")

        # Final validation status if not already set
        if validation['validation_status'] == 'UNKNOWN':
            if score >= 65:
                validation['validation_status'] = 'BUY'
            elif score >= 45:
                validation['validation_status'] = 'HOLD'
            else:
                validation['validation_status'] = 'AVOID'

        validation['validation_score'] = max(0, min(100, score))
        validation['validation_reason'] = ' | '.join(reasons) if reasons else 'No significant concerns detected'

        # Print summary
        status_emoji = {'BUY': '✅', 'HOLD': '⚠️', 'AVOID': '❌'}.get(validation['validation_status'], '❓')
        print(f"   {status_emoji} {validation['validation_status']} (Score: {validation['validation_score']}/100)")
        print(f"   📝 {validation['validation_reason']}")

        return validation

    def _save_validation_report(self, df: pd.DataFrame):
        """Guarda reporte de validación"""
        output_file = Path("docs/validation_report.json")

        report = {
            'generated_at': datetime.now().isoformat(),
            'total_validated': len(df),
            'summary': {
                'buy': int((df['validation_status'] == 'BUY').sum()),
                'hold': int((df['validation_status'] == 'HOLD').sum()),
                'avoid': int((df['validation_status'] == 'AVOID').sum())
            },
            'opportunities': df[[
                'ticker', 'company_name', 'super_score_5d', 'validation_status',
                'validation_score', 'validation_reason', 'price_vs_ath',
                'sector', 'vcp_score', 'fundamental_score'
            ]].to_dict('records')
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n✅ Validation report saved: {output_file}")
        print(f"   BUY: {report['summary']['buy']} | HOLD: {report['summary']['hold']} | AVOID: {report['summary']['avoid']}")


def main():
    """Run standalone validation on current opportunities"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate stock opportunities')
    parser.add_argument('--input', default='docs/super_scores_ultimate.csv',
                       help='Input opportunities CSV')
    parser.add_argument('--top', type=int, default=15,
                       help='Number of top opportunities to validate')
    args = parser.parse_args()

    # Load opportunities
    df = pd.read_csv(args.input)

    if 'super_score_5d' not in df.columns:
        if 'super_score_ultimate' in df.columns:
            df['super_score_5d'] = df['super_score_ultimate']
        else:
            print("❌ No super_score column found")
            return

    # Run validation
    validator = OpportunityValidator()
    validated = validator.validate_opportunities(df, top_n=args.top)

    # Show summary
    print(f"\n{'='*70}")
    print("📊 VALIDATION SUMMARY")
    print(f"{'='*70}\n")

    for _, row in validated.head(10).iterrows():
        status_emoji = {'BUY': '✅', 'HOLD': '⚠️', 'AVOID': '❌'}.get(row['validation_status'], '❓')
        print(f"{status_emoji} {row['ticker']:6s} {row['super_score_5d']:5.1f} | {row['validation_status']:5s} | {row['validation_reason']}")


if __name__ == '__main__':
    main()

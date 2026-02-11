#!/usr/bin/env python3
"""
FUNDAMENTAL SCORING SYSTEM
Sistema completo de análisis fundamental para complementar señales técnicas

Componentes (Weighted Score 0-100):
1. Earnings Quality (30%) - Calidad y crecimiento de ganancias
2. Growth Acceleration (25%) - Aceleración de crecimiento
3. Relative Strength (20%) - Fuerza relativa vs mercado
4. Financial Health (15%) - Salud financiera
5. Catalyst Timing (10%) - Timing de catalizadores

No requiere API keys externas - solo yfinance
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
from typing import Dict, List, Optional

class FundamentalScorer:
    """Sistema de scoring fundamental completo"""

    def __init__(self):
        self.cache_dir = Path('cache/fundamentals')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Weights para el fundamental score
        self.weights = {
            'earnings_quality': 0.30,    # 30% - Calidad de ganancias
            'growth_acceleration': 0.25, # 25% - Aceleración de crecimiento
            'relative_strength': 0.20,   # 20% - Fuerza relativa
            'financial_health': 0.15,    # 15% - Salud financiera
            'catalyst_timing': 0.10      # 10% - Timing de catalizadores
        }

    def score_ticker(self, ticker: str) -> Dict:
        """
        Análisis fundamental completo con scoring

        Returns:
            Dict con scores y detalles fundamentales
        """
        print(f"📊 Scoring fundamentales: {ticker}")

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Obtener datos necesarios
            quarterly_earnings = self._get_quarterly_earnings(stock)
            financials = self._get_financials(stock)
            price_history = self._get_price_history(stock)

            # Calcular cada componente del score
            earnings_score = self._calculate_earnings_quality_score(
                quarterly_earnings, info
            )

            growth_score = self._calculate_growth_acceleration_score(
                quarterly_earnings, financials
            )

            rs_score = self._calculate_relative_strength_score(
                price_history, ticker
            )

            health_score = self._calculate_financial_health_score(
                financials, info
            )

            catalyst_score = self._calculate_catalyst_timing_score(
                stock, info
            )

            # Calcular fundamental score total
            fundamental_score = (
                earnings_score['score'] * self.weights['earnings_quality'] +
                growth_score['score'] * self.weights['growth_acceleration'] +
                rs_score['score'] * self.weights['relative_strength'] +
                health_score['score'] * self.weights['financial_health'] +
                catalyst_score['score'] * self.weights['catalyst_timing']
            )

            # Determinar tier
            tier = self._get_tier(fundamental_score)
            quality = self._get_quality(fundamental_score)

            result = {
                'ticker': ticker,
                'company_name': info.get('shortName', ticker),
                'fundamental_score': round(fundamental_score, 1),
                'tier': tier,
                'quality': quality,

                # Componentes individuales
                'earnings_quality_score': earnings_score['score'],
                'growth_acceleration_score': growth_score['score'],
                'relative_strength_score': rs_score['score'],
                'financial_health_score': health_score['score'],
                'catalyst_timing_score': catalyst_score['score'],

                # Detalles de cada componente
                'earnings_details': earnings_score['details'],
                'growth_details': growth_score['details'],
                'rs_details': rs_score['details'],
                'health_details': health_score['details'],
                'catalyst_details': catalyst_score['details'],

                # Datos básicos
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),

                # Timestamp
                'analyzed_at': datetime.now().isoformat()
            }

            print(f"   ✅ Score: {fundamental_score:.1f}/100 - {quality}")
            return result

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return self._get_empty_result(ticker)

    def _get_quarterly_earnings(self, stock) -> pd.DataFrame:
        """Obtiene earnings trimestrales"""
        try:
            earnings = stock.quarterly_earnings
            if earnings is not None and not earnings.empty:
                return earnings
        except:
            pass
        return pd.DataFrame()

    def _get_financials(self, stock) -> Dict:
        """Obtiene datos financieros"""
        try:
            return {
                'quarterly_financials': stock.quarterly_financials,
                'quarterly_balance_sheet': stock.quarterly_balance_sheet,
            }
        except:
            return {
                'quarterly_financials': pd.DataFrame(),
                'quarterly_balance_sheet': pd.DataFrame(),
            }

    def _get_price_history(self, stock) -> pd.DataFrame:
        """Obtiene histórico de precios (1 año)"""
        try:
            hist = stock.history(period='1y')
            if hist is not None and not hist.empty:
                return hist
        except:
            pass
        return pd.DataFrame()

    def _calculate_earnings_quality_score(
        self,
        quarterly_earnings: pd.DataFrame,
        info: Dict
    ) -> Dict:
        """
        Score de calidad de earnings (0-100)

        Factores:
        - EPS growth YoY
        - Consecutive positive quarters
        - Earnings acceleration
        - Profit margins
        """
        score = 50.0
        details = {}

        try:
            if not quarterly_earnings.empty and 'Earnings' in quarterly_earnings.columns:
                earnings = quarterly_earnings['Earnings'].dropna()

                if len(earnings) >= 4:
                    # 1. EPS Growth YoY
                    latest_eps = earnings.iloc[0]
                    prev_eps = earnings.iloc[3]

                    if prev_eps > 0:
                        eps_growth = ((latest_eps - prev_eps) / prev_eps) * 100
                        details['eps_growth_yoy'] = round(eps_growth, 1)

                        # IBD-style: buscar growth >25%
                        if eps_growth >= 50:
                            score += 30
                        elif eps_growth >= 25:
                            score += 20
                        elif eps_growth >= 10:
                            score += 10
                        elif eps_growth < 0:
                            score -= 20

                    # 2. Consecutive positive earnings
                    positive_quarters = sum(1 for e in earnings.iloc[:4] if e > 0)
                    details['positive_quarters'] = positive_quarters

                    if positive_quarters == 4:
                        score += 15
                    elif positive_quarters >= 3:
                        score += 8

                    # 3. Earnings acceleration
                    if len(earnings) >= 4:
                        recent_growth = (earnings.iloc[0] - earnings.iloc[1]) / abs(earnings.iloc[1]) if earnings.iloc[1] != 0 else 0
                        older_growth = (earnings.iloc[2] - earnings.iloc[3]) / abs(earnings.iloc[3]) if earnings.iloc[3] != 0 else 0

                        if recent_growth > older_growth and recent_growth > 0:
                            score += 10
                            details['earnings_accelerating'] = True
                        else:
                            details['earnings_accelerating'] = False

            # 4. Profit margin
            profit_margin = info.get('profitMargins')
            if profit_margin:
                details['profit_margin_pct'] = round(profit_margin * 100, 1)
                if profit_margin >= 0.20:
                    score += 10
                elif profit_margin >= 0.10:
                    score += 5

            score = max(0, min(100, score))

        except Exception as e:
            print(f"      ⚠️ Earnings quality error: {e}")

        return {'score': round(score, 1), 'details': details}

    def _calculate_growth_acceleration_score(
        self,
        quarterly_earnings: pd.DataFrame,
        financials: Dict
    ) -> Dict:
        """
        Score de aceleración de crecimiento (0-100)

        Factores:
        - Revenue growth YoY
        - Revenue acceleration
        - Quarter-over-quarter improvement
        """
        score = 50.0
        details = {}

        try:
            qf = financials.get('quarterly_financials')

            if qf is not None and not qf.empty:
                # Revenue growth
                if 'Total Revenue' in qf.index:
                    revenue = qf.loc['Total Revenue'].dropna()

                    if len(revenue) >= 4:
                        latest_rev = revenue.iloc[0]
                        prev_rev = revenue.iloc[3]

                        if prev_rev > 0:
                            rev_growth = ((latest_rev - prev_rev) / prev_rev) * 100
                            details['revenue_growth_yoy'] = round(rev_growth, 1)

                            # IBD-style: buscar growth >25%
                            if rev_growth >= 30:
                                score += 30
                            elif rev_growth >= 20:
                                score += 20
                            elif rev_growth >= 10:
                                score += 10
                            elif rev_growth < 0:
                                score -= 20

                        # Revenue acceleration
                        if len(revenue) >= 4:
                            q1_growth = (revenue.iloc[0] - revenue.iloc[1]) / abs(revenue.iloc[1]) if revenue.iloc[1] != 0 else 0
                            q2_growth = (revenue.iloc[1] - revenue.iloc[2]) / abs(revenue.iloc[2]) if revenue.iloc[2] != 0 else 0

                            if q1_growth > q2_growth and q1_growth > 0:
                                score += 20
                                details['revenue_accelerating'] = True
                            else:
                                details['revenue_accelerating'] = False

            score = max(0, min(100, score))

        except Exception as e:
            print(f"      ⚠️ Growth acceleration error: {e}")

        return {'score': round(score, 1), 'details': details}

    def _calculate_relative_strength_score(
        self,
        price_history: pd.DataFrame,
        ticker: str
    ) -> Dict:
        """
        Relative Strength vs SPY (0-100)
        Similar a IBD RS Rating
        """
        score = 50.0
        details = {}

        try:
            if price_history.empty:
                return {'score': 50.0, 'details': {}}

            # Obtener SPY para comparación
            spy = yf.Ticker('SPY')
            spy_history = spy.history(period='1y')

            if not spy_history.empty:
                # Performance en diferentes periodos
                periods = {
                    '3m': 63,   # ~3 meses
                    '6m': 126,  # ~6 meses
                    '1y': 252   # ~1 año
                }

                for period_name, days in periods.items():
                    if len(price_history) > days and len(spy_history) > days:
                        # Stock performance
                        stock_return = (
                            (price_history['Close'].iloc[-1] - price_history['Close'].iloc[-days]) /
                            price_history['Close'].iloc[-days] * 100
                        )

                        # SPY performance
                        spy_return = (
                            (spy_history['Close'].iloc[-1] - spy_history['Close'].iloc[-days]) /
                            spy_history['Close'].iloc[-days] * 100
                        )

                        # Relative strength
                        rs = stock_return - spy_return
                        details[f'rs_{period_name}'] = round(rs, 1)

                        # Scoring
                        if period_name == '3m':
                            weight = 15
                        elif period_name == '6m':
                            weight = 20
                        else:  # 1y
                            weight = 15

                        if rs > 20:
                            score += weight
                        elif rs > 10:
                            score += weight * 0.7
                        elif rs > 0:
                            score += weight * 0.3
                        elif rs < -20:
                            score -= weight

                score = max(0, min(100, score))

        except Exception as e:
            print(f"      ⚠️ Relative strength error: {e}")

        return {'score': round(score, 1), 'details': details}

    def _calculate_financial_health_score(
        self,
        financials: Dict,
        info: Dict
    ) -> Dict:
        """
        Score de salud financiera (0-100)

        Factores:
        - ROE (Return on Equity)
        - Debt-to-Equity
        - Current Ratio
        - Operating Margins
        """
        score = 50.0
        details = {}

        try:
            # 1. ROE
            roe = info.get('returnOnEquity')
            if roe:
                details['roe_pct'] = round(roe * 100, 1)
                # IBD busca ROE >17%
                if roe >= 0.25:
                    score += 15
                elif roe >= 0.17:
                    score += 10
                elif roe >= 0.10:
                    score += 5
                elif roe < 0:
                    score -= 10

            # 2. Debt-to-Equity
            debt_to_equity = info.get('debtToEquity')
            if debt_to_equity is not None:
                details['debt_to_equity'] = round(debt_to_equity / 100, 2)
                # Menor deuda es mejor
                if debt_to_equity < 30:
                    score += 15
                elif debt_to_equity < 50:
                    score += 10
                elif debt_to_equity < 100:
                    score += 5
                elif debt_to_equity > 200:
                    score -= 15

            # 3. Current Ratio
            current_ratio = info.get('currentRatio')
            if current_ratio:
                details['current_ratio'] = round(current_ratio, 2)
                if 1.5 <= current_ratio <= 3.0:
                    score += 10
                elif current_ratio >= 1.0:
                    score += 5
                elif current_ratio < 1.0:
                    score -= 10

            # 4. Operating Margins
            operating_margins = info.get('operatingMargins')
            if operating_margins:
                details['operating_margin_pct'] = round(operating_margins * 100, 1)
                if operating_margins >= 0.20:
                    score += 10
                elif operating_margins >= 0.10:
                    score += 5

            score = max(0, min(100, score))

        except Exception as e:
            print(f"      ⚠️ Financial health error: {e}")

        return {'score': round(score, 1), 'details': details}

    def _calculate_catalyst_timing_score(
        self,
        stock,
        info: Dict
    ) -> Dict:
        """
        Score de timing de catalizadores (0-100)

        Factores:
        - Días hasta earnings (sweet spot: 30-60 días)
        - Analyst recommendations
        - Target price upside
        """
        score = 50.0
        details = {}

        try:
            # 1. Earnings date
            try:
                calendar = stock.calendar
                if calendar is not None and not calendar.empty:
                    # calendar puede ser Series o DataFrame
                    if isinstance(calendar, pd.Series):
                        earnings_date = calendar.get('Earnings Date')
                    else:
                        earnings_date = calendar.get('Earnings Date', [None])[0] if 'Earnings Date' in calendar else None

                    if earnings_date is not None and pd.notna(earnings_date):
                        days_to_earnings = (pd.Timestamp(earnings_date) - pd.Timestamp.now()).days
                        details['days_to_earnings'] = days_to_earnings

                        # Sweet spot: 30-60 días antes
                        if 30 <= days_to_earnings <= 60:
                            score += 30
                        elif 15 <= days_to_earnings <= 90:
                            score += 15
            except:
                details['days_to_earnings'] = 'N/A'

            # 2. Recommendation
            recommendation = info.get('recommendationKey')
            if recommendation:
                details['recommendation'] = recommendation
                if recommendation in ['strong_buy', 'buy']:
                    score += 10
                elif recommendation == 'hold':
                    score += 0
                elif recommendation in ['sell', 'strong_sell']:
                    score -= 10

            # 3. Target price upside
            target_price = info.get('targetMeanPrice')
            current_price = info.get('currentPrice', info.get('regularMarketPrice'))
            if target_price and current_price and current_price > 0:
                upside = ((target_price - current_price) / current_price) * 100
                details['analyst_upside_pct'] = round(upside, 1)

                if upside >= 30:
                    score += 10
                elif upside >= 15:
                    score += 5
                elif upside < -10:
                    score -= 10

            score = max(0, min(100, score))

        except Exception as e:
            print(f"      ⚠️ Catalyst timing error: {e}")

        return {'score': round(score, 1), 'details': details}

    def _get_tier(self, score: float) -> str:
        """Tier basado en score"""
        if score >= 80:
            return "🏆 ELITE"
        elif score >= 70:
            return "⭐⭐⭐ EXCELLENT"
        elif score >= 60:
            return "⭐⭐ GOOD"
        elif score >= 50:
            return "⭐ AVERAGE"
        else:
            return "⚠️ WEAK"

    def _get_quality(self, score: float) -> str:
        """Quality label para dashboards"""
        if score >= 80:
            return "🟢 Elite"
        elif score >= 70:
            return "🟢 Excellent"
        elif score >= 60:
            return "🟡 Good"
        elif score >= 50:
            return "🟡 Average"
        else:
            return "🔴 Weak"

    def _get_empty_result(self, ticker: str) -> Dict:
        """Resultado vacío en caso de error"""
        return {
            'ticker': ticker,
            'company_name': ticker,
            'fundamental_score': 0.0,
            'tier': '❌ ERROR',
            'quality': '🔴 Error',
            'earnings_quality_score': 0.0,
            'growth_acceleration_score': 0.0,
            'relative_strength_score': 0.0,
            'financial_health_score': 0.0,
            'catalyst_timing_score': 0.0,
            'earnings_details': {},
            'growth_details': {},
            'rs_details': {},
            'health_details': {},
            'catalyst_details': {},
            'current_price': 0,
            'market_cap': 0,
            'sector': 'N/A',
            'industry': 'N/A',
            'analyzed_at': datetime.now().isoformat()
        }

    def score_batch(
        self,
        tickers: List[str],
        delay: float = 0.5
    ) -> pd.DataFrame:
        """
        Score múltiples tickers en batch

        Args:
            tickers: Lista de tickers
            delay: Delay entre requests

        Returns:
            DataFrame con resultados
        """
        print(f"\n📊 FUNDAMENTAL SCORER - Batch Analysis")
        print(f"Scoring {len(tickers)} tickers...")
        print("=" * 80)

        results = []

        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{len(tickers)}] {ticker}")

            result = self.score_ticker(ticker)
            results.append(result)

            # Delay
            if i < len(tickers):
                time.sleep(delay)

        # Convertir a DataFrame
        df = pd.DataFrame(results)

        # Ordenar por fundamental_score
        df = df.sort_values('fundamental_score', ascending=False)

        print(f"\n✅ Scoring completado: {len(df)} tickers")
        print(f"   Promedio: {df['fundamental_score'].mean():.1f}/100")
        print(f"   Elite (≥80): {len(df[df['fundamental_score'] >= 80])}")
        print(f"   Excellent (≥70): {len(df[df['fundamental_score'] >= 70])}")

        return df

    def save_results(self, df: pd.DataFrame, filename: str = 'fundamental_scores'):
        """Guarda resultados en CSV y JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # CSV para fácil lectura
        csv_path = Path(f'docs/{filename}.csv')
        df.to_csv(csv_path, index=False)
        print(f"\n💾 CSV guardado: {csv_path}")

        # JSON con detalles completos
        json_path = Path(f'docs/{filename}_{timestamp}.json')

        # Convertir a dict y manejar numpy types
        results_dict = df.to_dict('records')
        results_dict = self._convert_to_native(results_dict)

        with open(json_path, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"💾 JSON guardado: {json_path}")

        return csv_path, json_path

    def _convert_to_native(self, obj):
        """Convierte numpy types a Python natives para JSON"""
        if isinstance(obj, dict):
            return {k: self._convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_native(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='📊 Fundamental Scorer')
    parser.add_argument('--ticker', type=str, help='Score un ticker específico')
    parser.add_argument('--vcp', action='store_true', help='Score VCP stocks')
    parser.add_argument('--ml', action='store_true', help='Score ML top stocks')
    parser.add_argument('--top', type=int, default=50, help='Top N tickers (default: 50)')
    parser.add_argument('--all', action='store_true', help='Score todas las fuentes (VCP + ML)')

    args = parser.parse_args()

    scorer = FundamentalScorer()

    if args.ticker:
        # Score un ticker
        result = scorer.score_ticker(args.ticker)

        print(f"\n{'='*80}")
        print(f"📊 FUNDAMENTAL SCORE: {result['ticker']}")
        print(f"{'='*80}")
        print(f"Company: {result['company_name']}")
        print(f"Sector: {result['sector']} | Industry: {result['industry']}")
        print(f"Price: ${result['current_price']:.2f}")
        print(f"\n🎯 FUNDAMENTAL SCORE: {result['fundamental_score']}/100 - {result['tier']}")
        print(f"\n📊 COMPONENTES:")
        print(f"  📈 Earnings Quality: {result['earnings_quality_score']:.1f}/100")
        for key, value in result['earnings_details'].items():
            print(f"      • {key}: {value}")
        print(f"  🚀 Growth Acceleration: {result['growth_acceleration_score']:.1f}/100")
        for key, value in result['growth_details'].items():
            print(f"      • {key}: {value}")
        print(f"  💪 Relative Strength: {result['relative_strength_score']:.1f}/100")
        for key, value in result['rs_details'].items():
            print(f"      • {key}: {value}")
        print(f"  💰 Financial Health: {result['financial_health_score']:.1f}/100")
        for key, value in result['health_details'].items():
            print(f"      • {key}: {value}")
        print(f"  🎯 Catalyst Timing: {result['catalyst_timing_score']:.1f}/100")
        for key, value in result['catalyst_details'].items():
            print(f"      • {key}: {value}")

    elif args.vcp or args.ml or args.all:
        tickers = []

        # Cargar tickers según fuente
        if args.vcp or args.all:
            vcp_path = Path('docs/reports/vcp/latest.csv')
            if vcp_path.exists():
                vcp_df = pd.read_csv(vcp_path)
                vcp_tickers = vcp_df['ticker'].head(args.top).tolist()
                tickers.extend(vcp_tickers)
                print(f"📊 Cargados {len(vcp_tickers)} tickers de VCP scan")

        if args.ml or args.all:
            ml_path = Path('docs/ml_scores.csv')
            if ml_path.exists():
                ml_df = pd.read_csv(ml_path)
                ml_tickers = ml_df['ticker'].head(args.top).tolist()
                tickers.extend(ml_tickers)
                print(f"🤖 Cargados {len(ml_tickers)} tickers de ML scores")

        # Eliminar duplicados
        tickers = list(dict.fromkeys(tickers))

        if not tickers:
            print("❌ No se encontraron tickers. Ejecuta primero VCP scan o ML scoring")
            return

        print(f"\n📊 Scoring {len(tickers)} tickers únicos...")

        # Score batch
        results_df = scorer.score_batch(tickers)

        # Guardar
        scorer.save_results(results_df)

        # Mostrar top 10
        print(f"\n{'='*80}")
        print(f"🏆 TOP 10 FUNDAMENTAL SCORES")
        print(f"{'='*80}")
        print(f"{'Ticker':<8} {'Company':<30} {'F-Score':<8} {'Quality':<15}")
        print(f"{'-'*80}")

        for _, row in results_df.head(10).iterrows():
            ticker = row['ticker']
            company = str(row['company_name'])[:28]
            score = row['fundamental_score']
            quality = row['quality']

            print(f"{ticker:<8} {company:<30} {score:<8.1f} {quality:<15}")

    else:
        print("❌ Especifica --ticker, --vcp, --ml, o --all")
        print("\nEjemplos:")
        print("  python3 fundamental_scorer.py --ticker AAPL")
        print("  python3 fundamental_scorer.py --vcp --top 50")
        print("  python3 fundamental_scorer.py --ml --top 30")
        print("  python3 fundamental_scorer.py --all --top 100")


if __name__ == "__main__":
    main()

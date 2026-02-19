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
import argparse
from typing import Dict, List, Optional

class FundamentalScorer:
    """Sistema de scoring fundamental completo"""

    def __init__(self, as_of_date: Optional[str] = None):
        """Initialize Fundamental Scorer

        Args:
            as_of_date: Historical date (YYYY-MM-DD) for scoring. Prevents look-ahead bias.
        """
        self.cache_dir = Path('cache/fundamentals')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 🔴 FIX LOOK-AHEAD BIAS: Store as_of_date
        self.as_of_date = as_of_date
        if as_of_date:
            self.as_of_date_dt = datetime.strptime(as_of_date, '%Y-%m-%d')
            print(f"📅 Fundamental Scorer: Historical mode (as_of_date={as_of_date})")
        else:
            self.as_of_date_dt = datetime.now()

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

                # RS Line flat columns (Minervini)
                'rs_line_score':       rs_score.get('rs_line_score'),
                'rs_line_percentile':  rs_score.get('rs_line_percentile'),
                'rs_line_at_new_high': rs_score.get('rs_line_at_new_high'),
                'rs_line_trend':       rs_score.get('rs_line_trend'),

                # CANSLIM "A" flat columns — EPS/Revenue Acceleration
                'eps_growth_yoy':    earnings_score.get('eps_growth_yoy'),
                'eps_accelerating':  earnings_score.get('eps_accelerating'),
                'eps_accel_quarters': earnings_score.get('eps_accel_quarters', 0),
                'rev_growth_yoy':    growth_score.get('rev_growth_yoy'),
                'rev_accelerating':  growth_score.get('rev_accelerating'),
                'rev_accel_quarters': growth_score.get('rev_accel_quarters', 0),

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

                # Short Interest (combustible para short squeeze)
                **self._extract_short_interest(info),

                # 52-Week High Proximity (Minervini: comprar cerca de máximos)
                **self._extract_52w_proximity(info),

                # Minervini Trend Template (8-criteria Stage 2 checklist)
                **self._calculate_trend_template(
                    price_history, info, rs_score.get('rs_line_percentile')
                ),

                # Timestamp
                'analyzed_at': datetime.now().isoformat()
            }

            print(f"   ✅ Score: {fundamental_score:.1f}/100 - {quality}")
            return result

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return self._get_empty_result(ticker)

    def _get_quarterly_earnings(self, stock) -> pd.DataFrame:
        """Obtiene earnings trimestrales

        Returns:
            DataFrame with quarterly earnings reported before as_of_date (if specified)
        """
        try:
            earnings = stock.quarterly_earnings
            if earnings is not None and not earnings.empty:
                # 🔴 FIX LOOK-AHEAD BIAS: Filter earnings by date
                if self.as_of_date:
                    # Filter to only include earnings with dates <= as_of_date
                    # Earnings index is typically datetime, so filter by index
                    if isinstance(earnings.index, pd.DatetimeIndex):
                        earnings = earnings[earnings.index <= self.as_of_date_dt]
                    # Some earnings might have a date column instead
                    elif 'date' in earnings.columns:
                        earnings['date'] = pd.to_datetime(earnings['date'])
                        earnings = earnings[earnings['date'] <= self.as_of_date_dt]

                return earnings
        except:
            pass
        return pd.DataFrame()

    def _get_financials(self, stock) -> Dict:
        """Obtiene datos financieros

        Returns:
            Dict with quarterly financials reported before as_of_date (if specified)
        """
        try:
            quarterly_financials = stock.quarterly_financials
            quarterly_balance_sheet = stock.quarterly_balance_sheet

            # 🔴 FIX LOOK-AHEAD BIAS: Filter financials by date
            if self.as_of_date:
                # Filter quarterly financials
                if quarterly_financials is not None and not quarterly_financials.empty:
                    if isinstance(quarterly_financials.columns, pd.DatetimeIndex):
                        quarterly_financials = quarterly_financials.loc[:, quarterly_financials.columns <= self.as_of_date_dt]

                # Filter balance sheet
                if quarterly_balance_sheet is not None and not quarterly_balance_sheet.empty:
                    if isinstance(quarterly_balance_sheet.columns, pd.DatetimeIndex):
                        quarterly_balance_sheet = quarterly_balance_sheet.loc[:, quarterly_balance_sheet.columns <= self.as_of_date_dt]

            return {
                'quarterly_financials': quarterly_financials,
                'quarterly_balance_sheet': quarterly_balance_sheet,
            }
        except:
            return {
                'quarterly_financials': pd.DataFrame(),
                'quarterly_balance_sheet': pd.DataFrame(),
            }

    def _get_price_history(self, stock) -> pd.DataFrame:
        """Obtiene histórico de precios (1 año)

        Returns:
            DataFrame with price history up to as_of_date (if specified)
        """
        try:
            # 🔴 FIX LOOK-AHEAD BIAS: Use date range instead of period
            if self.as_of_date:
                # Historical mode: fetch data up to as_of_date
                end_date = self.as_of_date_dt
                start_date = end_date - timedelta(days=365)

                hist = stock.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d')
                )
            else:
                # Current mode: use standard period
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
        eps_growth_yoy = None
        eps_accelerating = None
        eps_accel_quarters = 0

        try:
            if not quarterly_earnings.empty and 'Earnings' in quarterly_earnings.columns:
                earnings = quarterly_earnings['Earnings'].dropna()

                if len(earnings) >= 4:
                    # 1. EPS Growth YoY
                    latest_eps = earnings.iloc[0]
                    prev_eps = earnings.iloc[3]

                    if prev_eps > 0:
                        eps_growth = ((latest_eps - prev_eps) / prev_eps) * 100
                        eps_growth_yoy = round(eps_growth, 1)
                        details['eps_growth_yoy'] = eps_growth_yoy

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

                    # 3. Multi-quarter EPS acceleration (CANSLIM "A")
                    # Calculate QoQ growth rates for last 3 pairs (need ≥4 quarters)
                    qoq_rates = []
                    for i in range(min(3, len(earnings) - 1)):
                        curr = earnings.iloc[i]
                        prev = earnings.iloc[i + 1]
                        if prev != 0:
                            qoq_rates.append((curr - prev) / abs(prev) * 100)
                        else:
                            qoq_rates.append(None)

                    # Count consecutive accelerating pairs (most recent first)
                    accel_count = 0
                    for i in range(len(qoq_rates) - 1):
                        r0, r1 = qoq_rates[i], qoq_rates[i + 1]
                        if r0 is not None and r1 is not None and r0 > r1:
                            accel_count += 1
                        else:
                            break  # stop at first non-acceleration

                    eps_accel_quarters = accel_count
                    eps_accelerating = accel_count >= 1
                    details['earnings_accelerating'] = eps_accelerating
                    details['eps_accel_quarters'] = eps_accel_quarters

                    if accel_count >= 2:
                        score += 20    # 3 consecutive quarters
                    elif accel_count >= 1:
                        score += 10   # 2 consecutive quarters

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

        return {
            'score': round(score, 1),
            'details': details,
            'eps_growth_yoy':    eps_growth_yoy,
            'eps_accelerating':  eps_accelerating,
            'eps_accel_quarters': eps_accel_quarters,
        }

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
        rev_growth_yoy = None
        rev_accelerating = None
        rev_accel_quarters = 0

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
                            rev_growth_yoy = round(rev_growth, 1)
                            details['revenue_growth_yoy'] = rev_growth_yoy

                            # IBD-style: buscar growth >25%
                            if rev_growth >= 30:
                                score += 30
                            elif rev_growth >= 20:
                                score += 20
                            elif rev_growth >= 10:
                                score += 10
                            elif rev_growth < 0:
                                score -= 20

                        # Multi-quarter revenue acceleration (CANSLIM "A")
                        qoq_rates = []
                        for i in range(min(3, len(revenue) - 1)):
                            curr = revenue.iloc[i]
                            prev = revenue.iloc[i + 1]
                            if prev != 0:
                                qoq_rates.append((curr - prev) / abs(prev) * 100)
                            else:
                                qoq_rates.append(None)

                        accel_count = 0
                        for i in range(len(qoq_rates) - 1):
                            r0, r1 = qoq_rates[i], qoq_rates[i + 1]
                            if r0 is not None and r1 is not None and r0 > r1:
                                accel_count += 1
                            else:
                                break

                        rev_accel_quarters = accel_count
                        rev_accelerating = accel_count >= 1
                        details['revenue_accelerating'] = rev_accelerating
                        details['rev_accel_quarters'] = rev_accel_quarters

                        if accel_count >= 2:
                            score += 20
                        elif accel_count >= 1:
                            score += 10

            score = max(0, min(100, score))

        except Exception as e:
            print(f"      ⚠️ Growth acceleration error: {e}")

        return {
            'score': round(score, 1),
            'details': details,
            'rev_growth_yoy':    rev_growth_yoy,
            'rev_accelerating':  rev_accelerating,
            'rev_accel_quarters': rev_accel_quarters,
        }

    def _calculate_relative_strength_score(
        self,
        price_history: pd.DataFrame,
        ticker: str
    ) -> Dict:
        """
        Relative Strength vs SPY (0-100)
        Similar a IBD RS Rating + RS Line (Minervini)
        """
        score = 50.0
        details = {}
        rs_line_score = None
        rs_line_percentile = None
        rs_line_at_new_high = None
        rs_line_trend = None

        try:
            if price_history.empty:
                return {
                    'score': 50.0, 'details': {},
                    'rs_line_score': None, 'rs_line_percentile': None,
                    'rs_line_at_new_high': None, 'rs_line_trend': None,
                }

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

                # ── RS Line (Minervini): stock_price / SPY_price ratio ────────
                try:
                    # Align on common dates
                    stock_close = price_history['Close'].rename('stock')
                    spy_close   = spy_history['Close'].rename('spy')
                    aligned     = pd.concat([stock_close, spy_close], axis=1).dropna()

                    if len(aligned) >= 10:
                        rs_line = aligned['stock'] / aligned['spy']

                        rs_current    = float(rs_line.iloc[-1])
                        rs_52w_high   = float(rs_line.max())
                        rs_52w_low    = float(rs_line.min())
                        rs_range      = rs_52w_high - rs_52w_low

                        rs_line_percentile = round(
                            (rs_current - rs_52w_low) / rs_range * 100
                            if rs_range > 0 else 50.0, 1
                        )
                        rs_line_at_new_high = bool(rs_current >= rs_52w_high * 0.98)

                        # 50-day slope (use fewer days if series is short)
                        lookback = min(50, len(rs_line) - 1)
                        if lookback >= 5:
                            slope_pct = (rs_line.iloc[-1] - rs_line.iloc[-lookback]) / abs(rs_line.iloc[-lookback]) * 100
                            rs_line_trend = "up" if slope_pct > 2 else ("down" if slope_pct < -2 else "flat")
                        else:
                            rs_line_trend = "flat"

                        # RS Line score 0-100 based on percentile
                        if   rs_line_percentile >= 90: rs_line_score = 95
                        elif rs_line_percentile >= 75: rs_line_score = 80
                        elif rs_line_percentile >= 50: rs_line_score = 60
                        elif rs_line_percentile >= 25: rs_line_score = 35
                        else:                           rs_line_score = 15
                        if rs_line_at_new_high:
                            rs_line_score = min(100, rs_line_score + 10)

                        # Blend 60% existing RS + 40% RS Line score
                        score = round(score * 0.60 + rs_line_score * 0.40, 1)
                        score = max(0, min(100, score))

                        details['rs_line_percentile'] = rs_line_percentile
                        details['rs_line_at_new_high'] = rs_line_at_new_high
                        details['rs_line_trend']       = rs_line_trend
                        details['rs_line_score']       = rs_line_score

                except Exception as e_rs:
                    print(f"      ⚠️ RS Line calculation error: {e_rs}")

        except Exception as e:
            print(f"      ⚠️ Relative strength error: {e}")

        return {
            'score': round(score, 1),
            'details': details,
            'rs_line_score':       rs_line_score,
            'rs_line_percentile':  rs_line_percentile,
            'rs_line_at_new_high': rs_line_at_new_high,
            'rs_line_trend':       rs_line_trend,
        }

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
            'rs_line_score': None,
            'rs_line_percentile': None,
            'rs_line_at_new_high': None,
            'rs_line_trend': None,
            'eps_growth_yoy': None,
            'eps_accelerating': None,
            'eps_accel_quarters': 0,
            'rev_growth_yoy': None,
            'rev_accelerating': None,
            'rev_accel_quarters': 0,
            'earnings_details': {},
            'growth_details': {},
            'rs_details': {},
            'health_details': {},
            'catalyst_details': {},
            'current_price': 0,
            'market_cap': 0,
            'sector': 'N/A',
            'industry': 'N/A',
            'short_percent_float': None,
            'short_ratio': None,
            'short_squeeze_potential': None,
            'fifty_two_week_high': None,
            'proximity_to_52w_high': None,
            'trend_template_score': None,
            'trend_template_pass': None,
            'analyzed_at': datetime.now().isoformat()
        }

    def _calculate_trend_template(
        self,
        price_history: pd.DataFrame,
        info: Dict,
        rs_percentile: Optional[float]
    ) -> Dict:
        """
        Minervini Trend Template — 8 criterios Stage 2 uptrend.

        1. Price > 150MA and 200MA
        2. 150MA > 200MA
        3. 200MA trending up ≥ 1 month (20 bars)
        4. 50MA > 150MA and 200MA
        5. Price > 50MA
        6. Price ≥ 30% above 52-week low
        7. Price within 25% of 52-week high (proximity >= -25%)
        8. RS Rating ≥ 70

        Returns flat keys: trend_template_score (0-8), trend_template_pass (bool).
        """
        empty = {'trend_template_score': None, 'trend_template_pass': None}

        if price_history.empty or len(price_history) < 200:
            return empty

        try:
            close = price_history['Close']

            ma50  = float(close.rolling(50).mean().iloc[-1])
            ma150 = float(close.rolling(150).mean().iloc[-1])
            ma200 = float(close.rolling(200).mean().iloc[-1])

            # 200MA slope: current vs 20 bars ago
            if len(close) >= 221:
                ma200_20d = float(close.rolling(200).mean().iloc[-21])
                ma200_trending_up = ma200 > ma200_20d
            else:
                ma200_trending_up = False

            price = float(close.iloc[-1])

            low52  = info.get('fiftyTwoWeekLow')
            high52 = info.get('fiftyTwoWeekHigh')

            criteria = [
                price > ma150 and price > ma200,               # 1
                ma150 > ma200,                                  # 2
                ma200_trending_up,                              # 3
                ma50 > ma150 and ma50 > ma200,                 # 4
                price > ma50,                                   # 5
                (low52  is not None and float(low52)  > 0      # 6
                 and price >= float(low52) * 1.30),
                (high52 is not None and float(high52) > 0      # 7
                 and price >= float(high52) * 0.75),
                rs_percentile is not None and rs_percentile >= 70,  # 8
            ]

            score = int(sum(criteria))
            return {
                'trend_template_score': score,
                'trend_template_pass':  score >= 7,
            }
        except Exception:
            return empty

    def _extract_short_interest(self, info: Dict) -> Dict:
        """Extrae datos de short interest de yfinance info."""
        try:
            raw = info.get('shortPercentOfFloat')
            short_pct = round(float(raw) * 100, 1) if raw is not None else None
            raw_ratio = info.get('shortRatio')
            short_ratio = round(float(raw_ratio), 1) if raw_ratio is not None else None
            short_squeeze = short_pct is not None and short_pct >= 8.0
        except (TypeError, ValueError):
            short_pct = short_ratio = None
            short_squeeze = None
        return {
            'short_percent_float':     short_pct,
            'short_ratio':             short_ratio,
            'short_squeeze_potential': short_squeeze,
        }

    def _extract_52w_proximity(self, info: Dict) -> Dict:
        """Calcula proximidad al máximo de 52 semanas (Minervini: comprar cerca de máximos)."""
        try:
            high52 = info.get('fiftyTwoWeekHigh')
            price  = info.get('currentPrice') or info.get('regularMarketPrice')
            proximity = None
            if high52 and price and float(high52) > 0:
                proximity = round((float(price) / float(high52) - 1) * 100, 1)
                # e.g. -5.0 = 5% below 52w high; -40.0 = 40% below
        except (TypeError, ValueError):
            high52 = proximity = None
        return {
            'fifty_two_week_high':  float(high52) if high52 else None,
            'proximity_to_52w_high': proximity,
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
    parser.add_argument('--as-of-date', type=str, default=None,
                       help='Historical date for scoring (YYYY-MM-DD). Only use earnings/financials reported before this date. '
                            'Prevents look-ahead bias in backtesting.')

    args = parser.parse_args()

    # 🔴 FIX LOOK-AHEAD BIAS: Pass as_of_date to scorer
    scorer = FundamentalScorer(as_of_date=args.as_of_date)

    if args.as_of_date:
        print(f"📅 Historical mode: Scoring as of {args.as_of_date}")
        print(f"🔴 Only using earnings/financials reported before this date\n")

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

#!/usr/bin/env python3
"""
FUNDAMENTAL ANALYZER & PRICE TARGET SYSTEM
Análisis fundamental completo + Precio objetivo calculado

Features:
- Price targets de analistas (yfinance)
- Análisis de flujo de caja (FCF, FCF Yield)
- Métricas de valoración (P/E, PEG, P/B, P/S)
- Health financiero (Debt/Equity, Current Ratio, ROE)
- Cálculo de precio objetivo propio:
  - DCF Simplificado
  - P/E múltiplo
  - Promedio ponderado con analistas
"""
import yfinance as yf
import pandas as pd
from datetime import datetime

class FundamentalAnalyzer:
    """Analizador fundamental con price targets"""

    def __init__(self):
        self.cache = {}

    def get_fundamental_data(self, ticker):
        """
        Obtiene datos fundamentales completos

        Returns: dict con todos los datos fundamentales
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Price targets de analistas
            target_mean = info.get('targetMeanPrice', None)
            target_high = info.get('targetHighPrice', None)
            target_low = info.get('targetLowPrice', None)
            target_median = info.get('targetMedianPrice', None)
            num_analysts = info.get('numberOfAnalystOpinions', 0)

            # Precio actual
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))

            # Métricas de valoración
            pe_ratio = info.get('trailingPE', None)
            forward_pe = info.get('forwardPE', None)
            peg_ratio = info.get('pegRatio', None)
            price_to_book = info.get('priceToBook', None)
            price_to_sales = info.get('priceToSalesTrailing12Months', None)
            enterprise_value = info.get('enterpriseValue', None)
            ev_to_revenue = info.get('enterpriseToRevenue', None)
            ev_to_ebitda = info.get('enterpriseToEbitda', None)

            # Flujo de caja
            free_cash_flow = info.get('freeCashflow', None)
            operating_cash_flow = info.get('operatingCashflow', None)
            market_cap = info.get('marketCap', None)

            # Calcular FCF Yield si tenemos datos
            fcf_yield = None
            if free_cash_flow and market_cap and market_cap > 0:
                fcf_yield = (free_cash_flow / market_cap) * 100

            # Salud financiera
            debt_to_equity = info.get('debtToEquity', None)
            current_ratio = info.get('currentRatio', None)
            quick_ratio = info.get('quickRatio', None)

            # Rentabilidad
            roe = info.get('returnOnEquity', None)
            roa = info.get('returnOnAssets', None)
            profit_margin = info.get('profitMargins', None)
            operating_margin = info.get('operatingMargins', None)

            # Crecimiento
            revenue_growth = info.get('revenueGrowth', None)
            earnings_growth = info.get('earningsGrowth', None)
            earnings_quarterly_growth = info.get('earningsQuarterlyGrowth', None)

            # Dividendos
            dividend_yield = info.get('dividendYield', None)
            payout_ratio = info.get('payoutRatio', None)

            # Técnicos para entry evaluation
            fifty_two_week_high = info.get('fiftyTwoWeekHigh', None)
            fifty_two_week_low = info.get('fiftyTwoWeekLow', None)
            fifty_day_avg = info.get('fiftyDayAverage', None)
            two_hundred_day_avg = info.get('twoHundredDayAverage', None)
            fifty_two_week_change = info.get('52WeekChange', None)

            fundamental_data = {
                # Price Targets
                'analysts': {
                    'target_mean': target_mean,
                    'target_median': target_median,
                    'target_high': target_high,
                    'target_low': target_low,
                    'num_analysts': num_analysts,
                    'upside_analysts': ((target_mean / current_price - 1) * 100) if target_mean and current_price > 0 else None
                },

                # Precio actual
                'current_price': current_price,

                # Valoración
                'valuation': {
                    'pe_ratio': pe_ratio,
                    'forward_pe': forward_pe,
                    'peg_ratio': peg_ratio,
                    'price_to_book': price_to_book,
                    'price_to_sales': price_to_sales,
                    'ev_to_revenue': ev_to_revenue,
                    'ev_to_ebitda': ev_to_ebitda,
                },

                # Cash Flow
                'cashflow': {
                    'free_cash_flow': free_cash_flow,
                    'operating_cash_flow': operating_cash_flow,
                    'fcf_yield': fcf_yield,
                },

                # Salud Financiera
                'financial_health': {
                    'debt_to_equity': debt_to_equity,
                    'current_ratio': current_ratio,
                    'quick_ratio': quick_ratio,
                },

                # Rentabilidad
                'profitability': {
                    'roe': roe,
                    'roa': roa,
                    'profit_margin': profit_margin,
                    'operating_margin': operating_margin,
                },

                # Crecimiento
                'growth': {
                    'revenue_growth': revenue_growth,
                    'earnings_growth': earnings_growth,
                    'earnings_quarterly_growth': earnings_quarterly_growth,
                },

                # Dividendos
                'dividends': {
                    'yield': dividend_yield,
                    'payout_ratio': payout_ratio,
                },

                # Técnicos (para entry evaluation)
                'technicals': {
                    'fifty_two_week_high': fifty_two_week_high,
                    'fifty_two_week_low': fifty_two_week_low,
                    'fifty_day_avg': fifty_day_avg,
                    'two_hundred_day_avg': two_hundred_day_avg,
                    'fifty_two_week_change': fifty_two_week_change,
                },

                'market_cap': market_cap,
                'enterprise_value': enterprise_value,
            }

            self.cache[ticker] = fundamental_data
            return fundamental_data

        except Exception as e:
            print(f"⚠️  Error obteniendo datos de {ticker}: {e}")
            return None

    def calculate_dcf_price_target(self, ticker, fundamental_data=None):
        """
        Calcula precio objetivo usando DCF simplificado

        Formula simplificada:
        - Proyectar FCF a 5 años con growth rate
        - Discount con WACC estimado (10%)
        - Terminal value (perpetuity growth 3%)
        """
        if fundamental_data is None:
            fundamental_data = self.get_fundamental_data(ticker)

        if not fundamental_data:
            return None

        fcf = fundamental_data['cashflow']['free_cash_flow']
        market_cap = fundamental_data['market_cap']
        earnings_growth = fundamental_data['growth']['earnings_growth']
        revenue_growth = fundamental_data['growth']['revenue_growth']

        # Validaciones
        if not fcf or not market_cap or market_cap == 0:
            return None

        if fcf <= 0:
            return None  # No tiene sentido DCF con FCF negativo

        # Growth rate: usamos revenue_growth como base más estable que earnings_growth
        # (earnings puede tener picos por one-time items o base effects)
        # Cap conservador: 12% máximo para DCF a 5 años
        if revenue_growth and 0 < revenue_growth < 1.0:
            growth_rate = min(revenue_growth, 0.12)
        elif earnings_growth and 0 < earnings_growth < 0.5:
            growth_rate = min(earnings_growth, 0.12)
        else:
            growth_rate = 0.04  # 4% conservador por defecto

        # Parámetros
        discount_rate = 0.10  # WACC 10%
        terminal_growth = 0.03  # 3% perpetuo
        years = 5

        # Proyectar FCF
        fcf_projections = []
        for year in range(1, years + 1):
            projected_fcf = fcf * ((1 + growth_rate) ** year)
            pv_fcf = projected_fcf / ((1 + discount_rate) ** year)
            fcf_projections.append(pv_fcf)

        # Terminal value
        terminal_fcf = fcf * ((1 + growth_rate) ** years) * (1 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** years)

        # Enterprise value
        enterprise_value_dcf = sum(fcf_projections) + pv_terminal

        # Equity value (simplificado - sin ajustar por deuda)
        # En una versión completa: equity = EV - net debt
        equity_value = enterprise_value_dcf

        # Shares outstanding
        shares = market_cap / fundamental_data['current_price'] if fundamental_data['current_price'] > 0 else 0

        if shares == 0:
            return None

        # Precio por acción
        dcf_price = equity_value / shares

        # Sanity check: DCF no puede ser más de 2.5x ni menos de 0.2x el precio actual
        current = fundamental_data['current_price']
        if current and current > 0:
            if dcf_price > current * 2.5 or dcf_price < current * 0.2:
                return None  # Resultado irreal, descartamos

        return round(dcf_price, 2)

    def calculate_pe_multiple_target(self, ticker, fundamental_data=None):
        """
        Calcula precio objetivo usando múltiplo P/E

        Usa P/E forward si disponible, sino trailing P/E
        Proyecta earnings futuras y aplica múltiplo sectorial promedio
        """
        if fundamental_data is None:
            fundamental_data = self.get_fundamental_data(ticker)

        if not fundamental_data:
            return None

        pe = fundamental_data['valuation']['forward_pe']
        if not pe:
            pe = fundamental_data['valuation']['pe_ratio']

        current_price = fundamental_data['current_price']
        earnings_growth = fundamental_data['growth']['earnings_growth']

        if not pe or not current_price or current_price == 0:
            return None

        # Limitar P/E a rango razonable (evitar múltiplos extremos)
        pe = max(5, min(pe, 50))

        # Calcular EPS actual
        eps = current_price / pe if pe > 0 else 0
        if eps == 0:
            return None

        # Normalizar growth rate: yfinance devuelve decimales (1.13 = 113%)
        # Limitamos a rango conservador [-10%, 25%]
        if earnings_growth and 0 < earnings_growth < 2.0:
            growth = min(earnings_growth, 0.25)
        else:
            growth = 0.10  # 10% conservador

        # Proyectar EPS 1 año adelante
        future_eps = eps * (1 + growth)

        # Target = EPS proyectado × múltiplo actual
        target_price = future_eps * pe

        # Sanity check: no más de 2x el precio actual
        if target_price > current_price * 2:
            return None

        return round(target_price, 2)

    def calculate_custom_price_target(self, ticker):
        """
        Calcula precio objetivo COMBINADO

        Metodología:
        1. DCF simplificado (40%)
        2. P/E múltiplo (30%)
        3. Consenso de analistas (30%)
        """
        fundamental_data = self.get_fundamental_data(ticker)

        if not fundamental_data:
            return None

        # Componente 1: DCF
        dcf_target = self.calculate_dcf_price_target(ticker, fundamental_data)

        # Componente 2: P/E Múltiplo
        pe_target = self.calculate_pe_multiple_target(ticker, fundamental_data)

        # Componente 3: Analistas
        analyst_target = fundamental_data['analysts']['target_mean']

        # Calcular precio objetivo ponderado
        targets = []
        weights = []

        if dcf_target and dcf_target > 0:
            targets.append(dcf_target)
            weights.append(0.40)

        if pe_target and pe_target > 0:
            targets.append(pe_target)
            weights.append(0.30)

        if analyst_target and analyst_target > 0:
            targets.append(analyst_target)
            weights.append(0.30)

        if not targets:
            return None

        # Normalizar weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Precio objetivo final
        custom_target = sum(t * w for t, w in zip(targets, normalized_weights))

        # Calcular upside
        current_price = fundamental_data['current_price']
        upside = ((custom_target / current_price - 1) * 100) if current_price > 0 else 0

        return {
            'custom_target': round(custom_target, 2),
            'upside_percent': round(upside, 2),
            'components': {
                'dcf_target': dcf_target,
                'pe_target': pe_target,
                'analyst_target': analyst_target,
            },
            'weights_used': {
                'dcf': normalized_weights[0] if len(normalized_weights) > 0 else 0,
                'pe': normalized_weights[1] if len(normalized_weights) > 1 else 0,
                'analysts': normalized_weights[2] if len(normalized_weights) > 2 else 0,
            }
        }

    def get_fundamental_score(self, ticker):
        """
        Calcula un score fundamental (0-100) basado en:
        - Valoración (P/E, PEG razonables)
        - Cash Flow (FCF Yield alto)
        - Salud financiera (D/E bajo, Current Ratio alto)
        - Rentabilidad (ROE alto)
        - Crecimiento (Revenue growth positivo)
        """
        fundamental_data = self.get_fundamental_data(ticker)

        if not fundamental_data:
            return 50  # Neutral si no hay datos

        score = 0
        components = 0

        # 1. Valoración (20 puntos)
        peg = fundamental_data['valuation']['peg_ratio']
        if peg:
            if peg < 1:
                score += 20  # Undervalued
            elif peg < 2:
                score += 15
            elif peg < 3:
                score += 10
            components += 1

        # 2. FCF Yield (20 puntos)
        fcf_yield = fundamental_data['cashflow']['fcf_yield']
        if fcf_yield:
            if fcf_yield > 10:
                score += 20
            elif fcf_yield > 5:
                score += 15
            elif fcf_yield > 2:
                score += 10
            components += 1

        # 3. Salud financiera (20 puntos)
        debt_to_equity = fundamental_data['financial_health']['debt_to_equity']
        current_ratio = fundamental_data['financial_health']['current_ratio']

        if debt_to_equity is not None:
            if debt_to_equity < 50:
                score += 10
            elif debt_to_equity < 100:
                score += 5
            components += 1

        if current_ratio:
            if current_ratio > 2:
                score += 10
            elif current_ratio > 1.5:
                score += 5
            components += 1

        # 4. Rentabilidad (20 puntos)
        roe = fundamental_data['profitability']['roe']
        if roe:
            roe_percent = roe * 100
            if roe_percent > 20:
                score += 20
            elif roe_percent > 15:
                score += 15
            elif roe_percent > 10:
                score += 10
            components += 1

        # 5. Crecimiento (20 puntos)
        revenue_growth = fundamental_data['growth']['revenue_growth']
        if revenue_growth:
            growth_percent = revenue_growth * 100
            if growth_percent > 20:
                score += 20
            elif growth_percent > 10:
                score += 15
            elif growth_percent > 5:
                score += 10
            components += 1

        # Normalizar score
        if components > 0:
            final_score = (score / components) * (100 / 20)
        else:
            final_score = 50

        return round(final_score, 2)


    def calculate_entry_score(self, ticker):
        """
        Evalúa si es un buen momento técnico de entrada (0-100)

        Pensado para sistemas VCP: premia acción en Stage 2, cerca del
        breakout (52w high) y en uptrend confirmado por medias móviles.

        Componentes:
        - Proximidad a 52w high (40 pts): cuanto más cerca del máximo, mejor
        - Medias móviles (30 pts): por encima de SMA50 y SMA200
        - Momentum anual (30 pts): retorno positivo en 52 semanas
        """
        data = self.get_fundamental_data(ticker)
        if not data:
            return None

        tech = data.get('technicals', {})
        price = data.get('current_price', 0)
        if not price or price <= 0:
            return None

        score = 0

        # 1. Proximidad a 52w high (40 pts) — VCP breakout zone
        high_52w = tech.get('fifty_two_week_high')
        if high_52w and high_52w > 0:
            distance_pct = (high_52w - price) / high_52w * 100  # % por debajo del máximo
            if distance_pct <= 5:
                score += 40   # Zona de breakout
            elif distance_pct <= 10:
                score += 30
            elif distance_pct <= 20:
                score += 20
            elif distance_pct <= 35:
                score += 10
            # >35% del máximo = 0 pts (no está en zona)

        # 2. Medias móviles (30 pts)
        sma50 = tech.get('fifty_day_avg')
        sma200 = tech.get('two_hundred_day_avg')
        if sma50 and price > sma50:
            score += 15
        if sma200 and price > sma200:
            score += 15

        # 3. Momentum anual (30 pts)
        change_52w = tech.get('fifty_two_week_change')
        if change_52w is not None:
            if change_52w > 0.30:
                score += 30   # >30% en el año
            elif change_52w > 0.15:
                score += 20
            elif change_52w > 0:
                score += 10
            # Negativo = 0 pts

        return round(score, 1)

    def get_entry_bonus(self, entry_score):
        """
        Convierte entry_score (0-100) en bonus para el super score (+0 a +5)
        """
        if entry_score is None:
            return 0
        if entry_score >= 80:
            return 5
        if entry_score >= 60:
            return 3
        if entry_score >= 40:
            return 1
        return 0


def main():
    """Test del sistema"""
    print("💰 FUNDAMENTAL ANALYZER - TEST")
    print("=" * 80)

    analyzer = FundamentalAnalyzer()

    # Test con algunos tickers
    test_tickers = ['AAPL', 'MSFT', 'NVDA']

    for ticker in test_tickers:
        print(f"\n{'='*80}")
        print(f"📊 {ticker}")
        print(f"{'='*80}")

        # Obtener datos fundamentales
        data = analyzer.get_fundamental_data(ticker)

        if not data:
            print("❌ No se pudieron obtener datos")
            continue

        # Precio actual
        current_price = data['current_price']
        print(f"\n💵 Precio Actual: ${current_price:.2f}")

        # Analistas
        analysts = data['analysts']
        if analysts['target_mean']:
            print(f"\n🏦 Consenso de Analistas:")
            print(f"   Target Promedio: ${analysts['target_mean']:.2f}")
            print(f"   Rango: ${analysts['target_low']:.2f} - ${analysts['target_high']:.2f}")
            print(f"   Upside: {analysts['upside_analysts']:.1f}%")
            print(f"   # Analistas: {analysts['num_analysts']}")

        # Price target custom
        pt = analyzer.calculate_custom_price_target(ticker)
        if pt:
            print(f"\n🎯 NUESTRO PRICE TARGET:")
            print(f"   Target: ${pt['custom_target']:.2f}")
            print(f"   Upside: {pt['upside_percent']:.1f}%")
            print(f"\n   Componentes:")
            if pt['components']['dcf_target']:
                print(f"      DCF: ${pt['components']['dcf_target']:.2f} ({pt['weights_used']['dcf']*100:.0f}%)")
            if pt['components']['pe_target']:
                print(f"      P/E: ${pt['components']['pe_target']:.2f} ({pt['weights_used']['pe']*100:.0f}%)")
            if pt['components']['analyst_target']:
                print(f"      Analistas: ${pt['components']['analyst_target']:.2f} ({pt['weights_used']['analysts']*100:.0f}%)")

        # Fundamental score
        score = analyzer.get_fundamental_score(ticker)
        print(f"\n📈 Fundamental Score: {score}/100")

        # Métricas clave
        print(f"\n📊 Métricas Clave:")
        print(f"   P/E: {data['valuation']['pe_ratio']:.2f}" if data['valuation']['pe_ratio'] else "   P/E: N/A")
        print(f"   PEG: {data['valuation']['peg_ratio']:.2f}" if data['valuation']['peg_ratio'] else "   PEG: N/A")
        print(f"   FCF Yield: {data['cashflow']['fcf_yield']:.2f}%" if data['cashflow']['fcf_yield'] else "   FCF Yield: N/A")
        print(f"   ROE: {data['profitability']['roe']*100:.1f}%" if data['profitability']['roe'] else "   ROE: N/A")
        print(f"   Revenue Growth: {data['growth']['revenue_growth']*100:.1f}%" if data['growth']['revenue_growth'] else "   Revenue Growth: N/A")


if __name__ == "__main__":
    main()

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
        growth_rate = fundamental_data['growth']['earnings_growth']

        # Validaciones
        if not fcf or not market_cap or market_cap == 0:
            return None

        # Growth rate default si no hay datos
        if not growth_rate or growth_rate < 0:
            growth_rate = 0.05  # 5% conservador

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

        # Calcular earnings actuales
        eps = current_price / pe if pe > 0 else 0

        if eps == 0:
            return None

        # Proyectar earnings 1 año adelante
        if earnings_growth and earnings_growth > 0:
            future_eps = eps * (1 + earnings_growth)
        else:
            future_eps = eps * 1.10  # 10% conservador

        # Aplicar múltiplo P/E (usar el actual como proxy del sector)
        # En versión completa: usar P/E promedio del sector
        target_price = future_eps * pe

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

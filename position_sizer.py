#!/usr/bin/env python3
"""
PORTFOLIO POSITION SIZER
Calcula tamaño óptimo de posición usando Kelly Criterion + Risk Management
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
import json


def kelly_inputs_reales(horizonte: str = '90d', muestra_minima: int = 30,
                        docs: Path = Path('docs')):
    """Win rate, ganancia media y pérdida media REALES del tracker.

    Devuelve (None, None, None) si no hay muestra suficiente: un Kelly sobre
    cuatro señales no dimensiona nada, inventa. Vive aquí y no duplicado en
    ticker_api.py porque los dos sitios que dimensionan posiciones tienen que
    partir del mismo dato — antes la API usaba unos defaults escritos a mano
    (win rate 75%, +5%/-3%) que daban siempre exactamente el tope del 10%.
    """
    csv = docs / 'portfolio_tracker' / 'recommendations.csv'
    if not csv.exists():
        return None, None, None
    try:
        df = pd.read_csv(csv)
    except Exception as e:
        print(f"   ⚠️  No se pudo leer el tracker: {e}")
        return None, None, None

    col = f'return_{horizonte}'
    if col not in df.columns:
        return None, None, None

    retornos = pd.to_numeric(df[col], errors='coerce').dropna()
    if len(retornos) < muestra_minima:
        return None, None, None

    ganancias = retornos[retornos > 0]
    perdidas  = retornos[retornos <= 0]
    if ganancias.empty or perdidas.empty:
        return None, None, None

    return (
        len(ganancias) / len(retornos),
        float(ganancias.mean()),
        float(perdidas.mean()),
    )


class PositionSizer:
    """Calculadora de tamaño óptimo de posición"""

    def __init__(self, portfolio_value: float = 100000,
                 max_risk_per_trade: float = 0.02,
                 max_position_size: float = 0.10):
        """
        Args:
            portfolio_value: Valor total del portfolio en USD
            max_risk_per_trade: Máximo riesgo por trade (0.02 = 2%)
            max_position_size: Máximo tamaño de posición (0.10 = 10%)
        """
        self.portfolio_value = portfolio_value
        self.max_risk_per_trade = max_risk_per_trade
        self.max_position_size = max_position_size

    def calculate_kelly_criterion(self, win_rate: float, avg_win: float,
                                  avg_loss: float) -> float:
        """
        Calcula Kelly Criterion para tamaño óptimo

        Args:
            win_rate: Win rate histórico (0-1)
            avg_win: Avg return de wins (%)
            avg_loss: Avg return de losses (% negativo)

        Returns:
            Kelly percentage (0-1)
        """
        if avg_loss >= 0 or avg_win <= 0:
            return 0.0

        # Kelly = (W * R - L) / R
        # W = win rate, L = loss rate, R = win/loss ratio
        win_loss_ratio = abs(avg_win / avg_loss)
        loss_rate = 1 - win_rate

        kelly = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio

        # Kelly fractionado (usar 25-50% del Kelly completo para ser conservador)
        fractional_kelly = max(0, min(kelly * 0.5, self.max_position_size))

        return fractional_kelly

    def get_volatility(self, ticker: str, days: int = 30) -> Optional[float]:
        """
        Calcula volatilidad histórica (ATR-based)

        Args:
            ticker: Stock ticker
            days: Sesiones de histórico necesarias

        Returns:
            Volatilidad como fracción del precio, o None si no se pudo calcular.

        `days` son sesiones, no días naturales, así que hay que pedir bastante
        más calendario del que se necesita: un fin de semana cada cinco días,
        más festivos. Pedía `days + 10` —40 naturales para 30 sesiones, unas
        28 reales— así que el `len(df) < days` saltaba SIEMPRE y todos los
        tickers salían con el 20% por defecto. En el CSV de producción los 14
        tenían volatilidad 20.0, stop 40.0 y Kelly 10.0: idénticos.

        Y devolver un 0.20 inventado cuando el dato falla es justo lo que este
        repo no hace (ver CLAUDE.md): sin dato no hay número. Ahora es None y
        el ticker se queda fuera del sizing.
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=int(days * 1.6) + 15)

            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if df.empty or len(df) < days:
                print(f"   ⚠️  {ticker}: solo {len(df)} sesiones, hacen falta {days}")
                return None

            # Average True Range (ATR)
            high = df['High']
            low = df['Low']
            close = df['Close']

            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean().iloc[-1]

            # Volatility as % of current price
            current_price = float(close.iloc[-1].item() if hasattr(close.iloc[-1], 'item') else close.iloc[-1])
            if not (current_price > 0) or not (atr > 0):
                return None

            return float(atr / current_price)

        except Exception as e:
            print(f"   ⚠️  Error calculando volatility para {ticker}: {e}")
            return None

    # Horizonte sobre el que se mide el edge. Medido en el tracker (sep-2026),
    # la ventaja del sistema es una función del plazo y NO existe a corto:
    #
    #     7d   n=1692  win 29.2%   1/2 Kelly  0.0%
    #    14d   n=1644  win 30.4%   1/2 Kelly  0.0%
    #    30d   n=1557  win 45.9%   1/2 Kelly  0.0%
    #    90d   n=1511  win 55.1%   1/2 Kelly 12.3%
    #   180d   n= 844  win 70.7%   1/2 Kelly 25.6%
    #
    # Dimensionar a 30d daba Kelly 0 para todo, que es la respuesta correcta a
    # la pregunta equivocada: aquí no se vende a fecha, se vende a precio
    # objetivo por valoración. 90d es el plazo más corto con ventaja real y el
    # más conservador de los dos que la tienen.
    HORIZONTE_KELLY = '90d'
    MUESTRA_MINIMA_KELLY = 30

    def _kelly_inputs_reales(self):
        return kelly_inputs_reales(self.HORIZONTE_KELLY, self.MUESTRA_MINIMA_KELLY)

    def calculate_position_size(self, ticker: str, score_5d: float,
                                tier: str, timing_convergence: bool,
                                sector_status: str = 'NEUTRAL',
                                current_price: float = None,
                                win_rate: float = 0.75,
                                avg_win: float = 5.0,
                                avg_loss: float = -3.0) -> Dict:
        """
        Calcula tamaño óptimo de posición para un ticker

        Args:
            ticker: Stock ticker
            score_5d: Super score 5D
            tier: Tier de oportunidad
            timing_convergence: Si tiene timing convergence
            sector_status: Status del sector (LEADING, IMPROVING, etc.)
            current_price: Precio actual (None = fetch from yfinance)
            win_rate: Win rate histórico
            avg_win: Avg return wins
            avg_loss: Avg return losses

        Returns:
            Dict con sizing recommendation
        """
        print(f"   Calculando position size para {ticker}...")

        # Get current price
        if current_price is None:
            try:
                stock = yf.Ticker(ticker)
                current_price = stock.history(period='1d')['Close'].iloc[-1]
            except Exception:
                return {
                    'ticker': ticker,
                    'error': 'No se pudo obtener precio actual'
                }

        # El CSV de oportunidades trae NaN cuando el precio no se pudo leer, y
        # un NaN no es None: pasaba el filtro de arriba y reventaba más abajo
        # en int(position_value / current_price). El script llevaba caído desde
        # el 11-feb-2026 por esto, tapado por el `|| echo "Position sizing
        # failed"` del workflow, sirviendo un CSV de siete meses atrás.
        try:
            current_price = float(current_price)
        except (TypeError, ValueError):
            return {'ticker': ticker, 'error': 'Precio actual no numérico'}
        if not (current_price > 0):
            return {'ticker': ticker, 'error': 'Precio actual ausente o no positivo'}

        # Get volatility
        volatility = self.get_volatility(ticker)
        if volatility is None:
            return {'ticker': ticker, 'error': 'Sin volatilidad: no se dimensiona'}

        # Calculate Kelly
        kelly_pct = self.calculate_kelly_criterion(win_rate, avg_win, avg_loss)

        # Adjust based on score 5D
        score_multiplier = 1.0
        if score_5d >= 80:
            score_multiplier = 1.3  # LEGENDARY/ÉPICA - size up
        elif score_5d >= 70:
            score_multiplier = 1.2  # EXCELENTE
        elif score_5d >= 60:
            score_multiplier = 1.0  # BUENA
        else:
            score_multiplier = 0.7  # MODERADA - size down

        # Adjust based on timing convergence
        timing_multiplier = 1.2 if timing_convergence else 1.0

        # Adjust based on sector status
        sector_multiplier = {
            'LEADING': 1.2,
            'IMPROVING': 1.1,
            'NEUTRAL': 1.0,
            'WEAKENING': 0.7,
            'LAGGING': 0.5
        }.get(sector_status, 1.0)

        # Adjust based on volatility (more volatile = smaller position)
        volatility_multiplier = 1.0
        if volatility > 0.15:  # High volatility (>15%)
            volatility_multiplier = 0.7
        elif volatility < 0.05:  # Low volatility (<5%)
            volatility_multiplier = 1.2

        # Los cuatro multiplicadores se reescalan para que el mejor caso valga 1
        # y el resto descuente desde ahí. Antes multiplicaban por encima de 1
        # (hasta 2.25x entre los cuatro) contra un Kelly que ya estaba en el
        # tope del 10%, así que todo lo que no fuera malísimo se recortaba al
        # mismo 10%: 10 de 13 posiciones salían con el tamaño idéntico y el
        # "ajuste por volatilidad, score y timing" del subtítulo no ajustaba
        # nada. El tope es un techo, no un objetivo: solo lo alcanza un pick
        # que sea lo mejor en las cuatro dimensiones.
        techo = min(kelly_pct, self.max_position_size)
        descuento = (
            (score_multiplier / 1.3) *
            (timing_multiplier / 1.2) *
            (sector_multiplier / 1.2) *
            (volatility_multiplier / 1.2)
        )
        position_size_pct = techo * min(descuento, 1.0)

        # Calculate dollar amount
        position_value = self.portfolio_value * position_size_pct

        # Calculate shares
        shares = int(position_value / current_price)

        # Calculate stop loss (based on volatility)
        stop_loss_pct = volatility * 2  # 2x ATR
        stop_loss_price = current_price * (1 - stop_loss_pct)

        # Calculate risk amount
        risk_per_share = current_price - stop_loss_price
        total_risk = shares * risk_per_share
        risk_pct_portfolio = (total_risk / self.portfolio_value) * 100

        return {
            'ticker': ticker,
            'current_price': round(current_price, 2),
            'position_size_pct': round(position_size_pct * 100, 2),
            'position_value': round(position_value, 2),
            'shares': shares,
            'stop_loss_price': round(stop_loss_price, 2),
            'stop_loss_pct': round(stop_loss_pct * 100, 2),
            'risk_amount': round(total_risk, 2),
            'risk_pct_portfolio': round(risk_pct_portfolio, 2),
            'volatility': round(volatility * 100, 2),
            'kelly_pct': round(kelly_pct * 100, 2),
            'multipliers': {
                'score': score_multiplier,
                'timing': timing_multiplier,
                'sector': sector_multiplier,
                'volatility': volatility_multiplier
            }
        }

    def size_portfolio(self, opportunities_csv: str,
                      sector_rotation_json: str = None,
                      ) -> pd.DataFrame:
        """
        Calcula sizing para todas las oportunidades

        Args:
            opportunities_csv: Path al CSV con oportunidades 5D
            sector_rotation_json: Path al JSON con rotation data

        Returns:
            DataFrame con recommendations
        """
        print("\n💰 PORTFOLIO POSITION SIZER")
        print("=" * 70)

        # Load opportunities
        df = pd.read_csv(opportunities_csv)
        df = df[df['super_score_5d'] >= 55].copy()  # Filter BUENA o mejor

        # Load sector data
        sector_data = {}
        if sector_rotation_json and Path(sector_rotation_json).exists():
            with open(sector_rotation_json, 'r') as f:
                rotation = json.load(f)
                for sector in rotation.get('results', []):
                    sector_data[sector['sector']] = sector['status']

        # Kelly necesita win rate, ganancia media y PÉRDIDA media. La pérdida se
        # "estimaba" con avg_win * (w/(1-w)) * -0.6, que no es una estimación:
        # sustituyéndola en la fórmula, el ratio se cancela y Kelly queda en
        # 0.4*w, o sea 0.2*w tras el medio Kelly. Con cualquier win rate por
        # encima del 50% eso supera el tope del 10% y sale SIEMPRE 10%. Por eso
        # los 14 tickers del CSV tenían kelly_pct idéntico: el "Kelly criterion"
        # del titular era una constante por construcción, no una medida.
        #
        # Las tres cifras están medidas de verdad en el tracker, sobre señales
        # ya cerradas. Se usan esas o no se dimensiona nada.
        win_rate, avg_win, avg_loss = self._kelly_inputs_reales()
        if win_rate is None:
            print("   ⚠️  Sin señales cerradas suficientes en el tracker: no se dimensiona")
            return pd.DataFrame()
        print(f"   Win Rate (tracker, {self.HORIZONTE_KELLY}): {win_rate*100:.1f}%")
        print(f"   Avg Win: {avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")

        print(f"   Portfolio Value: ${self.portfolio_value:,.0f}")
        print(f"   Max Risk per Trade: {self.max_risk_per_trade*100:.1f}%")
        print(f"   Win Rate (from backtest): {win_rate*100:.1f}%")
        print(f"   Avg Win: {avg_win:.2f}% | Avg Loss: {avg_loss:.2f}%")

        # Calculate sizing for each opportunity
        results = []
        for idx, row in df.iterrows():
            ticker = row['ticker']
            score = row['super_score_5d']
            tier = row.get('tier', '')
            timing_conv = row.get('timing_convergence', False)
            sector_name = row.get('sector_name', '')
            sector_status = sector_data.get(sector_name, 'NEUTRAL')
            current_price = row.get('current_price', None)

            sizing = self.calculate_position_size(
                ticker, score, tier, timing_conv, sector_status,
                current_price, win_rate, avg_win, avg_loss
            )

            if 'error' not in sizing:
                results.append(sizing)

        results_df = pd.DataFrame(results)
        # El Kelly base no significa nada sin decir sobre qué plazo se midió:
        # con este mismo tracker, a 30 días sale 0 y a 90 sale 12.3%. Viaja con
        # el dato para que la interfaz pueda decirlo en vez de enseñar un
        # porcentaje suelto.
        results_df['kelly_horizon'] = self.HORIZONTE_KELLY
        results_df['kelly_win_rate'] = round(win_rate * 100, 1)
        if results_df.empty:
            print("   ⚠️  Ningún ticker pudo dimensionarse")
            return results_df

        # Sort by position_value (descending)
        results_df = results_df.sort_values('position_value', ascending=False)

        # Cada posición se dimensionaba por su cuenta y nadie miraba la suma:
        # el CSV de producción repartía 111.8% del capital, y la página lo
        # enseñaba tal cual ("Capital asignado $112k de $100k"). Kelly da el
        # tamaño de UNA apuesta aislada; con varias a la vez hay que repartir.
        # Si la suma se pasa, se escala todo proporcionalmente hasta el 100%.
        suma_pct = results_df['position_size_pct'].sum()
        if suma_pct > 100:
            factor = 100 / suma_pct
            print(f"   ℹ️  Asignación al {suma_pct:.1f}%: se escala x{factor:.3f} hasta el 100%")
            for col in ('position_size_pct', 'position_value', 'risk_amount', 'risk_pct_portfolio'):
                if col in results_df.columns:
                    results_df[col] = (results_df[col] * factor).round(2)
            results_df['shares'] = (
                results_df['position_value'] / results_df['current_price']
            ).astype(int)

        return results_df

    def print_summary(self, results_df: pd.DataFrame):
        """Imprime resumen de sizing"""
        print("\n📊 POSITION SIZING RECOMMENDATIONS")
        print("=" * 70)

        if results_df.empty:
            print("\n   (ninguna posición dimensionada)")
            return

        print(f"\n🏆 TOP 10 POSITIONS:")
        for idx, row in results_df.head(10).iterrows():
            print(f"\n   {row['ticker']}:")
            print(f"      Shares: {row['shares']} @ ${row['current_price']:.2f}")
            print(f"      Position: ${row['position_value']:,.0f} ({row['position_size_pct']:.1f}% of portfolio)")
            print(f"      Stop Loss: ${row['stop_loss_price']:.2f} (-{row['stop_loss_pct']:.1f}%)")
            print(f"      Risk: ${row['risk_amount']:,.0f} ({row['risk_pct_portfolio']:.2f}% of portfolio)")

        print(f"\n📈 PORTFOLIO ALLOCATION:")
        total_allocated = results_df['position_value'].sum()
        total_risk = results_df['risk_amount'].sum()
        print(f"   Total Allocated: ${total_allocated:,.0f} ({total_allocated/self.portfolio_value*100:.1f}%)")
        print(f"   Total Risk: ${total_risk:,.0f} ({total_risk/self.portfolio_value*100:.1f}%)")
        print(f"   Number of Positions: {len(results_df)}")

    def save_results(self, results_df: pd.DataFrame,
                    output_file: str = "docs/position_sizing.csv"):
        """Guarda resultados"""
        results_df.to_csv(output_file, index=False)
        print(f"\n💾 Position sizing guardado: {output_file}")


def main():
    """Main execution"""
    sizer = PositionSizer(portfolio_value=100000, max_risk_per_trade=0.02)

    # Size portfolio
    results = sizer.size_portfolio(
        "docs/super_opportunities_5d_complete.csv",
        "docs/sector_rotation/latest_scan.json",
    )

    # Sin resultados NO se sobrescribe el CSV: dejar el anterior es preferible a
    # borrar la sección por un fallo de red. Se sale con error para que el paso
    # del workflow no pase por bueno un día en blanco.
    if results.empty:
        print("\n❌ Sin posiciones dimensionadas: se mantiene el CSV anterior")
        raise SystemExit(1)

    # Print summary
    sizer.print_summary(results)

    # Save results
    sizer.save_results(results)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
ENTRY/EXIT PRICE CALCULATOR
Calcula precios de entrada y salida basados en análisis técnico y fundamental

Metodología:
- Entry: VCP pivot point, pullback zones, soporte
- Exit: Fair value (PE target), analyst targets, resistencias
- Stop Loss: Soporte técnico, -7-8% (Minervini rule)
- Risk/Reward: Ratio mínimo 3:1
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


def _num(v):
    """Número utilizable, o None. Sin inventar un 0 por el camino."""
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


class EntryExitCalculator:
    """Calcula precios óptimos de entrada/salida"""

    def __init__(self):
        self.min_risk_reward = 3.0  # Mínimo 3:1 risk/reward
        self.max_stop_loss_pct = 8.0  # Máximo 8% pérdida (Minervini)

    def calculate_entry_exit(
        self,
        ticker: str,
        current_price: float,
        hist: pd.DataFrame,
        vcp_analysis: Dict,
        fundamental_data: Dict,
        validation: Dict
    ) -> Dict:
        """
        Calcula precios de entrada, salida y stop loss

        Args:
            ticker: Ticker symbol
            current_price: Precio actual
            hist: Historical price data (OHLCV)
            vcp_analysis: VCP pattern analysis
            fundamental_data: Fundamental metrics
            validation: Validation data with ATH info

        Returns:
            Dict con entry, exit, stop loss, risk/reward
        """
        # Calculate technical levels
        entry_price = self._calculate_entry_price(
            current_price, hist, vcp_analysis, validation
        )

        stop_loss = self._calculate_stop_loss(
            entry_price, hist, vcp_analysis
        )

        exit_price = self._calculate_exit_price(
            current_price, hist, fundamental_data, validation
        )

        # Calculate risk/reward
        risk = entry_price - stop_loss
        # Sin objetivo por valoración no hay recompensa que medir, y por tanto
        # tampoco R:R. Antes esto no podía pasar porque el objetivo se inventaba.
        reward = (exit_price - entry_price) if exit_price is not None else None
        risk_reward = (reward / risk) if (reward is not None and risk > 0) else None

        # Entry timing recommendation
        entry_timing = self._get_entry_timing(
            current_price, entry_price, vcp_analysis
        )

        return {
            'ticker': ticker,
            'current_price': round(current_price, 2),
            'entry_price': round(entry_price, 2),
            'entry_range_low': round(entry_price * 0.98, 2),  # -2%
            'entry_range_high': round(entry_price * 1.02, 2),  # +2%
            'stop_loss': round(stop_loss, 2),
            'exit_price': round(exit_price, 2) if exit_price is not None else None,
            'exit_range_low': round(exit_price * 0.95, 2) if exit_price is not None else None,
            'exit_range_high': round(exit_price * 1.05, 2) if exit_price is not None else None,
            'risk_dollars': round(risk, 2),
            'reward_dollars': round(reward, 2) if reward is not None else None,
            'risk_reward_ratio': round(risk_reward, 2) if risk_reward is not None else None,
            'risk_pct': round((risk / entry_price) * 100, 2),
            'reward_pct': round((reward / entry_price) * 100, 2) if reward is not None else None,
            'entry_timing': entry_timing,
            'meets_criteria': (risk_reward is not None and risk_reward >= self.min_risk_reward)
        }

    def _calculate_entry_price(
        self,
        current_price: float,
        hist: pd.DataFrame,
        vcp_analysis: Dict,
        validation: Dict
    ) -> float:
        """
        Calcula precio de entrada óptimo

        Considera:
        1. VCP pivot point (breakout level)
        2. Pullback to 10-day MA
        3. Current support levels
        4. Price vs ATH
        """
        if hist.empty:
            return current_price

        # Get recent highs for pivot point
        # Handle both capitalized and lowercase column names
        high_col = 'high' if 'high' in hist.columns else 'High'
        low_col = 'low' if 'low' in hist.columns else 'Low'
        close_col = 'close' if 'close' in hist.columns else 'Close'

        recent_high = hist[high_col].tail(20).max()
        recent_low = hist[low_col].tail(20).min()

        # VCP pivot point (if detected)
        vcp_detected = vcp_analysis.get('pattern_detected', False)

        if vcp_detected:
            # Entry at pivot point (recent high resistance)
            pivot_point = recent_high

            # But if we're in a pullback, wait for better entry
            if current_price < pivot_point * 0.95:
                # Entry at 10-day MA or current price, whichever is lower
                ma_10 = hist[close_col].tail(10).mean()
                entry = min(ma_10, current_price * 1.02)  # Up to 2% above current
            else:
                # Entry at pivot breakout
                entry = pivot_point * 1.01  # 1% above pivot

        else:
            # No clear VCP, entry at current support levels
            # Use 20-day low as support
            support = recent_low * 1.02  # 2% above recent low
            entry = max(support, current_price * 0.98)  # Close to current

        # Adjust based on ATH distance
        price_vs_ath = validation.get('price_vs_ath', 0)
        if price_vs_ath and price_vs_ath > -5:
            # Very close to ATH - wait for confirmation
            entry = current_price * 1.01  # Buy on breakout confirmation
        elif price_vs_ath and price_vs_ath < -15:
            # Good pullback - can enter at current
            entry = min(entry, current_price)

        return max(entry, current_price * 0.95)  # Not more than 5% below current

    def _calculate_stop_loss(
        self,
        entry_price: float,
        hist: pd.DataFrame,
        vcp_analysis: Dict
    ) -> float:
        """
        Calcula stop loss basado en soporte técnico

        Metodología:
        1. Soporte técnico (recent low)
        2. -7-8% máximo (Minervini rule)
        3. Below 10-day MA if broken
        """
        if hist.empty:
            return entry_price * 0.92  # Default -8%

        # Handle both capitalized and lowercase column names
        low_col = 'low' if 'low' in hist.columns else 'Low'

        # Technical support (recent 20-day low)
        recent_low = hist[low_col].tail(20).min()
        technical_stop = recent_low * 0.98  # 2% below recent low

        # Minervini stop (-7-8%)
        minervini_stop = entry_price * (1 - (self.max_stop_loss_pct / 100))

        # Use tighter of the two
        stop_loss = max(technical_stop, minervini_stop)

        # But never more than 8% loss
        if (entry_price - stop_loss) / entry_price > 0.08:
            stop_loss = entry_price * 0.92

        return stop_loss

    def _calculate_exit_price(
        self,
        current_price: float,
        hist: pd.DataFrame,
        fundamental_data: Dict,
        validation: Dict
    ) -> float | None:
        """Precio de salida POR VALORACIÓN, con los objetivos que ya calcula el
        pipeline. None si no hay ninguno utilizable.

        Lo que había aquí no era una valoración. Era:

            40%  «un 10% por encima del máximo de 52 semanas»
            40%  «suponer que toda empresa merece un PER de 25»
            20%  `current_price * 1.30`  ← un placeholder fijo, y el comentario
                                            del código lo decía: "Placeholder"
            y un suelo de `max(exit, precio × 1.20)`, "asegurar al menos un 20%"

        Resultado medido el 16-sep-2026 sobre las 34 filas del VALUE filtrado:
        el `exit_price` quedaba POR ENCIMA del consenso de analistas en 33 de
        34, con un desvío mediano del +10,5% y hasta +35% en INTU.

        Dos problemas, y el segundo es el grave:

          · los objetivos de verdad —consenso, DCF, modelo P/E— ya están
            calculados en el CSV, en la fila de al lado, y no se miraban;
          · el suelo del 20% es vender a un PORCENTAJE FIJO, que es justo lo
            que el perfil del usuario descarta: vende a precio objetivo por
            valoración, nunca a un % de ganancia. Con ese suelo, ningún pick
            podía tener un objetivo por debajo de +20% aunque estuviera en su
            precio justo.

        Ahora: ancla en el consenso de analistas, y solo promedia con los
        modelos propios si esos modelos están de acuerdo ENTRE ELLOS. Cuando
        DCF y P/E se contradicen en el signo no hay valoración propia en la que
        apoyarse (ver upside_triangulation), así que se usa el consenso solo.
        Sin ningún objetivo utilizable no se inventa uno: None, y sin objetivo
        no hay R:R.
        """
        analista = _num(validation.get('target_price_analyst'))
        if not analista or analista <= 0:
            return None

        # Los modelos propios NO promedian con el analista: deciden si su
        # objetivo vale o no. Es la política que el resto del sistema ya aplica
        # (`upside_divergence` en super_score_integrator): «si DCF y P/E
        # contradicen al sell-side, el upside del analista no es argumento».
        #
        # Promediarlos sería repetir el error de `upside_triangulated_pct`, que
        # publicaba la mediana de respuestas contrarias como si fuera una
        # triangulación. Con VRSN salía un objetivo de 224,90 sobre un precio de
        # 301 — de promediar un +8% del consenso con un -59% de los modelos.
        # Eso no es una valoración, es la media de un sí y un no.
        dcf = _num(validation.get('target_price_dcf'))
        pe = _num(validation.get('target_price_pe'))
        if dcf and pe and dcf > 0 and pe > 0:
            up_dcf, up_pe = dcf / current_price - 1, pe / current_price - 1
            en_rango = abs(up_dcf) <= 2.0 and abs(up_pe) <= 2.0   # ADR con divisa rota
            if en_rango:
                up_analista = analista / current_price - 1
                # Si los dos modelos coinciden en que va al otro lado que el
                # analista, no hay objetivo en el que apoyarse.
                if (up_dcf < 0) == (up_pe < 0) and (up_dcf < 0) != (up_analista < 0):
                    return None

        return analista

    def _get_entry_timing(
        self,
        current_price: float,
        entry_price: float,
        vcp_analysis: Dict
    ) -> str:
        """
        Determina timing de entrada

        Returns:
            String con recomendación de timing
        """
        price_diff_pct = ((entry_price - current_price) / current_price) * 100

        vcp_detected = vcp_analysis.get('pattern_detected', False)

        if abs(price_diff_pct) < 2:
            if vcp_detected:
                return "BUY NOW - VCP setup confirmed, at entry point"
            else:
                return "BUY NOW - At target entry price"

        elif price_diff_pct > 2:
            if price_diff_pct > 5:
                return "WAIT - Price needs to rise 5%+ to entry point"
            else:
                return "BUY ON BREAKOUT - Entry 2-5% above current"

        else:  # entry_price < current_price
            if abs(price_diff_pct) < 5:
                return "BUY ON PULLBACK - Wait for 2-5% dip"
            else:
                return "CAUTION - Already above entry point, wait for pullback"


def calculate_position_size(
    account_size: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float
) -> Dict:
    """
    Calcula tamaño de posición basado en risk management

    Args:
        account_size: Total account value
        risk_pct: Risk per trade (e.g., 1.0 for 1%)
        entry_price: Entry price
        stop_loss: Stop loss price

    Returns:
        Dict con shares, position_value, risk_amount
    """
    risk_amount = account_size * (risk_pct / 100)
    risk_per_share = entry_price - stop_loss

    if risk_per_share <= 0:
        return {
            'shares': 0,
            'position_value': 0,
            'risk_amount': 0,
            'error': 'Invalid stop loss (must be below entry)'
        }

    shares = int(risk_amount / risk_per_share)
    position_value = shares * entry_price
    position_pct = (position_value / account_size) * 100

    return {
        'shares': shares,
        'position_value': round(position_value, 2),
        'position_pct': round(position_pct, 2),
        'risk_amount': round(risk_amount, 2),
        'risk_per_share': round(risk_per_share, 2)
    }


if __name__ == "__main__":
    # Test with sample data
    import sys

    print("\n" + "="*80)
    print("ENTRY/EXIT CALCULATOR - TEST")
    print("="*80)

    # Sample data
    ticker = "AAPL"
    current_price = 150.00
    hist = pd.DataFrame({
        'close': [145, 147, 149, 148, 150],
        'high': [146, 148, 150, 149, 151],
        'low': [144, 146, 148, 147, 149]
    })

    vcp_analysis = {
        'score': 85,
        'pattern_detected': True
    }

    fundamental_data = {
        'pe_ratio': 28.5
    }

    validation = {
        'price_vs_ath': -3.5  # 3.5% below ATH
    }

    calc = EntryExitCalculator()
    result = calc.calculate_entry_exit(
        ticker, current_price, hist, vcp_analysis,
        fundamental_data, validation
    )

    print(f"\n📊 {ticker} Entry/Exit Analysis:")
    print(f"   Current Price: ${result['current_price']}")
    print(f"\n🎯 ENTRY:")
    print(f"   Entry Price: ${result['entry_price']}")
    print(f"   Entry Range: ${result['entry_range_low']} - ${result['entry_range_high']}")
    print(f"   Timing: {result['entry_timing']}")
    print(f"\n🛑 STOP LOSS:")
    print(f"   Stop Loss: ${result['stop_loss']}")
    print(f"   Risk: ${result['risk_dollars']} ({result['risk_pct']}%)")
    print(f"\n🎯 EXIT:")
    print(f"   Target Price: ${result['exit_price']}")
    print(f"   Exit Range: ${result['exit_range_low']} - ${result['exit_range_high']}")
    print(f"   Reward: ${result['reward_dollars']} ({result['reward_pct']}%)")
    print(f"\n📈 RISK/REWARD:")
    print(f"   Ratio: {result['risk_reward_ratio']}:1")
    print(f"   Meets Criteria: {'✅ YES' if result['meets_criteria'] else '❌ NO'}")

    # Position sizing example
    print(f"\n💰 POSITION SIZING (1% risk on $100,000 account):")
    position = calculate_position_size(
        account_size=100000,
        risk_pct=1.0,
        entry_price=result['entry_price'],
        stop_loss=result['stop_loss']
    )
    print(f"   Shares: {position['shares']}")
    print(f"   Position Value: ${position['position_value']}")
    print(f"   Position %: {position['position_pct']}%")
    print(f"   Risk Amount: ${position['risk_amount']}")

    print("\n" + "="*80 + "\n")

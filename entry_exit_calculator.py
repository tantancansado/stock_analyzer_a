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
        reward = exit_price - entry_price
        risk_reward = reward / risk if risk > 0 else 0

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
            'exit_price': round(exit_price, 2),
            'exit_range_low': round(exit_price * 0.95, 2),  # Conservative
            'exit_range_high': round(exit_price * 1.05, 2),  # Optimistic
            'risk_dollars': round(risk, 2),
            'reward_dollars': round(reward, 2),
            'risk_reward_ratio': round(risk_reward, 2),
            'risk_pct': round((risk / entry_price) * 100, 2),
            'reward_pct': round((reward / entry_price) * 100, 2),
            'entry_timing': entry_timing,
            'meets_criteria': risk_reward >= self.min_risk_reward
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
    ) -> float:
        """
        Calcula precio de salida basado en fundamentales y técnico

        Considera:
        1. Fair value (PE target)
        2. Analyst price targets
        3. Technical resistance (52-week high)
        4. Risk/Reward minimum 3:1
        """
        # Technical target (ATH or above)
        year_high = validation.get('price_vs_ath')
        if year_high is not None:
            # Calculate actual 52-week high from percentage
            ath_price = current_price / (1 + (year_high / 100))
            technical_target = ath_price * 1.10  # 10% above ATH
        else:
            technical_target = current_price * 1.30  # Default 30% gain

        # Fundamental target (PE-based)
        pe_ratio = fundamental_data.get('pe_ratio')
        if pe_ratio and pe_ratio > 0:
            # Target PE of 25-30 for growth stocks
            sector_avg_pe = 25
            if pe_ratio < sector_avg_pe:
                # Undervalued - price could expand to sector avg
                fundamental_target = current_price * (sector_avg_pe / pe_ratio)
                # Cap at 100% upside
                fundamental_target = min(fundamental_target, current_price * 2.0)
            else:
                # Already at or above sector avg
                fundamental_target = current_price * 1.20  # 20% upside
        else:
            fundamental_target = current_price * 1.25  # Default 25%

        # Analyst target (if available)
        # Note: This would come from validation or analyst data
        analyst_target = current_price * 1.30  # Placeholder

        # Take weighted average of targets
        weights = {
            'technical': 0.40,
            'fundamental': 0.40,
            'analyst': 0.20
        }

        exit_price = (
            technical_target * weights['technical'] +
            fundamental_target * weights['fundamental'] +
            analyst_target * weights['analyst']
        )

        # Ensure minimum return (at least 20%)
        min_target = current_price * 1.20
        exit_price = max(exit_price, min_target)

        return exit_price

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

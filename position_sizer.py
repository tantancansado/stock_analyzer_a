#!/usr/bin/env python3
"""
PORTFOLIO POSITION SIZER
Calcula tamaño óptimo de posición usando Kelly Criterion + Risk Management
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import json


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

    def get_volatility(self, ticker: str, days: int = 30) -> float:
        """
        Calcula volatilidad histórica (ATR-based)

        Args:
            ticker: Stock ticker
            days: Días de histórico

        Returns:
            Volatility as % of price
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)

            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if df.empty or len(df) < days:
                return 0.20  # Default 20% volatility

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
            current_price = float(close.iloc[-1])
            volatility = (atr / current_price) if current_price > 0 else 0.20

            return float(volatility)

        except Exception as e:
            print(f"   ⚠️  Error calculando volatility para {ticker}: {e}")
            return 0.20

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
            except:
                return {
                    'ticker': ticker,
                    'error': 'No se pudo obtener precio actual'
                }

        # Get volatility
        volatility = self.get_volatility(ticker)

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

        # Calculate final position size
        position_size_pct = kelly_pct * score_multiplier * timing_multiplier * \
                           sector_multiplier * volatility_multiplier

        # Clamp to max position size
        position_size_pct = min(position_size_pct, self.max_position_size)

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
                      backtest_metrics_json: str = None) -> pd.DataFrame:
        """
        Calcula sizing para todas las oportunidades

        Args:
            opportunities_csv: Path al CSV con oportunidades 5D
            sector_rotation_json: Path al JSON con rotation data
            backtest_metrics_json: Path al JSON con backtest metrics

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

        # Load backtest metrics
        win_rate = 0.75
        avg_win = 5.0
        avg_loss = -3.0
        if backtest_metrics_json and Path(backtest_metrics_json).exists():
            with open(backtest_metrics_json, 'r') as f:
                metrics = json.load(f)
                win_rate = metrics.get('win_rate', 75) / 100
                avg_win = metrics.get('avg_return', 5.0)
                # Estimate avg loss from avg return and win rate
                avg_loss = avg_win * (win_rate / (1 - win_rate)) * -0.6 if win_rate < 1 else -3.0

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

        # Sort by position_value (descending)
        results_df = results_df.sort_values('position_value', ascending=False)

        return results_df

    def print_summary(self, results_df: pd.DataFrame):
        """Imprime resumen de sizing"""
        print("\n📊 POSITION SIZING RECOMMENDATIONS")
        print("=" * 70)

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
        sorted(Path("docs/backtest").glob("metrics_*.json"))[-1] if Path("docs/backtest").exists() else None
    )

    # Print summary
    sizer.print_summary(results)

    # Save results
    sizer.save_results(results)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MEAN REVERSION BACKTESTER
Valida las estrategias de Mean Reversion con datos históricos
Simula entradas en oversold bounces y bull flags para calcular rendimiento real
"""
import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json
from mean_reversion_detector import MeanReversionDetector


class MeanReversionBacktester:
    """Backtester para estrategias de Mean Reversion"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.trades = []
        self.detector = MeanReversionDetector()

    def backtest_opportunity(self, ticker: str, opportunity: Dict,
                            holding_period_days: int = 30) -> Dict:
        """
        Backtestea una oportunidad específica

        Args:
            ticker: Símbolo del stock
            opportunity: Dict con datos de la oportunidad
            holding_period_days: Días de retención máxima

        Returns:
            Dict con resultado del trade
        """
        try:
            # Obtener datos históricos (90 días adicionales para el holding period)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.detector.lookback_days + holding_period_days + 30)

            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)

            if len(hist) < 50:
                return None

            # Simular entrada en el precio actual de la oportunidad
            entry_price = opportunity['current_price']
            target_price = opportunity['target']
            stop_loss = opportunity['stop_loss']
            strategy = opportunity['strategy']

            # Encontrar la fecha más cercana al escaneo
            entry_date_idx = len(hist) - 1  # Último día disponible

            # Simular holding period
            exit_date_idx = min(entry_date_idx + holding_period_days, len(hist) - 1)

            # Tracking del trade
            max_profit = 0
            max_loss = 0
            hit_target = False
            hit_stop = False
            exit_reason = "HOLDING_PERIOD"
            exit_price = hist['Close'].iloc[exit_date_idx]

            # Simular movimiento intraperiodo
            for i in range(entry_date_idx, exit_date_idx + 1):
                current_price = hist['Close'].iloc[i]
                current_high = hist['High'].iloc[i]
                current_low = hist['Low'].iloc[i]

                # Calcular profit/loss
                profit_pct = ((current_price - entry_price) / entry_price) * 100
                max_profit = max(max_profit, ((current_high - entry_price) / entry_price) * 100)
                max_loss = min(max_loss, ((current_low - entry_price) / entry_price) * 100)

                # Check target
                if current_high >= target_price:
                    hit_target = True
                    exit_price = target_price
                    exit_reason = "TARGET"
                    break

                # Check stop loss
                if current_low <= stop_loss:
                    hit_stop = True
                    exit_price = stop_loss
                    exit_reason = "STOP_LOSS"
                    break

            # Calcular resultado final
            profit_loss_pct = ((exit_price - entry_price) / entry_price) * 100
            profit_loss_dollar = (exit_price - entry_price) * 100  # Asumiendo 100 shares

            trade_result = {
                'ticker': ticker,
                'company_name': opportunity.get('company_name', ticker),
                'strategy': strategy,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'target_price': target_price,
                'stop_loss': stop_loss,
                'entry_date': hist.index[entry_date_idx].strftime('%Y-%m-%d'),
                'exit_date': hist.index[min(exit_date_idx, len(hist)-1)].strftime('%Y-%m-%d'),
                'holding_days': min(exit_date_idx - entry_date_idx, holding_period_days),
                'profit_loss_pct': round(profit_loss_pct, 2),
                'profit_loss_dollar': round(profit_loss_dollar, 2),
                'max_profit_pct': round(max_profit, 2),
                'max_loss_pct': round(max_loss, 2),
                'hit_target': hit_target,
                'hit_stop': hit_stop,
                'exit_reason': exit_reason,
                'reversion_score': opportunity['reversion_score'],
                'win': profit_loss_pct > 0
            }

            return trade_result

        except Exception as e:
            print(f"   ⚠️  Error backtesting {ticker}: {e}")
            return None

    def backtest_opportunities(self, opportunities: List[Dict],
                              holding_period_days: int = 30) -> List[Dict]:
        """
        Backtestea lista de oportunidades

        Args:
            opportunities: Lista de oportunidades detectadas
            holding_period_days: Días de retención máxima

        Returns:
            Lista de trades ejecutados
        """
        print(f"📊 Backtesting {len(opportunities)} oportunidades...")
        print(f"   Holding period: {holding_period_days} días")
        print()

        trades = []

        for i, opp in enumerate(opportunities, 1):
            if i % 10 == 0:
                print(f"   Progreso: {i}/{len(opportunities)}")

            ticker = opp['ticker']
            result = self.backtest_opportunity(ticker, opp, holding_period_days)

            if result:
                trades.append(result)
                win_icon = "✅" if result['win'] else "❌"
                print(f"   {win_icon} {ticker}: {result['profit_loss_pct']:+.1f}% ({result['exit_reason']})")

        self.trades = trades
        return trades

    def calculate_metrics(self) -> Dict:
        """Calcula métricas de rendimiento del backtest"""
        if not self.trades:
            return {}

        df = pd.DataFrame(self.trades)

        # Overall metrics
        total_trades = len(df)
        winning_trades = len(df[df['win'] == True])
        losing_trades = len(df[df['win'] == False])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Profit metrics
        avg_win = df[df['win'] == True]['profit_loss_pct'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['win'] == False]['profit_loss_pct'].mean() if losing_trades > 0 else 0
        avg_trade = df['profit_loss_pct'].mean()

        total_profit = df[df['win'] == True]['profit_loss_pct'].sum()
        total_loss = abs(df[df['win'] == False]['profit_loss_pct'].sum())
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

        # Best/Worst trades
        best_trade = df.loc[df['profit_loss_pct'].idxmax()].to_dict() if len(df) > 0 else {}
        worst_trade = df.loc[df['profit_loss_pct'].idxmin()].to_dict() if len(df) > 0 else {}

        # Exit reasons
        target_hits = len(df[df['exit_reason'] == 'TARGET'])
        stop_hits = len(df[df['exit_reason'] == 'STOP_LOSS'])
        holding_exits = len(df[df['exit_reason'] == 'HOLDING_PERIOD'])

        # Strategy breakdown
        strategies = {}
        for strategy in df['strategy'].unique():
            strat_df = df[df['strategy'] == strategy]
            strategies[strategy] = {
                'total_trades': len(strat_df),
                'win_rate': (len(strat_df[strat_df['win'] == True]) / len(strat_df) * 100) if len(strat_df) > 0 else 0,
                'avg_profit': strat_df['profit_loss_pct'].mean(),
                'total_profit': strat_df['profit_loss_pct'].sum()
            }

        # Equity curve
        df_sorted = df.sort_values('entry_date')
        df_sorted['cumulative_return'] = (1 + df_sorted['profit_loss_pct'] / 100).cumprod() - 1
        equity_curve = df_sorted[['entry_date', 'cumulative_return']].to_dict('records')

        # Drawdown
        cumulative_returns = (1 + df_sorted['profit_loss_pct'] / 100).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns / running_max - 1) * 100
        max_drawdown = drawdown.min()

        metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'avg_trade': round(avg_trade, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 999,
            'total_profit_pct': round(total_profit, 2),
            'total_loss_pct': round(total_loss, 2),
            'max_drawdown': round(max_drawdown, 2),
            'target_hits': target_hits,
            'stop_hits': stop_hits,
            'holding_exits': holding_exits,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'strategies': strategies,
            'equity_curve': equity_curve,
            'total_return_pct': round((cumulative_returns.iloc[-1] - 1) * 100, 2) if len(cumulative_returns) > 0 else 0
        }

        return metrics

    def save_results(self, output_dir: str = "docs/backtest"):
        """Guarda resultados del backtest"""
        if not self.trades:
            print("⚠️  No hay trades para guardar")
            return

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save trades CSV
        df_trades = pd.DataFrame(self.trades)
        csv_path = output_path / f"mean_reversion_backtest_trades_{timestamp}.csv"
        df_trades.to_csv(csv_path, index=False)
        print(f"💾 Trades guardados: {csv_path}")

        # Save metrics JSON
        metrics = self.calculate_metrics()
        json_path = output_path / f"mean_reversion_backtest_{timestamp}.json"

        # Convert numpy types to Python native types for JSON serialization
        def convert_to_native(obj):
            if isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_native(item) for item in obj]
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj

        json_safe_data = {
            'backtest_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'initial_capital': self.initial_capital,
            'metrics': convert_to_native(metrics),
            'trades': convert_to_native(self.trades)
        }

        with open(json_path, 'w') as f:
            json.dump(json_safe_data, f, indent=2)

        print(f"📊 Métricas guardadas: {json_path}")

        # Create latest symlink
        latest_json = output_path / "mean_reversion_backtest_latest.json"
        if latest_json.exists():
            latest_json.unlink()

        # Copy instead of symlink for compatibility
        with open(json_path, 'r') as src:
            with open(latest_json, 'w') as dst:
                dst.write(src.read())

        print(f"🔗 Latest backtest: {latest_json}")

    def print_summary(self):
        """Imprime resumen del backtest"""
        if not self.trades:
            print("ℹ️  No hay trades para mostrar")
            return

        metrics = self.calculate_metrics()

        print()
        print("=" * 80)
        print("📊 MEAN REVERSION BACKTEST - RESUMEN")
        print("=" * 80)
        print()

        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  ├─ Wins: {metrics['winning_trades']}")
        print(f"  └─ Losses: {metrics['losing_trades']}")
        print()

        print(f"Performance:")
        print(f"  ├─ Avg Win: +{metrics['avg_win']:.2f}%")
        print(f"  ├─ Avg Loss: {metrics['avg_loss']:.2f}%")
        print(f"  ├─ Avg Trade: {metrics['avg_trade']:+.2f}%")
        print(f"  ├─ Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  ├─ Total Return: {metrics['total_return_pct']:+.2f}%")
        print(f"  └─ Max Drawdown: {metrics['max_drawdown']:.2f}%")
        print()

        print(f"Exit Reasons:")
        print(f"  ├─ Target Hit: {metrics['target_hits']} ({metrics['target_hits']/metrics['total_trades']*100:.1f}%)")
        print(f"  ├─ Stop Loss: {metrics['stop_hits']} ({metrics['stop_hits']/metrics['total_trades']*100:.1f}%)")
        print(f"  └─ Holding Period: {metrics['holding_exits']} ({metrics['holding_exits']/metrics['total_trades']*100:.1f}%)")
        print()

        print("Strategy Comparison:")
        for strategy, stats in metrics['strategies'].items():
            print(f"  {strategy}:")
            print(f"    ├─ Trades: {stats['total_trades']}")
            print(f"    ├─ Win Rate: {stats['win_rate']:.1f}%")
            print(f"    ├─ Avg Profit: {stats['avg_profit']:+.2f}%")
            print(f"    └─ Total: {stats['total_profit']:+.2f}%")
        print()

        if metrics.get('best_trade'):
            best = metrics['best_trade']
            print(f"🏆 Best Trade: {best['ticker']} ({best['strategy']})")
            print(f"   {best['profit_loss_pct']:+.2f}% - {best['exit_reason']}")

        if metrics.get('worst_trade'):
            worst = metrics['worst_trade']
            print(f"💔 Worst Trade: {worst['ticker']} ({worst['strategy']})")
            print(f"   {worst['profit_loss_pct']:+.2f}% - {worst['exit_reason']}")

        print()
        print("=" * 80)


def main():
    """Main execution"""
    print("=" * 80)
    print("📊 MEAN REVERSION BACKTESTER")
    print("   Validación histórica de estrategias de reversión")
    print("=" * 80)
    print()

    # Load opportunities
    csv_path = Path("docs/mean_reversion_opportunities.csv")

    if not csv_path.exists():
        print("❌ No hay oportunidades de Mean Reversion")
        print("   Ejecuta primero: python3 mean_reversion_detector.py")
        return

    df = pd.read_csv(csv_path)
    print(f"📁 Cargadas {len(df)} oportunidades")

    # Filter for quality opportunities (score >= 60)
    df_quality = df[df['reversion_score'] >= 60]
    print(f"🎯 Filtrando {len(df_quality)} oportunidades de alta calidad (score >= 60)")
    print()

    opportunities = df_quality.to_dict('records')

    # Run backtest
    backtester = MeanReversionBacktester(initial_capital=100000)
    trades = backtester.backtest_opportunities(opportunities, holding_period_days=30)

    if trades:
        # Print summary
        backtester.print_summary()

        # Save results
        backtester.save_results()
    else:
        print("❌ No se pudieron ejecutar trades")

    print()
    print("=" * 80)
    print("✅ Backtest completado")
    print("=" * 80)


if __name__ == "__main__":
    main()

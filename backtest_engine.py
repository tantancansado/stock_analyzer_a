#!/usr/bin/env python3
"""
BACKTEST ENGINE - Sistema de backtesting histórico
Simula trades basados en super_score_5d y mide performance
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
from collections import defaultdict


class BacktestEngine:
    """Motor de backtesting para validar estrategia 5D"""

    def __init__(self, initial_capital: float = 100000, position_size: float = 0.10):
        """
        Args:
            initial_capital: Capital inicial en USD
            position_size: Tamaño de posición como % del portfolio (0.10 = 10%)
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.trades = []
        self.equity_curve = []
        self.cache_dir = Path("data/backtest_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_historical_prices(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Obtiene precios históricos con caching

        Args:
            ticker: Stock ticker
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)

        Returns:
            DataFrame con precios OHLCV
        """
        cache_file = self.cache_dir / f"{ticker}_{start_date}_{end_date}.csv"

        # Check cache
        if cache_file.exists():
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)

        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if not df.empty:
                # Asegurar que el índice es Date
                df.index.name = 'Date'
                df.to_csv(cache_file)
                return df
        except Exception as e:
            print(f"   ⚠️  Error descargando {ticker}: {e}")

        return pd.DataFrame()

    def simulate_entry(self, ticker: str, entry_date: str, score: float,
                      tier: str, timing_convergence: bool) -> Dict:
        """
        Simula entrada en ticker según score

        Args:
            ticker: Stock ticker
            entry_date: Fecha de entrada (señal)
            score: Super score 5D
            tier: Tier de oportunidad
            timing_convergence: Si tiene timing convergence

        Returns:
            Dict con resultado del trade
        """
        # Holding period según tier
        hold_days = {
            '⭐⭐⭐⭐': 90,  # LEGENDARY - hold más tiempo
            '⭐⭐⭐': 60,    # ÉPICA
            '⭐⭐': 45,      # EXCELENTE
            '⭐': 30,        # BUENA
            '🔵': 20         # MODERADA
        }

        # Default 30 días si tier no reconocido
        hold_period = 30
        for tier_key in hold_days:
            if tier_key in tier:
                hold_period = hold_days[tier_key]
                break

        # Bonus hold si tiene timing convergence
        if timing_convergence:
            hold_period += 15

        # Obtener precios históricos
        start = datetime.strptime(entry_date, '%Y-%m-%d')
        end = start + timedelta(days=hold_period + 10)  # +10 para margen

        prices = self.get_historical_prices(ticker, start.strftime('%Y-%m-%d'),
                                           end.strftime('%Y-%m-%d'))

        if prices.empty or len(prices) < 2:
            return None

        # Entry price (close del día de señal, o siguiente día disponible)
        entry_idx = 0
        entry_price = float(prices.iloc[entry_idx]['Close'])

        # Exit price (después de hold_period días)
        exit_idx = min(hold_period, len(prices) - 1)
        exit_price = float(prices.iloc[exit_idx]['Close'])

        # Calcular return
        return_pct = ((exit_price - entry_price) / entry_price) * 100

        # Max drawdown durante el holding period
        max_price = float(prices.iloc[:exit_idx+1]['Close'].max())
        min_price = float(prices.iloc[:exit_idx+1]['Close'].min())
        max_drawdown = ((min_price - max_price) / max_price) * 100 if max_price > 0 else 0

        trade = {
            'ticker': ticker,
            'entry_date': entry_date,
            'exit_date': prices.index[exit_idx].strftime('%Y-%m-%d'),
            'entry_price': entry_price,
            'exit_price': exit_price,
            'return_pct': return_pct,
            'hold_days': (prices.index[exit_idx] - prices.index[entry_idx]).days,
            'score': score,
            'tier': tier,
            'timing_convergence': timing_convergence,
            'max_drawdown': max_drawdown,
            'win': return_pct > 0
        }

        return trade

    def run_backtest(self, opportunities_csv: str, lookback_days: int = 180) -> Dict:
        """
        Ejecuta backtest sobre oportunidades históricas

        Args:
            opportunities_csv: Path al CSV con oportunidades
            lookback_days: Días hacia atrás para simular (180 = 6 meses)

        Returns:
            Dict con resultados del backtest
        """
        print("\n🔬 EJECUTANDO BACKTEST")
        print("=" * 70)

        # Cargar oportunidades
        df = pd.read_csv(opportunities_csv)

        # Filtrar solo oportunidades con score >= 55 (BUENA o mejor)
        df = df[df['super_score_5d'] >= 55].copy()

        # Fecha de referencia (today - lookback_days)
        reference_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

        print(f"   📅 Fecha referencia: {reference_date}")
        print(f"   📊 Oportunidades a testear: {len(df)}")

        # Simular trades
        self.trades = []
        capital = self.initial_capital

        for idx, row in df.iterrows():
            ticker = row['ticker']
            score = row['super_score_5d']
            tier = row['tier']
            timing_conv = row.get('timing_convergence', False)

            print(f"   {idx+1}/{len(df)} Simulando {ticker} (Score: {score})...", end='\r')

            trade = self.simulate_entry(ticker, reference_date, score, tier, timing_conv)

            if trade:
                self.trades.append(trade)

        print(f"\n   ✅ {len(self.trades)} trades simulados")

        # Calcular métricas
        results = self.calculate_metrics()

        return results

    def calculate_metrics(self) -> Dict:
        """
        Calcula métricas de performance del backtest

        Returns:
            Dict con métricas detalladas
        """
        if not self.trades:
            return {}

        df = pd.DataFrame(self.trades)

        # Métricas globales
        total_trades = len(df)
        winning_trades = len(df[df['win'] == True])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        avg_return = df['return_pct'].mean()
        median_return = df['return_pct'].median()
        total_return = df['return_pct'].sum()

        # Best/worst trades
        best_trade = df.loc[df['return_pct'].idxmax()]
        worst_trade = df.loc[df['return_pct'].idxmin()]

        # Métricas por tier
        tier_metrics = {}
        for tier in df['tier'].unique():
            tier_df = df[df['tier'] == tier]
            tier_metrics[tier] = {
                'total_trades': len(tier_df),
                'win_rate': (len(tier_df[tier_df['win'] == True]) / len(tier_df)) * 100,
                'avg_return': tier_df['return_pct'].mean(),
                'median_return': tier_df['return_pct'].median(),
                'best_return': tier_df['return_pct'].max(),
                'worst_return': tier_df['return_pct'].min()
            }

        # Timing convergence impact
        timing_trades = df[df['timing_convergence'] == True]
        non_timing_trades = df[df['timing_convergence'] == False]

        timing_impact = {
            'with_timing': {
                'count': len(timing_trades),
                'win_rate': (len(timing_trades[timing_trades['win'] == True]) / len(timing_trades)) * 100 if len(timing_trades) > 0 else 0,
                'avg_return': timing_trades['return_pct'].mean() if len(timing_trades) > 0 else 0
            },
            'without_timing': {
                'count': len(non_timing_trades),
                'win_rate': (len(non_timing_trades[non_timing_trades['win'] == True]) / len(non_timing_trades)) * 100 if len(non_timing_trades) > 0 else 0,
                'avg_return': non_timing_trades['return_pct'].mean() if len(non_timing_trades) > 0 else 0
            }
        }

        results = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'median_return': median_return,
            'total_return': total_return,
            'best_trade': {
                'ticker': best_trade['ticker'],
                'return': best_trade['return_pct'],
                'score': best_trade['score']
            },
            'worst_trade': {
                'ticker': worst_trade['ticker'],
                'return': worst_trade['return_pct'],
                'score': worst_trade['score']
            },
            'tier_metrics': tier_metrics,
            'timing_impact': timing_impact,
            'avg_hold_days': df['hold_days'].mean(),
            'avg_max_drawdown': df['max_drawdown'].mean()
        }

        return results

    def generate_equity_curve(self) -> List[Dict]:
        """
        Genera equity curve del portfolio

        Returns:
            Lista de puntos de equity curve
        """
        if not self.trades:
            return []

        # Ordenar trades por fecha de salida
        df = pd.DataFrame(self.trades)
        df = df.sort_values('exit_date')

        equity = self.initial_capital
        equity_curve = [{'date': df.iloc[0]['entry_date'], 'equity': equity}]

        for _, trade in df.iterrows():
            # Calcular P&L del trade
            position_value = equity * self.position_size
            pnl = position_value * (trade['return_pct'] / 100)
            equity += pnl

            equity_curve.append({
                'date': trade['exit_date'],
                'equity': equity,
                'ticker': trade['ticker'],
                'return': trade['return_pct']
            })

        return equity_curve

    def save_results(self, results: Dict, output_dir: str = "docs/backtest"):
        """
        Guarda resultados del backtest

        Args:
            results: Dict con resultados
            output_dir: Directorio de salida
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Guardar métricas
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        metrics_file = output_path / f"metrics_{timestamp}.json"
        with open(metrics_file, 'w') as f:
            json.dump(results, f, indent=2)

        # Guardar trades
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            trades_file = output_path / f"trades_{timestamp}.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"   💾 Trades guardados: {trades_file}")

        # Guardar equity curve
        equity_curve = self.generate_equity_curve()
        if equity_curve:
            equity_df = pd.DataFrame(equity_curve)
            equity_file = output_path / f"equity_curve_{timestamp}.csv"
            equity_df.to_csv(equity_file, index=False)
            print(f"   💾 Equity curve guardada: {equity_file}")

        print(f"   💾 Métricas guardadas: {metrics_file}")

    def print_summary(self, results: Dict):
        """Imprime resumen de resultados"""
        print("\n📊 RESULTADOS DEL BACKTEST")
        print("=" * 70)

        print(f"\n🎯 MÉTRICAS GLOBALES:")
        print(f"   Total trades: {results['total_trades']}")
        print(f"   Win rate: {results['win_rate']:.1f}%")
        print(f"   Avg return: {results['avg_return']:.2f}%")
        print(f"   Median return: {results['median_return']:.2f}%")
        print(f"   Total return: {results['total_return']:.2f}%")
        print(f"   Avg hold: {results['avg_hold_days']:.0f} días")
        print(f"   Avg max drawdown: {results['avg_max_drawdown']:.2f}%")

        print(f"\n🏆 BEST/WORST TRADES:")
        print(f"   Best: {results['best_trade']['ticker']} "
              f"({results['best_trade']['return']:.1f}% | Score: {results['best_trade']['score']:.0f})")
        print(f"   Worst: {results['worst_trade']['ticker']} "
              f"({results['worst_trade']['return']:.1f}% | Score: {results['worst_trade']['score']:.0f})")

        print(f"\n⭐ PERFORMANCE POR TIER:")
        for tier, metrics in sorted(results['tier_metrics'].items(),
                                    key=lambda x: x[1]['avg_return'], reverse=True):
            print(f"   {tier}:")
            print(f"      Trades: {metrics['total_trades']} | "
                  f"Win rate: {metrics['win_rate']:.1f}% | "
                  f"Avg: {metrics['avg_return']:.2f}%")

        print(f"\n🔥 TIMING CONVERGENCE IMPACT:")
        timing = results['timing_impact']
        print(f"   Con timing:")
        print(f"      Trades: {timing['with_timing']['count']} | "
              f"Win rate: {timing['with_timing']['win_rate']:.1f}% | "
              f"Avg: {timing['with_timing']['avg_return']:.2f}%")
        print(f"   Sin timing:")
        print(f"      Trades: {timing['without_timing']['count']} | "
              f"Win rate: {timing['without_timing']['win_rate']:.1f}% | "
              f"Avg: {timing['without_timing']['avg_return']:.2f}%")


def main():
    """Main execution"""
    engine = BacktestEngine(initial_capital=100000, position_size=0.10)

    # Run backtest on 5D opportunities
    csv_path = "docs/super_opportunities_5d_complete.csv"
    results = engine.run_backtest(csv_path, lookback_days=180)

    # Print summary
    engine.print_summary(results)

    # Save results
    engine.save_results(results)

    print("\n✅ Backtest completado!")


if __name__ == "__main__":
    main()

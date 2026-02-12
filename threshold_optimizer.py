#!/usr/bin/env python3
"""
THRESHOLD OPTIMIZER
Encuentra automáticamente los mejores thresholds para maximizar performance
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from backtest_comprehensive import ComprehensiveBacktest
import json


class ThresholdOptimizer:
    """Optimiza thresholds de scoring para maximizar métricas"""

    def __init__(self):
        self.results = []

    def test_threshold(
        self,
        csv_path: str,
        threshold: int,
        lookback_days: int = 180
    ) -> Dict:
        """
        Testea un threshold específico

        Args:
            csv_path: Path al CSV de oportunidades
            threshold: Threshold mínimo de score a testear
            lookback_days: Período de backtest

        Returns:
            Dict con resultados del threshold
        """
        from backtest_engine import BacktestEngine

        engine = BacktestEngine(initial_capital=100000, position_size=0.10)

        # Load data
        df = pd.read_csv(csv_path)

        # Detect score column
        if 'super_score_ultimate' in df.columns:
            score_col = 'super_score_ultimate'
        elif 'super_score_5d' in df.columns:
            score_col = 'super_score_5d'
        else:
            return {}

        # Filter by threshold
        df_filtered = df[df[score_col] >= threshold].copy()

        num_opportunities = len(df_filtered)

        if num_opportunities == 0:
            return {
                'threshold': threshold,
                'num_opportunities': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0,
            }

        # Run backtest manually
        engine.trades = []
        reference_date = (pd.Timestamp.now() - pd.Timedelta(days=lookback_days)).strftime('%Y-%m-%d')

        for _, row in df_filtered.iterrows():
            ticker = row['ticker']
            score = row[score_col]
            tier = row.get('tier', '⭐⭐ GOOD')
            timing_conv = row.get('timing_convergence', False)

            trade = engine.simulate_entry(ticker, reference_date, score, tier, timing_conv)
            if trade:
                engine.trades.append(trade)

        # Calculate metrics
        if not engine.trades:
            return {
                'threshold': threshold,
                'num_opportunities': num_opportunities,
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0,
            }

        results = engine.calculate_metrics()

        return {
            'threshold': threshold,
            'num_opportunities': num_opportunities,
            'total_trades': results['total_trades'],
            'win_rate': results['win_rate'],
            'avg_return': results['avg_return'],
            'median_return': results['median_return'],
            'sharpe_ratio': results['sharpe_ratio'],
            'profit_factor': results['profit_factor'],
            'expectancy': results['expectancy'],
            'avg_max_drawdown': results['avg_max_drawdown'],
        }

    def optimize(
        self,
        csv_path: str,
        thresholds: List[int] = None,
        lookback_days: int = 180,
        optimization_metric: str = 'sharpe_ratio'
    ) -> pd.DataFrame:
        """
        Optimiza thresholds probando múltiples valores

        Args:
            csv_path: Path al CSV
            thresholds: Lista de thresholds a probar (default: [40, 45, 50, 55, 60, 65, 70])
            lookback_days: Período de backtest
            optimization_metric: Métrica a optimizar (sharpe_ratio, win_rate, profit_factor, expectancy)

        Returns:
            DataFrame con resultados de cada threshold
        """
        if thresholds is None:
            thresholds = [40, 45, 50, 55, 60, 65, 70, 75]

        print("\n🔧 THRESHOLD OPTIMIZER")
        print("=" * 80)
        print(f"Optimizando para: {optimization_metric}")
        print(f"Thresholds a probar: {thresholds}")
        print(f"Lookback: {lookback_days} días")
        print()

        results = []

        for i, threshold in enumerate(thresholds, 1):
            print(f"[{i}/{len(thresholds)}] Testing threshold {threshold}...", end='\r')

            result = self.test_threshold(csv_path, threshold, lookback_days)
            results.append(result)

        print()

        # Convert to DataFrame
        df = pd.DataFrame(results)

        # Sort by optimization metric
        if optimization_metric in df.columns:
            df = df.sort_values(optimization_metric, ascending=False)

        self.results = df

        return df

    def print_results(self, df: pd.DataFrame, optimization_metric: str = 'sharpe_ratio'):
        """Imprime resultados de optimización"""
        print("\n" + "=" * 80)
        print("📊 THRESHOLD OPTIMIZATION RESULTS")
        print("=" * 80)

        print(f"\n{'Threshold':<12} {'Opps':<8} {'Trades':<8} {'Win%':<8} "
              f"{'Avg Ret':<10} {'Sharpe':<8} {'PF':<8} {'Expect':<8}")
        print("-" * 80)

        for _, row in df.iterrows():
            threshold = int(row['threshold'])
            opps = int(row['num_opportunities'])
            trades = int(row['total_trades'])
            win_rate = row['win_rate']
            avg_ret = row['avg_return']
            sharpe = row['sharpe_ratio']
            pf = row['profit_factor']
            expect = row['expectancy']

            pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"

            print(f"{threshold:<12} {opps:<8} {trades:<8} {win_rate:<7.1f}% "
                  f"{avg_ret:<9.2f}% {sharpe:<8.2f} {pf_str:<8} {expect:<8.2f}%")

        # Best threshold
        best_row = df.iloc[0]
        print("\n" + "=" * 80)
        print(f"✅ BEST THRESHOLD: {int(best_row['threshold'])}")
        print("=" * 80)
        print(f"   Optimized for: {optimization_metric} = {best_row[optimization_metric]:.2f}")
        print(f"   Opportunities: {int(best_row['num_opportunities'])}")
        print(f"   Trades: {int(best_row['total_trades'])}")
        print(f"   Win Rate: {best_row['win_rate']:.1f}%")
        print(f"   Avg Return: {best_row['avg_return']:.2f}%")
        print(f"   Sharpe Ratio: {best_row['sharpe_ratio']:.2f}")
        print(f"   Profit Factor: {best_row['profit_factor']:.2f}")
        print(f"   Expectancy: {best_row['expectancy']:.2f}%")

        # Recommendations
        print("\n💡 RECOMENDACIONES:")

        # Sample size check
        if best_row['total_trades'] < 30:
            print(f"   ⚠️  Sample size pequeño ({int(best_row['total_trades'])} trades)")
            print(f"       Recomendado: ≥30 trades para significancia estadística")

        # Win rate check
        if best_row['win_rate'] >= 60:
            print(f"   ✅ Win rate excelente (≥60%)")
        elif best_row['win_rate'] >= 55:
            print(f"   ✅ Win rate aceptable (≥55%)")
        else:
            print(f"   ⚠️  Win rate bajo (<55%)")

        # Sharpe check
        if best_row['sharpe_ratio'] >= 0.5:
            print(f"   ✅ Sharpe ratio saludable (≥0.5)")
        else:
            print(f"   ⚠️  Sharpe ratio bajo (<0.5)")

        # Profit Factor check
        if best_row['profit_factor'] >= 2.0:
            print(f"   ✅ Profit factor excelente (≥2.0)")
        elif best_row['profit_factor'] >= 1.5:
            print(f"   ✅ Profit factor aceptable (≥1.5)")
        else:
            print(f"   ⚠️  Profit factor bajo (<1.5)")

    def save_results(self, df: pd.DataFrame, filename: str = 'threshold_optimization'):
        """Guarda resultados"""
        output_dir = Path("docs/optimization")
        output_dir.mkdir(parents=True, exist_ok=True)

        # CSV
        csv_path = output_dir / f"{filename}.csv"
        df.to_csv(csv_path, index=False)
        print(f"\n💾 Resultados guardados: {csv_path}")

        # JSON
        json_path = output_dir / f"{filename}.json"
        results_dict = df.to_dict('records')

        with open(json_path, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"💾 JSON guardado: {json_path}")


def main():
    """Main execution"""
    import sys

    print("🔧 THRESHOLD OPTIMIZER")
    print("Encontrando threshold óptimo para maximizar performance")
    print()

    # Check for CSV
    ultimate_path = Path("docs/super_scores_ultimate.csv")
    opps_5d_path = Path("docs/super_opportunities_5d_complete.csv")

    if ultimate_path.exists():
        csv_path = str(ultimate_path)
        print(f"📊 Usando: Super Score Ultimate")
    elif opps_5d_path.exists():
        csv_path = str(opps_5d_path)
        print(f"📊 Usando: 5D Opportunities (legacy)")
    else:
        print("❌ No se encontró CSV de oportunidades")
        sys.exit(1)

    # Optimize
    optimizer = ThresholdOptimizer()

    # Test multiple optimization metrics
    metrics = ['sharpe_ratio', 'profit_factor', 'expectancy', 'win_rate']

    all_results = {}

    for metric in metrics:
        print(f"\n{'='*80}")
        print(f"Optimizando para: {metric.upper()}")
        print(f"{'='*80}")

        results_df = optimizer.optimize(
            csv_path=csv_path,
            thresholds=[40, 45, 50, 55, 60, 65, 70, 75, 80],
            lookback_days=180,
            optimization_metric=metric
        )

        optimizer.print_results(results_df, metric)

        all_results[metric] = results_df

        # Save individual results
        optimizer.save_results(results_df, f"threshold_optimization_{metric}")

    # Summary comparison
    print("\n" + "=" * 80)
    print("📊 SUMMARY - BEST THRESHOLDS POR MÉTRICA")
    print("=" * 80)

    for metric, df in all_results.items():
        best = df.iloc[0]
        print(f"\n{metric.upper()}:")
        print(f"   Best threshold: {int(best['threshold'])}")
        print(f"   Value: {best[metric]:.2f}")
        print(f"   Win rate: {best['win_rate']:.1f}% | "
              f"Trades: {int(best['total_trades'])} | "
              f"Avg return: {best['avg_return']:.2f}%")

    print("\n" + "=" * 80)
    print("✅ OPTIMIZATION COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
COMPREHENSIVE BACKTEST - Validación rigurosa multi-período
Prueba el sistema en diferentes períodos de mercado para validar robustez
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from backtest_engine import BacktestEngine
import json


class ComprehensiveBacktest:
    """Backtest comprehensivo multi-período"""

    def __init__(self):
        self.engine = BacktestEngine(initial_capital=100000, position_size=0.10)
        self.results = []

    def run_multi_period_backtest(self):
        """
        Ejecuta backtest en múltiples períodos para validar robustez
        """
        print("\n🔬 COMPREHENSIVE BACKTEST - Validación Multi-Período")
        print("=" * 80)

        # Períodos a testear
        periods = [
            (90, "3 meses"),
            (180, "6 meses"),
            (365, "1 año"),
        ]

        # Cargar datos
        ultimate_path = Path("docs/super_scores_ultimate.csv")
        opps_5d_path = Path("docs/super_opportunities_5d_complete.csv")

        datasets = []
        if ultimate_path.exists():
            datasets.append(("Super Score Ultimate", str(ultimate_path), 65))  # 🎯 Threshold optimizado
        if opps_5d_path.exists():
            datasets.append(("5D Legacy", str(opps_5d_path), 40))

        if not datasets:
            print("❌ No hay datasets disponibles")
            return

        # Testear cada dataset en cada período
        all_results = {}

        for dataset_name, csv_path, min_score in datasets:
            print(f"\n{'='*80}")
            print(f"📊 DATASET: {dataset_name}")
            print(f"{'='*80}")

            dataset_results = {}

            for lookback_days, period_name in periods:
                print(f"\n⏱️  Período: {period_name} (lookback {lookback_days} días)")
                print("-" * 80)

                # Clear trades
                self.engine.trades = []

                # Run backtest con threshold optimizado
                results = self.engine.run_backtest(csv_path, lookback_days=lookback_days, min_score_override=min_score)

                if results and results.get('total_trades', 0) > 0:
                    # Get SPY comparison
                    spy_comparison = self.engine.compare_to_spy(lookback_days)

                    # Store results
                    dataset_results[period_name] = {
                        'backtest': results,
                        'spy': spy_comparison,
                        'lookback_days': lookback_days
                    }

                    # Print quick summary
                    print(f"   ✅ Trades: {results['total_trades']} | "
                          f"Win Rate: {results['win_rate']:.1f}% | "
                          f"Avg Return: {results['avg_return']:.2f}% | "
                          f"Sharpe: {results['sharpe_ratio']:.2f}")

                    if spy_comparison and 'spy_return' in spy_comparison:
                        outperf = results['avg_return'] - spy_comparison['spy_return']
                        print(f"   📊 SPY: {spy_comparison['spy_return']:.2f}% | "
                              f"Outperformance: {outperf:+.2f}%")
                else:
                    print(f"   ⚠️  No se pudieron generar resultados")

            all_results[dataset_name] = dataset_results

        # Print comparative summary
        self.print_comparative_summary(all_results)

        # Save comprehensive results
        self.save_comprehensive_results(all_results)

        return all_results

    def print_comparative_summary(self, all_results: dict):
        """Imprime resumen comparativo de todos los períodos"""
        print("\n" + "=" * 80)
        print("📊 RESUMEN COMPARATIVO - TODOS LOS PERÍODOS")
        print("=" * 80)

        for dataset_name, periods in all_results.items():
            if not periods:
                continue

            print(f"\n🎯 DATASET: {dataset_name}")
            print("-" * 80)

            # Table header
            print(f"{'Período':<15} {'Trades':<8} {'Win%':<8} {'Avg Ret':<10} "
                  f"{'Sharpe':<8} {'PF':<8} {'vs SPY':<10}")
            print("-" * 80)

            for period_name, data in periods.items():
                results = data['backtest']
                spy = data.get('spy', {})

                trades = results['total_trades']
                win_rate = results['win_rate']
                avg_ret = results['avg_return']
                sharpe = results['sharpe_ratio']
                pf = results['profit_factor']

                vs_spy = ""
                if spy and 'spy_return' in spy:
                    outperf = avg_ret - spy['spy_return']
                    vs_spy = f"{outperf:+.2f}%"

                # Truncate PF if infinite
                pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"

                print(f"{period_name:<15} {trades:<8} {win_rate:<7.1f}% "
                      f"{avg_ret:<9.2f}% {sharpe:<8.2f} {pf_str:<8} {vs_spy:<10}")

            # Overall assessment
            print("\n💡 EVALUACIÓN:")
            avg_metrics = self._calculate_average_metrics(periods)

            if avg_metrics['avg_win_rate'] >= 60:
                print("   ✅ Win rate consistentemente bueno (≥60%)")
            else:
                print(f"   ⚠️  Win rate promedio: {avg_metrics['avg_win_rate']:.1f}%")

            if avg_metrics['avg_sharpe'] >= 0.5:
                print("   ✅ Sharpe ratio saludable (≥0.5)")
            else:
                print(f"   ⚠️  Sharpe ratio bajo: {avg_metrics['avg_sharpe']:.2f}")

            if avg_metrics['avg_profit_factor'] >= 2.0:
                print("   ✅ Profit factor excelente (≥2.0)")
            else:
                print(f"   ⚠️  Profit factor: {avg_metrics['avg_profit_factor']:.2f}")

    def _calculate_average_metrics(self, periods: dict) -> dict:
        """Calcula métricas promedio de todos los períodos"""
        if not periods:
            return {}

        total_win_rate = 0
        total_sharpe = 0
        total_pf = 0
        count = 0

        for data in periods.values():
            results = data['backtest']
            total_win_rate += results['win_rate']
            total_sharpe += results['sharpe_ratio']

            pf = results['profit_factor']
            if pf != float('inf'):
                total_pf += pf
            count += 1

        return {
            'avg_win_rate': total_win_rate / count if count > 0 else 0,
            'avg_sharpe': total_sharpe / count if count > 0 else 0,
            'avg_profit_factor': total_pf / count if count > 0 else 0,
        }

    def save_comprehensive_results(self, all_results: dict):
        """Guarda resultados comprehensivos"""
        output_dir = Path("docs/backtest")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Convert to JSON-serializable format
        json_results = {}
        for dataset_name, periods in all_results.items():
            json_results[dataset_name] = {}
            for period_name, data in periods.items():
                json_results[dataset_name][period_name] = {
                    'backtest': self._make_json_serializable(data['backtest']),
                    'spy': data['spy'],
                    'lookback_days': data['lookback_days']
                }

        output_file = output_dir / f"comprehensive_results_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(json_results, f, indent=2)

        print(f"\n💾 Resultados comprehensivos guardados: {output_file}")

    def _make_json_serializable(self, obj):
        """Convierte objetos a JSON-serializable"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, float):
            if obj == float('inf'):
                return "Infinity"
            elif obj == float('-inf'):
                return "-Infinity"
            return obj
        else:
            return obj


def main():
    """Main execution"""
    tester = ComprehensiveBacktest()
    results = tester.run_multi_period_backtest()

    print("\n" + "=" * 80)
    print("✅ COMPREHENSIVE BACKTEST COMPLETADO")
    print("=" * 80)
    print("\n💡 PRÓXIMOS PASOS:")
    print("   1. Analizar resultados en docs/backtest/comprehensive_results_*.json")
    print("   2. Si win rate < 60% → Refinar scoring thresholds")
    print("   3. Si Sharpe < 0.5 → Revisar risk management")
    print("   4. Si Profit Factor < 2.0 → Ajustar entry/exit timing")
    print()


if __name__ == "__main__":
    main()

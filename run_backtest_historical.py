#!/usr/bin/env python3
"""
BACKTEST CON SNAPSHOTS HISTÓRICOS - Sin Look-Ahead Bias

Este script ejecuta el backtest V2 usando los snapshots históricos generados
con --as-of-date, eliminando completamente el look-ahead bias.
"""
import json
from pathlib import Path
from datetime import datetime
from backtest_engine_v2 import BacktestEngineV2


def run_historical_backtest():
    """Ejecuta backtest con snapshots históricos"""

    print("\n" + "="*80)
    print("🔬 BACKTEST V2 CON SNAPSHOTS HISTÓRICOS (SIN LOOK-AHEAD BIAS)")
    print("="*80)

    engine = BacktestEngineV2()

    # Mapeo de snapshots a lookback days
    snapshots = {
        "2025-11-13": {"lookback_days": 90, "period": "3 MESES"},
        "2025-08-15": {"lookback_days": 180, "period": "6 MESES"},
        "2025-02-11": {"lookback_days": 365, "period": "1 AÑO"}
    }

    results_all = {}

    for snapshot_date, config in snapshots.items():
        snapshot_path = f"docs/historical_scores/{snapshot_date}_scores.csv"

        if not Path(snapshot_path).exists():
            print(f"\n⚠️  Snapshot no encontrado: {snapshot_path}")
            continue

        print(f"\n{'='*80}")
        print(f"📅 TESTING: {config['period']} (Snapshot: {snapshot_date})")
        print(f"   Snapshot: {snapshot_path}")
        print(f"   Lookback: {config['lookback_days']} días")
        print("="*80)

        # Ejecutar backtest con min_score_override=60 (balanceado)
        results = engine.run_backtest_v2(
            snapshot_path,
            lookback_days=config['lookback_days'],
            min_score_override=60
        )

        if results:
            results_all[config['period']] = results

            print(f"\n📊 RESULTADOS {config['period']}:")
            print(f"   Win Rate: {results.get('win_rate', 0):.1f}%")
            print(f"   Total Trades: {results.get('total_trades', 0)}")
            print(f"   Avg Return: {results.get('avg_return', 0):.1f}%")
            print(f"   Total Return: {results.get('total_return', 0):.1f}%")

    # Guardar resultados completos
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"docs/backtest/historical_backtest_results_{timestamp}.json"

    Path("docs/backtest").mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results_all, f, indent=2, default=str)

    print(f"\n{'='*80}")
    print(f"✅ BACKTEST HISTÓRICO COMPLETADO")
    print(f"📁 Resultados guardados: {output_file}")
    print("="*80)

    # Comparación con resultados V1 (con bias)
    print("\n📊 COMPARACIÓN V1 (CON BIAS) vs V2 (SIN BIAS):")
    print("="*80)
    print("\nV1 (Con Look-Ahead Bias) - Resultados Originales:")
    print("   3M: 90.9% WR | 11 trades | Avg: +9.4%")
    print("   6M: 56.4% WR | 39 trades | Avg: +0.8%")
    print("   1Y: 14.5% WR | 69 trades | Avg: -4.1%")

    print("\nV2 (Sin Look-Ahead Bias) - Snapshots Históricos:")
    for period, results in results_all.items():
        wr = results.get('win_rate', 0)
        trades = results.get('total_trades', 0)
        avg_ret = results.get('avg_return', 0)
        print(f"   {period}: {wr:.1f}% WR | {trades} trades | Avg: {avg_ret:+.1f}%")

    print("\n" + "="*80)

    return results_all


if __name__ == "__main__":
    run_historical_backtest()

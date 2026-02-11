#!/usr/bin/env python3
"""
BACKTEST DIAGNOSTICS - Diagnóstico profundo del sistema
Detecta look-ahead bias, analiza trades fallidos, compara distribuciones
"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from collections import Counter
import numpy as np


class BacktestDiagnostics:
    """Diagnóstico profundo del backtest"""

    def __init__(self):
        self.results_dir = Path("docs/backtest")
        self.diagnostics = {}

    def load_backtest_results(self):
        """Carga los resultados del backtest comprehensivo más reciente"""
        # Buscar archivo más reciente
        results_files = sorted(self.results_dir.glob("comprehensive_results_*.json"))

        if not results_files:
            print("❌ No se encontraron resultados de backtest")
            return None

        latest_file = results_files[-1]
        print(f"📂 Cargando: {latest_file}")

        with open(latest_file, 'r') as f:
            return json.load(f)

    def load_trades_detail(self):
        """Carga detalles de trades individuales si existen"""
        trades_files = sorted(self.results_dir.glob("trades_*.csv"))

        if trades_files:
            latest_trades = trades_files[-1]
            return pd.read_csv(latest_trades)
        return None

    def diagnose_lookahead_bias(self):
        """
        Diagnóstico 1: Detectar Look-Ahead Bias

        ¿Estamos usando scores de HOY para simular trades de AYER?
        """
        print("\n" + "=" * 80)
        print("🔬 DIAGNÓSTICO 1: LOOK-AHEAD BIAS")
        print("=" * 80)

        # Cargar el CSV de scores actual
        scores_path = Path("docs/super_scores_ultimate.csv")

        if not scores_path.exists():
            print("❌ No se encontró super_scores_ultimate.csv")
            return

        df = pd.read_csv(scores_path)

        print(f"\n📊 Dataset: {len(df)} stocks con scores")
        print(f"   Columnas: {list(df.columns)}")

        # Análisis de timestamps
        if 'last_updated' in df.columns or 'timestamp' in df.columns:
            timestamp_col = 'last_updated' if 'last_updated' in df.columns else 'timestamp'
            print(f"\n✅ Encontrado timestamp: {timestamp_col}")

            # Verificar cuándo se generaron los scores
            if df[timestamp_col].notna().any():
                dates = pd.to_datetime(df[timestamp_col], errors='coerce')
                print(f"   📅 Scores generados el: {dates.max()}")
                print(f"   📅 Fecha más antigua: {dates.min()}")
        else:
            print("\n⚠️  NO hay columna de timestamp en los scores")
            print("   🚨 PROBLEMA: No podemos verificar cuándo se generaron los scores")
            print("   🚨 Esto sugiere LOOK-AHEAD BIAS")

        # Verificar si hay columnas de datos históricos
        historical_cols = [col for col in df.columns if 'historical' in col.lower() or '_date' in col.lower()]

        if historical_cols:
            print(f"\n✅ Columnas históricas encontradas: {historical_cols}")
        else:
            print("\n⚠️  NO hay columnas históricas explícitas")
            print("   💡 Los scores parecen ser calculados con datos actuales")

        # Análisis del VCP score
        if 'vcp_score' in df.columns:
            print(f"\n📈 VCP Score:")
            print(f"   Media: {df['vcp_score'].mean():.2f}")
            print(f"   Max: {df['vcp_score'].max():.2f}")
            print(f"   Min: {df['vcp_score'].min():.2f}")

            # VCP score alto sugiere patrones actuales, no históricos
            high_vcp = df[df['vcp_score'] > 30]
            print(f"   ⚠️  {len(high_vcp)} stocks con VCP score > 30 (probablemente usando precios actuales)")

        # VEREDICTO
        print("\n" + "=" * 80)
        print("⚖️  VEREDICTO LOOK-AHEAD BIAS:")

        has_timestamps = 'last_updated' in df.columns or 'timestamp' in df.columns
        has_historical = len(historical_cols) > 0

        if not has_timestamps:
            print("🔴 ALTO RIESGO de look-ahead bias:")
            print("   - No hay timestamps de cuando se generaron los scores")
            print("   - Probablemente usando datos actuales para simular trades pasados")
            print("   - Backtest results INFLADOS y NO confiables")
            bias_level = "HIGH"
        elif has_historical:
            print("🟢 BAJO RIESGO de look-ahead bias:")
            print("   - Hay timestamps y columnas históricas")
            print("   - Scoring parece usar datos históricos")
            bias_level = "LOW"
        else:
            print("🟡 RIESGO MEDIO de look-ahead bias:")
            print("   - Hay timestamps pero no columnas históricas explícitas")
            print("   - Necesita validación manual del código de scoring")
            bias_level = "MEDIUM"

        self.diagnostics['lookahead_bias'] = {
            'level': bias_level,
            'has_timestamps': has_timestamps,
            'has_historical_cols': has_historical,
            'recommendation': 'INVALIDATE BACKTEST' if bias_level == 'HIGH' else 'VALIDATE MANUALLY'
        }

        return bias_level

    def analyze_failed_trades_1y(self):
        """
        Diagnóstico 2: Analizar Trades Fallidos del Período 1Y

        ¿Qué tienen en común las 47 pérdidas?
        """
        print("\n" + "=" * 80)
        print("📉 DIAGNÓSTICO 2: ANÁLISIS DE TRADES FALLIDOS (1Y)")
        print("=" * 80)

        # Cargar resultados del backtest
        results = self.load_backtest_results()

        if not results:
            return

        # Extraer trades del período 1Y
        if 'Super Score Ultimate' not in results:
            print("❌ No se encontraron resultados de Super Score Ultimate")
            return

        ultimate_results = results['Super Score Ultimate']

        if '1 año' not in ultimate_results:
            print("❌ No se encontraron resultados del período 1 año")
            return

        period_1y = ultimate_results['1 año']
        backtest_data = period_1y['backtest']

        print(f"\n📊 Período 1 Año:")
        print(f"   Total Trades: {backtest_data['total_trades']}")
        print(f"   Ganadores: {backtest_data['winning_trades']}")
        print(f"   Perdedores: {backtest_data['losing_trades']}")
        print(f"   Win Rate: {backtest_data['win_rate']:.1f}%")
        print(f"   Avg Return: {backtest_data['avg_return']:.2f}%")

        # Cargar CSV de scores para analizar
        scores_df = pd.read_csv("docs/super_scores_ultimate.csv")

        # Top tickers (asumiendo que son los que se testearon)
        top_tickers = scores_df.nlargest(55, 'super_score_ultimate')['ticker'].tolist()

        print(f"\n🔍 Analizando {len(top_tickers)} tickers testeados...")

        # Análisis sectorial
        if 'sector' in scores_df.columns:
            tested_stocks = scores_df[scores_df['ticker'].isin(top_tickers)]
            sector_dist = tested_stocks['sector'].value_counts()

            print("\n📊 Distribución Sectorial:")
            for sector, count in sector_dist.head(10).items():
                print(f"   {sector}: {count} stocks")

            # Calcular performance esperada por sector
            print("\n💡 HIPÓTESIS: ¿Algún sector falla más?")
            print("   (Necesitaríamos trades individuales para confirmar)")

        # Análisis de scores
        if 'super_score_ultimate' in scores_df.columns:
            tested_stocks = scores_df[scores_df['ticker'].isin(top_tickers)]

            print(f"\n📈 Distribución de Scores (Testeados):")
            print(f"   Media: {tested_stocks['super_score_ultimate'].mean():.2f}")
            print(f"   Mediana: {tested_stocks['super_score_ultimate'].median():.2f}")
            print(f"   Rango: {tested_stocks['super_score_ultimate'].min():.2f} - {tested_stocks['super_score_ultimate'].max():.2f}")

            # Scores por rango
            score_ranges = [
                (75, 100, "LEGENDARY"),
                (70, 75, "EXCELLENT"),
                (65, 70, "GOOD"),
            ]

            print(f"\n   Distribución por Rango:")
            for min_s, max_s, label in score_ranges:
                count = len(tested_stocks[(tested_stocks['super_score_ultimate'] >= min_s) &
                                         (tested_stocks['super_score_ultimate'] < max_s)])
                print(f"   {label} ({min_s}-{max_s}): {count} stocks")

        # HIPÓTESIS sobre fallos
        print("\n" + "=" * 80)
        print("💡 HIPÓTESIS SOBRE FALLOS:")
        print("=" * 80)

        print("\n1. 🔴 MARKET REGIME CHANGE (1 año atrás)")
        print("   - Hace 1 año (Feb 2025): ¿Mercado diferente?")
        print("   - Posibles factores: tasas interés, inflación, sector rotation")

        print("\n2. 🔴 HOLD PERIODS DEMASIADO LARGOS")
        print("   - Hold 30-90 días en mercado de hace 1 año")
        print("   - Puede capturar drawdowns completos")

        print("\n3. 🔴 SCORING OPTIMIZADO PARA HOY")
        print("   - VCP patterns actuales ≠ VCP patterns de hace 1 año")
        print("   - ML model entrenado en datos recientes")
        print("   - Fundamentales 'fuertes' hoy ≠ predictivos hace 1 año")

        self.diagnostics['failed_trades_1y'] = {
            'total_trades': backtest_data['total_trades'],
            'losing_trades': backtest_data['losing_trades'],
            'win_rate': backtest_data['win_rate'],
            'avg_return': backtest_data['avg_return'],
            'top_hypothesis': 'MARKET_REGIME_CHANGE'
        }

    def compare_score_distributions(self):
        """
        Diagnóstico 3: Comparar Distribución de Scores

        ¿Los scores "altos" significan lo mismo en 3M vs 6M vs 1Y?
        """
        print("\n" + "=" * 80)
        print("📊 DIAGNÓSTICO 3: COMPARACIÓN DE DISTRIBUCIONES")
        print("=" * 80)

        results = self.load_backtest_results()

        if not results:
            return

        # Analizar cada período
        periods_data = {}

        for dataset_name, periods in results.items():
            if dataset_name != "Super Score Ultimate":
                continue

            print(f"\n🎯 Dataset: {dataset_name}")
            print("-" * 80)

            for period_name, data in periods.items():
                backtest = data['backtest']

                print(f"\n📅 Período: {period_name}")
                print(f"   Trades: {backtest['total_trades']}")
                print(f"   Win Rate: {backtest['win_rate']:.1f}%")
                print(f"   Avg Return: {backtest['avg_return']:.2f}%")
                print(f"   Sharpe: {backtest['sharpe_ratio']:.2f}")

                periods_data[period_name] = {
                    'win_rate': backtest['win_rate'],
                    'avg_return': backtest['avg_return'],
                    'sharpe': backtest['sharpe_ratio']
                }

        # Análisis de tendencias
        print("\n" + "=" * 80)
        print("📈 ANÁLISIS DE TENDENCIAS:")
        print("=" * 80)

        if len(periods_data) >= 3:
            periods_list = ['3 meses', '6 meses', '1 año']

            print("\n🔻 Degradación de Métricas:")

            for metric in ['win_rate', 'avg_return', 'sharpe']:
                print(f"\n   {metric.upper()}:")

                for i, period in enumerate(periods_list):
                    if period in periods_data:
                        value = periods_data[period][metric]

                        # Calcular cambio vs período anterior
                        if i > 0:
                            prev_period = periods_list[i-1]
                            if prev_period in periods_data:
                                prev_value = periods_data[prev_period][metric]
                                change = value - prev_value
                                pct_change = (change / abs(prev_value) * 100) if prev_value != 0 else 0

                                print(f"   {period}: {value:.2f} (Δ {change:+.2f}, {pct_change:+.1f}%)")
                        else:
                            print(f"   {period}: {value:.2f}")

        # CONCLUSIÓN
        print("\n" + "=" * 80)
        print("💡 CONCLUSIÓN:")
        print("=" * 80)

        # Calcular degradación promedio
        if '3 meses' in periods_data and '1 año' in periods_data:
            wr_3m = periods_data['3 meses']['win_rate']
            wr_1y = periods_data['1 año']['win_rate']
            degradation = wr_3m - wr_1y

            print(f"\n🔴 Degradación Total (3M → 1Y):")
            print(f"   Win Rate: -{degradation:.1f} puntos ({wr_3m:.1f}% → {wr_1y:.1f}%)")

            if degradation > 50:
                print(f"\n   ⚠️  DEGRADACIÓN SEVERA (>{50}pts)")
                print(f"   🚨 Sistema NO es robusto temporalmente")
                print(f"   🚨 Scoring está overfitted a condiciones recientes")
            elif degradation > 30:
                print(f"\n   ⚠️  Degradación significativa (30-50pts)")
                print(f"   💡 Necesita ajustes de robustez")
            else:
                print(f"\n   ✅ Degradación aceptable (<30pts)")

        self.diagnostics['score_distribution'] = {
            'periods': periods_data,
            'degradation': degradation if 'degradation' in locals() else None
        }

    def generate_diagnostic_report(self):
        """Genera reporte final de diagnóstico"""
        print("\n" + "=" * 80)
        print("📋 REPORTE DE DIAGNÓSTICO")
        print("=" * 80)

        # Guardar diagnóstico
        output_dir = Path("docs/diagnostics")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"backtest_diagnostics_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump(self.diagnostics, f, indent=2)

        print(f"\n💾 Diagnóstico guardado: {output_file}")

        # Resumen ejecutivo
        print("\n" + "=" * 80)
        print("🎯 RESUMEN EJECUTIVO:")
        print("=" * 80)

        if 'lookahead_bias' in self.diagnostics:
            bias_level = self.diagnostics['lookahead_bias']['level']

            if bias_level == "HIGH":
                print("\n🔴 LOOK-AHEAD BIAS: ALTO RIESGO")
                print("   ⚠️  Backtest results probablemente INFLADOS")
                print("   ⚠️  NO confiar en métricas reportadas")
                print("   🔧 ACCIÓN: Re-implementar scoring con datos históricos")
            elif bias_level == "MEDIUM":
                print("\n🟡 LOOK-AHEAD BIAS: RIESGO MEDIO")
                print("   💡 Validar manualmente código de scoring")
                print("   💡 Verificar que usa solo datos históricos")
            else:
                print("\n🟢 LOOK-AHEAD BIAS: BAJO RIESGO")
                print("   ✅ Scoring parece usar datos históricos")

        if 'failed_trades_1y' in self.diagnostics:
            wr_1y = self.diagnostics['failed_trades_1y']['win_rate']

            print(f"\n📉 TRADES FALLIDOS (1Y):")
            print(f"   Win Rate: {wr_1y:.1f}% (Target: ≥55%)")

            if wr_1y < 20:
                print(f"   🔴 Performance CATASTRÓFICA")
                print(f"   💡 Hipótesis: Market regime change + hold periods largos")

        if 'score_distribution' in self.diagnostics:
            degradation = self.diagnostics['score_distribution'].get('degradation')

            if degradation:
                print(f"\n📊 DEGRADACIÓN TEMPORAL:")
                print(f"   3M → 1Y: -{degradation:.1f} puntos de win rate")

                if degradation > 50:
                    print(f"   🔴 SEVERA: Sistema overfitted a corto plazo")

        # RECOMENDACIONES FINALES
        print("\n" + "=" * 80)
        print("🎯 RECOMENDACIONES FINALES:")
        print("=" * 80)

        print("\n1. 🚨 PRIORIDAD ALTA:")

        if self.diagnostics.get('lookahead_bias', {}).get('level') == 'HIGH':
            print("   - Fix look-ahead bias INMEDIATAMENTE")
            print("   - Re-implementar scoring con datos históricos punto-en-tiempo")
            print("   - Invalidar resultados actuales del backtest")
        else:
            print("   - Reducir hold periods a 10-30 días máximo")
            print("   - Implementar stops agresivos (-8% a -10%)")
            print("   - Agregar market regime filter")

        print("\n2. 🔧 FIXES TÉCNICOS:")
        print("   - Walk-forward validation del ML model")
        print("   - Regime detection (bull/bear/choppy)")
        print("   - Scoring dinámico basado en régimen")

        print("\n3. ⏱️ TIMELINE:")
        print("   - Diagnóstico completado: ✅")
        print("   - Fix look-ahead bias: 1 semana")
        print("   - Implementar stops/regime: 2-3 semanas")
        print("   - Re-validación: 1 semana")
        print("   - Total: ~1 mes para sistema confiable")

        print("\n" + "=" * 80)


def main():
    """Main execution"""
    print("🔬 BACKTEST DIAGNOSTICS - Diagnóstico Profundo")
    print("=" * 80)

    diagnostics = BacktestDiagnostics()

    # Ejecutar diagnósticos
    diagnostics.diagnose_lookahead_bias()
    diagnostics.analyze_failed_trades_1y()
    diagnostics.compare_score_distributions()
    diagnostics.generate_diagnostic_report()

    print("\n✅ DIAGNÓSTICO COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    main()

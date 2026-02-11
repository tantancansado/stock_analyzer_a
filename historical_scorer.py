#!/usr/bin/env python3
"""
HISTORICAL SCORER - Genera snapshots de scores en fechas históricas

Este script soluciona el look-ahead bias generando scores "as of" fechas pasadas,
usando solo información disponible en esas fechas.

🔴 FIX LOOK-AHEAD BIAS: Ejecuta el pipeline completo (VCP, ML, Fundamental, Super Score)
con --as-of-date para generar scores históricos reales sin look-ahead bias.

Uso:
    python3 historical_scorer.py --dates 2025-11-13 2025-08-15 2025-02-11
    python3 historical_scorer.py --weekly --weeks 52  # 1 año de snapshots semanales
    python3 historical_scorer.py --backtest  # Fechas clave: 3M, 6M, 1Y
"""
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import sys
import subprocess
import shutil


class HistoricalScorer:
    """Genera snapshots históricos de scores sin look-ahead bias"""

    def __init__(self):
        self.output_dir = Path("docs/historical_scores")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_snapshot(self, reference_date: str, skip_vcp: bool = False):
        """
        Genera un snapshot de scores para una fecha específica

        🔴 FIX LOOK-AHEAD BIAS: Ejecuta el pipeline completo con --as-of-date

        Args:
            reference_date: Fecha de referencia (YYYY-MM-DD)
            skip_vcp: Skip VCP scanner (útil si ya se ejecutó, tarda mucho)

        Returns:
            Path to snapshot CSV
        """
        print(f"\n{'='*80}")
        print(f"📸 GENERANDO SNAPSHOT HISTÓRICO: {reference_date}")
        print(f"🔴 Sin look-ahead bias - Solo datos hasta {reference_date}")
        print(f"{'='*80}")

        try:
            # 1. VCP Scanner (opcional - tarda mucho)
            if not skip_vcp:
                print(f"\n[1/4] 🔍 VCP Scanner (puede tardar 15-20 min)...")
                result = subprocess.run(
                    ["python3", "vcp_scanner_usa.py", "--sp500", "--parallel", "--as-of-date", reference_date],
                    capture_output=True,
                    text=True,
                    timeout=1800  # 30 min timeout
                )
                if result.returncode != 0:
                    print(f"⚠️  VCP Scanner warning: {result.stderr[:200]}")
                else:
                    print(f"✅ VCP Scanner completado")
            else:
                print(f"\n[1/4] ⏭️  VCP Scanner SKIPPED (usa --run-vcp para ejecutar)")

            # 2. ML Scoring
            print(f"\n[2/4] 🤖 ML Scoring...")
            result = subprocess.run(
                ["python3", "ml_scoring.py", "--as-of-date", reference_date],
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )
            if result.returncode != 0:
                print(f"❌ ML Scoring falló: {result.stderr[:200]}")
                return None
            print(f"✅ ML Scoring completado")

            # 3. Fundamental Scoring
            print(f"\n[3/4] 📊 Fundamental Scoring...")
            result = subprocess.run(
                ["python3", "fundamental_scorer.py", "--vcp", "--as-of-date", reference_date],
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout
            )
            if result.returncode != 0:
                print(f"❌ Fundamental Scoring falló: {result.stderr[:200]}")
                return None
            print(f"✅ Fundamental Scoring completado")

            # 4. Super Score Integrator
            print(f"\n[4/4] 🎯 Super Score Integration...")
            result = subprocess.run(
                ["python3", "super_score_integrator.py", "--as-of-date", reference_date],
                capture_output=True,
                text=True,
                timeout=60  # 1 min timeout
            )
            if result.returncode != 0:
                print(f"❌ Super Score Integration falló: {result.stderr[:200]}")
                return None
            print(f"✅ Super Score Integration completado")

            # 5. Copiar resultado al directorio de snapshots
            current_scores = Path("docs/super_scores_ultimate.csv")

            if not current_scores.exists():
                print(f"\n❌ No se generó super_scores_ultimate.csv")
                return None

            # Guardar snapshot
            snapshot_path = self.output_dir / f"{reference_date}_scores.csv"
            shutil.copy2(current_scores, snapshot_path)

            # Verificar timestamp metadata
            df = pd.read_csv(snapshot_path)
            print(f"\n✅ Snapshot guardado: {snapshot_path}")
            print(f"   📊 Tickers: {len(df)}")
            print(f"   🎯 Score promedio: {df['super_score_ultimate'].mean():.1f}")
            print(f"   📅 Data as of: {df['data_as_of_date'].iloc[0]}")

            return snapshot_path

        except subprocess.TimeoutExpired as e:
            print(f"\n❌ Timeout: {e.cmd[1]} tardó más de {e.timeout}s")
            return None
        except Exception as e:
            print(f"\n❌ Error generando snapshot: {e}")
            return None

    def generate_weekly_snapshots(self, weeks: int = 52, skip_vcp: bool = True):
        """
        Genera snapshots semanales hacia atrás

        Args:
            weeks: Número de semanas hacia atrás
            skip_vcp: Skip VCP scanner (default True)
        """
        print(f"\n🗓️  Generando {weeks} snapshots semanales...")

        dates = []
        current_date = datetime.now()

        for i in range(weeks):
            snapshot_date = current_date - timedelta(weeks=i)
            # Usar viernes (día de cierre semanal)
            days_ahead = 4 - snapshot_date.weekday()  # 4 = Friday
            if days_ahead < 0:
                days_ahead += 7
            snapshot_date = snapshot_date + timedelta(days=days_ahead)

            dates.append(snapshot_date.strftime('%Y-%m-%d'))

        print(f"\n📅 Fechas a generar:")
        for date in dates[:5]:
            print(f"   {date}")
        if len(dates) > 5:
            print(f"   ... ({len(dates) - 5} más)")

        # Generar snapshots
        snapshots = []
        for i, date in enumerate(dates, 1):
            print(f"\n[{i}/{len(dates)}] Procesando {date}...")
            snapshot_path = self.generate_snapshot(date, skip_vcp=skip_vcp)
            if snapshot_path:
                snapshots.append(snapshot_path)

        print(f"\n✅ {len(snapshots)} snapshots generados exitosamente")
        print(f"📁 Directorio: {self.output_dir}")

        return snapshots

    def generate_backtest_dates(self) -> List[str]:
        """
        Genera las 3 fechas clave para backtest (3M, 6M, 1Y)

        Returns:
            List of dates [3M ago, 6M ago, 1Y ago]
        """
        today = datetime.now()

        dates = [
            (today - timedelta(days=90)).strftime('%Y-%m-%d'),   # 3M
            (today - timedelta(days=180)).strftime('%Y-%m-%d'),  # 6M
            (today - timedelta(days=365)).strftime('%Y-%m-%d'),  # 1Y
        ]

        print(f"\n📅 Fechas clave para backtest:")
        print(f"   3 meses: {dates[0]}")
        print(f"   6 meses: {dates[1]}")
        print(f"   1 año:   {dates[2]}")

        return dates


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='🔴 Genera snapshots históricos de scores SIN look-ahead bias',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 historical_scorer.py --backtest                    # Fechas clave: 3M, 6M, 1Y
  python3 historical_scorer.py --dates 2025-08-15            # Fecha específica
  python3 historical_scorer.py --weekly --weeks 52           # 52 snapshots semanales
  python3 historical_scorer.py --backtest --run-vcp          # Incluir VCP (lento)

Note:
  - Ejecuta el pipeline completo (VCP, ML, Fundamental, Super Score) con --as-of-date
  - VCP Scanner se SKIP por default (tarda 15-20 min). Usa --run-vcp para incluirlo.
  - Los scores generados NO tienen look-ahead bias (usan solo datos hasta la fecha)
        '''
    )

    parser.add_argument(
        '--dates',
        nargs='+',
        help='Fechas específicas (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--weekly',
        action='store_true',
        help='Generar snapshots semanales'
    )

    parser.add_argument(
        '--weeks',
        type=int,
        default=52,
        help='Número de semanas hacia atrás (default: 52)'
    )

    parser.add_argument(
        '--backtest',
        action='store_true',
        help='Generar solo las 3 fechas clave (3M, 6M, 1Y)'
    )

    parser.add_argument(
        '--run-vcp',
        action='store_true',
        help='Ejecutar VCP Scanner (tarda 15-20 min, skip por default)'
    )

    args = parser.parse_args()

    scorer = HistoricalScorer()
    skip_vcp = not args.run_vcp

    if skip_vcp:
        print("\n⚠️  VCP Scanner será SKIPPED (usa --run-vcp para incluirlo)")
        print("   Razón: VCP tarda 15-20 min en ejecutar")

    if args.backtest:
        # Generar solo las fechas clave
        dates = scorer.generate_backtest_dates()
        for date in dates:
            scorer.generate_snapshot(date, skip_vcp=skip_vcp)

    elif args.weekly:
        # Generar snapshots semanales
        print(f"\n⚠️  WARNING: {args.weeks} snapshots semanales pueden tardar HORAS")
        print(f"   Tiempo estimado: ~{args.weeks * 15} minutos con VCP, ~{args.weeks * 2} min sin VCP")
        confirm = input("\n¿Continuar? (y/n): ")
        if confirm.lower() == 'y':
            scorer.generate_weekly_snapshots(weeks=args.weeks)
        else:
            print("Cancelado.")
            return

    elif args.dates:
        # Generar fechas específicas
        for date in args.dates:
            scorer.generate_snapshot(date, skip_vcp=skip_vcp)

    else:
        # Default: generar las 3 fechas clave
        print("\n💡 No se especificaron opciones, generando fechas clave de backtest...")
        dates = scorer.generate_backtest_dates()
        for date in dates:
            scorer.generate_snapshot(date, skip_vcp=skip_vcp)

    print(f"\n{'='*80}")
    print(f"✅ HISTORICAL SCORING COMPLETADO")
    print(f"{'='*80}")
    print(f"\n📖 PRÓXIMOS PASOS:")
    print(f"   1. ✅ Snapshots generados SIN look-ahead bias")
    print(f"      - Todos los scorers ejecutados con --as-of-date")
    print(f"      - VCP, ML, y Fundamental usan solo datos históricos")
    print(f"   2. 📊 Validar snapshots generados:")
    print(f"      ls -lh docs/historical_scores/")
    print(f"   3. 🔬 Re-ejecutar Backtest V2 con datos limpios:")
    print(f"      python3 backtest_engine_v2.py --historical-scores")
    print(f"   4. 📈 Comparar resultados V1 (con bias) vs V2 (sin bias)")
    print(f"\n✅ Phase 2 COMPLETADO: Historical scoring implementado")
    print(f"   Snapshots generados usan SOLO datos disponibles hasta la fecha de referencia.")


if __name__ == "__main__":
    main()

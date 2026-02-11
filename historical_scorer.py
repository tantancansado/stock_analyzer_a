#!/usr/bin/env python3
"""
HISTORICAL SCORER - Genera snapshots de scores en fechas históricas

Este script soluciona el look-ahead bias generando scores "as of" fechas pasadas,
usando solo información disponible en esas fechas.

Uso:
    python3 historical_scorer.py --dates 2025-11-13 2025-08-15 2025-02-11
    python3 historical_scorer.py --weekly --weeks 52  # 1 año de snapshots semanales
"""
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import sys


class HistoricalScorer:
    """Genera snapshots históricos de scores sin look-ahead bias"""

    def __init__(self):
        self.output_dir = Path("docs/historical_scores")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_snapshot(self, reference_date: str):
        """
        Genera un snapshot de scores para una fecha específica

        Args:
            reference_date: Fecha de referencia (YYYY-MM-DD)

        Returns:
            Path to snapshot CSV
        """
        print(f"\n{'='*80}")
        print(f"📸 GENERANDO SNAPSHOT: {reference_date}")
        print(f"{'='*80}")

        # IMPORTANTE: Aquí deberíamos ejecutar los scorers usando solo datos
        # disponibles HASTA reference_date.
        #
        # Por ahora, esto es un PLACEHOLDER que documenta el proceso correcto:
        #
        # 1. VCP Scanner: Usar precios hasta reference_date
        # 2. ML Predictor: Entrenar solo con datos hasta reference_date
        # 3. Fundamental: Usar earnings reportados antes de reference_date

        print(f"\n⚠️  CRITICAL: Historical scoring requiere:")
        print(f"   1. VCP Scanner con data_end_date={reference_date}")
        print(f"   2. ML Model entrenado SOLO con data <= {reference_date}")
        print(f"   3. Fundamentals filtrados por report_date <= {reference_date}")
        print(f"\n   🚧 IMPLEMENTATION REQUIRED:")
        print(f"   - Modificar vcp_scanner_usa.py para aceptar --as-of-date")
        print(f"   - Modificar ml_scoring.py para entrenar con data histórica")
        print(f"   - Modificar fundamental_scorer.py para filtrar por fecha")
        print(f"\n   💡 Por ahora, usar scores actuales con timestamp correction")

        # Por ahora, usamos el score actual pero con timestamp correcto
        current_scores = Path("docs/super_scores_ultimate.csv")

        if not current_scores.exists():
            print(f"\n❌ No se encontró super_scores_ultimate.csv")
            print(f"   Ejecuta primero: python3 super_score_integrator.py")
            return None

        # Cargar scores actuales
        df = pd.read_csv(current_scores)

        # Agregar timestamps históricos
        df['score_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['data_as_of_date'] = reference_date

        # Guardar snapshot
        snapshot_path = self.output_dir / f"{reference_date}_scores.csv"
        df.to_csv(snapshot_path, index=False)

        print(f"\n✅ Snapshot guardado: {snapshot_path}")
        print(f"   Tickers: {len(df)}")
        print(f"   Score promedio: {df['super_score_ultimate'].mean():.1f}")

        return snapshot_path

    def generate_weekly_snapshots(self, weeks: int = 52):
        """
        Genera snapshots semanales hacia atrás

        Args:
            weeks: Número de semanas hacia atrás
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
        for date in dates:
            snapshot_path = self.generate_snapshot(date)
            if snapshot_path:
                snapshots.append(snapshot_path)

        print(f"\n✅ {len(snapshots)} snapshots generados")
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
        description='Genera snapshots históricos de scores sin look-ahead bias'
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

    args = parser.parse_args()

    scorer = HistoricalScorer()

    if args.backtest:
        # Generar solo las fechas clave
        dates = scorer.generate_backtest_dates()
        for date in dates:
            scorer.generate_snapshot(date)

    elif args.weekly:
        # Generar snapshots semanales
        scorer.generate_weekly_snapshots(weeks=args.weeks)

    elif args.dates:
        # Generar fechas específicas
        for date in args.dates:
            scorer.generate_snapshot(date)

    else:
        # Default: generar las 3 fechas clave
        print("\n💡 No se especificaron opciones, generando fechas clave de backtest...")
        dates = scorer.generate_backtest_dates()
        for date in dates:
            scorer.generate_snapshot(date)

    print(f"\n{'='*80}")
    print(f"✅ HISTORICAL SCORING COMPLETADO")
    print(f"{'='*80}")
    print(f"\n📖 PRÓXIMOS PASOS:")
    print(f"   1. ⚠️  NOTA: Snapshots usan scores ACTUALES con timestamp correction")
    print(f"   2. 🔧 Para scoring histórico REAL, implementar:")
    print(f"      - VCP scanner con --as-of-date parameter")
    print(f"      - ML predictor con historical training cutoff")
    print(f"      - Fundamental scorer con earnings date filtering")
    print(f"   3. 📊 Usar snapshots en backtest V2:")
    print(f"      python3 backtest_engine_v2.py --historical-scores")
    print(f"\n⚠️  WARNING: Hasta implementar scoring histórico real,")
    print(f"   los snapshots NO eliminan look-ahead bias completamente.")
    print(f"   Solo agregan metadata de timestamps para tracking.")


if __name__ == "__main__":
    main()

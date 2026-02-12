#!/usr/bin/env python3
"""
Genera 52 snapshots semanales sin confirmación interactiva
"""
from historical_scorer import HistoricalScorer

print("\n🚀 GENERANDO 52 SNAPSHOTS SEMANALES")
print("⏱️  Tiempo estimado: ~104 minutos sin VCP")
print("="*80)

scorer = HistoricalScorer()
snapshots = scorer.generate_weekly_snapshots(weeks=52, skip_vcp=True)

print(f"\n{'='*80}")
print(f"✅ COMPLETADO: {len(snapshots)} snapshots generados")
print(f"📁 Directorio: docs/historical_scores/")
print("="*80)

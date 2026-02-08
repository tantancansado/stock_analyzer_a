#!/usr/bin/env python3
"""
WEEKLY WHALE SCAN
Escanea whales una vez por semana (13F filings son trimestrales)
"""
import subprocess
from datetime import datetime
from pathlib import Path

def run_weekly_whale_scan():
    """Ejecuta scan de whales y actualiza sistema"""
    print("🐋 WEEKLY WHALE SCAN")
    print("="*80)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # 1. Scan all whales
    print("\n🔄 FASE 1: Escaneando whales...")
    result = subprocess.run(
        'echo "1" | python3 scan_all_whales.py',
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("   ✅ Whale scan completado")
    else:
        print("   ⚠️  Whale scan con errores")

    # 2. Build index
    print("\n🔨 FASE 2: Construyendo índice institucional...")
    result = subprocess.run(
        'python3 build_institutional_index.py',
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("   ✅ Índice construido")
    else:
        print("   ⚠️  Error construyendo índice")

    # 3. Update 4D analysis
    print("\n🎯 FASE 3: Actualizando análisis 4D...")
    result = subprocess.run(
        'python3 run_super_analyzer_4d.py',
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("   ✅ Análisis 4D actualizado")
    else:
        print("   ⚠️  Error en análisis 4D")

    # 4. Commit and push
    print("\n📤 FASE 4: Subiendo cambios...")

    subprocess.run('git add -A', shell=True)

    commit_msg = f"Weekly whale scan: {datetime.now().strftime('%Y-%m-%d')}"
    subprocess.run(
        f'git commit -m "{commit_msg}\n\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"',
        shell=True
    )

    result = subprocess.run('git push', shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("   ✅ Cambios subidos a GitHub")
    else:
        print("   ⚠️  Error al hacer push")

    print("\n🎉 Weekly whale scan completado!")
    print("="*80)


if __name__ == "__main__":
    run_weekly_whale_scan()

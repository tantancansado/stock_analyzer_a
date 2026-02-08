#!/usr/bin/env python3
"""
WEEKLY WHALE SCAN
Escanea whales una vez por semana (13F filings son trimestrales)
"""
import subprocess
from datetime import datetime
from pathlib import Path

def send_telegram_alerts():
    """Envía alertas de Telegram después del whale scan"""
    try:
        from telegram_legendary_alerts import TelegramLegendaryAlerts
        import pandas as pd

        # Verificar configuración
        config_path = Path('config/telegram_config.json')
        if not config_path.exists():
            print("   ℹ️  Telegram no configurado")
            return

        alerts = TelegramLegendaryAlerts()

        # Verificar datos
        csv_path = Path('docs/super_opportunities_4d_complete.csv')
        if not csv_path.exists():
            print("   ℹ️  No hay datos 4D")
            return

        df = pd.read_csv(csv_path)
        legendary = df[df['super_score_4d'] >= 85]

        if legendary.empty:
            print("   ℹ️  No hay LEGENDARY opportunities")
            return

        print(f"   🌟 {len(legendary)} LEGENDARY opportunities!")

        # Enviar alertas
        sent = 0
        for _, row in legendary.iterrows():
            opportunity = {
                'ticker': row['ticker'],
                'super_score_4d': row['super_score_4d'],
                'tier': row.get('tier', '⭐⭐⭐⭐ LEGENDARY'),
                'dimensions': {
                    'vcp': row.get('vcp_score', 0),
                    'insiders': row.get('insiders_score', 0),
                    'sector': row.get('sector_score', 0),
                    'institutional': row.get('institutional_score', 0)
                },
                'description': 'Confirmación cuádruple - Probabilidad histórica',
                'institutional_details': {
                    'num_whales': row.get('num_whales', 0),
                    'top_whales': row.get('top_whales', '').split(', ') if row.get('top_whales') else []
                }
            }

            message = alerts.format_legendary_alert(opportunity)
            if alerts.send_message(message):
                sent += 1

        print(f"   ✅ {sent}/{len(legendary)} alertas enviadas")

    except Exception as e:
        print(f"   ⚠️  Error en alertas: {e}")

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

    # 4. Telegram alerts
    print("\n📱 FASE 4: Telegram alerts...")
    send_telegram_alerts()

    # 5. Commit and push
    print("\n📤 FASE 5: Subiendo cambios...")

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

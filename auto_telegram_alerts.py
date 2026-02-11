#!/usr/bin/env python3
"""
AUTO TELEGRAM ALERTS
Script automatizado para enviar alertas diarias de oportunidades 5D
Se puede ejecutar manualmente o via cron/GitHub Actions
"""
import sys
from pathlib import Path
from datetime import datetime

# Importar el sistema de config existente
try:
    import config
    from telegram_legendary_alerts import TelegramLegendaryAlerts
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)


def main():
    """Execute automated alerts pipeline"""
    print("=" * 80)
    print("🤖 AUTO TELEGRAM ALERTS - SISTEMA 5D")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    try:
        # Initialize alerts with config from config.py
        alerts = TelegramLegendaryAlerts(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_CHAT_ID
        )

        # Send startup message
        startup_msg = f"""
🤖 <b>Sistema de Alertas Activado</b>

Ejecutando pipeline automático de alertas 5D...
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        alerts.send_message(startup_msg, disable_notification=True)

        # 1. Daily Summary (always first)
        print("📊 Enviando resumen diario...")
        alerts.send_daily_summary()
        print()

        # 2. LEGENDARY alerts (high priority)
        print("🌟 Buscando oportunidades LEGENDARY...")
        alerts.check_and_alert_legendary()
        print()

        # 3. Timing Convergence (critical timing signals)
        print("🔥 Verificando Timing Convergence...")
        alerts.send_timing_convergence_alerts()
        print()

        # 4. VCP Repeaters (quality stocks)
        print("🔁 Analizando VCP Repeaters...")
        alerts.send_vcp_repeater_alerts()
        print()

        # Send completion message
        completion_msg = """
✅ <b>Pipeline de Alertas Completado</b>

Todas las alertas han sido procesadas exitosamente.
"""
        alerts.send_message(completion_msg, disable_notification=True)

        print("=" * 80)
        print("✅ AUTO ALERTS COMPLETADO EXITOSAMENTE")
        print("=" * 80)

        return 0

    except Exception as e:
        error_msg = f"""
❌ <b>Error en Pipeline de Alertas</b>

{str(e)}

📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        try:
            alerts = TelegramLegendaryAlerts(
                bot_token=config.TELEGRAM_BOT_TOKEN,
                chat_id=config.TELEGRAM_CHAT_ID
            )
            alerts.send_message(error_msg)
        except:
            pass

        print(f"\n❌ ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

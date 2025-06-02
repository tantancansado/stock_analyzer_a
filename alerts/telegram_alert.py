import os
from datetime import datetime
from alerts.alert_system import send_message, send_file
from insiders.insider_tracker import scrape_openinsider
from insiders.insiders_filter import run_filter_opportunities

# Ejecutar scraping de insiders
print("🔄 Ejecutando scraping diario de insiders...")
scrape_openinsider()

# Enviar CSV de insiders diario
insiders_csv = "reports/insiders_daily.csv"
if os.path.exists(insiders_csv):
    send_message("📄 Archivo diario de insiders:")
    send_file(insiders_csv)
else:
    send_message("⚠️ No se pudo generar el archivo diario de insiders.")

# Ejecutar filtro de oportunidades
print("🔍 Buscando oportunidades basadas en fundamentales...")
run_filter_opportunities()

# Enviar CSV de oportunidades si existe
opps_csv = "reports/insiders_opportunities.csv"
if os.path.exists(opps_csv):
    send_message("📈 Oportunidades detectadas por actividad de insiders:")
    send_file(opps_csv)
else:
    send_message("⚠️ No se encontraron oportunidades hoy.")
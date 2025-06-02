from insiders.insider_tracker import scrape_openinsider
from alerts.telegram_utils import send_message, send_file, send_image_telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from insiders.insiders_filter import run_filter
from alerts.plot_utils import descargar_grafico_finviz
import os
import pandas as pd
import time

# Ejecutar scrapers y análisis
scrape_openinsider()
run_filter()

# Enviar CSV de insiders
insiders_csv = "reports/insiders_daily.csv"
if os.path.exists(insiders_csv):
    send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "📊 Informe diario de compras de insiders:")
    send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, insiders_csv)

    # Leer CSV y añadir gráficas
    insiders_df = pd.read_csv(insiders_csv)
    tickers = insiders_df["Ticker"].dropna().unique()

    daily_chart_col = []
    weekly_chart_col = []

    for ticker in insiders_df["Ticker"]:
        d_path = descargar_grafico_finviz(ticker, "d")
        time.sleep(3)
        w_path = descargar_grafico_finviz(ticker, "w")
        time.sleep(3)
        daily_chart_col.append(f"reports/graphs/{ticker}_d.png" if d_path else "")
        weekly_chart_col.append(f"reports/graphs/{ticker}_w.png" if w_path else "")

    insiders_df["Chart_Daily"] = daily_chart_col
    insiders_df["Chart_Weekly"] = weekly_chart_col
    insiders_df.to_csv(insiders_csv, index=False)

else:
    send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "❌ No se encontró el archivo de insiders.")

# Enviar CSV de oportunidades
opps_csv = "reports/insiders_opportunities.csv"
if os.path.exists(opps_csv):
    df = pd.read_csv(opps_csv)
    if not df.empty:
        send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "✅ Oportunidades detectadas hoy:")
        send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, opps_csv)

        for ticker in df["Ticker"]:
            for timeframe, label in [("d", "Diario"), ("w", "Semanal")]:
                image_path = descargar_grafico_finviz(ticker, timeframe)
                if image_path:
                    caption = f"📈 {label} - {ticker}"
                    send_image_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, image_path, caption)
                    time.sleep(3)
    else:
        send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "⚠️ No se encontraron oportunidades hoy.")
else:
    send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "⚠️ No se generó el archivo de oportunidades.")

try:
    import generate_html_report
    html_path = "reports/insiders_report.html"
    if os.path.exists(html_path):
        send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, "📄 Informe visual en HTML:")
        send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, html_path)
except Exception as e:
    print(f"⚠️ Error al generar/enviar HTML: {e}")
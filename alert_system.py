import subprocess
import pandas as pd
from alerts.telegram_alert import send_telegram_message
import os

# Ejecutar el script de predicción
print("🔮 Ejecutando predicciones IA...")
subprocess.run(["python3", "predict.py"])

# Leer resultados
predictions_path = "reports/predictions.csv"
if not os.path.exists(predictions_path):
    print("❌ No se encontró el archivo de predicciones")
    exit(1)

df = pd.read_csv(predictions_path)

# Filtrar por probabilidad alta (> 0.75)
high_confidence = df[df["Probability"] > 0.75]

if high_confidence.empty:
    send_telegram_message("🤖 No se detectaron oportunidades claras de compra hoy.")
else:
    message = "🚨 Acciones con alta probabilidad de subida:\n"
    for _, row in high_confidence.iterrows():
        message += f"• {row['Ticker']} — {row['Probability']:.2%}\n"
    send_telegram_message(message)

print("✅ Alerta enviada.")
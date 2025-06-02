import os
import pandas as pd
from alerts.telegram_alert import send_telegram_message

def send_message(text):
    print(text)
    send_telegram_message(text)

def send_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if content.strip():
            send_telegram_message("📊 Contenido del archivo:\n" + content[:4000])  # Telegram tiene límite de 4096
        else:
            send_telegram_message(f"⚠️ El archivo {file_path} está vacío.")
    else:
        send_telegram_message(f"⚠️ No se encontró el archivo: {file_path}")
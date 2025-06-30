#!/usr/bin/env python3
"""
Telegram Utils - Versión original del usuario con caption opcional
"""

import requests

def send_image_telegram(token, chat_id, image_path, caption=""):
    """Envía una imagen por Telegram"""
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(image_path, 'rb') as img:
        files = {'photo': img}
        data = {'chat_id': chat_id, 'caption': caption}
        r = requests.post(url, files=files, data=data)
    if r.status_code == 200:
        print("Imagen enviada correctamente")
        return True
    else:
        print(f"Error al enviar imagen: {r.text}")
        return False

def send_message(token, chat_id, message):
    """Envía un mensaje de texto por Telegram"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    r = requests.post(url, data=data)
    if r.status_code == 200:
        print("Mensaje enviado correctamente")
        return True
    else:
        print(f"Error al enviar mensaje: {r.text}")
        return False
        
def send_file(token, chat_id, file_path, caption=""):
    """
    Envía un archivo por Telegram
    ACTUALIZADO: Ahora acepta caption opcional como 4to argumento
    """
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        
        # Añadir caption si se proporciona
        if caption:
            data["caption"] = caption
            
        r = requests.post(url, files=files, data=data)
    if r.status_code == 200:
        print("Archivo enviado correctamente")
        return True
    else:
        print(f"Error al enviar archivo: {r.text}")
        return False
        
def send_document_telegram(chat_id, file_path, caption=""):
    """
    Envía un documento a Telegram
    """
    try:
        from config import TELEGRAM_BOT_TOKEN
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        
        with open(file_path, 'rb') as file:
            data = {
                'chat_id': chat_id,
                'caption': caption
            }
            files = {
                'document': file
            }
            
            response = requests.post(url, data=data, files=files)
            
            if response.status_code == 200:
                print(f"✅ Documento enviado: {file_path}")
                return True
            else:
                print(f"❌ Error enviando documento: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error en send_document_telegram: {e}")
        return False
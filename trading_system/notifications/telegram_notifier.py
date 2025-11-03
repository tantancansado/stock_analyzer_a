"""
Notificador de Telegram
"""

import requests
import os
from typing import Optional
from datetime import datetime

class TelegramNotifier:
    """Clase para enviar notificaciones por Telegram"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        
    def is_configured(self) -> bool:
        """Verifica si Telegram está configurado"""
        return bool(self.bot_token and self.chat_id)
    
    def send_message(self, message: str) -> bool:
        """Envía un mensaje por Telegram"""
        if not self.is_configured():
            print("❌ Telegram no configurado")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data, timeout=30)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False
    
    def send_file(self, file_path: str, caption: str = "") -> bool:
        """Envía un archivo por Telegram"""
        if not self.is_configured():
            print("❌ Telegram no configurado")
            return False
        
        if not os.path.exists(file_path):
            print(f"❌ Archivo no encontrado: {file_path}")
            return False
        
        try:
            url = f"{self.base_url}/sendDocument"
            
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption
                }
                
                response = requests.post(url, files=files, data=data, timeout=60)
                return response.status_code == 200
                
        except Exception as e:
            print(f"❌ Error enviando archivo: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Prueba la conexión con Telegram"""
        print("📱 Probando conexión con Telegram...")
        
        if not self.is_configured():
            print("❌ Variables de entorno no configuradas:")
            print("  - TELEGRAM_BOT_TOKEN")
            print("  - TELEGRAM_CHAT_ID")
            return False
        
        test_message = f"🧪 Test desde Sistema Trading - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if self.send_message(test_message):
            print("✅ Telegram funcionando correctamente")
            return True
        else:
            print("❌ Error enviando mensaje de prueba")
            return False

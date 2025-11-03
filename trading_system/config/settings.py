"""
Configuraciones centralizadas del sistema
"""

import os
from pathlib import Path

class SystemSettings:
    """Configuraciones del sistema"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.reports_dir = self.base_dir / "reports"
        self.data_dir = self.base_dir / "data"
        
        # GitHub Pages
        self.github_base_url = "https://tantancansado.github.io/stock_analyzer_a"
        self.github_docs_path = self.base_dir / "docs"
        
        # Telegram
        self.telegram_bot_token = os.getenv('TELEGRAM_762243037:AAFnEVl8saspHl40caBWePSnhe8CLSXWlvYBOT_TOKEN')
        self.telegram_chat_id = os.getenv('3165866')
        
        # Configuraciones de análisis
        self.max_retries = 3
        self.timeout_seconds = 30
        self.default_days_back = 365
        
        # Configuraciones de scraping
        self.scraper_delay = 1
        self.batch_size = 5
    
    def validate(self) -> bool:
        """Valida que las configuraciones sean correctas"""
        warnings = []
        
        if not self.reports_dir.exists():
            try:
                self.reports_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                warnings.append(f"No se puede crear directorio reports: {e}")
        
        if not self.telegram_bot_token:
            warnings.append("TELEGRAM_BOT_TOKEN no configurado")
        
        if not self.telegram_chat_id:
            warnings.append("TELEGRAM_CHAT_ID no configurado")
        
        if warnings:
            print("⚠️ Advertencias de configuración:")
            for warning in warnings:
                print(f"  - {warning}")
        
        return True  # No bloquear el sistema por configuraciones faltantes

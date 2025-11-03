"""
Clase base para todos los analizadores
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import os
import pandas as pd

class BaseAnalyzer(ABC):
    """Clase base que define la interfaz común para todos los analizadores"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.last_run = None
        self.setup()
    
    def setup(self):
        """Configuración específica del analizador (override si es necesario)"""
        pass
    
    @abstractmethod
    def run_analysis(self, **kwargs) -> Dict[str, Any]:
        """
        Método principal que debe implementar cada analizador
        
        Returns:
            Dict con al menos:
            {
                'success': bool,
                'title': str,
                'description': str,
                'html_path': str,
                'csv_path': str,
                'data': Any,
                'timestamp': str
            }
        """
        pass
    
    def is_enabled(self) -> bool:
        """Verifica si el analizador está habilitado"""
        return self.enabled
    
    def get_output_paths(self, base_name: str = None) -> tuple:
        """Genera rutas de salida estándar"""
        if base_name is None:
            base_name = self.name
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_path = f"reports/{base_name}_{timestamp}.html"
        csv_path = f"reports/{base_name}_{timestamp}.csv"
        return html_path, csv_path
    
    def save_results(self, data: Any, html_content: str, csv_data: Any) -> Dict[str, str]:
        """Guarda resultados en archivos"""
        html_path, csv_path = self.get_output_paths()
        
        # Crear directorio si no existe
        os.makedirs("reports", exist_ok=True)
        
        # Guardar HTML
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Guardar CSV
        if hasattr(csv_data, 'to_csv'):
            csv_data.to_csv(csv_path, index=False)
        elif isinstance(csv_data, list):
            pd.DataFrame(csv_data).to_csv(csv_path, index=False)
        
        return {
            'html_path': html_path,
            'csv_path': csv_path
        }
    
    def log_execution(self, success: bool, message: str = ""):
        """Registra la ejecución del analizador"""
        self.last_run = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'message': message
        }

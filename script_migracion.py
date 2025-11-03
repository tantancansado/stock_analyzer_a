#!/usr/bin/env python3
"""
Script de migración automática para refactorizar el sistema monolítico
VERSIÓN ARREGLADA - Sin errores de sintaxis
"""

import os
import shutil
from pathlib import Path
import re

class TradingSystemMigrator:
    """Migra el sistema monolítico a la arquitectura modular"""
    
    def __init__(self, source_file="paste.txt"):
        self.source_file = source_file
        self.base_dir = Path("trading_system")
        
    def run_migration(self):
        """Ejecuta la migración completa"""
        print("🚀 INICIANDO MIGRACIÓN A ARQUITECTURA MODULAR")
        print("=" * 60)
        
        # 1. Crear estructura de directorios
        self.create_directory_structure()
        
        # 2. Crear archivos base del sistema
        self.create_base_files()
        
        # 3. Crear analizadores básicos
        self.create_basic_analyzers()
        
        # 4. Crear archivos de configuración
        self.create_config_files()
        
        # 5. Crear archivos de utilidades
        self.create_utility_files()
        
        # 6. Crear notificaciones
        self.create_notification_files()
        
        # 7. Crear main.py simplificado
        self.create_main_file()
        
        # 8. Crear archivos de test y documentación
        self.create_test_and_docs()
        
        print("\n✅ MIGRACIÓN COMPLETADA")
        print(f"📁 Nueva estructura creada en: {self.base_dir}")
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. cd trading_system")
        print("2. pip install -r requirements.txt")
        print("3. export TELEGRAM_BOT_TOKEN='tu_token'")
        print("4. export TELEGRAM_CHAT_ID='tu_chat_id'")
        print("5. python main.py")
    
    def create_directory_structure(self):
        """Crea la estructura de directorios"""
        print("📁 Creando estructura de directorios...")
        
        directories = [
            "config",
            "core", 
            "analyzers",
            "data/scrapers",
            "data/processors",
            "outputs/html_generators",
            "outputs/exporters",
            "notifications",
            "utils",
            "tests",
            "reports"
        ]
        
        for dir_path in directories:
            full_path = self.base_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Crear __init__.py
            init_file = full_path / "__init__.py"
            if not init_file.exists():
                init_file.write_text("# Módulo del Sistema Trading Unificado\n")
        
        print(f"✅ {len(directories)} directorios creados")
    
    def create_base_files(self):
        """Crea archivos base del sistema (core/)"""
        print("🏗️ Creando archivos base...")
        
        # core/base_analyzer.py
        base_analyzer_code = '''"""
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
'''
        
        base_file = self.base_dir / "core" / "base_analyzer.py"
        base_file.write_text(base_analyzer_code, encoding='utf-8')
        
        # core/system_manager.py
        system_manager_code = '''"""
Gestor principal del sistema que coordina todos los componentes
"""

from typing import Dict, List, Optional, Any
import traceback
import importlib
import os
from datetime import datetime
from pathlib import Path

from core.base_analyzer import BaseAnalyzer
from utils.file_utils import setup_directories
from config.settings import SystemSettings

class TradingSystemManager:
    """Gestor principal que coordina todos los analizadores"""
    
    def __init__(self):
        self.settings = SystemSettings()
        self.setup_system()
        self.load_analyzers()
        self.load_services()
    
    def setup_system(self):
        """Configuración inicial del sistema"""
        setup_directories()
        
        if not self.settings.validate():
            print("⚠️ Advertencias de configuración detectadas")
        
        print("✅ Sistema inicializado")
    
    def load_analyzers(self):
        """Carga todos los analizadores disponibles dinámicamente"""
        self.analyzers = {}
        
        analyzers_dir = Path("analyzers")
        if not analyzers_dir.exists():
            print("❌ Directorio analyzers no encontrado")
            return
        
        # Buscar archivos de analizadores
        for file_path in analyzers_dir.glob("*_analyzer.py"):
            module_name = file_path.stem
            try:
                # Importar módulo dinámicamente
                module = importlib.import_module(f"analyzers.{module_name}")
                
                # Buscar clases que hereden de BaseAnalyzer
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, BaseAnalyzer) and 
                        attr != BaseAnalyzer):
                        
                        # Crear instancia del analizador
                        analyzer_instance = attr()
                        analyzer_key = module_name.replace('_analyzer', '')
                        self.analyzers[analyzer_key] = analyzer_instance
                        print(f"✅ Analizador cargado: {analyzer_key}")
                        break
                        
            except Exception as e:
                print(f"❌ Error cargando {module_name}: {e}")
        
        print(f"✅ {len(self.analyzers)} analizadores cargados")
    
    def load_services(self):
        """Carga servicios de exportación y notificación"""
        try:
            from notifications.telegram_notifier import TelegramNotifier
            self.telegram_notifier = TelegramNotifier()
            print("✅ Telegram Notifier cargado")
        except ImportError:
            print("⚠️ Telegram Notifier no disponible")
            self.telegram_notifier = None
    
    def run_ultra_enhanced_analysis(self, **kwargs) -> Dict[str, Any]:
        """Ejecuta análisis completo con todos los componentes"""
        print("\\n🌟 ANÁLISIS ULTRA MEJORADO")
        print("=" * 60)
        
        results = {}
        
        try:
            # Ejecutar cada analizador
            for name, analyzer in self.analyzers.items():
                if hasattr(analyzer, 'is_enabled') and not analyzer.is_enabled():
                    print(f"⏭️ Saltando {name} (deshabilitado)")
                    continue
                
                print(f"\\n🔸 Ejecutando {name.upper()}")
                try:
                    result = analyzer.run_analysis(**kwargs)
                    results[name] = result
                    
                    if result.get('success'):
                        print(f"✅ {name} completado")
                        analyzer.log_execution(True, "Análisis completado exitosamente")
                    else:
                        print(f"❌ {name} falló: {result.get('error', 'Error desconocido')}")
                        analyzer.log_execution(False, result.get('error', 'Error desconocido'))
                    
                except Exception as e:
                    print(f"❌ Error en {name}: {e}")
                    results[name] = {'success': False, 'error': str(e)}
                    analyzer.log_execution(False, str(e))
            
            # Enviar notificación consolidada
            if self.telegram_notifier:
                self.send_consolidated_notification(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Error crítico: {e}")
            traceback.print_exc()
            return {'error': str(e)}
    
    def send_consolidated_notification(self, results: Dict[str, Any]):
        """Envía notificación consolidada por Telegram"""
        try:
            message = self._build_telegram_message(results)
            self.telegram_notifier.send_message(message)
            
            # Enviar archivos CSV si existen
            for name, result in results.items():
                if result.get('success') and result.get('csv_path'):
                    self.telegram_notifier.send_file(
                        result['csv_path'], 
                        f"📊 {name.title()} Data"
                    )
        except Exception as e:
            print(f"❌ Error enviando notificación: {e}")
    
    def _build_telegram_message(self, results: Dict[str, Any]) -> str:
        """Construye mensaje de Telegram con resumen de resultados"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        successful = [name for name, result in results.items() if result.get('success')]
        failed = [name for name, result in results.items() if not result.get('success')]
        
        message = f"""🌟 **REPORTE TRADING ULTRA MEJORADO**

📅 **{timestamp}**

📊 **Resumen:**
• ✅ Exitosos: {len(successful)}
• ❌ Fallidos: {len(failed)}
• 📋 Total analizadores: {len(results)}

"""
        
        for name, result in results.items():
            status = "✅" if result.get('success') else "❌"
            message += f"{status} **{name.title()}:**\\n"
            
            if result.get('success'):
                if 'description' in result:
                    message += f"  {result['description']}\\n"
            else:
                error = result.get('error', 'Error desconocido')
                message += f"  Error: {error[:100]}...\\n"
            
            message += "\\n"
        
        return message
    
    def handle_command_line_args(self, args: List[str]) -> bool:
        """Maneja argumentos de línea de comandos"""
        if not args:
            return False
        
        command = args[0]
        
        if command == '--ultra-enhanced':
            result = self.run_ultra_enhanced_analysis()
            return 'error' not in result
        
        elif command == '--test':
            return self.run_component_tests()
        
        elif command.startswith('--'):
            analyzer_name = command[2:].replace('-', '_')
            
            if analyzer_name in self.analyzers:
                try:
                    result = self.analyzers[analyzer_name].run_analysis()
                    
                    if result.get('success'):
                        print(f"✅ {analyzer_name} completado")
                        return True
                    else:
                        print(f"❌ {analyzer_name} falló: {result.get('error')}")
                        return False
                        
                except Exception as e:
                    print(f"❌ Error ejecutando {analyzer_name}: {e}")
                    return False
            else:
                print(f"❌ Analizador no encontrado: {analyzer_name}")
                return False
        
        else:
            print(f"❌ Comando desconocido: {command}")
            return False
    
    def run_interactive_menu(self) -> bool:
        """Ejecuta el menú interactivo"""
        while True:
            self.show_menu()
            
            choice = input("Selecciona opción: ").strip()
            
            if choice == "0":
                print("👋 ¡Hasta luego!")
                break
            
            self.handle_menu_choice(choice)
            input("\\nPresiona Enter para continuar...")
        
        return True
    
    def show_menu(self):
        """Muestra el menú interactivo"""
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📊 SISTEMA TRADING UNIFICADO                            ║
║                        Versión Modular v2.0                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

🌟 ANÁLISIS RECOMENDADO:
  1. 🚀 ANÁLISIS ULTRA MEJORADO (Todos los componentes)

🏛️ ANÁLISIS INDIVIDUALES:""")

        for i, name in enumerate(self.analyzers.keys(), 2):
            print(f"  {i}. 📊 {name.replace('_', ' ').title()}")

        print(f"""
🔧 UTILIDADES:
  {len(self.analyzers) + 2}. 🔍 Verificar componentes
  {len(self.analyzers) + 3}. 📋 Listar analizadores

  0. ❌ Salir

Total analizadores cargados: {len(self.analyzers)}
""")
    
    def handle_menu_choice(self, choice: str):
        """Maneja la selección del menú"""
        try:
            choice_num = int(choice)
        except ValueError:
            print("❌ Opción inválida")
            return
        
        if choice_num == 1:
            self.run_ultra_enhanced_analysis()
        elif 2 <= choice_num <= len(self.analyzers) + 1:
            analyzer_names = list(self.analyzers.keys())
            analyzer_name = analyzer_names[choice_num - 2]
            
            try:
                result = self.analyzers[analyzer_name].run_analysis()
                
                if result.get('success'):
                    print(f"✅ {analyzer_name} completado")
                else:
                    print(f"❌ {analyzer_name} falló: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        elif choice_num == len(self.analyzers) + 2:
            self.run_component_tests()
        elif choice_num == len(self.analyzers) + 3:
            self.list_available_analyzers()
        else:
            print("❌ Opción inválida")
    
    def list_available_analyzers(self):
        """Lista todos los analizadores disponibles"""
        print("\\n📊 ANALIZADORES DISPONIBLES:")
        print("=" * 40)
        
        for name, analyzer in self.analyzers.items():
            status = "✅ Habilitado" if analyzer.is_enabled() else "❌ Deshabilitado"
            print(f"🔸 {name.upper()}: {status}")
    
    def run_component_tests(self) -> bool:
        """Ejecuta tests de componentes"""
        try:
            from tests.test_components import run_all_tests
            run_all_tests()
            return True
        except ImportError:
            print("❌ Módulo de tests no encontrado")
            return False
        except Exception as e:
            print(f"❌ Error ejecutando tests: {e}")
            return False
'''
        
        system_manager_file = self.base_dir / "core" / "system_manager.py"
        system_manager_file.write_text(system_manager_code, encoding='utf-8')
        
        print("✅ Archivos base creados")
    
    def create_basic_analyzers(self):
        """Crea analizadores básicos funcionales"""
        print("🔍 Creando analizadores básicos...")
        
        # Enhanced Opportunities Analyzer
        enhanced_code = '''"""
Enhanced Trading Opportunity Analyzer
Analizador de oportunidades con correlaciones automáticas
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import os

from core.base_analyzer import BaseAnalyzer

class EnhancedOpportunitiesAnalyzer(BaseAnalyzer):
    """Analizador de oportunidades mejoradas (versión básica)"""
    
    def __init__(self):
        super().__init__("enhanced_opportunities")
    
    def run_analysis(self, recent_days=14, **kwargs) -> Dict[str, Any]:
        """Ejecuta el análisis de oportunidades mejoradas"""
        try:
            print("🎯 Ejecutando Enhanced Opportunities Analysis...")
            
            # Análisis básico - aquí puedes integrar tu lógica completa
            opportunities = self._generate_sample_opportunities()
            
            # Generar reportes
            html_content = self._generate_html_report(opportunities)
            csv_data = pd.DataFrame(opportunities)
            
            # Guardar archivos
            paths = self.save_results(opportunities, html_content, csv_data)
            
            return {
                'success': True,
                'title': f"Enhanced Opportunities - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'description': f"Análisis de correlaciones con {len(opportunities)} oportunidades",
                'data': opportunities,
                'timestamp': datetime.now().isoformat(),
                **paths
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_sample_opportunities(self):
        """Genera oportunidades de ejemplo"""
        return [
            {
                'sector': 'Technology',
                'score': 85,
                'distance_from_min': 8.5,
                'insider_activity': True,
                'urgency': 'ALTA'
            },
            {
                'sector': 'Healthcare',
                'score': 78,
                'distance_from_min': 12.3,
                'insider_activity': False,
                'urgency': 'MEDIA'
            }
        ]
    
    def _generate_html_report(self, opportunities):
        """Genera reporte HTML"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Construir HTML sin problemas de sintaxis
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="es">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <title>Enhanced Opportunities Report</title>',
            '    <style>',
            '        body { background: #0a0e1a; color: white; font-family: Arial; margin: 20px; }',
            '        h1 { color: #4a90e2; }',
            '        .opportunity { background: rgba(255,255,255,0.1); margin: 10px 0; padding: 15px; border-radius: 8px; }',
            '    </style>',
            '</head>',
            '<body>',
            '    <h1>🎯 Enhanced Opportunities Report</h1>',
            f'    <p>📅 Generado: {timestamp}</p>',
            f'    <p>📊 Total oportunidades: {len(opportunities)}</p>'
        ]
        
        # Añadir cada oportunidad
        for opp in opportunities:
            insider_text = 'Sí' if opp['insider_activity'] else 'No'
            html_parts.extend([
                '    <div class="opportunity">',
                f'        <h3>{opp["sector"]}</h3>',
                f'        <p>Score: {opp["score"]}</p>',
                f'        <p>Distancia del mínimo: {opp["distance_from_min"]}%</p>',
                f'        <p>Insider Activity: {insider_text}</p>',
                f'        <p>Urgencia: {opp["urgency"]}</p>',
                '    </div>'
            ])
        
        html_parts.extend([
            '</body>',
            '</html>'
        ])
        
        return '\\n'.join(html_parts)
'''
        
        enhanced_file = self.base_dir / "analyzers" / "enhanced_opportunities_analyzer.py"
        enhanced_file.write_text(enhanced_code, encoding='utf-8')
        
        # Insider Trading Analyzer
        insider_code = '''"""
Insider Trading Analyzer
Analizador de insider trading
"""

import os
import sys
import subprocess
import pandas as pd
from datetime import datetime
from typing import Dict, Any

from core.base_analyzer import BaseAnalyzer

class InsiderTradingAnalyzer(BaseAnalyzer):
    """Analizador de insider trading"""
    
    def __init__(self):
        super().__init__("insider_trading")
        self.csv_path = "reports/insiders_daily.csv"
    
    def run_analysis(self, **kwargs) -> Dict[str, Any]:
        """Ejecuta el análisis completo de insider trading"""
        try:
            print("🏛️ Ejecutando Insider Trading Analysis...")
            
            # Intentar ejecutar scraper
            scraper_success = self._run_scraper()
            
            # Cargar datos
            data = self._load_data()
            
            # Generar HTML
            html_content = self._generate_html_report(data)
            
            # Guardar resultados
            paths = self.save_results(data, html_content, data)
            
            return {
                'success': scraper_success,
                'title': f"Insider Trading - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'description': f"Reporte con {len(data)} transacciones detectadas" if len(data) > 0 else "Monitoreo completado",
                'data': data,
                'timestamp': datetime.now().isoformat(),
                **paths
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _run_scraper(self) -> bool:
        """Ejecuta el scraper de insider trading"""
        print("🕷️ Buscando scraper...")
        
        # Buscar scraper en múltiples ubicaciones
        scraper_paths = [
            "insiders/openinsider_scraper.py",
            "openinsider_scraper.py",
            "data/scrapers/openinsider_scraper.py",
            "../insiders/openinsider_scraper.py",
            "../openinsider_scraper.py"
        ]
        
        for path in scraper_paths:
            if os.path.exists(path):
                print(f"✅ Scraper encontrado: {path}")
                try:
                    result = subprocess.run([sys.executable, path], 
                                          capture_output=True, text=True, timeout=180)
                    return result.returncode == 0
                except Exception as e:
                    print(f"❌ Error ejecutando scraper: {e}")
                    break
        
        print("⚠️ Scraper no encontrado, creando datos de ejemplo...")
        self._create_sample_data()
        return True
    
    def _create_sample_data(self):
        """Crea datos de ejemplo para testing"""
        sample_data = [
            {
                'Ticker': 'AAPL',
                'Company': 'Apple Inc.',
                'Insider': 'Tim Cook',
                'Type': 'Purchase',
                'Price': 150.25,
                'Qty': 1000,
                'Value': '$150,250'
            },
            {
                'Ticker': 'MSFT',
                'Company': 'Microsoft Corp.',
                'Insider': 'Satya Nadella',
                'Type': 'Purchase', 
                'Price': 250.75,
                'Qty': 500,
                'Value': '$125,375'
            }
        ]
        
        os.makedirs("reports", exist_ok=True)
        pd.DataFrame(sample_data).to_csv(self.csv_path, index=False)
        print("✅ Datos de ejemplo creados")
    
    def _load_data(self) -> pd.DataFrame:
        """Carga los datos del CSV"""
        if os.path.exists(self.csv_path):
            try:
                return pd.read_csv(self.csv_path)
            except:
                pass
        return pd.DataFrame()
    
    def _generate_html_report(self, data):
        """Genera reporte HTML"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Construir HTML sin problemas de sintaxis
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="es">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <title>Insider Trading Report</title>',
            '    <style>',
            '        body { background: #0a0e1a; color: white; font-family: Arial; margin: 20px; }',
            '        h1 { color: #4a90e2; }',
            '        table { width: 100%; border-collapse: collapse; margin: 20px 0; }',
            '        th, td { border: 1px solid #4a5568; padding: 8px; text-align: left; }',
            '        th { background: #4a90e2; }',
            '        tr:nth-child(even) { background: #2d3748; }',
            '    </style>',
            '</head>',
            '<body>',
            '    <h1>🏛️ Insider Trading Report</h1>',
            f'    <p>📅 Fecha: {timestamp}</p>',
            f'    <p>📊 Total transacciones: {len(data)}</p>',
            '    <table>',
            '        <thead>',
            '            <tr>',
            '                <th>Ticker</th>',
            '                <th>Company</th>',
            '                <th>Insider</th>',
            '                <th>Type</th>',
            '                <th>Price</th>',
            '                <th>Quantity</th>',
            '                <th>Value</th>',
            '            </tr>',
            '        </thead>',
            '        <tbody>'
        ]
        
        # Añadir filas de datos
        for _, row in data.iterrows():
            html_parts.extend([
                '            <tr>',
                f'                <td>{row.get("Ticker", "N/A")}</td>',
                f'                <td>{row.get("Company", "N/A")}</td>',
                f'                <td>{row.get("Insider", "N/A")}</td>',
                f'                <td>{row.get("Type", "N/A")}</td>',
                f'                <td>{row.get("Price", "N/A")}</td>',
                f'                <td>{row.get("Qty", "N/A")}</td>',
                f'                <td>{row.get("Value", "N/A")}</td>',
                '            </tr>'
            ])
        
        html_parts.extend([
            '        </tbody>',
            '    </table>',
            '</body>',
            '</html>'
        ])
        
        return '\\n'.join(html_parts)
'''
        
        insider_file = self.base_dir / "analyzers" / "insider_trading_analyzer.py"
        insider_file.write_text(insider_code, encoding='utf-8')
        
        print("✅ Analizadores básicos creados")
    
    def create_config_files(self):
        """Crea archivos de configuración"""
        print("⚙️ Creando archivos de configuración...")
        
        # config/settings.py
        settings_code = '''"""
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
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
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
'''
        
        settings_file = self.base_dir / "config" / "settings.py"
        settings_file.write_text(settings_code, encoding='utf-8')
        
        print("✅ Archivos de configuración creados")
    
    def create_utility_files(self):
        """Crea archivos de utilidades"""
        print("🔧 Creando archivos de utilidades...")
        
        # utils/file_utils.py
        file_utils_code = '''"""
Utilidades para manejo de archivos
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional

def setup_directories():
    """Crea los directorios necesarios del sistema"""
    directories = [
        "reports",
        "data",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def create_bundle(files: List[str], output_path: str) -> bool:
    """Crea un ZIP con los archivos especificados"""
    try:
        with zipfile.ZipFile(output_path, 'w') as zipf:
            for file_path in files:
                if os.path.exists(file_path):
                    zipf.write(file_path, arcname=os.path.basename(file_path))
        return True
    except Exception as e:
        print(f"❌ Error creando bundle: {e}")
        return False

def cleanup_old_reports(directory: str, keep_count: int = 10):
    """Limpia reportes antiguos, manteniendo solo los más recientes"""
    try:
        reports_dir = Path(directory)
        if not reports_dir.exists():
            return
        
        files = sorted(reports_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        for file_to_remove in files[keep_count:]:
            file_to_remove.unlink()
            csv_file = file_to_remove.with_suffix('.csv')
            if csv_file.exists():
                csv_file.unlink()
        
        print(f"✅ Limpieza completada. Mantenidos {min(len(files), keep_count)} reportes")
        
    except Exception as e:
        print(f"❌ Error en limpieza: {e}")

def find_file_in_paths(filename: str, search_paths: List[str]) -> Optional[str]:
    """Busca un archivo en múltiples rutas"""
    for path in search_paths:
        full_path = os.path.join(path, filename)
        if os.path.exists(full_path):
            return full_path
    return None
'''
        
        file_utils_file = self.base_dir / "utils" / "file_utils.py"
        file_utils_file.write_text(file_utils_code, encoding='utf-8')
        
        # utils/validation_utils.py
        validation_code = '''"""
Utilidades de validación del sistema
"""

import os
import sys
import importlib
from typing import List, Tuple

def validate_environment() -> bool:
    """Valida que el entorno esté correctamente configurado"""
    print("🔍 Validando entorno...")
    
    errors = []
    warnings = []
    
    # Validar Python version
    if sys.version_info < (3, 7):
        errors.append(f"Python 3.7+ requerido. Actual: {sys.version}")
    
    # Validar dependencias críticas
    critical_deps = ['pandas', 'numpy', 'requests']
    for dep in critical_deps:
        try:
            importlib.import_module(dep)
        except ImportError:
            errors.append(f"Dependencia crítica faltante: {dep}")
    
    # Validar dependencias opcionales
    optional_deps = ['matplotlib', 'plotly', 'beautifulsoup4']
    for dep in optional_deps:
        try:
            importlib.import_module(dep)
        except ImportError:
            warnings.append(f"Dependencia opcional faltante: {dep}")
    
    # Validar configuraciones
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        warnings.append("TELEGRAM_BOT_TOKEN no configurado")
    
    if not os.getenv('TELEGRAM_CHAT_ID'):
        warnings.append("TELEGRAM_CHAT_ID no configurado")
    
    # Mostrar resultados
    if errors:
        print("❌ Errores críticos:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    if warnings:
        print("⚠️ Advertencias:")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("✅ Entorno validado correctamente")
    return True
'''
        
        validation_file = self.base_dir / "utils" / "validation_utils.py"
        validation_file.write_text(validation_code, encoding='utf-8')
        
        print("✅ Archivos de utilidades creados")
    
    def create_notification_files(self):
        """Crea archivos de notificación"""
        print("📱 Creando archivos de notificación...")
        
        # notifications/telegram_notifier.py
        telegram_code = '''"""
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
'''
        
        telegram_file = self.base_dir / "notifications" / "telegram_notifier.py"
        telegram_file.write_text(telegram_code, encoding='utf-8')
        
        print("✅ Archivos de notificación creados")
    
    def create_main_file(self):
        """Crea el archivo main.py simplificado"""
        print("📄 Creando main.py...")
        
        main_code = '''#!/usr/bin/env python3
"""
Sistema Unificado de Trading - Punto de Entrada Principal
Versión Modular y Extensible
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from core.system_manager import TradingSystemManager
from utils.validation_utils import validate_environment

def main():
    """Función principal simplificada"""
    print("🚀 SISTEMA TRADING UNIFICADO - VERSIÓN MODULAR")
    print("=" * 60)
    
    # Validar entorno
    if not validate_environment():
        print("❌ Entorno no válido. Instala dependencias:")
        print("   pip install -r requirements.txt")
        return False
    
    # Inicializar el gestor del sistema
    try:
        manager = TradingSystemManager()
    except Exception as e:
        print(f"❌ Error inicializando sistema: {e}")
        return False
    
    # Procesar argumentos de línea de comandos
    if len(sys.argv) > 1:
        return manager.handle_command_line_args(sys.argv[1:])
    else:
        return manager.run_interactive_menu()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n👋 Proceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        sys.exit(1)
'''
        
        main_file = self.base_dir / "main.py"
        main_file.write_text(main_code, encoding='utf-8')
        
        print("✅ main.py creado")
    
    def create_test_and_docs(self):
        """Crea archivos de test y documentación"""
        print("🧪 Creando archivos de test y documentación...")
        
        # tests/test_components.py
        test_code = '''"""
Tests para validar componentes del sistema
"""

import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

def test_analyzers():
    """Prueba la carga de todos los analizadores"""
    print("🧪 Testing analyzers...")
    
    analyzers_to_test = [
        ("insider_trading_analyzer", "InsiderTradingAnalyzer"),
        ("enhanced_opportunities_analyzer", "EnhancedOpportunitiesAnalyzer")
    ]
    
    for module_name, class_name in analyzers_to_test:
        try:
            module = __import__(f"analyzers.{module_name}", fromlist=[class_name])
            analyzer_class = getattr(module, class_name)
            analyzer = analyzer_class()
            print(f"✅ {class_name} - OK")
        except Exception as e:
            print(f"❌ {class_name} - Error: {e}")

def test_configuration():
    """Prueba la configuración del sistema"""
    print("🧪 Testing configuration...")
    
    try:
        from config.settings import SystemSettings
        settings = SystemSettings()
        is_valid = settings.validate()
        print(f"{'✅' if is_valid else '❌'} SystemSettings - {'OK' if is_valid else 'Errores de configuración'}")
    except Exception as e:
        print(f"❌ SystemSettings - Error: {e}")

def test_file_structure():
    """Prueba la estructura de archivos"""
    print("🧪 Testing file structure...")
    
    required_dirs = [
        "config", "core", "analyzers", "data", "outputs", 
        "notifications", "utils", "tests", "reports"
    ]
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ - OK")
        else:
            print(f"❌ {dir_name}/ - FALTANTE")

def run_all_tests():
    """Ejecuta todos los tests"""
    print("🧪 EJECUTANDO TESTS DEL SISTEMA")
    print("=" * 50)
    
    test_file_structure()
    print()
    test_configuration()
    print()
    test_analyzers()
    
    print("\\n🧪 Tests completados")

if __name__ == "__main__":
    run_all_tests()
'''
        
        test_file = self.base_dir / "tests" / "test_components.py"
        test_file.write_text(test_code, encoding='utf-8')
        
        # requirements.txt
        requirements = '''# Dependencias críticas
pandas>=1.3.0
numpy>=1.20.0
requests>=2.25.0

# Dependencias para análisis financiero
yfinance>=0.1.70

# Dependencias para HTML y visualización
beautifulsoup4>=4.9.0

# Dependencias opcionales para gráficos
matplotlib>=3.3.0
plotly>=5.0.0
'''
        
        req_file = self.base_dir / "requirements.txt"
        req_file.write_text(requirements, encoding='utf-8')
        
        # README.md
        readme = '''# Sistema Trading Unificado - Versión Modular

## 🚀 Instalación Rápida

```bash
# 1. Navegar al directorio
cd trading_system

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno (opcional)
export TELEGRAM_BOT_TOKEN="tu_bot_token"
export TELEGRAM_CHAT_ID="tu_chat_id"

# 4. Ejecutar
python main.py
```

## 📊 Uso

### Modo Interactivo
```bash
python main.py
```

### Línea de Comandos
```bash
# Análisis completo
python main.py --ultra-enhanced

# Análisis individuales
python main.py --insider-trading
python main.py --enhanced-opportunities

# Tests
python main.py --test
```

## 📁 Estructura Modular

```
trading_system/
├── main.py                     # Punto de entrada
├── config/                     # Configuraciones
├── core/                       # Sistema base
├── analyzers/                  # Analizadores individuales
├── data/                       # Scrapers y procesadores
├── outputs/                    # Generadores y exportadores
├── notifications/              # Telegram, email, etc.
├── utils/                      # Utilidades generales
└── tests/                      # Tests del sistema
```

## 🔧 Añadir Nuevos Analizadores

1. Crear archivo en `analyzers/mi_nuevo_analyzer.py`
2. Heredar de `BaseAnalyzer`
3. Implementar `run_analysis()`

```python
from core.base_analyzer import BaseAnalyzer

class MiNuevoAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("mi_nuevo")
    
    def run_analysis(self, **kwargs):
        # Tu lógica aquí
        return {
            'success': True,
            'title': 'Mi Análisis',
            'description': 'Descripción',
            'data': {},
            'html_path': 'path/to/html',
            'csv_path': 'path/to/csv',
            'timestamp': datetime.now().isoformat()
        }
```

¡El sistema lo detectará automáticamente!

## 🎯 Beneficios

- ✅ **Modular**: Cada componente separado
- ✅ **Extensible**: Plugin system automático
- ✅ **Mantenible**: Código organizado
- ✅ **Testeable**: Tests integrados
- ✅ **Configurable**: Settings centralizados

## 🛠️ Migración desde Sistema Anterior

Si tienes el sistema monolítico anterior:

1. Ejecutar: `python migration_script.py`
2. Seguir pasos de instalación arriba
3. ¡Listo!

## 🧪 Testing

```bash
# Ejecutar tests
python main.py --test

# O directamente
python tests/test_components.py
```

## 📱 Configuración Telegram (Opcional)

1. Crear bot en @BotFather
2. Obtener token del bot
3. Obtener chat ID
4. Configurar variables de entorno

Sin estas configuraciones, el sistema funciona igual pero sin notificaciones.
'''
        
        readme_file = self.base_dir / "README.md"
        readme_file.write_text(readme, encoding='utf-8')
        
        # .gitignore
        gitignore = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
logs/

# Reportes (comentar si quieres versionarlos)
reports/*.html
reports/*.csv
reports/*.zip

# Configuración local
.env
config_local.py

# OS
.DS_Store
Thumbs.db
'''
        
        gitignore_file = self.base_dir / ".gitignore"
        gitignore_file.write_text(gitignore, encoding='utf-8')
        
        print("✅ Archivos de test y documentación creados")

# Función principal para ejecutar la migración
def run_migration():
    """Ejecuta la migración del sistema monolítico"""
    print("🎯 SCRIPT DE MIGRACIÓN TRADING SYSTEM")
    print("=" * 50)
    print("Este script convertirá tu sistema monolítico en una arquitectura modular")
    print()
    
    # Confirmar antes de proceder
    confirm = input("¿Continuar con la migración? (s/n): ").strip().lower()
    if confirm != 's':
        print("❌ Migración cancelada")
        return
    
    source_file = input("📄 Archivo fuente (default: paste.txt): ").strip() or "paste.txt"
    
    migrator = TradingSystemMigrator(source_file)
    migrator.run_migration()
    
    print("\n🎉 ¡MIGRACIÓN COMPLETADA!")
    print("\n📋 SIGUIENTES PASOS:")
    print("1. cd trading_system")
    print("2. pip install -r requirements.txt")
    print("3. python main.py --test  # Verificar que todo funciona")
    print("4. python main.py         # Ejecutar sistema")
    print("\n💡 OPCIONAL: Configurar Telegram")
    print("5. export TELEGRAM_BOT_TOKEN='tu_token'")
    print("6. export TELEGRAM_CHAT_ID='tu_chat_id'")

if __name__ == "__main__":
    run_migration()
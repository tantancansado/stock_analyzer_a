"""
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
        print("\n🌟 ANÁLISIS ULTRA MEJORADO")
        print("=" * 60)
        
        results = {}
        
        try:
            # Ejecutar cada analizador
            for name, analyzer in self.analyzers.items():
                if hasattr(analyzer, 'is_enabled') and not analyzer.is_enabled():
                    print(f"⏭️ Saltando {name} (deshabilitado)")
                    continue
                
                print(f"\n🔸 Ejecutando {name.upper()}")
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
            message += f"{status} **{name.title()}:**\n"
            
            if result.get('success'):
                if 'description' in result:
                    message += f"  {result['description']}\n"
            else:
                error = result.get('error', 'Error desconocido')
                message += f"  Error: {error[:100]}...\n"
            
            message += "\n"
        
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
            input("\nPresiona Enter para continuar...")
        
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
        print("\n📊 ANALIZADORES DISPONIBLES:")
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

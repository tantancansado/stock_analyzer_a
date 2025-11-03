"""
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
    
    print("\n🧪 Tests completados")

if __name__ == "__main__":
    run_all_tests()

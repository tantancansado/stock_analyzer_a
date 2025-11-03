"""
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

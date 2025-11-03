#!/usr/bin/env python3
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
        print("\n👋 Proceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        sys.exit(1)

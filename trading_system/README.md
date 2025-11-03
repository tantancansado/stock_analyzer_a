# Sistema Trading Unificado - Versión Modular

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

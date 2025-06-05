#!/usr/bin/env python3
"""
Script de diagnóstico para identificar y solucionar problemas en el sistema
"""

import os
import sys
import subprocess
import importlib
from datetime import datetime, timedelta
import json

class DiagnosticoSistema:
    def __init__(self):
        self.problemas = []
        self.advertencias = []
        self.info = []
        
    def agregar_problema(self, descripcion, solucion=None):
        self.problemas.append({
            'descripcion': descripcion,
            'solucion': solucion
        })
    
    def agregar_advertencia(self, descripcion):
        self.advertencias.append(descripcion)
    
    def agregar_info(self, descripcion):
        self.info.append(descripcion)
    
    def verificar_estructura_proyecto(self):
        """Verifica la estructura básica del proyecto"""
        print("🏗️ Verificando estructura del proyecto...")
        
        archivos_criticos = {
            'openinsider_scraper.py': 'Scraper principal de datos',
            'config.py': 'Configuración del sistema',
            'requirements.txt': 'Dependencias de Python'
        }
        
        directorios_criticos = {
            'reports': 'Directorio de reportes',
            'insiders': 'Módulo de análisis de insiders',
            'alerts': 'Módulo de alertas y notificaciones'
        }
        
        for archivo, descripcion in archivos_criticos.items():
            if os.path.exists(archivo):
                self.agregar_info(f"✅ {descripcion}: {archivo}")
            else:
                # Buscar en ubicaciones alternativas
                ubicaciones = [f"../{archivo}", f"src/{archivo}"]
                encontrado = False
                
                for ubicacion in ubicaciones:
                    if os.path.exists(ubicacion):
                        self.agregar_advertencia(f"⚠️ {descripcion} en ubicación no estándar: {ubicacion}")
                        encontrado = True
                        break
                
                if not encontrado:
                    if archivo == 'requirements.txt':
                        self.agregar_advertencia(f"⚠️ {descripcion} no encontrado (opcional)")
                    else:
                        self.agregar_problema(f"❌ {descripcion} no encontrado", f"Crear archivo: {archivo}")
        
        for directorio, descripcion in directorios_criticos.items():
            if os.path.exists(directorio):
                self.agregar_info(f"✅ {descripcion}: {directorio}/")
            else:
                self.agregar_advertencia(f"⚠️ {descripcion} no existe (se creará automáticamente)")
    
    def verificar_dependencias_python(self):
        """Verifica las dependencias de Python"""
        print("🐍 Verificando dependencias de Python...")
        
        dependencias_criticas = [
            ('pandas', 'Procesamiento de datos'),
            ('numpy', 'Cálculos numéricos'),
            ('requests', 'Peticiones HTTP'),
            ('beautifulsoup4', 'Parsing HTML')
        ]
        
        dependencias_opcionales = [
            ('matplotlib', 'Generación de gráficos'),
            ('yfinance', 'Datos financieros'),
            ('python-telegram-bot', 'Bot de Telegram'),
            ('plotly', 'Gráficos interactivos')
        ]
        
        for modulo, descripcion in dependencias_criticas:
            try:
                importlib.import_module(modulo)
                self.agregar_info(f"✅ {descripcion}: {modulo}")
            except ImportError:
                self.agregar_problema(
                    f"❌ {descripcion} no disponible: {modulo}",
                    f"pip install {modulo}"
                )
        
        for modulo, descripcion in dependencias_opcionales:
            try:
                importlib.import_module(modulo)
                self.agregar_info(f"✅ {descripcion}: {modulo}")
            except ImportError:
                self.agregar_advertencia(f"⚠️ {descripcion} no disponible: {modulo} (opcional)")
    
    def verificar_configuracion(self):
        """Verifica la configuración del sistema"""
        print("⚙️ Verificando configuración...")
        
        try:
            import config
            self.agregar_info("✅ Archivo config.py importado correctamente")
            
            # Verificar Telegram
            if hasattr(config, 'TELEGRAM_BOT_TOKEN') and hasattr(config, 'TELEGRAM_CHAT_ID'):
                if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
                    self.agregar_info("✅ Configuración de Telegram completa")
                else:
                    self.agregar_advertencia("⚠️ Configuración de Telegram incompleta")
            else:
                self.agregar_problema(
                    "❌ Variables de Telegram no encontradas en config.py",
                    "Agregar TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID a config.py"
                )
            
            # Verificar API keys
            if hasattr(config, 'ALPHA_VANTAGE_API_KEY'):
                if config.ALPHA_VANTAGE_API_KEY and config.ALPHA_VANTAGE_API_KEY != "TU_API_KEY_AQUI":
                    self.agregar_info("✅ API key de Alpha Vantage configurada")
                else:
                    self.agregar_advertencia("⚠️ API key de Alpha Vantage no configurada (se usarán datos simulados)")
            
        except ImportError:
            self.agregar_problema(
                "❌ No se puede importar config.py",
                "Crear archivo config.py con las variables necesarias"
            )
    
    def verificar_datos_existentes(self):
        """Verifica los datos existentes"""
        print("📊 Verificando datos existentes...")
        
        archivos_datos = {
            'reports/insiders_daily.csv': 'Datos de insiders diarios',
            'reports/finviz_ml_dataset_with_fundamentals.csv': 'Datos fundamentales',
            'reports/insiders_opportunities.csv': 'Oportunidades identificadas'
        }
        
        for archivo, descripcion in archivos_datos.items():
            if os.path.exists(archivo):
                try:
                    stat = os.stat(archivo)
                    size = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    hours_old = (datetime.now() - mtime).total_seconds() / 3600
                    
                    if hours_old > 24:
                        self.agregar_advertencia(f"⚠️ {descripcion} tiene más de 24 horas ({hours_old:.1f}h)")
                    else:
                        self.agregar_info(f"✅ {descripcion}: {size:,} bytes, {hours_old:.1f}h")
                        
                except Exception as e:
                    self.agregar_advertencia(f"⚠️ Error leyendo {archivo}: {e}")
            else:
                if archivo == 'reports/insiders_daily.csv':
                    self.agregar_problema(
                        f"❌ {descripcion} no encontrado",
                        "Ejecutar scraper: python openinsider_scraper.py"
                    )
                else:
                    self.agregar_advertencia(f"⚠️ {descripcion} no encontrado (se generará)")
    
    def verificar_permisos(self):
        """Verifica permisos de archivos y directorios"""
        print("🔐 Verificando permisos...")
        
        directorios_escribir = ['reports', 'logs', 'reports/graphs']
        
        for directorio in directorios_escribir:
            if os.path.exists(directorio):
                if os.access(directorio, os.W_OK):
                    self.agregar_info(f"✅ Permisos de escritura en {directorio}/")
                else:
                    self.agregar_problema(
                        f"❌ Sin permisos de escritura en {directorio}/",
                        f"chmod 755 {directorio}"
                    )
            else:
                # Verificar si podemos crear el directorio
                try:
                    os.makedirs(directorio, exist_ok=True)
                    self.agregar_info(f"✅ Directorio {directorio}/ creado")
                except PermissionError:
                    self.agregar_problema(
                        f"❌ No se puede crear {directorio}/",
                        f"Verificar permisos del directorio padre"
                    )
    
    def verificar_conexion_internet(self):
        """Verifica la conexión a internet y APIs"""
        print("🌐 Verificando conexión a internet...")
        
        urls_test = [
            ('http://openinsider.com', 'OpenInsider'),
            ('https://www.alphavantage.co', 'Alpha Vantage'),
            ('https://api.telegram.org', 'Telegram API')
        ]
        
        import requests
        
        for url, descripcion in urls_test:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    self.agregar_info(f"✅ Conexión a {descripcion}: OK")
                else:
                    self.agregar_advertencia(f"⚠️ {descripcion} respondió con código {response.status_code}")
            except requests.RequestException as e:
                self.agregar_problema(
                    f"❌ No se puede conectar a {descripcion}",
                    "Verificar conexión a internet o firewall"
                )
    
    def verificar_procesos_activos(self):
        """Verifica si hay procesos del sistema ejecutándose"""
        print("🔄 Verificando procesos activos...")
        
        try:
            # Buscar procesos relacionados
            result = subprocess.run(['pgrep', '-f', 'insider_tracker|openinsider_scraper'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                self.agregar_advertencia(f"⚠️ Procesos activos encontrados: PIDs {', '.join(pids)}")
            else:
                self.agregar_info("✅ No hay procesos activos del sistema")
                
        except FileNotFoundError:
            # pgrep no disponible (Windows)
            self.agregar_info("ℹ️ Verificación de procesos no disponible en este sistema")
    
    def verificar_cron(self):
        """Verifica la configuración de cron"""
        print("🕒 Verificando configuración de cron...")
        
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            
            if result.returncode == 0:
                crontab_content = result.stdout
                
                if 'insider' in crontab_content.lower() or 'stock_analyzer' in crontab_content.lower():
                    self.agregar_info("✅ Configuración de cron encontrada")
                    
                    # Mostrar las líneas relevantes
                    relevant_lines = [line for line in crontab_content.split('\n') 
                                    if 'insider' in line.lower() or 'stock_analyzer' in line.lower()]
                    for line in relevant_lines:
                        self.agregar_info(f"   📅 {line}")
                else:
                    self.agregar_advertencia("⚠️ No se encontró configuración de cron para el proyecto")
            else:
                self.agregar_advertencia("⚠️ No hay crontab configurado")
                
        except FileNotFoundError:
            self.agregar_info("ℹ️ Cron no disponible en este sistema")
    
    def generar_script_reparacion(self):
        """Genera un script para reparar problemas automáticamente"""
        script_content = """#!/bin/bash
# Script de reparación automática generado por diagnóstico

echo "🔧 REPARANDO PROBLEMAS DETECTADOS..."

"""
        
        for problema in self.problemas:
            if problema['solucion']:
                if 'pip install' in problema['solucion']:
                    script_content += f"echo \"📦 Instalando dependencia...\"\n"
                    script_content += f"{problema['solucion']}\n\n"
                elif 'chmod' in problema['solucion']:
                    script_content += f"echo \"🔐 Arreglando permisos...\"\n"
                    script_content += f"{problema['solucion']}\n\n"
                elif 'mkdir' in problema['solucion']:
                    script_content += f"echo \"📁 Creando directorio...\"\n"
                    script_content += f"{problema['solucion']}\n\n"
        
        script_content += """
echo "✅ Reparación completada"
echo "🔄 Ejecuta el diagnóstico nuevamente para verificar"
"""
        
        with open('reparar_sistema.sh', 'w') as f:
            f.write(script_content)
        
        os.chmod('reparar_sistema.sh', 0o755)
        self.agregar_info("✅ Script de reparación generado: reparar_sistema.sh")
    
    def ejecutar_diagnostico_completo(self):
        """Ejecuta todas las verificaciones"""
        print("🔍 INICIANDO DIAGNÓSTICO COMPLETO DEL SISTEMA")
        print("=" * 60)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Ejecutar todas las verificaciones
        self.verificar_estructura_proyecto()
        print()
        
        self.verificar_dependencias_python()
        print()
        
        self.verificar_configuracion()
        print()
        
        self.verificar_datos_existentes()
        print()
        
        self.verificar_permisos()
        print()
        
        self.verificar_conexion_internet()
        print()
        
        self.verificar_procesos_activos()
        print()
        
        self.verificar_cron()
        print()
        
        # Mostrar resumen
        self.mostrar_resumen()
        
        # Generar script de reparación si hay problemas
        if self.problemas:
            self.generar_script_reparacion()
    
    def mostrar_resumen(self):
        """Muestra el resumen del diagnóstico"""
        print("\n" + "=" * 60)
        print("📋 RESUMEN DEL DIAGNÓSTICO")
        print("=" * 60)
        
        # Estadísticas
        total_checks = len(self.info) + len(self.advertencias) + len(self.problemas)
        print(f"📊 Total de verificaciones: {total_checks}")
        print(f"✅ Correctas: {len(self.info)}")
        print(f"⚠️ Advertencias: {len(self.advertencias)}")
        print(f"❌ Problemas críticos: {len(self.problemas)}")
        print()
        
        # Mostrar problemas críticos
        if self.problemas:
            print("🚨 PROBLEMAS CRÍTICOS QUE REQUIEREN ATENCIÓN:")
            print("-" * 50)
            for i, problema in enumerate(self.problemas, 1):
                print(f"{i}. {problema['descripcion']}")
                if problema['solucion']:
                    print(f"   🔧 Solución: {problema['solucion']}")
                print()
        
        # Mostrar advertencias
        if self.advertencias:
            print("⚠️ ADVERTENCIAS (opcionales pero recomendadas):")
            print("-" * 50)
            for i, advertencia in enumerate(self.advertencias, 1):
                print(f"{i}. {advertencia}")
            print()
        
        # Estado general
        if not self.problemas:
            if not self.advertencias:
                print("🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!")
                print("✅ Todos los componentes están configurados correctamente")
            else:
                print("✅ SISTEMA FUNCIONAL CON ADVERTENCIAS MENORES")
                print("💡 El sistema debería funcionar, pero revisa las advertencias")
        else:
            print("❌ SISTEMA CON PROBLEMAS CRÍTICOS")
            print("🔧 Requiere atención antes de poder funcionar correctamente")
            
            if os.path.exists('reparar_sistema.sh'):
                print("💡 Ejecuta: ./reparar_sistema.sh para reparar algunos problemas automáticamente")
        
        print("\n" + "=" * 60)
    
    def generar_reporte_json(self):
        """Genera un reporte en formato JSON"""
        reporte = {
            'timestamp': datetime.now().isoformat(),
            'resumen': {
                'total_verificaciones': len(self.info) + len(self.advertencias) + len(self.problemas),
                'correctas': len(self.info),
                'advertencias': len(self.advertencias),
                'problemas_criticos': len(self.problemas)
            },
            'estado_general': 'OK' if not self.problemas else 'ERROR',
            'problemas': self.problemas,
            'advertencias': self.advertencias,
            'info': self.info
        }
        
        with open('diagnostico_reporte.json', 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        
        print("📄 Reporte JSON generado: diagnostico_reporte.json")

def test_scraper():
    """Prueba específica del scraper"""
    print("🧪 PROBANDO SCRAPER DE OPENINSIDER")
    print("=" * 40)
    
    if not os.path.exists('openinsider_scraper.py'):
        print("❌ openinsider_scraper.py no encontrado")
        return False
    
    try:
        print("🚀 Ejecutando scraper...")
        result = subprocess.run([
            sys.executable, 'openinsider_scraper.py'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Scraper ejecutado exitosamente")
            print("📊 Output:")
            print(result.stdout[-500:])  # Últimas 500 caracteres
            
            # Verificar CSV generado
            if os.path.exists('reports/insiders_daily.csv'):
                print("✅ CSV generado correctamente")
                
                # Verificar contenido
                try:
                    import pandas as pd
                    df = pd.read_csv('reports/insiders_daily.csv')
                    print(f"📋 Filas en CSV: {len(df)}")
                    print(f"📋 Columnas: {list(df.columns)}")
                    
                    if len(df) > 0:
                        print("✅ CSV contiene datos")
                    else:
                        print("⚠️ CSV está vacío")
                        
                except Exception as e:
                    print(f"⚠️ Error leyendo CSV: {e}")
            else:
                print("❌ CSV no se generó")
                
            return True
        else:
            print(f"❌ Scraper falló (código: {result.returncode})")
            print("📋 Error output:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Scraper tardó más de 5 minutos (timeout)")
        return False
    except Exception as e:
        print(f"❌ Error ejecutando scraper: {e}")
        return False

def test_analisis():
    """Prueba específica del análisis"""
    print("🧪 PROBANDO ANÁLISIS DE OPORTUNIDADES")
    print("=" * 45)
    
    # Verificar que existe el CSV
    if not os.path.exists('reports/insiders_daily.csv'):
        print("❌ reports/insiders_daily.csv no encontrado")
        print("   Ejecuta primero el scraper")
        return False
    
    # Buscar insider_tracker.py
    tracker_paths = [
        'insiders/insider_tracker.py',
        'insider_tracker.py'
    ]
    
    tracker_path = None
    for path in tracker_paths:
        if os.path.exists(path):
            tracker_path = path
            break
    
    if not tracker_path:
        print("❌ insider_tracker.py no encontrado")
        return False
    
    try:
        print(f"🚀 Ejecutando: python {tracker_path} --solo-oportunidades")
        result = subprocess.run([
            sys.executable, tracker_path, '--solo-oportunidades'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Análisis ejecutado exitosamente")
            
            # Verificar archivos generados
            archivos_esperados = [
                'reports/insiders_opportunities.csv',
                'reports/insiders_opportunities.html'
            ]
            
            for archivo in archivos_esperados:
                if os.path.exists(archivo):
                    size = os.path.getsize(archivo)
                    print(f"✅ {archivo}: {size:,} bytes")
                else:
                    print(f"⚠️ {archivo}: No generado")
            
            return True
        else:
            print(f"❌ Análisis falló (código: {result.returncode})")
            print("📋 Error output:")
            print(result.stderr[-500:])
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Análisis tardó más de 10 minutos (timeout)")
        return False
    except Exception as e:
        print(f"❌ Error ejecutando análisis: {e}")
        return False

def test_telegram():
    """Prueba específica de Telegram"""
    print("🧪 PROBANDO CONFIGURACIÓN DE TELEGRAM")
    print("=" * 45)
    
    try:
        from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("❌ Variables de Telegram no configuradas")
            return False
        
        print(f"✅ Token: {TELEGRAM_BOT_TOKEN[:8]}...")
        print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
        
        # Probar envío
        try:
            from alerts.telegram_utils import send_message
            
            test_message = f"🧪 Test de diagnóstico - {datetime.now().strftime('%H:%M:%S')}"
            send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, test_message)
            print("✅ Mensaje de prueba enviado correctamente")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Error importando configuración: {e}")
        return False

def crear_config_template():
    """Crea un archivo config.py de ejemplo"""
    config_template = '''# Configuración del sistema de análisis de insider trading

# Configuración de Telegram
TELEGRAM_BOT_TOKEN = "tu_bot_token_aqui"
TELEGRAM_CHAT_ID = "tu_chat_id_aqui"

# API Keys
ALPHA_VANTAGE_API_KEY = "tu_api_key_aqui"

# Configuración de GitHub Pages (opcional)
GITHUB_USERNAME = "tu_usuario_github"
GITHUB_REPO = "tu_repositorio"

# Configuración de notificaciones
EMAIL_NOTIFICATIONS = "tu_email@ejemplo.com"  # Opcional

# Configuración de logging
LOG_LEVEL = "INFO"
MAX_LOG_FILES = 30

# Configuración de datos
DATA_RETENTION_DAYS = 90
MAX_OPPORTUNITIES = 50
MIN_TRANSACTION_VALUE = 10000

# URLs de APIs (no cambiar a menos que sepas lo que haces)
OPENINSIDER_BASE_URL = "http://openinsider.com"
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
'''
    
    if not os.path.exists('config.py'):
        with open('config.py', 'w') as f:
            f.write(config_template)
        print("✅ Archivo config.py creado con valores de ejemplo")
        print("🔧 Edita config.py con tus valores reales")
    else:
        print("ℹ️ config.py ya existe")

def main():
    """Función principal del diagnóstico"""
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        
        if comando == "--scraper":
            test_scraper()
        elif comando == "--analisis":
            test_analisis()
        elif comando == "--telegram":
            test_telegram()
        elif comando == "--crear-config":
            crear_config_template()
        elif comando == "--rapido":
            # Diagnóstico rápido (solo lo esencial)
            diagnostico = DiagnosticoSistema()
            diagnostico.verificar_estructura_proyecto()
            diagnostico.verificar_dependencias_python()
            diagnostico.verificar_configuracion()
            diagnostico.mostrar_resumen()
        elif comando == "--help":
            print("""
🔍 DIAGNÓSTICO DEL SISTEMA DE INSIDER TRADING

Uso: python diagnostico_sistema.py [opción]

Opciones:
  (sin opción)    Diagnóstico completo
  --scraper      Probar solo el scraper
  --analisis     Probar solo el análisis
  --telegram     Probar solo Telegram
  --crear-config Crear archivo config.py de ejemplo
  --rapido       Diagnóstico rápido (solo esencial)
  --help         Mostrar esta ayuda

Ejemplos:
  python diagnostico_sistema.py
  python diagnostico_sistema.py --scraper
  python diagnostico_sistema.py --crear-config
            """)
        else:
            print(f"❌ Opción no reconocida: {comando}")
            print("   Usa --help para ver opciones disponibles")
    else:
        # Diagnóstico completo
        diagnostico = DiagnosticoSistema()
        diagnostico.ejecutar_diagnostico_completo()
        diagnostico.generar_reporte_json()

if __name__ == "__main__":
    main()
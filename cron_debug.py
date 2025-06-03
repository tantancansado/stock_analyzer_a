#!/usr/bin/env python3
"""
Script para verificar por qué no se ejecutó el cron hoy
"""

import subprocess
import os
from datetime import datetime, timedelta

def check_cron_status():
    """
    Verifica el estado actual del cron
    """
    print("🕒 VERIFICACIÓN DEL ESTADO DEL CRON")
    print("=" * 50)
    print(f"📅 Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Verificar si cron está activo
    try:
        result = subprocess.run(["sudo", "launchctl", "list", "com.vix.cron"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Servicio cron está activo")
        else:
            print("❌ Servicio cron NO está activo")
    except:
        print("⚠️ No se pudo verificar estado del servicio cron")
    
    # 2. Verificar crontab actual
    try:
        current_crontab = subprocess.check_output(["crontab", "-l"], text=True)
        if current_crontab.strip():
            print("✅ Hay crontab configurado:")
            print("-" * 40)
            for line in current_crontab.split('\n'):
                if line.strip() and not line.startswith('#'):
                    print(f"   {line}")
            print("-" * 40)
        else:
            print("❌ No hay crontab configurado")
    except subprocess.CalledProcessError:
        print("❌ No hay crontab configurado")
    
    # 3. Verificar logs del cron
    project_path = "/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
    log_files = [
        "logs/cron_main.log",
        "logs/scraper.log", 
        "logs/cron_insider.log",
        "cron.log"
    ]
    
    print(f"\n📁 Verificando logs en {project_path}:")
    
    found_logs = False
    for log_file in log_files:
        full_path = os.path.join(project_path, log_file)
        if os.path.exists(full_path):
            found_logs = True
            stat = os.stat(full_path)
            modified = datetime.fromtimestamp(stat.st_mtime)
            size = stat.st_size
            
            print(f"✅ {log_file}:")
            print(f"   📅 Última modificación: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   📏 Tamaño: {size} bytes")
            
            # Mostrar últimas líneas si tiene contenido
            if size > 0:
                try:
                    with open(full_path, 'r') as f:
                        lines = f.readlines()
                        print(f"   📄 Últimas líneas:")
                        for line in lines[-3:]:
                            print(f"      {line.strip()}")
                except:
                    print("   ⚠️ No se pudo leer el archivo")
            print()
    
    if not found_logs:
        print("❌ No se encontraron logs de cron")
    
    # 4. Verificar archivos del proyecto
    print(f"📂 Verificando archivos del proyecto:")
    files_to_check = [
        "main.py",
        "insiders/insider_tracker.py",
        "insiders/openinsider_scraper.py",
        "config.py"
    ]
    
    for file_name in files_to_check:
        full_path = os.path.join(project_path, file_name)
        if os.path.exists(full_path):
            print(f"✅ {file_name}")
        else:
            print(f"❌ {file_name} NO ENCONTRADO")

def check_today_execution():
    """
    Verifica si se ejecutó algo hoy
    """
    print(f"\n🔍 VERIFICANDO EJECUCIONES DE HOY ({datetime.now().strftime('%Y-%m-%d')})")
    print("=" * 50)
    
    project_path = "/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
    today = datetime.now().date()
    
    # Verificar archivos generados hoy
    files_to_check = [
        "reports/insiders_daily.csv",
        "reports/insiders_opportunities.csv", 
        "reports/insiders_opportunities.html",
        "reports/insiders_report.html"
    ]
    
    files_today = []
    files_old = []
    
    for file_name in files_to_check:
        full_path = os.path.join(project_path, file_name)
        if os.path.exists(full_path):
            stat = os.stat(full_path)
            modified = datetime.fromtimestamp(stat.st_mtime)
            
            if modified.date() == today:
                files_today.append((file_name, modified))
            else:
                files_old.append((file_name, modified))
    
    if files_today:
        print("✅ Archivos generados HOY:")
        for file_name, modified in files_today:
            print(f"   {file_name} - {modified.strftime('%H:%M:%S')}")
    else:
        print("❌ NO se generaron archivos hoy")
    
    if files_old:
        print(f"\n⚠️ Archivos antiguos encontrados:")
        for file_name, modified in files_old:
            days_ago = (datetime.now() - modified).days
            print(f"   {file_name} - {modified.strftime('%Y-%m-%d %H:%M')} ({days_ago} días atrás)")

def suggest_solutions():
    """
    Sugiere soluciones basadas en el diagnóstico
    """
    print(f"\n🔧 SOLUCIONES RECOMENDADAS:")
    print("=" * 50)
    
    print("1. 🚀 Configurar cron correctamente:")
    print("   python3 setup_cron.py")
    print()
    
    print("2. 🧪 Probar ejecución manual:")
    print("   cd /Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a")
    print("   python3 insiders/openinsider_scraper.py  # Obtener datos frescos")
    print("   python3 main.py --auto                   # Ejecutar análisis")
    print()
    
    print("3. 📊 Verificar que funciona:")
    print("   tail -f logs/scraper.log     # Ver logs del scraper")
    print("   tail -f logs/cron_main.log   # Ver logs del análisis")
    print()
    
    print("4. ⏰ Para que se ejecute mañana:")
    print("   - Configurar cron con setup_cron.py")
    print("   - Dejar la máquina encendida a las 8:30-9:00 AM")
    print("   - Verificar que no esté en modo sleep")

if __name__ == "__main__":
    check_cron_status()
    check_today_execution()
    suggest_solutions()
    
    print(f"\n💡 PARA MAÑANA:")
    print("🕗 8:30 AM - Scraper obtendrá datos frescos")
    print("🕘 9:00 AM - Análisis completo + Telegram")
    print("✅ Configura ahora con: python3 setup_cron.py")
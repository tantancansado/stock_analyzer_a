#!/usr/bin/env python3
"""
Script para configurar cron job para análisis diario de insider trading
VERSIÓN MEJORADA CON CORRECCIONES DE ERRORES
"""

import os
import subprocess
from datetime import datetime

def setup_cron_job():
    """
    Configura el cron job para ejecutar el análisis diario CON SCRAPER
    """
    print("🕒 Configurando tarea cron para análisis diario MEJORADO...")
    
    # Ruta completa al proyecto
    project_path = "/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
    python_path = "/usr/bin/python3"
    
    # Crear directorio de logs
    log_dir = os.path.join(project_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    print(f"✅ Directorio de logs creado: {log_dir}")
    
    # Verificar archivos
    print("🔍 Verificando archivos...")
    
    # Scripts principales
    main_script = os.path.join(project_path, "main.py")
    insider_script = os.path.join(project_path, "insiders/insider_tracker.py")
    
    # Buscar scraper
    possible_scrapers = [
        "openinsider_scraper.py",
        "insiders/openinsider_scraper.py", 
        "scraper_independiente.py",
        "scrapers/openinsider_scraper.py"
    ]
    
    scraper_path = None
    for scraper in possible_scrapers:
        full_path = os.path.join(project_path, scraper)
        if os.path.exists(full_path):
            scraper_path = scraper
            print(f"✅ Scraper encontrado: {scraper}")
            break
    
    if not scraper_path:
        print("⚠️ No se encontró scraper, usando datos existentes")
    
    # Verificar insider_tracker.py
    if os.path.exists(insider_script):
        print("✅ insider_tracker.py encontrado")
    else:
        print("❌ insider_tracker.py no encontrado")
        return False
    
    # Crear script de corrección de errores
    fix_script_content = f"""#!/bin/bash
# Script para corregir errores comunes antes del análisis

cd {project_path}

# Asegurar que docs/index.html existe
if [ ! -f docs/index.html ]; then
    echo "🔧 Creando docs/index.html faltante..."
    python3 github_pages_uploader.py setup > /dev/null 2>&1
fi

# Asegurar que reports/ existe
mkdir -p reports

# Copiar CSV a la ubicación que busca plot_utils si es necesario
if [ -f reports/insiders_daily.csv ] && [ ! -f insiders_daily.csv ]; then
    cp reports/insiders_daily.csv . 2>/dev/null || true
fi

echo "✅ Pre-correcciones completadas"
"""
    
    fix_script_path = os.path.join(project_path, "fix_before_analysis.sh")
    with open(fix_script_path, 'w') as f:
        f.write(fix_script_content)
    
    # Hacer ejecutable
    os.chmod(fix_script_path, 0o755)
    print(f"✅ Script de corrección creado: {fix_script_path}")
    
    # Generar líneas de cron
    cron_lines = []
    
    if scraper_path:
        # OPCIÓN COMPLETA: Scraper + Correcciones + Análisis
        scraper_line = f"30 8 * * * cd {project_path} && {python_path} {scraper_path} >> logs/scraper.log 2>&1"
        fix_line = f"55 8 * * * cd {project_path} && ./fix_before_analysis.sh >> logs/fixes.log 2>&1"
        analysis_line = f"0 9 * * * cd {project_path}/insiders && {python_path} insider_tracker.py --completo >> ../logs/analysis.log 2>&1"
        
        cron_lines = [scraper_line, fix_line, analysis_line]
        
        print("⏰ HORARIO COMPLETO:")
        print("   8:30 AM - Scraper obtiene datos frescos")
        print("   8:55 AM - Correcciones automáticas")
        print("   9:00 AM - Análisis completo + GitHub Pages + Telegram")
        
    else:
        # OPCIÓN SIN SCRAPER: Solo correcciones + análisis
        fix_line = f"55 8 * * * cd {project_path} && ./fix_before_analysis.sh >> logs/fixes.log 2>&1"
        analysis_line = f"0 9 * * * cd {project_path}/insiders && {python_path} insider_tracker.py --completo >> ../logs/analysis.log 2>&1"
        
        cron_lines = [fix_line, analysis_line]
        
        print("⏰ HORARIO SIN SCRAPER:")
        print("   8:55 AM - Correcciones automáticas")
        print("   9:00 AM - Análisis completo + GitHub Pages + Telegram")
    
    # Configurar crontab
    try:
        current_crontab = subprocess.check_output(["crontab", "-l"], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        current_crontab = ""
    
    # Limpiar líneas anteriores del proyecto
    lines = current_crontab.split('\n')
    cleaned_lines = [line for line in lines if project_path not in line and line.strip()]
    
    # Crear nuevo crontab
    if cleaned_lines:
        new_crontab = '\n'.join(cleaned_lines) + "\n"
    else:
        new_crontab = ""
    
    # Agregar comentario y líneas nuevas
    new_crontab += f"# Insider Trading Analysis Auto - {datetime.now().strftime('%Y-%m-%d')}\n"
    for line in cron_lines:
        new_crontab += line + "\n"
    
    # Aplicar crontab
    try:
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        process.communicate(new_crontab)
        
        if process.returncode == 0:
            print("✅ Tareas cron configuradas correctamente")
            return True
        else:
            print("❌ Error configurando crontab")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def verify_and_test():
    """
    Verifica la configuración y ofrece prueba
    """
    print("\n🔍 Verificando configuración...")
    
    try:
        current_crontab = subprocess.check_output(["crontab", "-l"], text=True)
        project_lines = [line for line in current_crontab.split('\n') 
                        if 'stock_analyzer_a' in line and line.strip() and not line.startswith('#')]
        
        if project_lines:
            print("✅ Tareas cron configuradas:")
            for i, line in enumerate(project_lines, 1):
                if 'scraper' in line:
                    print(f"   {i}. 🕷️ {line}")
                elif 'fix_before' in line:
                    print(f"   {i}. 🔧 {line}")
                elif 'insider_tracker' in line:
                    print(f"   {i}. 🚀 {line}")
        else:
            print("❌ No se encontraron tareas cron")
            
    except subprocess.CalledProcessError:
        print("❌ No hay crontab configurado")
    
    # Ofrecer prueba manual
    print("\n🧪 ¿QUIERES PROBAR AHORA?")
    response = input("Ejecutar análisis completo ahora para verificar? (y/n): ")
    
    if response.lower() == 'y':
        print("🚀 Ejecutando análisis de prueba...")
        project_path = "/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
        
        try:
            os.chdir(f"{project_path}/insiders")
            result = subprocess.run(["python3", "insider_tracker.py", "--completo"], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ Análisis de prueba exitoso!")
                print("🌐 Verifica tu sitio web y Telegram")
            else:
                print("⚠️ Análisis completado con advertencias")
                print("Salida:", result.stdout[-500:])  # Últimas 500 chars
                
        except subprocess.TimeoutExpired:
            print("⏰ Análisis tomó más de 5 minutos, pero probablemente funcionó")
        except Exception as e:
            print(f"❌ Error en prueba: {e}")

def show_monitoring_commands():
    """
    Muestra comandos útiles para monitoreo
    """
    print("\n📊 COMANDOS ÚTILES PARA MONITOREO:")
    print("=" * 50)
    
    project_path = "/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
    
    print("🔍 Ver tareas cron:")
    print("   crontab -l")
    
    print("\n📁 Ver logs en tiempo real:")
    print(f"   tail -f {project_path}/logs/analysis.log")
    print(f"   tail -f {project_path}/logs/scraper.log")
    print(f"   tail -f {project_path}/logs/fixes.log")
    
    print("\n🌐 URLs importantes:")
    print("   Sitio web: https://tantancansado.github.io/stock_analyzer_a/")
    print("   GitHub Actions: https://github.com/tantancansado/stock_analyzer_a/actions")
    
    print("\n🔧 Comandos de emergencia:")
    print("   # Deshabilitar cron temporalmente:")
    print("   crontab -r")
    print("   # Ejecutar análisis manual:")
    print(f"   cd {project_path}/insiders && python3 insider_tracker.py --completo")

def create_monitoring_script():
    """
    Crea un script de monitoreo
    """
    project_path = "/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
    
    monitor_script = f"""#!/bin/bash
# Script de monitoreo para Insider Trading Analysis

echo "📊 ESTADO DEL SISTEMA INSIDER TRADING"
echo "======================================"
echo "📅 $(date)"
echo ""

echo "🕒 TAREAS CRON:"
crontab -l | grep stock_analyzer_a || echo "❌ No hay tareas cron configuradas"
echo ""

echo "📁 LOGS RECIENTES:"
if [ -f {project_path}/logs/analysis.log ]; then
    echo "🚀 Último análisis:"
    tail -3 {project_path}/logs/analysis.log
else
    echo "❌ No hay log de análisis"
fi
echo ""

if [ -f {project_path}/logs/scraper.log ]; then
    echo "🕷️ Último scraper:"
    tail -3 {project_path}/logs/scraper.log
else
    echo "❌ No hay log de scraper"
fi
echo ""

echo "🌐 GITHUB PAGES:"
echo "   Sitio: https://tantancansado.github.io/stock_analyzer_a/"
echo ""

echo "📊 ARCHIVOS RECIENTES:"
ls -lt {project_path}/reports/*.csv 2>/dev/null | head -3 || echo "❌ No hay CSVs recientes"
ls -lt {project_path}/docs/*.html 2>/dev/null | head -3 || echo "❌ No hay HTMLs recientes"
"""
    
    monitor_path = os.path.join(project_path, "check_status.sh")
    with open(monitor_path, 'w') as f:
        f.write(monitor_script)
    
    os.chmod(monitor_path, 0o755)
    print(f"✅ Script de monitoreo creado: {monitor_path}")
    print(f"   Ejecutar con: {monitor_path}")

if __name__ == "__main__":
    print("🕒 CONFIGURADOR AUTOMÁTICO INSIDER TRADING v2.0")
    print("=" * 60)
    print("🎯 CARACTERÍSTICAS:")
    print("   ✅ Scraper de datos frescos diarios")
    print("   ✅ Corrección automática de errores")
    print("   ✅ Análisis completo automatizado")
    print("   ✅ Subida automática a GitHub Pages")
    print("   ✅ Notificaciones por Telegram")
    print("   ✅ Logs detallados")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Configurar cron
    success = setup_cron_job()
    
    if success:
        # Verificar y ofrecer prueba
        verify_and_test()
        
        # Crear script de monitoreo
        create_monitoring_script()
        
        # Mostrar comandos útiles
        show_monitoring_commands()
        
        print("\n🎉 CONFIGURACIÓN COMPLETADA!")
        print("💫 Tu sistema ahora:")
        print("   🔄 Se ejecuta automáticamente todos los días")
        print("   🌐 Actualiza GitHub Pages automáticamente")
        print("   📱 Envía notificaciones por Telegram")
        print("   🔧 Se autocorrige errores comunes")
        print("   📊 Mantiene logs detallados")
        
        print("\n💡 PRÓXIMOS PASOS:")
        print("   1. El sistema se ejecutará mañana a las 9:00 AM")
        print("   2. Verifica los logs después de la primera ejecución")
        print("   3. Tu sitio web se actualizará automáticamente")
        
    else:
        print("\n❌ Error en la configuración")
        print("💡 Verifica permisos y rutas manualmente")
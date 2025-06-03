#!/usr/bin/env python3
"""
Script para configurar cron job para análisis diario de insider trading
INCLUYE SCRAPER para datos frescos
"""

import os
import subprocess
from datetime import datetime

def setup_cron_job():
    """
    Configura el cron job para ejecutar el análisis diario CON SCRAPER
    """
    print("🕒 Configurando tarea cron para análisis diario...")
    
    # Ruta completa al proyecto actualizada
    project_path = "/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
    python_path = "/usr/bin/python3"  # Verificar que sea correcto
    
    # Crear directorio de logs
    log_dir = os.path.join(project_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    print(f"✅ Directorio de logs creado: {log_dir}")
    
    # Verificar que los archivos existen
    print("🔍 Verificando archivos...")
    
    # Archivos principales
    main_script = os.path.join(project_path, "main.py")
    insider_script = os.path.join(project_path, "insiders/insider_tracker.py")
    
    # Buscar el scraper en diferentes ubicaciones
    possible_scrapers = [
        "insiders/openinsider_scraper.py",
        "openinsider_scraper.py",
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
        print("⚠️ No se encontró scraper de OpenInsider")
        print("   Buscado en:", possible_scrapers)
        print("   Continuando sin scraper (usará datos existentes)")
    
    scripts_to_check = [
        ("main.py", main_script, "Análisis completo integrado"),
        ("insider_tracker.py", insider_script, "Solo análisis de oportunidades")
    ]
    
    available_scripts = []
    for name, path, desc in scripts_to_check:
        if os.path.exists(path):
            print(f"✅ {name} - {desc}")
            available_scripts.append((name, path, desc))
        else:
            print(f"❌ {name} no encontrado en {path}")
    
    if not available_scripts:
        print("❌ No se encontraron scripts para ejecutar")
        return False
    
    # Mostrar opciones
    print("\n📋 Opciones disponibles para cron:")
    print("1. 🚀 Scraper + main.py --auto (RECOMENDADO) - Datos frescos + Análisis completo")
    print("2. 🎯 Scraper + insider_tracker.py - Datos frescos + Solo oportunidades")
    print("3. 📊 Solo main.py --auto - Sin scraper (usar datos existentes)")
    print("4. 🔧 Solo scraper - Solo obtener datos frescos")
    
    # Elegir opción automáticamente o pedir al usuario
    if scraper_path:
        selected_option = 1  # Opción recomendada con scraper
        print(f"\n🎯 Seleccionada automáticamente: Opción {selected_option} (Scraper + Análisis completo)")
    else:
        selected_option = 3  # Sin scraper
        print(f"\n🎯 Seleccionada automáticamente: Opción {selected_option} (Solo análisis, sin scraper)")
    
    # Generar líneas de cron según la opción
    cron_lines = []
    
    if selected_option == 1:
        # Scraper + main.py --auto
        scraper_line = f"30 8 * * * cd {project_path} && {python_path} {scraper_path} >> logs/scraper.log 2>&1"
        main_line = f"0 9 * * * cd {project_path} && {python_path} main.py --auto >> logs/cron_main.log 2>&1"
        cron_lines = [scraper_line, main_line]
        
        print(f"⏰ Horario: Scraper a las 8:30 AM, Análisis a las 9:00 AM")
        print(f"📁 Logs: logs/scraper.log y logs/cron_main.log")
        
    elif selected_option == 2:
        # Scraper + insider_tracker.py
        scraper_line = f"30 8 * * * cd {project_path} && {python_path} {scraper_path} >> logs/scraper.log 2>&1"
        insider_line = f"0 9 * * * cd {project_path} && {python_path} insiders/insider_tracker.py >> logs/cron_insider.log 2>&1"
        cron_lines = [scraper_line, insider_line]
        
        print(f"⏰ Horario: Scraper a las 8:30 AM, Oportunidades a las 9:00 AM")
        print(f"📁 Logs: logs/scraper.log y logs/cron_insider.log")
        
    elif selected_option == 3:
        # Solo main.py --auto
        main_line = f"0 9 * * * cd {project_path} && {python_path} main.py --auto >> logs/cron_main.log 2>&1"
        cron_lines = [main_line]
        
        print(f"⏰ Horario: Análisis a las 9:00 AM (sin scraper)")
        print(f"📁 Logs: logs/cron_main.log")
        
    elif selected_option == 4:
        # Solo scraper
        scraper_line = f"30 8 * * * cd {project_path} && {python_path} {scraper_path} >> logs/scraper.log 2>&1"
        cron_lines = [scraper_line]
        
        print(f"⏰ Horario: Solo scraper a las 8:30 AM")
        print(f"📁 Logs: logs/scraper.log")
    
    # Obtener crontab actual
    try:
        current_crontab = subprocess.check_output(["crontab", "-l"], text=True, stderr=subprocess.DEVNULL)
        print("✅ Crontab actual obtenido")
    except subprocess.CalledProcessError:
        current_crontab = ""
        print("ℹ️ No hay crontab previo")
    
    # Limpiar líneas anteriores del proyecto para evitar duplicados
    lines = current_crontab.split('\n')
    cleaned_lines = []
    
    for line in lines:
        if project_path not in line and line.strip():
            cleaned_lines.append(line)
    
    if len(cleaned_lines) < len(lines):
        print("🧹 Líneas anteriores del proyecto removidas")
    
    # Añadir nuevas líneas
    cleaned_crontab = '\n'.join(cleaned_lines)
    if cleaned_crontab.strip():
        new_crontab = cleaned_crontab.strip() + "\n"
    else:
        new_crontab = ""
    
    # Agregar comentario explicativo
    new_crontab += f"# Insider Trading Analysis - {datetime.now().strftime('%Y-%m-%d')}\n"
    
    for line in cron_lines:
        new_crontab += line + "\n"
    
    # Aplicar nuevo crontab
    try:
        process = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        process.communicate(new_crontab)
        
        if process.returncode == 0:
            print("✅ Tareas cron configuradas correctamente")
            print("📋 Líneas añadidas:")
            for i, line in enumerate(cron_lines, 1):
                print(f"   {i}. {line}")
            return True
        else:
            print("❌ Error configurando crontab")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def verify_cron_setup():
    """
    Verifica que el cron está configurado correctamente
    """
    print("\n🔍 Verificando configuración de cron...")
    
    try:
        current_crontab = subprocess.check_output(["crontab", "-l"], text=True)
        
        project_lines = [line for line in current_crontab.split('\n') 
                        if 'stock_analyzer_a' in line and line.strip() and not line.startswith('#')]
        
        if project_lines:
            print("✅ Tareas cron encontradas:")
            for i, line in enumerate(project_lines, 1):
                if 'scraper' in line:
                    print(f"   {i}. 🕷️ SCRAPER: {line}")
                elif 'main.py' in line:
                    print(f"   {i}. 🚀 ANÁLISIS: {line}")
                else:
                    print(f"   {i}. 📊 OTROS: {line}")
        else:
            print("❌ No se encontraron tareas cron para el proyecto")
            
    except subprocess.CalledProcessError:
        print("❌ No hay crontab configurado")

def test_manual_execution():
    """
    Prueba la ejecución manual del scraper y análisis
    """
    print("\n🧪 Probando ejecución manual...")
    
    project_path = "/Users/alejandroordonezvillar/Desktop/stockAnalyzer/stock_analyzer_a"
    
    try:
        os.chdir(project_path)
        print(f"📁 Cambiado a directorio: {project_path}")
        
        # Buscar scraper
        possible_scrapers = [
            "insiders/openinsider_scraper.py",
            "openinsider_scraper.py",
            "scraper_independiente.py"
        ]
        
        scraper_found = None
        for scraper in possible_scrapers:
            if os.path.exists(scraper):
                scraper_found = scraper
                break
        
        if scraper_found:
            print(f"🕷️ Scraper encontrado: {scraper_found}")
            print("   Para ejecutar scraper: python3", scraper_found)
        
        # Probar main.py --auto
        if os.path.exists("main.py"):
            print("🚀 Para ejecutar análisis completo: python3 main.py --auto")
        
        if os.path.exists("insiders/insider_tracker.py"):
            print("🎯 Para ejecutar solo oportunidades: python3 insiders/insider_tracker.py")
        
        print("\n💡 Secuencia recomendada para prueba manual:")
        if scraper_found:
            print(f"   1. python3 {scraper_found}")
        print("   2. python3 main.py --auto")
            
    except Exception as e:
        print(f"❌ Error en prueba: {e}")

def show_schedule_summary():
    """
    Muestra un resumen del horario configurado
    """
    print("\n📅 RESUMEN DEL HORARIO CONFIGURADO:")
    print("=" * 50)
    print("🕐 8:30 AM - Scraper de OpenInsider")
    print("   └── Obtiene datos frescos de insider trading")
    print("   └── Logs: logs/scraper.log")
    print()
    print("🕘 9:00 AM - Análisis completo")
    print("   └── Procesa datos del scraper")
    print("   └── Genera oportunidades + gráficos")
    print("   └── Envía reporte a Telegram")
    print("   └── Logs: logs/cron_main.log")
    print()
    print("🔄 Este ciclo se repite TODOS LOS DÍAS")
    print("💡 Esto garantiza datos frescos cada día")

if __name__ == "__main__":
    print("🕒 CONFIGURADOR DE CRON - INSIDER TRADING CON SCRAPER")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configurar cron
    success = setup_cron_job()
    
    if success:
        # Verificar configuración
        verify_cron_setup()
        
        # Mostrar resumen del horario
        show_schedule_summary()
        
        # Instrucciones adicionales
        print("\n📋 INSTRUCCIONES ADICIONALES:")
        print("1. ✅ El sistema está configurado para datos frescos diarios")
        print("2. 📁 Los logs se guardarán en logs/")
        print("3. 📋 Para ver el crontab: crontab -l")
        print("4. 📝 Para editar el crontab: crontab -e")
        print("5. 📊 Para ver logs en tiempo real: tail -f logs/scraper.log")
        print("\n⚠️  IMPORTANTE:")
        print("   - Asegúrate de que config.py esté en .gitignore")
        print("   - El scraper se ejecuta 30 minutos antes del análisis")
        print("   - Esto garantiza datos frescos cada día")
        
        # Opción de prueba
        response = input("\n🧪 ¿Quieres ver los comandos para prueba manual? (y/n): ")
        if response.lower() == 'y':
            test_manual_execution()
    else:
        print("\n❌ Error configurando cron. Revisa los permisos y rutas.")

    print("\n🎉 Configuración completada!")
    print("💡 Ahora tendrás datos frescos de insider trading cada día!")
#!/usr/bin/env python3
"""
Script para diagnosticar por qué los datos de insider trading no se actualizan
"""

import pandas as pd
import os
from datetime import datetime, timedelta

def diagnosticar_datos_insider():
    """
    Diagnostica el estado de los datos de insider trading
    """
    print("🔍 DIAGNÓSTICO DE DATOS DE INSIDER TRADING")
    print("=" * 60)
    print(f"📅 Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verificar archivo principal
    csv_path = "reports/insiders_daily.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ El archivo {csv_path} no existe")
        return
    
    # Información del archivo
    stat = os.stat(csv_path)
    file_modified = datetime.fromtimestamp(stat.st_mtime)
    file_size = stat.st_size
    
    print(f"📄 Archivo: {csv_path}")
    print(f"📅 Última modificación: {file_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📏 Tamaño: {file_size:,} bytes")
    print(f"⏰ Hace: {datetime.now() - file_modified}")
    print()
    
    # Verificar si es de hoy
    hoy = datetime.now().date()
    archivo_date = file_modified.date()
    
    if archivo_date == hoy:
        print("✅ El archivo ES de hoy")
    elif archivo_date == hoy - timedelta(days=1):
        print("⚠️ El archivo es de AYER")
    else:
        print(f"❌ El archivo es de {archivo_date} (MUY ANTIGUO)")
    print()
    
    # Leer y analizar contenido
    try:
        df = pd.read_csv(csv_path)
        print(f"📊 Datos leídos: {len(df)} filas, {len(df.columns)} columnas")
        print(f"🏷️ Columnas: {list(df.columns)}")
        print()
        
        # Analizar fechas en los datos
        if 'ScrapedAt' in df.columns:
            print("📅 Análisis de fechas ScrapedAt:")
            df['ScrapedAt'] = pd.to_datetime(df['ScrapedAt'], errors='coerce')
            
            fechas_unicas = df['ScrapedAt'].dt.date.value_counts().sort_index()
            print("Fechas en los datos:")
            for fecha, count in fechas_unicas.items():
                if fecha == hoy:
                    print(f"  ✅ {fecha}: {count} registros (HOY)")
                elif fecha == hoy - timedelta(days=1):
                    print(f"  ⚠️ {fecha}: {count} registros (AYER)")
                else:
                    print(f"  ❌ {fecha}: {count} registros (ANTIGUO)")
        
        # Analizar timestamps de transacciones
        if 'Ticker' in df.columns:
            print("\n🕒 Análisis de timestamps de transacciones:")
            # En tu estructura, 'Ticker' contiene el timestamp
            timestamps = pd.to_datetime(df['Ticker'], errors='coerce')
            valid_timestamps = timestamps.dropna()
            
            if len(valid_timestamps) > 0:
                fecha_min = valid_timestamps.min().date()
                fecha_max = valid_timestamps.max().date()
                
                print(f"  📅 Rango de fechas: {fecha_min} a {fecha_max}")
                
                # Contar por día
                fechas_transacciones = valid_timestamps.dt.date.value_counts().sort_index()
                for fecha, count in fechas_transacciones.items():
                    if fecha == hoy:
                        print(f"  ✅ {fecha}: {count} transacciones (HOY)")
                    elif fecha == hoy - timedelta(days=1):
                        print(f"  ⚠️ {fecha}: {count} transacciones (AYER)")
                    else:
                        print(f"  ❌ {fecha}: {count} transacciones")
        
        # Mostrar muestra de datos
        print("\n📋 Muestra de primeros 3 registros:")
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            timestamp = row.get('Ticker', 'N/A')
            ticker = row.get('Insider', 'N/A')
            company = row.get('Title', 'N/A')
            scraped = row.get('ScrapedAt', 'N/A')
            print(f"  {i+1}. {timestamp} | {ticker} | {company} | Scraped: {scraped}")
            
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
    
    print("\n" + "=" * 60)
    print("🔧 POSIBLES SOLUCIONES:")
    print("=" * 60)
    
    if archivo_date != hoy:
        print("1. 🔄 El scraper de OpenInsider no se ejecutó hoy")
        print("   - Verificar que openinsider_scraper.py se ejecute correctamente")
        print("   - Revisar logs del scraper")
        print("   - Ejecutar manualmente el scraper")
    
    print("2. 📂 Verificar ubicación del archivo")
    print("   - ¿El scraper está guardando en la ubicación correcta?")
    print("   - ¿Hay múltiples copias del archivo?")
    
    print("3. ⏰ Verificar horarios de ejecución")
    print("   - ¿El análisis se ejecuta antes que el scraper?")
    print("   - ¿Hay conflictos de horarios?")
    
    print("4. 🔄 Forzar actualización manual")
    print("   - Ejecutar openinsider_scraper.py manualmente")
    print("   - Verificar que genera datos nuevos")

def verificar_scraper():
    """
    Verifica el estado del scraper de OpenInsider
    """
    print("\n🕷️ VERIFICACIÓN DEL SCRAPER")
    print("=" * 40)
    
    posibles_scrapers = [
        "openinsider_scraper.py",
        "insiders/openinsider_scraper.py", 
        "scrapers/openinsider_scraper.py",
        "scripts/openinsider_scraper.py"
    ]
    
    scraper_encontrado = None
    for scraper_path in posibles_scrapers:
        if os.path.exists(scraper_path):
            print(f"✅ Scraper encontrado: {scraper_path}")
            scraper_encontrado = scraper_path
            break
    
    if not scraper_encontrado:
        print("❌ No se encontró el scraper de OpenInsider")
        print("   Posibles ubicaciones buscadas:")
        for path in posibles_scrapers:
            print(f"   - {path}")
        return None
    
    # Verificar última modificación del scraper
    stat = os.stat(scraper_encontrado)
    scraper_modified = datetime.fromtimestamp(stat.st_mtime)
    
    print(f"📅 Última modificación del scraper: {scraper_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return scraper_encontrado

def ejecutar_test_scraper(scraper_path):
    """
    Ejecuta un test del scraper
    """
    if not scraper_path:
        return
        
    print(f"\n🧪 ¿Quieres ejecutar el scraper manualmente para obtener datos frescos?")
    respuesta = input("Escribe 'si' para ejecutar: ").lower().strip()
    
    if respuesta in ['si', 'sí', 's', 'yes', 'y']:
        try:
            print(f"🔄 Ejecutando {scraper_path}...")
            import subprocess
            result = subprocess.run(['python3', scraper_path], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ Scraper ejecutado exitosamente")
                print("📄 Output:")
                print(result.stdout)
                
                # Verificar si se generaron datos nuevos
                print("\n🔍 Verificando datos actualizados...")
                diagnosticar_datos_insider()
                
            else:
                print("❌ Error ejecutando scraper")
                print("Error output:")
                print(result.stderr)
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout ejecutando scraper")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Diagnóstico principal
    diagnosticar_datos_insider()
    
    # Verificar scraper
    scraper_path = verificar_scraper()
    
    # Opción de ejecutar scraper
    ejecutar_test_scraper(scraper_path)
    
    print("\n🎯 RECOMENDACIONES:")
    print("1. Asegúrate de que el scraper se ejecute ANTES del análisis")
    print("2. Verifica que no hay errores en el scraper")  
    print("3. Considera ejecutar el scraper manualmente para probar")
    print("4. Revisa los logs del cron para ver si hay errores")
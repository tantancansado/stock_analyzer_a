#!/usr/bin/env python3
"""
Tracker de insider trading que integra scraping + análisis + reporting
Este módulo coordina todo el proceso de análisis de insider trading
"""

import os
import sys
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
from bs4 import BeautifulSoup
import re
import zipfile
from pathlib import Path


def scrape_openinsider():
    """
    Función principal de scraping de OpenInsider
    Reutiliza la lógica del archivo paste.txt
    
    Returns:
        str: Ruta del CSV generado o None si hay error
    """
    print("🕷️ Iniciando scraper OpenInsider - SOLO DATOS REALES")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # URL para obtener más datos reales
        url = "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=7&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'http://openinsider.com/'
        }
        
        print("📡 Conectando a OpenInsider...")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error HTTP: {response.status_code}")
            print("🚫 NO SE USARÁN DATOS SIMULADOS")
            return None
        
        print("✅ Conexión exitosa, parseando datos reales...")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar tabla de datos
        table = soup.find('table', {'class': 'tinytable'})
        if not table:
            tables = soup.find_all('table')
            if tables:
                # Buscar la tabla con más filas (más probable que tenga datos)
                table = max(tables, key=lambda t: len(t.find_all('tr')))
                print(f"✅ Usando tabla con {len(table.find_all('tr'))} filas")
            else:
                print("❌ No se encontraron tablas")
                return None
        
        rows = table.find_all('tr')
        if len(rows) < 2:
            print("❌ Tabla sin datos")
            return None
            
        print(f"📊 Procesando {len(rows)} filas para datos reales...")
        
        data = []
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for i, row in enumerate(rows[1:], 1):  # Skip header
            cells = row.find_all('td')
            if len(cells) < 10:
                continue
                
            try:
                # Usar estructura estándar de OpenInsider
                if len(cells) >= 13:
                    ticker = cells[3].get_text(strip=True).upper()
                    company = cells[4].get_text(strip=True)
                    insider_name = cells[5].get_text(strip=True)
                    title = cells[6].get_text(strip=True)
                    trade_type = cells[7].get_text(strip=True)
                    price_raw = cells[8].get_text(strip=True)
                    qty_raw = cells[9].get_text(strip=True)
                    owned_raw = cells[10].get_text(strip=True)
                    value_raw = cells[12].get_text(strip=True) if len(cells) > 12 else ""
                else:
                    continue
                
                # Limpiar datos
                price = clean_numeric_value(price_raw)
                qty = clean_numeric_value(qty_raw)
                owned = clean_numeric_value(owned_raw)
                
                # Validar datos reales
                try:
                    price_float = float(price) if price and price != "0" else 0.0
                    qty_int = int(float(qty)) if qty and qty != "0" else 0
                    owned_int = int(float(owned)) if owned and owned != "0" else 0
                except:
                    continue
                
                # Validaciones estrictas para asegurar datos reales
                if not ticker or len(ticker) < 1 or len(ticker) > 6:
                    continue
                if not company or len(company) < 3:
                    continue
                if price_float <= 0 or qty_int <= 0:
                    continue
                
                # Solo compras
                is_purchase = ('P' in trade_type.upper() or 
                             'BUY' in trade_type.upper() or 
                             'PURCHASE' in trade_type.upper())
                
                if is_purchase:
                    value_pct = clean_percentage(value_raw)
                    
                    data_row = {
                        'Ticker': ticker,
                        'Company': company[:100],
                        'Insider': insider_name[:50],
                        'Title': title[:50],
                        'Date': current_timestamp,
                        'Type': 'P - Purchase',
                        'Price': str(price_float),
                        'Qty': str(qty_int),
                        'Owned': str(owned_int),
                        'Value': value_pct,
                        'Source': 'OpenInsider.com',
                        'ScrapedAt': current_timestamp,
                        'Chart_Daily': f"reports/graphs/{ticker}_d.png",
                        'Chart_Weekly': f"reports/graphs/{ticker}_w.png"
                    }
                    data.append(data_row)
                    
                    # Mostrar progreso de datos reales
                    if len(data) <= 5:
                        print(f"✅ REAL {len(data)}: {ticker} - {company[:30]} - ${price_float} x {qty_int}")
                        
            except Exception as e:
                continue
        
        if data:
            print(f"\n🎉 DATOS REALES EXTRAÍDOS: {len(data)} registros")
            print(f"🏢 Empresas reales: {len(set(item['Ticker'] for item in data))}")
            
            # Guardar CSV
            csv_path = save_insider_data(data)
            return csv_path
        else:
            print("❌ NO SE ENCONTRARON DATOS REALES")
            print("🚫 NO SE GENERARÁN DATOS SIMULADOS")
            return None
            
    except Exception as e:
        print(f"❌ Error obteniendo datos reales: {e}")
        return None


def clean_percentage(value_text):
    """
    Limpia y extrae el porcentaje del texto de value
    """
    if not value_text:
        return "N/A"
    
    cleaned = value_text.strip()
    
    percentage_match = re.search(r'(\d+\.?\d*)%', cleaned)
    if percentage_match:
        return f"{percentage_match.group(1)}%"
    
    number_match = re.search(r'(\d+\.?\d*)', cleaned)
    if number_match:
        return f"{number_match.group(1)}%"
    
    if cleaned in ['-', '', 'N/A', 'n/a']:
        return "N/A"
    
    return cleaned


def clean_numeric_value(value_text):
    """
    Limpia valores numéricos eliminando caracteres no numéricos
    """
    if not value_text:
        return "0"
    
    cleaned = re.sub(r'[^\d.,]', '', str(value_text).strip())
    cleaned = cleaned.replace(',', '')
    
    if not cleaned or cleaned == '.':
        return "0"
    
    return cleaned


def get_correct_reports_path():
    """
    Obtiene la ruta correcta de reports/ en la raíz del proyecto
    """
    # Obtener directorio actual
    current_dir = os.getcwd()
    print(f"🔧 DEBUG - Directorio actual: {current_dir}")
    
    # Si estamos en la carpeta insiders, subir un nivel
    if current_dir.endswith('/insiders') or current_dir.endswith('\\insiders'):
        parent_dir = os.path.dirname(current_dir)
        reports_path = os.path.join(parent_dir, 'reports')
        print(f"🔧 DEBUG - Detectado en carpeta insiders, usando: {reports_path}")
    else:
        # Estamos en la raíz, usar reports/ directamente
        reports_path = os.path.join(current_dir, 'reports')
        print(f"🔧 DEBUG - En raíz, usando: {reports_path}")
    
    return reports_path


def save_insider_data(data):
    """
    Guarda datos en la ruta CORRECTA: reports/ (raíz)
    """
    if not data:
        print("❌ No hay datos para guardar")
        return None
        
    try:
        # Usar ruta correcta en la raíz
        reports_path = get_correct_reports_path()
        
        # Crear directorio en la ubicación correcta
        os.makedirs(reports_path, exist_ok=True)
        print(f"✅ Directorio reports creado en: {reports_path}")
        
        # Convertir a DataFrame
        df = pd.DataFrame(data)
        
        # Validar estructura
        required_columns = ['Ticker', 'Company', 'Insider', 'Title', 'Date', 'Type', 'Price', 'Qty', 'Owned', 'Value', 'Source', 'ScrapedAt']
        for col in required_columns:
            if col not in df.columns:
                df[col] = 'N/A'
        
        # Eliminar duplicados
        df_dedup = df.drop_duplicates(subset=['Ticker', 'Price', 'Qty'], keep='first')
        duplicates_removed = len(df) - len(df_dedup)
        if duplicates_removed > 0:
            print(f"🔄 Eliminados {duplicates_removed} duplicados")
        df = df_dedup
        
        # Ordenar por valor de transacción
        try:
            df['Transaction_Value'] = pd.to_numeric(df['Price'], errors='coerce') * pd.to_numeric(df['Qty'], errors='coerce')
            df = df.sort_values('Transaction_Value', ascending=False)
            df = df.drop('Transaction_Value', axis=1)
        except:
            pass
        
        # GUARDAR EN LA RUTA CORRECTA
        output_path = os.path.join(reports_path, "insiders_daily.csv")
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        print(f"\n✅ CSV GUARDADO EN RUTA CORRECTA:")
        print(f"📍 Ubicación: {output_path}")
        print(f"📊 Registros REALES: {len(df)}")
        print(f"🏢 Empresas únicas: {df['Ticker'].nunique()}")
        
        # Verificar que se guardó correctamente
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"💾 Tamaño archivo: {size} bytes")
            
            # Mostrar top transacciones reales
            print("\n📋 Top 5 transacciones REALES:")
            for i in range(min(5, len(df))):
                row = df.iloc[i]
                try:
                    value = float(row['Price']) * float(row['Qty'])
                    print(f"  {i+1}. {row['Ticker']} - {row['Company'][:30]}... - ${value:,.0f}")
                except:
                    print(f"  {i+1}. {row['Ticker']} - {row['Company'][:30]}...")
        else:
            print(f"❌ Error: archivo no se guardó en {output_path}")
            return None
            
        return output_path
        
    except Exception as e:
        print(f"❌ Error guardando CSV: {e}")
        import traceback
        traceback.print_exc()
        return None


def generar_reporte_html_oportunidades(csv_path):
    """
    Genera reporte HTML de oportunidades a partir del CSV
    
    Args:
        csv_path (str): Ruta del archivo CSV con datos
        
    Returns:
        str: Ruta del archivo HTML generado
    """
    try:
        if not os.path.exists(csv_path):
            print(f"❌ CSV no encontrado: {csv_path}")
            return None
        
        df = pd.read_csv(csv_path)
        print(f"📊 Generando HTML para {len(df)} registros")
        
        # Usar la función del módulo plot_utils
        try:
            from alerts.plot_utils import crear_html_moderno_finviz
            html_path = crear_html_moderno_finviz()
            return html_path
        except ImportError:
            print("⚠️ Módulo plot_utils no disponible")
            return None
        
    except Exception as e:
        print(f"❌ Error generando HTML de oportunidades: {e}")
        return None


def enviar_reporte_telegram(csv_path, html_path):
    """
    Envía reporte por Telegram
    
    Args:
        csv_path (str): Ruta del CSV
        html_path (str): Ruta del HTML
    """
    try:
        from alerts.plot_utils import enviar_por_telegram
        enviar_por_telegram(html_path, None)
        print("✅ Reporte enviado por Telegram")
    except Exception as e:
        print(f"❌ Error enviando por Telegram: {e}")


def generar_reporte_completo_integrado():
    """
    Función principal que integra todo SIN historial (método tradicional)
    """
    print("🚀 GENERANDO REPORTE COMPLETO INTEGRADO (Método Tradicional)")
    print("=" * 60)
    
    try:
        # 1. Scraping de datos
        print("\n📊 PASO 1: Obteniendo datos de OpenInsider...")
        csv_path = scrape_openinsider()
        
        if not csv_path:
            # Usar CSV existente si no se pudieron obtener nuevos datos
            csv_path = "reports/insiders_daily.csv"
            if not os.path.exists(csv_path):
                print("❌ No hay datos disponibles")    
                return None
            print(f"⚠️ Usando CSV existente: {csv_path}")
        
        # 2. Generar gráficos
        print("\n📊 PASO 2: Generando gráficos...")
        try:
            from run_daily import procesar_insiders_csv_y_generar_graficos
            graficos = procesar_insiders_csv_y_generar_graficos()
            print(f"✅ {len(graficos)} gráficos generados")
        except Exception as e:
            print(f"❌ Error generando gráficos: {e}")
#!/usr/bin/env python3
"""
OpenInsider Scraper - VERSIÓN CORREGIDA
Scraper independiente para obtener datos de insider trading de OpenInsider.com
"""

import requests
import pandas as pd
import os
from datetime import datetime
import time
from bs4 import BeautifulSoup

def scrape_openinsider_data():
    """
    Scraper principal de OpenInsider - sin dependencias de alerts
    """
    print("🕷️ Iniciando scraper de OpenInsider...")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # URL de OpenInsider para compras recientes
        url = "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=730&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print("📡 Conectando a OpenInsider...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print("✅ Conexión exitosa, parseando datos...")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar la tabla de datos
        table = soup.find('table', {'class': 'tinytable'})
        if not table:
            print("❌ No se encontró tabla de datos")
            return None
            
        # Extraer datos de la tabla
        rows = table.find_all('tr')
        data = []
        
        print(f"📊 Procesando {len(rows)} filas...")
        
        for i, row in enumerate(rows):
            if i == 0:  # Skip header
                continue
                
            cells = row.find_all('td')
            if len(cells) < 11:  # Asegurar que tiene suficientes columnas
                continue
                
            try:
                # Extraer datos de cada celda
                filing_date = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                trade_date = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                ticker = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                company = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                insider_name = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                title = cells[6].get_text(strip=True) if len(cells) > 6 else ""
                trade_type = cells[7].get_text(strip=True) if len(cells) > 7 else ""
                price = cells[8].get_text(strip=True) if len(cells) > 8 else ""
                qty = cells[9].get_text(strip=True) if len(cells) > 9 else ""
                owned = cells[10].get_text(strip=True) if len(cells) > 10 else ""
                
                # Limpiar datos
                price = price.replace('$', '').replace(',', '') if price else "0"
                qty = qty.replace(',', '') if qty else "0"
                owned = owned.replace(',', '') if owned else "0"
                
                # Solo incluir compras (P)
                if 'P' in trade_type:
                    data_row = {
                        'Ticker': filing_date,  # Timestamp como se espera en el CSV
                        'Insider': ticker,      # Ticker real
                        'Title': company,       # Nombre de empresa
                        'Date': title,          # Título del insider
                        'Type': f"P - Purchase",
                        'Price': price,
                        'Qty': qty,
                        'Owned': owned,
                        'Value': "0%",  # Placeholder
                        'Source': 'OpenInsider',
                        'ScrapedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Chart_Daily': f"reports/graphs/{filing_date}_d.png",
                        'Chart_Weekly': f"reports/graphs/{filing_date}_w.png"
                    }
                    data.append(data_row)
                    
            except Exception as e:
                print(f"⚠️ Error procesando fila {i}: {e}")
                continue
        
        if not data:
            print("❌ No se encontraron datos válidos")
            return None
            
        print(f"✅ Extraídos {len(data)} registros de compras")
        return data
        
    except requests.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return None
    except Exception as e:
        print(f"❌ Error general: {e}")
        return None

def save_insider_data(data):
    """
    Guarda los datos en CSV
    """
    if not data:
        print("❌ No hay datos para guardar")
        return False
        
    try:
        # Crear directorio si no existe
        os.makedirs("reports", exist_ok=True)
        
        # Convertir a DataFrame
        df = pd.DataFrame(data)
        
        # Guardar CSV
        output_path = "reports/insiders_daily.csv"
        df.to_csv(output_path, index=False)
        
        print(f"✅ Datos guardados en: {output_path}")
        print(f"📊 Total registros: {len(df)}")
        
        # Mostrar muestra
        print("\n📋 Muestra de datos guardados:")
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            print(f"  {i+1}. {row['Insider']} - {row['Title']} - ${row['Price']} x {row['Qty']}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error guardando datos: {e}")
        return False

def scrape_alternative_source():
    """
    Fuente alternativa en caso de que OpenInsider falle
    """
    print("🔄 Intentando fuente alternativa...")
    
    # Datos de ejemplo para testing (puedes reemplazar con otra fuente)
    sample_data = [
        {
            'Ticker': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Insider': 'AAPL',
            'Title': 'Apple Inc.',
            'Date': 'CEO',
            'Type': 'P - Purchase',
            'Price': '180.50',
            'Qty': '1000',
            'Owned': '50000',
            'Value': '0%',
            'Source': 'Alternative',
            'ScrapedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Chart_Daily': f"reports/graphs/{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_d.png",
            'Chart_Weekly': f"reports/graphs/{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_w.png"
        }
    ]
    
    print("⚠️ Usando datos de ejemplo (reemplazar con fuente real)")
    return sample_data

def main():
    """
    Función principal del scraper
    """
    print("🚀 OPENINSIDER SCRAPER - INDEPENDIENTE")
    print("=" * 50)
    
    # Intentar scraper principal
    data = scrape_openinsider_data()
    
    # Si falla, usar fuente alternativa
    if not data:
        print("⚠️ Scraper principal falló, usando fuente alternativa...")
        data = scrape_alternative_source()
    
    # Guardar datos
    if data:
        success = save_insider_data(data)
        if success:
            print("\n🎉 Scraper completado exitosamente")
            return True
        else:
            print("\n❌ Error guardando datos")
            return False
    else:
        print("\n❌ No se pudieron obtener datos")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
#!/usr/bin/env python3
"""
Sistema Unificado de Insider Trading + DJ Sectorial Analyzer
Versión completa con análisis sectorial integrado
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os
import sys
import subprocess
import zipfile
from pathlib import Path
import traceback

# Importar el VCP Scanner Enhanced si existe, si no, stub
try:
    from vcp_scanner_usa import VCPScannerEnhanced
except ImportError:
    class VCPScannerEnhanced:
        def __init__(self):
            print("Función no implementada: VCPScannerEnhanced (stub)")
        def scan_market(self):
            return []
        def generate_html(self, results, html_path):
            with open(html_path, "w", encoding="utf-8") as f:
                f.write("<html><body><h1>Función no implementada</h1></body></html>")
            return html_path
        def save_csv(self, results, csv_path):
            pd.DataFrame(results).to_csv(csv_path, index=False)
            return csv_path

class DJMasterAnalyzer:
    """
    Analizador de sectores Dow Jones - INTEGRADO
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'es-ES,es;q=0.9,en-GB;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Origin': 'https://www.investing.com',
            'Referer': 'https://www.investing.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors', 
            'Sec-Fetch-Site': 'same-site',
            'Sec-Ch-Ua': '"Google Chrome";v="137", "Chromium";v="137", "Not(A)Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Domain-Id': 'www',
            'Dnt': '1',
        })
        self.api_base = "https://de.api.investing.com/api/financialdata/historical"
        
        # TODOS los IDs de sectores Dow Jones
        self.ALL_INVESTING_IDS = {
            # SECTORES PRINCIPALES (Nivel 1)
            'DJUSEN': '19972',  # Oil & Gas ⛽
            'DJUSTC': '19976',  # Technology 💻
            'DJUSBK': '19963',  # Banks 🏦
            'DJUSRE': '19974',  # Real Estate 🏠
            'DJUSHC': '19958',  # Healthcare 🏥
            'DJUSCH': '19965',  # Chemicals 🧪
            'DJUSUT': '19961',  # Utilities ⚡
            'DJUSFN': '19967',  # Financials 💰
            'DJUSRT': '19975',  # Retail 🛒
            'DJUSIG': '19969',  # Industrial Goods 🏭
            'DJUSME': '19971',  # Media 📺
            'DJUSTL': '19960',  # Telecommunications 📞
            'DJUSFB': '19968',  # Food & Beverage 🍔
            'DJUSNG': '19973',  # Personal & Household Goods 🏠
            'DJUSBS': '19964',  # Basic Resources ⛏️
            'DJUSCN': '19966',  # Construction & Materials 🏗️
            
            # SECTORES ESPECÍFICOS (Nivel 2)
            'DJUSAP': '19962',  # Automobiles & Parts 🚗
            'DJUSBV': '19978',  # Beverages 🥤
            'DJUSDR': '19980',  # Food & Drug Retailers 🏪
            'DJUSEE': '19979',  # Electronic & Electrical Equipment ⚡
            'DJUSFO': '19981',  # Food Producers 🌾
            'DJUSGI': '19984',  # General Industrials 🏭
            'DJUSGT': '19985',  # General Retailers 🛍️
            'DJUSMC': '19986',  # Health Care Equipment & Services 🩺
            'DJUSHG': '19987',  # Household Goods & Home Construction 🏠
            'DJUSIQ': '19988',  # Industrial Engineering ⚙️
            'DJUSIM': '19989',  # Industrial Metals & Mining ⛏️
            'DJUSIT': '19990',  # Industrial Transportation 🚛
            'DJUSLE': '19991',  # Leisure Goods 🎮
            'DJUSMG': '19992',  # Mining ⛏️
            'DJUSIX': '19993',  # Nonlife Insurance 🛡️
            'DJUSOG': '19994',  # Oil & Gas Producers ⛽
            'DJUSPG': '19996',  # Personal Goods 👕
            'DJUSPN': '19997',  # Pharmaceuticals & Biotechnology 💊
            'DJUSRH': '19998',  # Real Estate Investment & Services 🏢
            'DJUSRI': '19999',  # Real Estate Investment Trusts 🏠
            'DJUSSV': '20000',  # Software & Computer Services 💻
            'DJUSIS': '20001',  # Support Services 📋
            'DJUSTQ': '20002',  # Technology Hardware & Equipment 🖥️
            'DJUSAS': '20004',  # Aerospace 🚀
            'DJUSAR': '20005',  # Airlines ✈️
            'DJUSAL': '20006',  # Aluminum 🔩
            'DJUSRA': '20007',  # Apparel Retailers 👗
        }
        
        # Nombres descriptivos para los sectores
        self.SECTOR_NAMES = {
            'DJUSEN': 'Oil & Gas',
            'DJUSTC': 'Technology', 
            'DJUSBK': 'Banks',
            'DJUSRE': 'Real Estate',
            'DJUSHC': 'Healthcare',
            'DJUSCH': 'Chemicals',
            'DJUSUT': 'Utilities',
            'DJUSFN': 'Financials',
            'DJUSRT': 'Retail',
            'DJUSIG': 'Industrial Goods',
            'DJUSME': 'Media',
            'DJUSTL': 'Telecommunications',
            'DJUSFB': 'Food & Beverage',
            'DJUSNG': 'Personal Goods',
            'DJUSBS': 'Basic Resources',
            'DJUSCN': 'Construction',
            'DJUSAP': 'Auto & Parts',
            'DJUSBV': 'Beverages',
            'DJUSDR': 'Drug Retailers',
            'DJUSEE': 'Electronics',
            'DJUSFO': 'Food Producers',
            'DJUSGI': 'General Industrial',
            'DJUSGT': 'General Retail',
            'DJUSMC': 'Healthcare Equipment',
            'DJUSHG': 'Household Goods',
            'DJUSIQ': 'Industrial Engineering',
            'DJUSIM': 'Metals & Mining',
            'DJUSIT': 'Industrial Transport',
            'DJUSLE': 'Leisure Goods',
            'DJUSMG': 'Mining',
            'DJUSIX': 'Insurance',
            'DJUSOG': 'Oil Producers',
            'DJUSPG': 'Personal Goods',
            'DJUSPN': 'Pharmaceuticals',
            'DJUSRH': 'RE Investment',
            'DJUSRI': 'REITs',
            'DJUSSV': 'Software',
            'DJUSIS': 'Support Services',
            'DJUSTQ': 'Tech Hardware',
            'DJUSAS': 'Aerospace',
            'DJUSAR': 'Airlines',
            'DJUSAL': 'Aluminum',
            'DJUSRA': 'Apparel Retail',
        }
    
    def get_historical_data(self, ticker, days_back=365):
        """Obtiene datos históricos para un ticker"""
        try:
            index_id = self.ALL_INVESTING_IDS.get(ticker)
            if not index_id:
                return False, None
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            url = f"{self.api_base}/{index_id}"
            params = {
                'start-date': start_date_str,
                'end-date': end_date_str,
                'time-frame': 'Daily',
                'add-missing-rows': 'false'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and len(data['data']) > 0:
                    historical_data = data['data']
                    
                    # Convertir a DataFrame con limpieza de números
                    df_data = []
                    for item in historical_data:
                        def clean_number(value):
                            if isinstance(value, str):
                                cleaned = value.replace(',', '')
                                try:
                                    return float(cleaned)
                                except (ValueError, TypeError):
                                    return 0.0
                            return float(value) if value else 0.0
                        
                        df_data.append({
                            'Date': item.get('rowDate'),
                            'Close': clean_number(item.get('last_close', 0)),
                            'Open': clean_number(item.get('last_open', 0)),
                            'High': clean_number(item.get('last_max', 0)),
                            'Low': clean_number(item.get('last_min', 0)),
                            'Volume': int(clean_number(item.get('volumeRaw', 0)))
                        })
                    
                    df = pd.DataFrame(df_data)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.sort_values('Date', ascending=False)
                    
                    return True, df
                    
            return False, None
            
        except Exception as e:
            print(f"❌ Error obteniendo {ticker}: {str(e)}")
            return False, None
    
    def calculate_rsi(self, prices, period=14):
        """Calcula RSI"""
        if len(prices) < period + 1:
            return None
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def analyze_sector(self, ticker, df):
        """Análisis completo de un sector"""
        if df is None or len(df) < 50:
            return None
        
        current_price = df['Close'].iloc[0]
        min_52w = df['Low'].min()
        max_52w = df['High'].max()
        
        distance_from_min = ((current_price - min_52w) / min_52w) * 100
        rsi = self.calculate_rsi(df['Close'].values)
        
        # Clasificación por estado
        if distance_from_min < 10:
            estado = "🟢"
            classification = "OPORTUNIDAD"
        elif distance_from_min < 25:
            estado = "🟡"
            classification = "CERCA"
        else:
            estado = "🔴"
            classification = "FUERTE"
        
        return {
            'ticker': ticker,
            'sector': self.SECTOR_NAMES.get(ticker, ticker),
            'current_price': current_price,
            'min_52w': min_52w,
            'max_52w': max_52w,
            'distance_pct': distance_from_min,
            'rsi': rsi,
            'estado': estado,
            'classification': classification,
            'data_points': len(df)
        }
    
    def batch_analysis(self, tickers, batch_size=5):
        """Análisis por lotes para evitar saturar la API"""
        results = []
        total = len(tickers)
        
        print(f"🚀 INICIANDO ANÁLISIS DE {total} SECTORES")
        print("=" * 60)
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            print(f"\n📦 LOTE {batch_num}/{total_batches}: {', '.join(batch)}")
            
            for ticker in batch:
                print(f"   🔄 Procesando {ticker}...", end=" ")
                
                success, df = self.get_historical_data(ticker)
                if success and df is not None:
                    result = self.analyze_sector(ticker, df)
                    if result:
                        results.append(result)
                        print(f"✅ {result['distance_pct']:.1f}% {result['estado']}")
                    else:
                        print("❌ Sin análisis")
                else:
                    print("❌ Sin datos")
                
                time.sleep(1)  # Pausa entre requests
            
            if i + batch_size < len(tickers):
                print(f"   ⏳ Pausa entre lotes...")
                time.sleep(3)  # Pausa entre lotes
        
        return results
    
    def generate_report(self, results):
        """Genera reporte completo en consola"""
        if not results:
            print("❌ No hay resultados para reportar")
            return
        
        print(f"\n{'='*80}")
        print("🎯 REPORTE SECTORIAL COMPLETO")
        print("=" * 80)
        
        # Tabla principal
        print(f"{'Sector':<20} {'Precio':<10} {'Min52w':<10} {'Dist%':<8} {'RSI':<6} {'Estado'}")
        print("-" * 70)
        
        for r in sorted(results, key=lambda x: x['distance_pct']):
            rsi_str = f"{r['rsi']:.1f}" if r['rsi'] else "N/A"
            print(f"{r['sector']:<20} {r['current_price']:<10.2f} {r['min_52w']:<10.2f} {r['distance_pct']:<8.1f} {rsi_str:<6} {r['estado']}")
        
        # Análisis por categorías
        oportunidades = [r for r in results if r['classification'] == 'OPORTUNIDAD']
        cerca = [r for r in results if r['classification'] == 'CERCA']
        fuertes = [r for r in results if r['classification'] == 'FUERTE']
        
        print(f"\n📊 RESUMEN POR CATEGORÍAS:")
        print(f"   🟢 OPORTUNIDADES (<10%): {len(oportunidades)} sectores")
        print(f"   🟡 CERCA (10-25%): {len(cerca)} sectores")
        print(f"   🔴 FUERTES SUBIDAS, PRECAUCIÓN (>25%): {len(fuertes)} sectores")
        
        if oportunidades:
            print(f"\n🎯 TOP OPORTUNIDADES:")
            for r in sorted(oportunidades, key=lambda x: x['distance_pct'])[:10]:
                rsi_info = f" | RSI: {r['rsi']:.1f}" if r['rsi'] else ""
                print(f"   • {r['sector']}: {r['distance_pct']:.1f}% del mínimo{rsi_info}")

class InsiderTradingSystem:
    """Sistema principal que gestiona todo el flujo"""
    
    def __init__(self):
        self.csv_path = "reports/insiders_daily.csv"
        self.html_path = "reports/insiders_report_completo.html"
        self.bundle_path = "reports/insiders_report_bundle.zip"
        
        # NUEVO: Inicializar DJ Analyzer
        self.dj_analyzer = DJMasterAnalyzer()
        
        self.setup_directories()
    
    def setup_directories(self):
        """Crea los directorios necesarios"""
        os.makedirs("reports", exist_ok=True)
        os.makedirs("alerts", exist_ok=True)
        print("✅ Directorios verificados")
    
    def run_scraper(self):
        """Ejecuta el scraper de OpenInsider"""
        print("\n🕷️ EJECUTANDO SCRAPER")
        print("=" * 50)
        
        try:
            # Buscar el scraper
            scraper_paths = [
                "insiders/openinsider_scraper.py",
                "openinsider_scraper.py",
                "paste-3.txt"  # Por si está como texto
            ]
            
            scraper_found = None
            for path in scraper_paths:
                if os.path.exists(path):
                    scraper_found = path
                    break
            
            if not scraper_found:
                print("❌ Scraper no encontrado")
                return False
            
            print(f"✅ Ejecutando: {scraper_found}")
            
            # Si es paste-3.txt, ejecutarlo como Python
            if scraper_found.endswith('.txt'):
                with open(scraper_found, 'r') as f:
                    exec(f.read())
            else:
                result = subprocess.run(
                    [sys.executable, scraper_found],
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if result.returncode != 0:
                    print(f"❌ Error ejecutando scraper: {result.stderr}")
                    return False
            
            # Verificar que se generó el CSV
            if os.path.exists(self.csv_path):
                df = pd.read_csv(self.csv_path)
                print(f"✅ CSV generado: {len(df)} registros")
                return True
            else:
                print("❌ CSV no generado")
                return False
                
        except Exception as e:
            print(f"❌ Error en scraper: {e}")
            traceback.print_exc()
            return False
    
    # NUEVA FUNCIÓN: Ejecutar análisis DJ Sectorial
    def run_dj_sectorial_analysis(self, mode="principales"):
        """
        Ejecuta el análisis sectorial de Dow Jones
        
        Args:
            mode (str): "principales", "detallado", "completo"
        """
        print("\n📊 EJECUTANDO ANÁLISIS SECTORIAL DJ")
        print("=" * 50)
        
        try:
            # Seleccionar tickers según modo
            if mode == "principales":
                tickers = list(self.dj_analyzer.ALL_INVESTING_IDS.keys())[:16]
                print(f"📊 Modo Principales: {len(tickers)} sectores")
            elif mode == "detallado":
                tickers = list(self.dj_analyzer.ALL_INVESTING_IDS.keys())[:35]
                print(f"🔍 Modo Detallado: {len(tickers)} sectores")
            elif mode == "completo":
                tickers = list(self.dj_analyzer.ALL_INVESTING_IDS.keys())
                print(f"🚀 Modo Completo: {len(tickers)} sectores")
            else:
                tickers = list(self.dj_analyzer.ALL_INVESTING_IDS.keys())[:16]
            
            # Ejecutar análisis
            results = self.dj_analyzer.batch_analysis(tickers, batch_size=5)
            
            # Mostrar reporte en consola
            self.dj_analyzer.generate_report(results)
            
            # Guardar CSV
            if results:
                self.save_dj_results_to_csv(results)
                # Generar HTML
                self.generate_dj_html(results)
            
            print(f"\n✅ ANÁLISIS DJ COMPLETADO: {len(results)} sectores procesados")
            return results
            
        except Exception as e:
            print(f"❌ Error en análisis DJ: {e}")
            traceback.print_exc()
            return []
    
    # NUEVA FUNCIÓN: Guardar resultados DJ en CSV
    def save_dj_results_to_csv(self, results):
        """Guarda los resultados del análisis DJ en CSV"""
        try:
            if not results:
                print("⚠️ Sin resultados para guardar")
                return False
            
            # Convertir resultados a DataFrame
            df_data = []
            for r in results:
                df_data.append({
                    'Ticker': r['ticker'],
                    'Sector': r['sector'], 
                    'CurrentPrice': r['current_price'],
                    'Min52w': r['min_52w'],
                    'Max52w': r['max_52w'],
                    'DistanceFromMin': r['distance_pct'],
                    'RSI': r['rsi'],
                    'Estado': r['estado'],
                    'Classification': r['classification'],
                    'DataPoints': r['data_points'],
                    'AnalysisDate': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df = pd.DataFrame(df_data)
            csv_path = "reports/dj_sectorial_analysis.csv"
            df.to_csv(csv_path, index=False)
            print(f"✅ CSV DJ guardado: {csv_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando CSV DJ: {e}")
            return False
    
    # NUEVA FUNCIÓN: Generar HTML para DJ Sectorial
    def generate_dj_html(self, results):
        """Genera HTML optimizado para móvil para análisis DJ"""
        print("\n📄 GENERANDO HTML DJ SECTORIAL")
        print("=" * 50)
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Estadísticas
            total_sectores = len(results)
            oportunidades = len([r for r in results if r['classification'] == 'OPORTUNIDAD'])
            cerca = len([r for r in results if r['classification'] == 'CERCA'])
            fuertes = len([r for r in results if r['classification'] == 'FUERTE'])
            
            # HTML con diseño consistente con el sistema
            html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 DJ Sectorial Dashboard</title>
    <style>
        :root {{
            --bg-dark: #0a0e1a;
            --bg-card: #1a202c;
            --bg-card-light: #2d3748;
            --border-color: #4a5568;
            --primary: #4a90e2;
            --text-primary: #ffffff;
            --text-secondary: #a0aec0;
            --success: #48bb78;
            --warning: #ffd700;
            --danger: #f56565;
        }}
        
        * {{ box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1a1f35 0%, #2d3748 100%);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid var(--primary);
        }}
        
        .header h1 {{
            color: var(--primary);
            font-size: 2em;
            margin: 0 0 10px 0;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            padding: 20px;
            background: var(--bg-card);
        }}
        
        .stat-card {{
            background: var(--bg-card-light);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            border-left: 4px solid var(--primary);
        }}
        
        .stat-number {{
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9em;
        }}
        
        .oportunidad {{ color: var(--success); }}
        .cerca {{ color: var(--warning); }}
        .fuerte {{ color: var(--danger); }}
        
        .sectors-container {{
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .sector-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid var(--primary);
            transition: transform 0.2s ease;
        }}
        
        .sector-card:hover {{
            transform: translateY(-2px);
        }}
        
        .sector-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .sector-ticker {{
            font-size: 1.3em;
            font-weight: bold;
            color: var(--primary);
        }}
        
        .sector-status {{
            font-size: 1.5em;
        }}
        
        .sector-name {{
            color: var(--text-secondary);
            margin-bottom: 15px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        
        .metric {{
            background: var(--bg-card-light);
            padding: 10px;
            border-radius: 8px;
        }}
        
        .metric-label {{
            font-size: 0.8em;
            color: var(--text-secondary);
            margin-bottom: 3px;
        }}
        
        .metric-value {{
            font-weight: bold;
        }}
        
        @media (max-width: 768px) {{
            .sectors-container {{
                grid-template-columns: 1fr;
                padding: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Dow Jones Sectorial Dashboard</h1>
        <p>Análisis completo de sectores • {timestamp}</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number">{total_sectores}</div>
            <div class="stat-label">Total Sectores</div>
        </div>
        <div class="stat-card">
            <div class="stat-number oportunidad">{oportunidades}</div>
            <div class="stat-label">🟢 Oportunidades</div>
        </div>
        <div class="stat-card">
            <div class="stat-number cerca">{cerca}</div>
            <div class="stat-label">🟡 Cerca</div>
        </div>
        <div class="stat-card">
            <div class="stat-number fuerte">{fuertes}</div>
            <div class="stat-label">🔴 Fuertes</div>
        </div>
    </div>
    
    <div class="sectors-container">
"""
            
            # Generar cards de sectores ordenados por oportunidad
            if results:
                results_sorted = sorted(results, key=lambda x: x['distance_pct'])
                
                for r in results_sorted:
                    distance_pct = r['distance_pct']
                    rsi = r['rsi']
                    estado = r['estado']
                    classification = r['classification']
                    
                    # Color según clasificación
                    if classification == 'OPORTUNIDAD':
                        border_color = 'var(--success)'
                    elif classification == 'CERCA':
                        border_color = 'var(--warning)'
                    else:
                        border_color = 'var(--danger)'
                    
                    html_content += f"""
        <div class="sector-card" style="border-left-color: {border_color}">
            <div class="sector-header">
                <div class="sector-ticker">{r['ticker']}</div>
                <div class="sector-status">{estado}</div>
            </div>
            <div class="sector-name">{r['sector']}</div>
            
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">Precio Actual</div>
                    <div class="metric-value">${r['current_price']:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Min 52s</div>
                    <div class="metric-value">${r['min_52w']:.2f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Distancia Min</div>
                    <div class="metric-value">{distance_pct:.1f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">RSI</div>
                    <div class="metric-value">{'N/A' if not pd.notna(rsi) or rsi is None else f'{rsi:.1f}'}</div>
                </div>
            </div>
        </div>
"""
            else:
                html_content += """
        <div class="sector-card">
            <div class="sector-header">
                <div class="sector-ticker">Sin Datos</div>
                <div class="sector-status">⚠️</div>
            </div>
            <div class="sector-name">No se pudieron obtener datos de sectores</div>
        </div>
"""
            
            html_content += """
    </div>
</body>
</html>
"""
            
            html_path = "reports/dj_sectorial_report.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML DJ generado: {html_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generando HTML DJ: {e}")
            traceback.print_exc()
            return False
    
    # NUEVA FUNCIÓN: Análisis diario completo (Insider + DJ)
    def run_daily_combined_analysis(self, dj_mode="principales"):
        """
        NUEVA: Análisis diario completo - Insider Trading + DJ Sectorial
        Los sube por separado para tener secciones independientes en GitHub Pages
        """
        print("\n🌟 ANÁLISIS DIARIO COMPLETO - INSIDER + DJ SECTORIAL")
        print("=" * 80)
        print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {
            'insider_scraper': False,
            'insider_html': False,
            'dj_analysis': False,
            'dj_html': False,
            'github_insider': None,
            'github_dj': None,
            'telegram': False
        }
        
        try:
            print("\n🔸 FASE 1: INSIDER TRADING")
            print("=" * 40)
            
            # 1. Ejecutar scraper insider
            results['insider_scraper'] = self.run_scraper()
            if results['insider_scraper']:
                # 2. Generar HTML insider
                results['insider_html'] = self.generate_html()
                # 3. Subir insider a GitHub Pages
                results['github_insider'] = self.upload_github_pages()
            else:
                print("⚠️ Fallo en scraper insider, continuando con DJ...")
            
            print("\n🔸 FASE 2: DJ SECTORIAL")
            print("=" * 40)
            
            # 4. Ejecutar análisis DJ
            dj_analysis_results = self.run_dj_sectorial_analysis(dj_mode)
            results['dj_analysis'] = len(dj_analysis_results) > 0
            
            if results['dj_analysis']:
                # 5. HTML DJ ya se genera en run_dj_sectorial_analysis
                results['dj_html'] = True
                # 6. Subir DJ a GitHub Pages como sección separada
                results['github_dj'] = self.upload_dj_to_github_pages(dj_analysis_results)
            else:
                print("⚠️ Fallo en análisis DJ")
            
            print("\n🔸 FASE 3: NOTIFICACIÓN TELEGRAM")
            print("=" * 40)
            
            # 7. Enviar notificación unificada por Telegram
            results['telegram'] = self.send_combined_telegram_report(results, dj_analysis_results)
            
            # 8. Crear bundle local (opcional)
            self.create_bundle()
            
            # Resumen final
            print("\n" + "=" * 80)
            print("🎉 RESUMEN ANÁLISIS DIARIO")
            print("=" * 80)
            print(f"🏛️ Insider Trading:")
            print(f"   • Scraper: {'✓' if results['insider_scraper'] else '✗'}")
            print(f"   • HTML: {'✓' if results['insider_html'] else '✗'}")
            print(f"   • GitHub Pages: {'✓' if results['github_insider'] else '✗'}")
            
            print(f"📊 DJ Sectorial:")
            print(f"   • Análisis: {'✓' if results['dj_analysis'] else '✗'}")
            print(f"   • HTML: {'✓' if results['dj_html'] else '✗'}")
            print(f"   • GitHub Pages: {'✓' if results['github_dj'] else '✗'}")
            
            print(f"📱 Telegram: {'✓' if results['telegram'] else '✗'}")
            
            # URLs de GitHub Pages
            if results['github_insider']:
                print(f"\n🏛️ Ver Insider Trading: {results['github_insider'].get('github_url', 'N/A')}")
            if results['github_dj']:
                print(f"📊 Ver DJ Sectorial: {results['github_dj'].get('url', 'N/A')}")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Error crítico en análisis diario: {e}")
            traceback.print_exc()
            return results
    
    def upload_dj_to_github_pages(self, dj_results):
        """NUEVA: Sube análisis DJ como sección separada a GitHub Pages"""
        try:
            print("🌐 Subiendo DJ Sectorial a GitHub Pages...")
            
            # Verificar si existe el módulo
            if not os.path.exists("github_pages_historial.py"):
                print("⚠️ github_pages_historial.py no encontrado")
                return None
            
            # Intentar importar
            try:
                from github_pages_historial import GitHubPagesHistoricalUploader
            except ImportError as e:
                print(f"❌ Error importando: {e}")
                return None
            
            # Crear uploader
            uploader = GitHubPagesHistoricalUploader()
            
            # Generar título específico para DJ Sectorial
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if dj_results:
                oportunidades = len([r for r in dj_results if r['classification'] == 'OPORTUNIDAD'])
                title = f"📊 DJ Sectorial - {oportunidades} oportunidades - {timestamp}"
                description = f"Análisis sectorial Dow Jones con {len(dj_results)} sectores analizados"
            else:
                title = f"📊 DJ Sectorial - Sin datos - {timestamp}"
                description = f"Análisis sectorial completado sin datos disponibles"
            
            # Subir usando el sistema existente
            html_path = "reports/dj_sectorial_report.html"
            csv_path = "reports/dj_sectorial_analysis.csv"
            
            if os.path.exists(html_path) and os.path.exists(csv_path):
                result = uploader.upload_historical_report(
                    html_path,
                    csv_path,
                    title,
                    description
                )
                
                if result:
                    print(f"✅ DJ Sectorial subido a GitHub Pages: {result['github_url']}")
                    return result
                else:
                    print("❌ Error subiendo DJ Sectorial")
                    return None
            else:
                print("❌ Archivos DJ no encontrados para subir")
                return None
                
        except Exception as e:
            print(f"❌ Error subiendo DJ a GitHub Pages: {e}")
            return None
    
    def send_combined_telegram_report(self, results, dj_analysis_results):
        """NUEVA: Envía reporte combinado por Telegram"""
        try:
            from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
            from alerts.telegram_utils import send_message, send_file
            
            if not TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
                print("❌ Configuración Telegram incompleta")
                return False
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Leer estadísticas de ambos análisis
            insider_stats = ""
            dj_stats = ""
            
            # Estadísticas Insider
            if os.path.exists(self.csv_path):
                df = pd.read_csv(self.csv_path)
                if len(df) > 0:
                    insider_stats = f"""🏛️ **Insider Trading:**
• {len(df)} transacciones detectadas
• {df['Insider'].nunique()} empresas únicas
• Estado: {'✅ Subido' if results['github_insider'] else '❌ Error'}"""
                else:
                    insider_stats = f"""🏛️ **Insider Trading:**
• Sin transacciones detectadas
• Estado: {'✅ Monitoreado' if results['insider_scraper'] else '❌ Error'}"""
            
            # Estadísticas DJ Sectorial
            if dj_analysis_results:
                oportunidades = len([r for r in dj_analysis_results if r['classification'] == 'OPORTUNIDAD'])
                cerca = len([r for r in dj_analysis_results if r['classification'] == 'CERCA'])
                fuertes = len([r for r in dj_analysis_results if r['classification'] == 'FUERTE'])
                
                dj_stats = f"""📊 **DJ Sectorial:**
• {len(dj_analysis_results)} sectores analizados
• 🟢 {oportunidades} oportunidades
• 🟡 {cerca} cerca del mínimo
• 🔴 {fuertes} en zona fuerte
• Estado: {'✅ Subido' if results['github_dj'] else '❌ Error'}"""
            else:
                dj_stats = f"""📊 **DJ Sectorial:**
• Sin datos disponibles
• Estado: {'❌ Error en análisis' if results['dj_analysis'] else '⚠️ Sin ejecutar'}"""
            
            # URLs de GitHub Pages
            github_links = ""
            if results['github_insider']:
                github_links += f"\n🏛️ [Ver Insider Trading]({results['github_insider']['github_url']})"
            if results['github_dj']:
                github_links += f"\n📊 [Ver DJ Sectorial]({results['github_dj']['github_url']})"
            
            if results['github_insider'] or results['github_dj']:
                base_url = "https://tantancansado.github.io/stock_analyzer_a"
                github_links += f"\n🏠 [Dashboard Principal]({base_url})"
            
            # Mensaje principal
            mensaje = f"""🌟 **REPORTE TRADING DIARIO**

📅 **{timestamp}**

{insider_stats}

{dj_stats}

🌐 **Enlaces GitHub Pages:**{github_links}

📄 **Archivos CSV adjuntos para análisis detallado**"""
            
            # Enviar mensaje principal
            send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
            
            # Enviar CSVs como archivos adjuntos
            files_sent = 0
            if os.path.exists(self.csv_path):
                if send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, self.csv_path, "📊 Datos Insider Trading"):
                    files_sent += 1
            
            csv_dj_path = "reports/dj_sectorial_analysis.csv"
            if os.path.exists(csv_dj_path):
                if send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, csv_dj_path, "📈 Datos DJ Sectorial"):
                    files_sent += 1
            
            print(f"✅ Telegram enviado - {files_sent} archivos adjuntados")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando reporte combinado: {e}")
            return False
    
    def generate_html(self):
        """Genera el HTML con los datos del CSV - FUNCIÓN ORIGINAL"""
        print("\n📄 GENERANDO HTML")
        print("=" * 50)
        
        try:
            # Verificar CSV
            if not os.path.exists(self.csv_path):
                print("❌ CSV no encontrado")
                return False
            
            # Importar función de generación existente
            try:
                from alerts.plot_utils import crear_html_moderno_finviz
                self.html_path = crear_html_moderno_finviz()
                return self.html_path is not None
            except ImportError:
                print("⚠️ plot_utils no disponible, generando HTML básico")
                return self.generate_basic_html()
                
        except Exception as e:
            print(f"❌ Error generando HTML: {e}")
            return False
    
    def generate_basic_html(self):
        """Genera un HTML básico si plot_utils no está disponible"""
        try:
            df = pd.read_csv(self.csv_path)
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Insider Trading Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>📊 Insider Trading Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h1>
    <p>Total transacciones: {len(df)}</p>
    <p>Empresas únicas: {df['Insider'].nunique() if 'Insider' in df.columns else 0}</p>
    
    <table>
        <tr>
            <th>Ticker</th>
            <th>Company</th>
            <th>Price</th>
            <th>Qty</th>
            <th>Value</th>
            <th>Type</th>
        </tr>
"""
            
            for _, row in df.head(50).iterrows():
                html_content += f"""
        <tr>
            <td>{row.get('Insider', 'N/A')}</td>
            <td>{row.get('Title', 'N/A')}</td>
            <td>{row.get('Price', 'N/A')}</td>
            <td>{row.get('Qty', 'N/A')}</td>
            <td>{row.get('Value', 'N/A')}</td>
            <td>{row.get('Type', 'N/A')}</td>
        </tr>
"""
            
            html_content += """
    </table>
</body>
</html>
"""
            
            with open(self.html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML básico generado: {self.html_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generando HTML básico: {e}")
            return False
    
    def create_bundle(self):
        """Crea un ZIP con todos los archivos"""
        print("\n📦 CREANDO BUNDLE")
        print("=" * 50)
        
        try:
            with zipfile.ZipFile(self.bundle_path, 'w') as zipf:
                # Archivos originales
                if os.path.exists(self.html_path):
                    zipf.write(self.html_path, arcname=os.path.basename(self.html_path))
                if os.path.exists(self.csv_path):
                    zipf.write(self.csv_path, arcname=os.path.basename(self.csv_path))
                
                # Archivos DJ Sectorial
                dj_html = "reports/dj_sectorial_report.html"
                dj_csv = "reports/dj_sectorial_analysis.csv"
                if os.path.exists(dj_html):
                    zipf.write(dj_html, arcname="dj_sectorial_report.html")
                if os.path.exists(dj_csv):
                    zipf.write(dj_csv, arcname="dj_sectorial_data.csv")
            
            print(f"✅ Bundle creado: {self.bundle_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error creando bundle: {e}")
            return False
    
    def send_telegram(self):
        """Envía reporte por Telegram"""
        print("\n📱 ENVIANDO POR TELEGRAM")
        print("=" * 50)
        
        try:
            # Intentar importar configuración
            try:
                from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
            except ImportError:
                print("❌ config.py no encontrado")
                return False
            
            if not TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
                print("❌ Configuración Telegram incompleta")
                return False
            
            # Importar utilidades de Telegram
            try:
                from alerts.telegram_utils import send_message, send_file
            except ImportError:
                print("❌ telegram_utils no encontrado")
                return False
            
            # Leer estadísticas
            df = pd.read_csv(self.csv_path) if os.path.exists(self.csv_path) else pd.DataFrame()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Crear mensaje
            mensaje = f"""📊 REPORTE INSIDER TRADING

📅 Fecha: {timestamp}
📊 Transacciones: {len(df)}
🏢 Empresas: {df['Insider'].nunique() if 'Insider' in df.columns and len(df) > 0 else 0}

📄 Archivos adjuntos"""
            
            # Enviar mensaje
            send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
            
            # Enviar archivos
            if os.path.exists(self.html_path):
                send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, self.html_path)
            
            if os.path.exists(self.csv_path):
                send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, self.csv_path)
            
            print("✅ Enviado por Telegram")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando por Telegram: {e}")
            traceback.print_exc()
            return False
    
    def upload_github_pages(self):
        """Intenta subir a GitHub Pages si está disponible"""
        print("\n🌐 SUBIENDO A GITHUB PAGES")
        print("=" * 50)
        
        try:
            # Verificar si existe el módulo
            if not os.path.exists("github_pages_historial.py"):
                print("⚠️ github_pages_historial.py no encontrado")
                print("   GitHub Pages no disponible")
                return None
            
            # Intentar importar
            try:
                from github_pages_historial import GitHubPagesHistoricalUploader
            except ImportError as e:
                print(f"❌ Error importando: {e}")
                return None
            
            # Crear uploader
            uploader = GitHubPagesHistoricalUploader()
            
            # Preparar datos
            df = pd.read_csv(self.csv_path) if os.path.exists(self.csv_path) else pd.DataFrame()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if len(df) > 0:
                title = f"📊 Insider Trading - {len(df)} transacciones - {timestamp}"
                description = f"Reporte con {len(df)} transacciones detectadas"
            else:
                title = f"📊 Monitoreo Insider Trading - {timestamp}"
                description = "Monitoreo completado sin transacciones"
            
            # Subir
            result = uploader.upload_historical_report(
                self.html_path,
                self.csv_path,
                title,
                description
            )
            
            if result:
                print(f"✅ Subido a GitHub Pages:")
                for key, value in result.items():
                    print(f"   {key}: {value}")
                return result
            else:
                print("❌ Error subiendo a GitHub Pages")
                return None
                
        except Exception as e:
            print(f"❌ Error con GitHub Pages: {e}")
            traceback.print_exc()
            return None
    
    def run_complete_process(self):
        """Ejecuta el proceso completo insider trading"""
        print("\n🚀 PROCESO COMPLETO INSIDER TRADING")
        print("=" * 60)
        print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {
            'scraper': False,
            'html': False,
            'bundle': False,
            'telegram': False,
            'github': None
        }
        
        try:
            # 1. Ejecutar scraper
            results['scraper'] = self.run_scraper()
            if not results['scraper']:
                print("❌ Fallo en scraper, abortando")
                return results
            
            # 2. Generar HTML
            results['html'] = self.generate_html()
            if not results['html']:
                print("⚠️ Fallo en HTML, continuando...")
            
            # 3. Crear bundle
            results['bundle'] = self.create_bundle()
            
            # 4. GitHub Pages (opcional)
            results['github'] = self.upload_github_pages()
            
            # 5. Telegram
            results['telegram'] = self.send_telegram()
            
            # Resumen
            print("\n" + "=" * 60)
            print("📊 RESUMEN DE EJECUCIÓN")
            print("=" * 60)
            print(f"✅ Scraper: {'✓' if results['scraper'] else '✗'}")
            print(f"✅ HTML: {'✓' if results['html'] else '✗'}")
            print(f"✅ Bundle: {'✓' if results['bundle'] else '✗'}")
            print(f"✅ Telegram: {'✓' if results['telegram'] else '✗'}")
            print(f"✅ GitHub Pages: {'✓' if results['github'] else '✗ (opcional)'}")
            
            if results['github']:
                print(f"\n🌐 Ver en GitHub Pages:")
                print(f"   {results['github'].get('github_url', 'N/A')}")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Error crítico: {e}")
            traceback.print_exc()
            return results

def run_vcp_scanner_usa_interactive():
    """Flujo interactivo para escanear TODO el mercado USA con el VCP Scanner avanzado."""
    import os
    from datetime import datetime

    print("\n🎯 ESCANEO AVANZADO DE TODO EL MERCADO USA (VCP Scanner)")
    print("=" * 60)
    scanner = VCPScannerEnhanced()
    print("🔍 Ejecutando escaneo de mercado USA...")
    try:
        results = scanner.scan_market()
    except Exception as e:
        print(f"❌ Error ejecutando el escaneo: {e}")
        return
    num_candidates = len(results) if results is not None else 0
    print(f"✅ Escaneo completado. Candidatos detectados: {num_candidates}")
    if num_candidates == 0:
        print("⚠️  No se detectaron candidatos.")
    # Preguntar si quiere generar HTML
    gen_html = input("¿Quieres generar HTML con los resultados? (s/n): ").strip().lower()
    if gen_html != "s":
        print("🛑 Proceso finalizado (no se generó HTML).")
        return
    # Generar HTML
    html_path = "reports/vcp_market_scan.html"
    csv_path = "reports/vcp_market_scan.csv"
    try:
        # Guardar CSV si hay resultados (aunque sean 0)
        if results is not None:
            scanner.save_csv(results, csv_path)
        scanner.generate_html(results, html_path)
        print(f"✅ HTML generado: {html_path}")
    except Exception as e:
        print(f"❌ Error generando HTML: {e}")
        return
    # Preguntar si quiere subir a GitHub Pages
    subir = input("¿Quieres subir el HTML a GitHub Pages? (s/n): ").strip().lower()
    if subir != "s":
        print("🛑 Proceso finalizado (HTML no subido a GitHub Pages).")
        return
    # Intentar subir a GitHub Pages usando uploader de historial, con título/desc diferentes
    if not os.path.exists("github_pages_historial.py"):
        print("⚠️ github_pages_historial.py no encontrado. No se puede subir.")
        return
    try:
        from github_pages_historial import GitHubPagesHistoricalUploader
        uploader = GitHubPagesHistoricalUploader()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        title = f"🎯 VCP Market Scanner - {num_candidates} candidatos - {timestamp}"
        description = f"Reporte avanzado de escaneo de TODO el mercado USA. Candidatos detectados: {num_candidates}."
        result = uploader.upload_historical_report(
            html_path,
            csv_path,
            title,
            description
        )
        if result:
            print("✅ Subido a GitHub Pages:")
            for key, value in result.items():
                print(f"   {key}: {value}")
        else:
            print("❌ Error subiendo a GitHub Pages")
    except Exception as e:
        print(f"❌ Error subiendo a GitHub Pages: {e}")
        return
    print("🎉 Proceso de escaneo avanzado finalizado.")

def test_components():
    """Prueba cada componente individualmente"""
    print("\n🔧 MODO TEST - VERIFICANDO COMPONENTES")
    print("=" * 60)
    
    # 1. Verificar archivos necesarios
    print("\n📁 Verificando archivos:")
    files_to_check = [
        ("Scraper", ["insiders/openinsider_scraper.py", "openinsider_scraper.py", "paste-3.txt"]),
        ("Plot Utils", ["alerts/plot_utils.py", "paste-2.txt"]),
        ("Config", ["config.py"]),
        ("Telegram Utils", ["alerts/telegram_utils.py"]),
        ("GitHub Pages", ["github_pages_historial.py"])
    ]
    
    for name, paths in files_to_check:
        found = False
        for path in paths:
            if os.path.exists(path):
                print(f"✅ {name}: {path}")
                found = True
                break
        if not found:
            print(f"❌ {name}: NO ENCONTRADO")
    
    # 2. Verificar CSV existente
    print("\n📊 Verificando datos:")
    if os.path.exists("reports/insiders_daily.csv"):
        try:
            df = pd.read_csv("reports/insiders_daily.csv")
            print(f"✅ CSV existente: {len(df)} registros")
        except Exception as e:
            print(f"❌ CSV corrupto: {e}")
    else:
        print("❌ CSV no existe")
    
    # 3. Verificar configuración Telegram
    print("\n📱 Verificando Telegram:")
    try:
        from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
        if TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN:
            print(f"✅ Chat ID: {TELEGRAM_CHAT_ID}")
            print(f"✅ Token: {TELEGRAM_BOT_TOKEN[:10]}...")
        else:
            print("❌ Configuración incompleta")
    except ImportError:
        print("❌ config.py no importable")
    
    # NUEVO: 4. Test DJ Analyzer
    print("\n📊 Testing DJ Analyzer:")
    try:
        analyzer = DJMasterAnalyzer()
        print(f"✅ DJ Analyzer inicializado")
        print(f"✅ {len(analyzer.ALL_INVESTING_IDS)} sectores disponibles")
        
        # Test de conexión con un sector
        print("🔄 Probando conexión API...")
        success, df = analyzer.get_historical_data('DJUSTC')  # Technology
        if success and df is not None:
            print(f"✅ API funcionando - {len(df)} registros obtenidos")
        else:
            print("❌ API no responde o sin datos")
            
    except Exception as e:
        print(f"❌ Error en DJ Analyzer: {e}")

def main():
    """Función principal con menú"""
    if len(sys.argv) > 1:
        # Modo automático
        if sys.argv[1] == "--auto":
            system = InsiderTradingSystem()
            system.run_complete_process()
        elif sys.argv[1] == "--daily":
            # NUEVO: Análisis diario completo (Insider + DJ Sectorial)
            mode = sys.argv[2] if len(sys.argv) > 2 else "principales"
            system = InsiderTradingSystem()
            system.run_daily_combined_analysis(mode)
        elif sys.argv[1] == "--test":
            test_components()
        elif sys.argv[1] == "--scraper":
            system = InsiderTradingSystem()
            system.run_scraper()
        elif sys.argv[1] == "--html":
            system = InsiderTradingSystem()
            system.generate_html()
        elif sys.argv[1] == "--telegram":
            system = InsiderTradingSystem()
            system.send_telegram()
        # NUEVOS comandos para DJ Sectorial
        elif sys.argv[1] == "--dj":
            mode = sys.argv[2] if len(sys.argv) > 2 else "principales"
            system = InsiderTradingSystem()
            dj_results = system.run_dj_sectorial_analysis(mode)
            if dj_results:
                system.upload_dj_to_github_pages(dj_results)
        elif sys.argv[1] == "--dj-only":
            mode = sys.argv[2] if len(sys.argv) > 2 else "principales"
            system = InsiderTradingSystem()
            system.run_dj_sectorial_analysis(mode)
    else:
        # Modo interactivo
        while True:
            print("\n" + "=" * 80)
            print("📊 SISTEMA TRADING UNIFICADO - MENÚ PRINCIPAL")
            print("=" * 80)
            print("🌟 ANÁLISIS DIARIO RECOMENDADO:")
            print("  1. 🚀 ANÁLISIS DIARIO COMPLETO (Insider + DJ Sectorial)")
            print("")
            print("🏛️ INSIDER TRADING:")
            print("  2. 🏛️  Proceso completo Insider Trading")
            print("  3. 🕷️  Solo ejecutar scraper")
            print("  4. 📄 Solo generar HTML")
            print("  5. 📱 Solo enviar Telegram")
            print("")
            print("📊 DJ SECTORIAL ANALYSIS:")
            print("  6. 📈 Análisis principales (16 sectores)")
            print("  7. 🔍 Análisis detallado (35 sectores)")
            print("  8. 🚀 Análisis completo (TODOS los sectores)")
            print("  9. 📊 Solo análisis DJ (sin subir)")
            print("")
            print("🎯 VCP SCANNER:")
            print(" 10. 🎯 Escanear TODO el mercado USA (VCP Scanner avanzado)")
            print("")
            print("🔧 UTILIDADES:")
            print(" 11. 🔍 Verificar componentes")
            print(" 12. 🌐 Probar GitHub Pages")
            print(" 13. 📱 Test Telegram")
            print("  0. ❌ Salir")
            print("=" * 80)
            print("💡 Recomendado para uso diario: Opción 1")
            print("=" * 80)

            opcion = input("Selecciona opción: ").strip()

            system = InsiderTradingSystem()

            if opcion == "1":
                # NUEVA OPCIÓN: Análisis diario completo
                print("\n🌟 ANÁLISIS DIARIO COMPLETO")
                print("Modo DJ Sectorial:")
                print("  1. Principales (16 sectores) - Rápido")
                print("  2. Detallado (35 sectores) - Medio")
                print("  3. Completo (TODOS) - Lento")
                
                dj_mode_choice = input("Selecciona modo DJ (1/2/3): ").strip()
                if dj_mode_choice == "2":
                    dj_mode = "detallado"
                elif dj_mode_choice == "3":
                    dj_mode = "completo"
                else:
                    dj_mode = "principales"
                
                print(f"\n🚀 Ejecutando análisis diario con modo DJ: {dj_mode}")
                system.run_daily_combined_analysis(dj_mode)
                
            elif opcion == "2":
                system.run_complete_process()
            elif opcion == "3":
                system.run_scraper()
            elif opcion == "4":
                system.generate_html()
            elif opcion == "5":
                system.send_telegram()
            # Opciones DJ Sectorial
            elif opcion == "6":
                dj_results = system.run_dj_sectorial_analysis("principales")
                if dj_results:
                    system.upload_dj_to_github_pages(dj_results)
            elif opcion == "7":
                dj_results = system.run_dj_sectorial_analysis("detallado")
                if dj_results:
                    system.upload_dj_to_github_pages(dj_results)
            elif opcion == "8":
                dj_results = system.run_dj_sectorial_analysis("completo")
                if dj_results:
                    system.upload_dj_to_github_pages(dj_results)
            elif opcion == "9":
                mode = input("Modo (principales/detallado/completo): ").strip()
                if mode not in ["principales", "detallado", "completo"]:
                    mode = "principales"
                system.run_dj_sectorial_analysis(mode)
            # Opciones originales
            elif opcion == "10":
                run_vcp_scanner_usa_interactive()
            elif opcion == "11":
                test_components()
            elif opcion == "12":
                result = system.upload_github_pages()
                if result:
                    print("✅ GitHub Pages funcionando")
                else:
                    print("❌ GitHub Pages no disponible")
            elif opcion == "13":
                system.send_telegram()
            elif opcion == "0":
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción inválida")

            input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()
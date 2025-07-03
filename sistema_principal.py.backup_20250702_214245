#!/usr/bin/env python3
"""
Sistema Unificado de Insider Trading + DJ Sectorial + Market Breadth Analyzer
Versión COMPLETA con Market Breadth integrado - Con GitHub Pages funcionando
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
import shutil
from pathlib import Path
import traceback

# Importar Market Breadth Analyzer
try:
    from market_breadth_analyzer import MarketBreadthAnalyzer, MarketBreadthHTMLGenerator
    MARKET_BREADTH_AVAILABLE = True
    print("✅ Market Breadth Analyzer cargado")
except ImportError:
    print("⚠️ Market Breadth Analyzer no disponible")
    MARKET_BREADTH_AVAILABLE = False

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

# Importar templates HTML
try:
    from templates.html_generator import HTMLGenerator, generate_html_report
    HTML_TEMPLATES_AVAILABLE = True
except ImportError:
    print("⚠️ Templates HTML no disponibles - usando fallback básico")
    HTML_TEMPLATES_AVAILABLE = False

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

class GitHubPagesUploader:
    """
    NUEVA CLASE: Uploader integrado para GitHub Pages
    """
    def __init__(self):
        self.repo_path = Path("docs")
        self.reports_path = self.repo_path / "reports"
        self.manifest_file = self.repo_path / "manifest.json"
        self.index_file = self.repo_path / "index.html"
        self.base_url = "https://tantancansado.github.io/stock_analyzer_a"
        
        # Inicializar templates si están disponibles
        try:
            from templates.github_pages_templates import GitHubPagesTemplates
            self.templates = GitHubPagesTemplates(self.base_url)
            self.templates_available = True
        except ImportError:
            self.templates = None
            self.templates_available = False
        
        self.setup_directories()
    
    def setup_directories(self):
        """Crea la estructura de directorios necesaria"""
        try:
            self.repo_path.mkdir(exist_ok=True)
            self.reports_path.mkdir(exist_ok=True)
            (self.reports_path / "daily").mkdir(exist_ok=True)
            (self.reports_path / "dj_sectorial").mkdir(exist_ok=True)
            (self.reports_path / "market_breadth").mkdir(exist_ok=True)  # NUEVO
            
            # Crear archivo .nojekyll
            nojekyll = self.repo_path / ".nojekyll"
            if not nojekyll.exists():
                nojekyll.touch()
        except Exception as e:
            print(f"❌ Error creando directorios: {e}")
    
    def load_manifest(self):
        """Carga el manifest de reportes"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "total_reports": 0,
            "total_dj_reports": 0,
            "total_breadth_reports": 0,  # NUEVO
            "last_update": None,
            "reports": [],
            "dj_reports": [],
            "breadth_reports": [],  # NUEVO
            "base_url": self.base_url
        }
    
    def save_manifest(self, manifest):
        """Guarda el manifest"""
        try:
            with open(self.manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error guardando manifest: {e}")
            return False
    
    def upload_report(self, html_file, csv_file, title, description):
        """Sube un reporte a GitHub Pages"""
        try:
            # Determinar tipo de reporte
            if "DJ Sectorial" in title or "sectorial" in title.lower():
                report_type = "dj_sectorial"
            elif "Market Breadth" in title or "breadth" in title.lower():
                report_type = "market_breadth"  # NUEVO
            else:
                report_type = "insider"
            
            # Verificar archivos
            if not os.path.exists(html_file) or not os.path.exists(csv_file):
                print(f"❌ Archivos no encontrados: {html_file}, {csv_file}")
                return None
            
            timestamp = datetime.now()
            date_only = timestamp.strftime('%Y-%m-%d')
            
            # Crear ID y carpeta
            if report_type == "dj_sectorial":
                report_id = f"dj_sectorial_{date_only}"
                report_dir = self.reports_path / "dj_sectorial" / report_id
            elif report_type == "market_breadth":
                report_id = f"market_breadth_{date_only}"
                report_dir = self.reports_path / "market_breadth" / report_id
            else:
                report_id = f"report_{date_only}"
                report_dir = self.reports_path / "daily" / report_id
            
            report_dir.mkdir(exist_ok=True, parents=True)
            
            # Copiar archivos
            shutil.copy2(html_file, report_dir / "index.html")
            shutil.copy2(csv_file, report_dir / "data.csv")
            
            # Actualizar manifest
            manifest = self.load_manifest()
            
            # Crear entrada del reporte
            if report_type == "dj_sectorial":
                base_path = f"reports/dj_sectorial/{report_id}"
            elif report_type == "market_breadth":
                base_path = f"reports/market_breadth/{report_id}"
            else:
                base_path = f"reports/daily/{report_id}"
            
            report_entry = {
                "id": report_id,
                "title": title,
                "description": description,
                "timestamp": timestamp.isoformat(),
                "date": timestamp.strftime('%Y-%m-%d'),
                "time": timestamp.strftime('%H:%M:%S'),
                "html_url": f"{base_path}/index.html",
                "csv_url": f"{base_path}/data.csv",
                "full_url": f"{self.base_url}/{base_path}/index.html",
                "type": report_type
            }
            
            # Actualizar lista de reportes
            if report_type == "dj_sectorial":
                if 'dj_reports' not in manifest:
                    manifest['dj_reports'] = []
                manifest["dj_reports"].insert(0, report_entry)
                manifest["total_dj_reports"] = len(manifest["dj_reports"])
            elif report_type == "market_breadth":
                if 'breadth_reports' not in manifest:
                    manifest['breadth_reports'] = []
                manifest["breadth_reports"].insert(0, report_entry)
                manifest["total_breadth_reports"] = len(manifest["breadth_reports"])
            else:
                manifest["reports"].insert(0, report_entry)
                manifest["total_reports"] = len(manifest["reports"])
            
            manifest["last_update"] = timestamp.isoformat()
            
            # Guardar manifest
            self.save_manifest(manifest)
            
            # Generar páginas
            self.generate_all_pages(manifest)
            
            # Git commit
            self.git_push(report_id)
            
            return {
                "success": True,
                "report_id": report_id,
                "github_url": f"{self.base_url}/{base_path}/index.html",
                "type": report_type
            }
            
        except Exception as e:
            print(f"❌ Error subiendo reporte: {e}")
            traceback.print_exc()
            return None
    
    def generate_all_pages(self, manifest):
        """Genera todas las páginas usando templates"""
        try:
            if self.templates_available:
                # Usar templates Liquid Glass
                html_content = self.templates.generate_main_dashboard_with_breadth(manifest)
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Generar página DJ Sectorial
                dj_content = self.templates.generate_dj_sectorial_page(manifest)
                with open(self.repo_path / "dj_sectorial.html", 'w', encoding='utf-8') as f:
                    f.write(dj_content)
                
                # Generar página Market Breadth (NUEVO)
                breadth_content = self.templates.generate_breadth_page(manifest)
                with open(self.repo_path / "market_breadth.html", 'w', encoding='utf-8') as f:
                    f.write(breadth_content)
                
                print("✅ Páginas generadas con diseño Liquid Glass")
            else:
                # Fallback básico
                self.generate_basic_pages(manifest)
                print("✅ Páginas generadas con diseño básico")
            
        except Exception as e:
            print(f"❌ Error generando páginas: {e}")
    
    def generate_basic_pages(self, manifest):
        """Fallback básico si no hay templates"""
        total_reports = manifest['total_reports']
        total_dj = manifest.get('total_dj_reports', 0)
        total_breadth = manifest.get('total_breadth_reports', 0)
        
        basic_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Trading Analytics</title>
<style>body{{background:#020617;color:white;font-family:Arial;padding:20px;}}
.card{{background:rgba(255,255,255,0.1);padding:20px;margin:20px 0;border-radius:12px;}}
.stat{{display:inline-block;margin:20px;text-align:center;}}
.stat-num{{font-size:2em;color:#4a90e2;}}</style></head>
<body><div class="card"><h1>📊 Trading Analytics System</h1></div>
<div class="card"><h2>📈 Estadísticas</h2>
<div class="stat"><div class="stat-num">{total_reports}</div><div>Reportes Insider</div></div>
<div class="stat"><div class="stat-num">{total_dj}</div><div>Análisis DJ</div></div>
<div class="stat"><div class="stat-num">{total_breadth}</div><div>Market Breadth</div></div>
</div></body></html>"""
        
        with open(self.index_file, 'w', encoding='utf-8') as f:
            f.write(basic_html)
    
    def git_push(self, report_id):
        """Intenta hacer push automático a GitHub"""
        try:
            if not os.path.exists(".git"):
                return False
            
            subprocess.run(["git", "add", "docs/"], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"📊 {report_id}"], check=True, capture_output=True)
            subprocess.run(["git", "push"], check=True, capture_output=True)
            return True
        except:
            return False

class InsiderTradingSystem:
    """Sistema principal que gestiona todo el flujo"""
    
    def __init__(self):
        self.csv_path = "reports/insiders_daily.csv"
        self.html_path = "reports/insiders_report_completo.html"
        self.bundle_path = "reports/insiders_report_bundle.zip"
        
        # Inicializar DJ Analyzer
        self.dj_analyzer = DJMasterAnalyzer()
        
        # Inicializar GitHub Pages Uploader
        self.github_uploader = GitHubPagesUploader()
        
        # Inicializar generador HTML
        if HTML_TEMPLATES_AVAILABLE:
            self.html_generator = HTMLGenerator()
        else:
            self.html_generator = None
        
        self.setup_directories()
    
    def setup_directories(self):
        """Crea los directorios necesarios"""
        os.makedirs("reports", exist_ok=True)
        os.makedirs("alerts", exist_ok=True)
        os.makedirs("templates", exist_ok=True)
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
                "paste-3.txt"
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
    
    def run_dj_sectorial_analysis(self, mode="principales"):
        """Ejecuta el análisis sectorial de Dow Jones"""
        print("\n📊 EJECUTANDO ANÁLISIS SECTORIAL DJ")
        print("=" * 50)
        
        try:
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
            
            results = self.dj_analyzer.batch_analysis(tickers, batch_size=5)
            self.dj_analyzer.generate_report(results)
            
            if results:
                self.save_dj_results_to_csv(results)
                self.generate_dj_html(results)
            
            print(f"\n✅ ANÁLISIS DJ COMPLETADO: {len(results)} sectores procesados")
            return results
            
        except Exception as e:
            print(f"❌ Error en análisis DJ: {e}")
            traceback.print_exc()
            return []
    
    def run_market_breadth_analysis(self):
        """Ejecuta análisis de amplitud de mercado - NUEVO"""
        print("\n📊 EJECUTANDO ANÁLISIS DE AMPLITUD DE MERCADO")
        print("=" * 60)
        
        try:
            if not MARKET_BREADTH_AVAILABLE:
                print("❌ Market Breadth Analyzer no disponible")
                return None
            
            analyzer = MarketBreadthAnalyzer()
            analysis_result = analyzer.run_breadth_analysis()
            
            if analysis_result:
                # Guardar CSV
                csv_path = analyzer.save_to_csv(analysis_result)
                
                # Generar HTML
                html_generator = MarketBreadthHTMLGenerator(self.github_uploader.base_url)
                html_content = html_generator.generate_breadth_html(analysis_result)
                
                if html_content:
                    html_path = "reports/market_breadth_report.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print(f"✅ HTML generado: {html_path}")
                    
                    return {
                        'analysis_result': analysis_result,
                        'html_path': html_path,
                        'csv_path': csv_path
                    }
                else:
                    print("❌ Error generando HTML")
                    return None
            else:
                print("❌ Error en análisis")
                return None
                
        except Exception as e:
            print(f"❌ Error en análisis de amplitud: {e}")
            traceback.print_exc()
            return None
    
    def upload_breadth_to_github_pages(self, breadth_results):
        """Sube análisis de amplitud a GitHub Pages - NUEVO"""
        try:
            if not breadth_results:
                return None
            
            analysis_result = breadth_results['analysis_result']
            summary = analysis_result['summary']
            timestamp = analysis_result['analysis_date']
            
            title = f"📊 Market Breadth - {summary['market_bias']} - {timestamp}"
            description = f"Análisis de amplitud con {summary['bullish_signals']} señales alcistas y {summary['bearish_signals']} bajistas"
            
            result = self.github_uploader.upload_report(
                breadth_results['html_path'],
                breadth_results['csv_path'],
                title,
                description
            )
            
            if result:
                print(f"✅ Market Breadth subido a GitHub Pages: {result['github_url']}")
                return result
            else:
                print("❌ Error subiendo Market Breadth")
                return None
                
        except Exception as e:
            print(f"❌ Error subiendo Market Breadth: {e}")
            return None
    
    def save_dj_results_to_csv(self, results):
        """Guarda los resultados del análisis DJ en CSV"""
        try:
            if not results:
                return False
            
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
    
    def generate_dj_html(self, results):
        """Genera HTML para análisis DJ usando templates externos"""
        print("\n📄 GENERANDO HTML DJ SECTORIAL")
        print("=" * 50)
        
        try:
            html_path = "reports/dj_sectorial_report.html"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if self.html_generator:
                html_content = self.html_generator.generate_dj_sectorial_html(results, timestamp)
            else:
                html_content = self._generate_basic_dj_html_fallback(results, timestamp)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML DJ generado: {html_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generando HTML DJ: {e}")
            traceback.print_exc()
            return False
    
    def _generate_basic_dj_html_fallback(self, results, timestamp):
        """Fallback básico para HTML DJ si no hay templates"""
        total_sectores = len(results) if results else 0
        oportunidades = len([r for r in results if r['classification'] == 'OPORTUNIDAD']) if results else 0
        
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>DJ Sectorial Report</title>
<style>body{{background:#0a0e1a;color:white;font-family:Arial;margin:20px;}}
h1{{color:#4a90e2;}}table{{width:100%;border-collapse:collapse;}}
th,td{{border:1px solid #4a5568;padding:8px;}}th{{background:#4a90e2;}}</style>
</head><body><h1>📊 DJ Sectorial - {timestamp}</h1>
<p>Total: {total_sectores} | Oportunidades: {oportunidades}</p><table>
<tr><th>Sector</th><th>Precio</th><th>Distancia</th><th>Estado</th></tr>"""
        
        if results:
            for r in sorted(results, key=lambda x: x['distance_pct']):
                html += f"<tr><td>{r['sector']}</td><td>${r['current_price']:.2f}</td><td>{r['distance_pct']:.1f}%</td><td>{r['estado']}</td></tr>"
        
        html += "</table></body></html>"
        return html
    
    def upload_github_pages(self):
        """Sube reporte insider a GitHub Pages"""
        print("\n🌐 SUBIENDO INSIDER A GITHUB PAGES")
        print("=" * 50)
        
        try:
            df = pd.read_csv(self.csv_path) if os.path.exists(self.csv_path) else pd.DataFrame()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if len(df) > 0:
                title = f"📊 Insider Trading - {len(df)} transacciones - {timestamp}"
                description = f"Reporte con {len(df)} transacciones detectadas"
            else:
                title = f"📊 Monitoreo Insider Trading - {timestamp}"
                description = "Monitoreo completado sin transacciones"
            
            result = self.github_uploader.upload_report(
                self.html_path,
                self.csv_path,
                title,
                description
            )
            
            if result:
                print(f"✅ Subido a GitHub Pages: {result['github_url']}")
                return result
            else:
                print("❌ Error subiendo a GitHub Pages")
                return None
                
        except Exception as e:
            print(f"❌ Error con GitHub Pages: {e}")
            traceback.print_exc()
            return None
    
    def upload_dj_to_github_pages(self, dj_results):
        """Sube análisis DJ a GitHub Pages"""
        try:
            print("🌐 Subiendo DJ Sectorial a GitHub Pages...")
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if dj_results:
                oportunidades = len([r for r in dj_results if r['classification'] == 'OPORTUNIDAD'])
                title = f"📊 DJ Sectorial - {oportunidades} oportunidades - {timestamp}"
                description = f"Análisis sectorial Dow Jones con {len(dj_results)} sectores analizados"
            else:
                title = f"📊 DJ Sectorial - Sin datos - {timestamp}"
                description = f"Análisis sectorial completado sin datos disponibles"
            
            html_path = "reports/dj_sectorial_report.html"
            csv_path = "reports/dj_sectorial_analysis.csv"
            
            if os.path.exists(html_path) and os.path.exists(csv_path):
                result = self.github_uploader.upload_report(
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
    
    def run_daily_combined_analysis(self, dj_mode="principales"):
        """Análisis diario completo - Insider Trading + DJ Sectorial"""
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
            
            results['insider_scraper'] = self.run_scraper()
            if results['insider_scraper']:
                results['insider_html'] = self.generate_html()
                results['github_insider'] = self.upload_github_pages()
            else:
                print("⚠️ Fallo en scraper insider, continuando con DJ...")
            
            print("\n🔸 FASE 2: DJ SECTORIAL")
            print("=" * 40)
            
            dj_analysis_results = self.run_dj_sectorial_analysis(dj_mode)
            results['dj_analysis'] = len(dj_analysis_results) > 0
            
            if results['dj_analysis']:
                results['dj_html'] = True
                results['github_dj'] = self.upload_dj_to_github_pages(dj_analysis_results)
            else:
                print("⚠️ Fallo en análisis DJ")
            
            print("\n🔸 FASE 3: NOTIFICACIÓN TELEGRAM")
            print("=" * 40)
            
            results['telegram'] = self.send_combined_telegram_report(results, dj_analysis_results)
            
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
            
            if results['github_insider']:
                print(f"\n🏛️ Ver Insider Trading: {results['github_insider'].get('github_url', 'N/A')}")
            if results['github_dj']:
                print(f"📊 Ver DJ Sectorial: {results['github_dj'].get('github_url', 'N/A')}")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Error crítico en análisis diario: {e}")
            traceback.print_exc()
            return results
    
    def run_daily_analysis_with_breadth(self, dj_mode="principales", include_breadth=True):
        """Análisis diario ULTRA completo - Insider + DJ + Market Breadth - NUEVO"""
        print("\n🌟 ANÁLISIS DIARIO ULTRA COMPLETO - INSIDER + DJ + MARKET BREADTH")
        print("=" * 80)
        print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {
            'insider_scraper': False,
            'insider_html': False,
            'dj_analysis': False,
            'dj_html': False,
            'breadth_analysis': False,
            'breadth_html': False,
            'github_insider': None,
            'github_dj': None,
            'github_breadth': None,
            'telegram': False
        }
        
        try:
            # FASE 1: INSIDER TRADING
            print("\n🔸 FASE 1: INSIDER TRADING")
            print("=" * 40)
            
            results['insider_scraper'] = self.run_scraper()
            if results['insider_scraper']:
                results['insider_html'] = self.generate_html()
                results['github_insider'] = self.upload_github_pages()
            
            # FASE 2: DJ SECTORIAL
            print("\n🔸 FASE 2: DJ SECTORIAL")
            print("=" * 40)
            
            dj_analysis_results = self.run_dj_sectorial_analysis(dj_mode)
            results['dj_analysis'] = len(dj_analysis_results) > 0
            
            if results['dj_analysis']:
                results['dj_html'] = True
                results['github_dj'] = self.upload_dj_to_github_pages(dj_analysis_results)
            
            # FASE 3: MARKET BREADTH (NUEVO)
            breadth_results = None
            if include_breadth and MARKET_BREADTH_AVAILABLE:
                print("\n🔸 FASE 3: MARKET BREADTH")
                print("=" * 40)
                
                breadth_results = self.run_market_breadth_analysis()
                results['breadth_analysis'] = breadth_results is not None
                
                if results['breadth_analysis']:
                    results['breadth_html'] = True
                    results['github_breadth'] = self.upload_breadth_to_github_pages(breadth_results)
            else:
                print("\n⚠️ FASE 3: MARKET BREADTH OMITIDA")
            
            # FASE 4: NOTIFICACIÓN TELEGRAM
            print("\n🔸 FASE 4: NOTIFICACIÓN TELEGRAM")
            print("=" * 40)
            
            results['telegram'] = self.send_ultra_telegram_report(results, dj_analysis_results, breadth_results)
            
            self.create_bundle()
            
            # Resumen final
            print("\n" + "=" * 80)
            print("🎉 RESUMEN ANÁLISIS ULTRA COMPLETO")
            print("=" * 80)
            print(f"🏛️ Insider Trading:")
            print(f"   • Scraper: {'✓' if results['insider_scraper'] else '✗'}")
            print(f"   • HTML: {'✓' if results['insider_html'] else '✗'}")
            print(f"   • GitHub Pages: {'✓' if results['github_insider'] else '✗'}")
            
            print(f"📊 DJ Sectorial:")
            print(f"   • Análisis: {'✓' if results['dj_analysis'] else '✗'}")
            print(f"   • HTML: {'✓' if results['dj_html'] else '✗'}")
            print(f"   • GitHub Pages: {'✓' if results['github_dj'] else '✗'}")
            
            print(f"📈 Market Breadth:")
            print(f"   • Análisis: {'✓' if results['breadth_analysis'] else '✗'}")
            print(f"   • HTML: {'✓' if results['breadth_html'] else '✗'}")
            print(f"   • GitHub Pages: {'✓' if results['github_breadth'] else '✗'}")
            
            print(f"📱 Telegram: {'✓' if results['telegram'] else '✗'}")
            
            # URLs de GitHub Pages
            if results['github_insider']:
                print(f"\n🏛️ Ver Insider Trading: {results['github_insider'].get('github_url', 'N/A')}")
            if results['github_dj']:
                print(f"📊 Ver DJ Sectorial: {results['github_dj'].get('github_url', 'N/A')}")
            if results['github_breadth']:
                print(f"📈 Ver Market Breadth: {results['github_breadth'].get('github_url', 'N/A')}")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Error crítico en análisis ultra completo: {e}")
            traceback.print_exc()
            return results
    
    def send_combined_telegram_report(self, results, dj_analysis_results):
        """Envía reporte combinado por Telegram"""
        try:
            from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
            from alerts.telegram_utils import send_message, send_file
            
            if not TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
                print("❌ Configuración Telegram incompleta")
                return False
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Estadísticas Insider
            insider_stats = ""
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
            dj_stats = ""
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
            
            mensaje = f"""🌟 **REPORTE TRADING DIARIO**

📅 **{timestamp}**

{insider_stats}

{dj_stats}

🌐 **Enlaces GitHub Pages:**{github_links}

📄 **Archivos CSV adjuntos para análisis detallado**"""
            
            send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
            
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
    
    def send_ultra_telegram_report(self, results, dj_analysis_results, breadth_results):
        """Envía reporte ultra completo por Telegram con Market Breadth - NUEVO"""
        try:
            from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
            from alerts.telegram_utils import send_message, send_file
            
            if not TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
                print("❌ Configuración Telegram incompleta")
                return False
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Estadísticas Insider
            insider_stats = ""
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
            dj_stats = ""
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
            
            # Estadísticas Market Breadth (NUEVO)
            breadth_stats = ""
            if breadth_results and results['breadth_analysis']:
                summary = breadth_results['analysis_result']['summary']
                breadth_stats = f"""📈 **Market Breadth:**
• Sesgo: {summary['market_bias']}
• Confianza: {summary['confidence']}
• 🟢 {summary['bullish_signals']} señales alcistas
• 🔴 {summary['bearish_signals']} señales bajistas
• 💪 Fuerza: {summary['strength_score']}
• Estado: {'✅ Subido' if results['github_breadth'] else '❌ Error'}"""
            else:
                breadth_stats = f"""📈 **Market Breadth:**
• Análisis de amplitud de mercado
• Estado: {'❌ Error' if MARKET_BREADTH_AVAILABLE else '⚠️ No disponible'}"""
            
            # URLs de GitHub Pages
            github_links = ""
            if results['github_insider']:
                github_links += f"\n🏛️ [Ver Insider Trading]({results['github_insider']['github_url']})"
            if results['github_dj']:
                github_links += f"\n📊 [Ver DJ Sectorial]({results['github_dj']['github_url']})"
            if results['github_breadth']:
                github_links += f"\n📈 [Ver Market Breadth]({results['github_breadth']['github_url']})"
            
            if github_links:
                base_url = "https://tantancansado.github.io/stock_analyzer_a"
                github_links += f"\n🏠 [Dashboard Principal]({base_url})"
            
            mensaje = f"""🌟 **REPORTE TRADING ULTRA COMPLETO**

📅 **{timestamp}**

{insider_stats}

{dj_stats}

{breadth_stats}

🌐 **Enlaces GitHub Pages:**{github_links}

📄 **Archivos CSV adjuntos para análisis detallado**"""
            
            send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
            
            # Enviar archivos CSV
            files_sent = 0
            
            # CSV Insider
            if os.path.exists(self.csv_path):
                if send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, self.csv_path, "📊 Datos Insider Trading"):
                    files_sent += 1
            
            # CSV DJ Sectorial
            csv_dj_path = "reports/dj_sectorial_analysis.csv"
            if os.path.exists(csv_dj_path):
                if send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, csv_dj_path, "📈 Datos DJ Sectorial"):
                    files_sent += 1
            
            # CSV Market Breadth (NUEVO)
            csv_breadth_path = "reports/market_breadth_analysis.csv"
            if os.path.exists(csv_breadth_path) and results['breadth_analysis']:
                if send_file(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, csv_breadth_path, "📊 Datos Market Breadth"):
                    files_sent += 1
            
            print(f"✅ Telegram ultra completo enviado - {files_sent} archivos adjuntados")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando reporte ultra completo: {e}")
            return False
    
    def generate_html(self):
        """Genera el HTML con los datos del CSV usando templates externos"""
        print("\n📄 GENERANDO HTML INSIDER TRADING")
        print("=" * 50)
        
        try:
            if not os.path.exists(self.csv_path):
                print("❌ CSV no encontrado")
                return False
            
            try:
                from alerts.plot_utils import crear_html_moderno_finviz
                self.html_path = crear_html_moderno_finviz()
                return self.html_path is not None
            except ImportError:
                print("⚠️ plot_utils no disponible, usando templates propios")
                return self.generate_insider_html_with_templates()
                
        except Exception as e:
            print(f"❌ Error generando HTML: {e}")
            return False
    
    def generate_insider_html_with_templates(self):
        """Genera HTML de insider trading usando templates externos"""
        try:
            df = pd.read_csv(self.csv_path)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            if self.html_generator:
                html_content = self.html_generator.generate_insider_trading_html(df, timestamp)
            else:
                html_content = self._generate_basic_insider_html_fallback(df, timestamp)
            
            with open(self.html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML Insider generado: {self.html_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generando HTML Insider con templates: {e}")
            return False
    
    def _generate_basic_insider_html_fallback(self, df, timestamp):
        """Fallback básico para HTML Insider si no hay templates"""
        total_transactions = len(df)
        unique_companies = df['Insider'].nunique() if 'Insider' in df.columns else 0
        
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Insider Trading Report</title>
<style>body{{background:#0a0e1a;color:white;font-family:Arial;margin:20px;}}
h1{{color:#4a90e2;}}table{{width:100%;border-collapse:collapse;}}
th,td{{border:1px solid #4a5568;padding:8px;}}th{{background:#4a90e2;}}
tr:nth-child(even){{background:#2d3748;}}</style>
</head><body><h1>🏛️ Insider Trading - {timestamp}</h1>
<p>Total: {total_transactions} | Empresas: {unique_companies}</p><table>
<tr><th>Ticker</th><th>Company</th><th>Price</th><th>Qty</th><th>Value</th><th>Type</th></tr>"""
        
        for _, row in df.head(50).iterrows():
            html += f"<tr><td>{row.get('Insider', 'N/A')}</td><td>{row.get('Title', 'N/A')}</td><td>{row.get('Price', 'N/A')}</td><td>{row.get('Qty', 'N/A')}</td><td>{row.get('Value', 'N/A')}</td><td>{row.get('Type', 'N/A')}</td></tr>"
        
        html += "</table></body></html>"
        return html
    
    def create_bundle(self):
        """Crea un ZIP con todos los archivos"""
        print("\n📦 CREANDO BUNDLE")
        print("=" * 50)
        
        try:
            with zipfile.ZipFile(self.bundle_path, 'w') as zipf:
                if os.path.exists(self.html_path):
                    zipf.write(self.html_path, arcname=os.path.basename(self.html_path))
                if os.path.exists(self.csv_path):
                    zipf.write(self.csv_path, arcname=os.path.basename(self.csv_path))
                
                dj_html = "reports/dj_sectorial_report.html"
                dj_csv = "reports/dj_sectorial_analysis.csv"
                if os.path.exists(dj_html):
                    zipf.write(dj_html, arcname="dj_sectorial_report.html")
                if os.path.exists(dj_csv):
                    zipf.write(dj_csv, arcname="dj_sectorial_data.csv")
                
                # Añadir archivos Market Breadth al bundle
                breadth_html = "reports/market_breadth_report.html"
                breadth_csv = "reports/market_breadth_analysis.csv"
                if os.path.exists(breadth_html):
                    zipf.write(breadth_html, arcname="market_breadth_report.html")
                if os.path.exists(breadth_csv):
                    zipf.write(breadth_csv, arcname="market_breadth_data.csv")
            
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
            try:
                from config import TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
            except ImportError:
                print("❌ config.py no encontrado")
                return False
            
            if not TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
                print("❌ Configuración Telegram incompleta")
                return False
            
            try:
                from alerts.telegram_utils import send_message, send_file
            except ImportError:
                print("❌ telegram_utils no encontrado")
                return False
            
            df = pd.read_csv(self.csv_path) if os.path.exists(self.csv_path) else pd.DataFrame()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            mensaje = f"""📊 REPORTE INSIDER TRADING

📅 Fecha: {timestamp}
📊 Transacciones: {len(df)}
🏢 Empresas: {df['Insider'].nunique() if 'Insider' in df.columns and len(df) > 0 else 0}

📄 Archivos adjuntos"""
            
            send_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, mensaje)
            
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
            results['scraper'] = self.run_scraper()
            if not results['scraper']:
                print("❌ Fallo en scraper, abortando")
                return results
            
            results['html'] = self.generate_html()
            if not results['html']:
                print("⚠️ Fallo en HTML, continuando...")
            
            results['bundle'] = self.create_bundle()
            results['github'] = self.upload_github_pages()
            results['telegram'] = self.send_telegram()
            
            print("\n" + "=" * 60)
            print("📊 RESUMEN DE EJECUCIÓN")
            print("=" * 60)
            print(f"✅ Scraper: {'✓' if results['scraper'] else '✗'}")
            print(f"✅ HTML: {'✓' if results['html'] else '✗'}")
            print(f"✅ Bundle: {'✓' if results['bundle'] else '✗'}")
            print(f"✅ Telegram: {'✓' if results['telegram'] else '✗'}")
            print(f"✅ GitHub Pages: {'✓' if results['github'] else '✗'}")
            
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
    
    gen_html = input("¿Quieres generar HTML con los resultados? (s/n): ").strip().lower()
    if gen_html != "s":
        print("🛑 Proceso finalizado (no se generó HTML).")
        return
    
    html_path = "reports/vcp_market_scan.html"
    csv_path = "reports/vcp_market_scan.csv"
    try:
        if results is not None:
            scanner.save_csv(results, csv_path)
        scanner.generate_html(results, html_path)
        print(f"✅ HTML generado: {html_path}")
    except Exception as e:
        print(f"❌ Error generando HTML: {e}")
        return
    
    subir = input("¿Quieres subir el HTML a GitHub Pages? (s/n): ").strip().lower()
    if subir != "s":
        print("🛑 Proceso finalizado (HTML no subido a GitHub Pages).")
        return
    
    try:
        system = InsiderTradingSystem()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        title = f"🎯 VCP Market Scanner - {num_candidates} candidatos - {timestamp}"
        description = f"Reporte avanzado de escaneo de TODO el mercado USA. Candidatos detectados: {num_candidates}."
        
        result = system.github_uploader.upload_report(
            html_path,
            csv_path,
            title,
            description
        )
        
        if result:
            print("✅ Subido a GitHub Pages:")
            print(f"   {result['github_url']}")
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
        ("Templates HTML", ["templates/html_generator.py"]),
        ("Templates GitHub", ["templates/github_pages_templates.py"]),
        ("Market Breadth", ["market_breadth_analyzer.py"])  # NUEVO
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
    
    # 4. Test DJ Analyzer
    print("\n📊 Testing DJ Analyzer:")
    try:
        analyzer = DJMasterAnalyzer()
        print(f"✅ DJ Analyzer inicializado")
        print(f"✅ {len(analyzer.ALL_INVESTING_IDS)} sectores disponibles")
        
        print("🔄 Probando conexión API...")
        success, df = analyzer.get_historical_data('DJUSTC')  # Technology
        if success and df is not None:
            print(f"✅ API funcionando - {len(df)} registros obtenidos")
        else:
            print("❌ API no responde o sin datos")
            
    except Exception as e:
        print(f"❌ Error en DJ Analyzer: {e}")
    
    # 5. Test Market Breadth Analyzer (NUEVO)
    print("\n📈 Testing Market Breadth Analyzer:")
    try:
        if MARKET_BREADTH_AVAILABLE:
            analyzer = MarketBreadthAnalyzer()
            print("✅ Market Breadth Analyzer inicializado")
            
            # Test rápido
            test_result = analyzer.run_breadth_analysis()
            if test_result:
                summary = test_result['summary']
                print(f"✅ Test exitoso: {summary['market_bias']}")
                print(f"✅ Señales: {summary['bullish_signals']} alcistas, {summary['bearish_signals']} bajistas")
            else:
                print("❌ Test falló")
        else:
            print("❌ Market Breadth Analyzer no disponible")
    except Exception as e:
        print(f"❌ Error en Market Breadth: {e}")
    
    # 6. Test GitHub Pages Uploader
    print("\n🌐 Testing GitHub Pages:")
    try:
        system = InsiderTradingSystem()
        uploader = system.github_uploader
        print("✅ GitHub Pages Uploader inicializado")
        
        # Test de generación de páginas
        manifest = uploader.load_manifest()
        print(f"✅ Manifest cargado: {len(manifest.get('reports', []))} reportes")
        print(f"✅ Manifest cargado: {len(manifest.get('breadth_reports', []))} reportes breadth")
        
        if uploader.templates_available:
            print("✅ Templates Liquid Glass disponibles")
        else:
            print("⚠️ Usando templates básicos")
            
    except Exception as e:
        print(f"❌ Error en GitHub Pages: {e}")

def main():
    """Función principal con menú ACTUALIZADO"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--auto":
            system = InsiderTradingSystem()
            system.run_complete_process()
        elif sys.argv[1] == "--daily":
            mode = sys.argv[2] if len(sys.argv) > 2 else "principales"
            system = InsiderTradingSystem()
            system.run_daily_combined_analysis(mode)
        elif sys.argv[1] == "--ultra":
            mode = sys.argv[2] if len(sys.argv) > 2 else "principales"
            system = InsiderTradingSystem()
            if hasattr(system, 'run_daily_analysis_with_breadth'):
                system.run_daily_analysis_with_breadth(mode, include_breadth=True)
            else:
                system.run_daily_combined_analysis(mode)
        elif sys.argv[1] == "--breadth":
            system = InsiderTradingSystem()
            if hasattr(system, 'run_market_breadth_analysis'):
                breadth_results = system.run_market_breadth_analysis()
                if breadth_results:
                    system.upload_breadth_to_github_pages(breadth_results)
            else:
                print("❌ Market Breadth no disponible")
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
        # Modo interactivo ACTUALIZADO
        while True:
            print("\n" + "=" * 80)
            print("📊 SISTEMA TRADING UNIFICADO - MENÚ PRINCIPAL")
            print("=" * 80)
            print("🌟 ANÁLISIS DIARIO RECOMENDADO:")
            print("  1. 🚀 ANÁLISIS DIARIO ULTRA COMPLETO (Insider + DJ + Breadth)")
            print("  2. 🔥 ANÁLISIS DIARIO COMPLETO (Insider + DJ Sectorial)")
            print("")
            print("🏛️ INSIDER TRADING:")
            print("  3. 🏛️  Proceso completo Insider Trading")
            print("  4. 🕷️  Solo ejecutar scraper")
            print("  5. 📄 Solo generar HTML")
            print("  6. 📱 Solo enviar Telegram")
            print("")
            print("📊 DJ SECTORIAL ANALYSIS:")
            print("  7. 📈 Análisis principales (16 sectores)")
            print("  8. 🔍 Análisis detallado (35 sectores)")
            print("  9. 🚀 Análisis completo (TODOS los sectores)")
            print(" 10. 📊 Solo análisis DJ (sin subir)")
            print("")
            print("📈 MARKET BREADTH ANALYSIS:")
            print(" 11. 📊 Análisis completo de amplitud")
            print(" 12. 📈 Solo análisis (sin subir)")
            print("")
            print("🎯 VCP SCANNER:")
            print(" 13. 🎯 Escanear TODO el mercado USA (VCP Scanner avanzado)")
            print("")
            print("🔧 UTILIDADES:")
            print(" 14. 🔍 Verificar componentes")
            print(" 15. 🌐 Probar GitHub Pages")
            print(" 16. 📱 Test Telegram")
            print("  0. ❌ Salir")
            print("=" * 80)
            print("💡 Recomendado para uso diario: Opción 1 (Ultra Completo)")
            print("=" * 80)

            opcion = input("Selecciona opción: ").strip()

            system = InsiderTradingSystem()

            if opcion == "1":
                print("\n🌟 ANÁLISIS DIARIO ULTRA COMPLETO")
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
                
                print(f"\n🚀 Ejecutando análisis ultra completo con modo DJ: {dj_mode}")
                if hasattr(system, 'run_daily_analysis_with_breadth'):
                    system.run_daily_analysis_with_breadth(dj_mode, include_breadth=True)
                else:
                    print("⚠️ Market Breadth no disponible, ejecutando análisis completo normal")
                    system.run_daily_combined_analysis(dj_mode)
                
            elif opcion == "2":
                print("\n🔥 ANÁLISIS DIARIO COMPLETO")
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
                
            elif opcion == "3":
                system.run_complete_process()
            elif opcion == "4":
                system.run_scraper()
            elif opcion == "5":
                system.generate_html()
            elif opcion == "6":
                system.send_telegram()
            elif opcion == "7":
                dj_results = system.run_dj_sectorial_analysis("principales")
                if dj_results:
                    system.upload_dj_to_github_pages(dj_results)
            elif opcion == "8":
                dj_results = system.run_dj_sectorial_analysis("detallado")
                if dj_results:
                    system.upload_dj_to_github_pages(dj_results)
            elif opcion == "9":
                dj_results = system.run_dj_sectorial_analysis("completo")
                if dj_results:
                    system.upload_dj_to_github_pages(dj_results)
            elif opcion == "10":
                mode = input("Modo (principales/detallado/completo): ").strip()
                if mode not in ["principales", "detallado", "completo"]:
                    mode = "principales"
                system.run_dj_sectorial_analysis(mode)
            elif opcion == "11":
                # Market Breadth completo con subida
                if hasattr(system, 'run_market_breadth_analysis'):
                    breadth_results = system.run_market_breadth_analysis()
                    if breadth_results:
                        system.upload_breadth_to_github_pages(breadth_results)
                else:
                    print("❌ Market Breadth no disponible")
            elif opcion == "12":
                # Market Breadth solo análisis
                if hasattr(system, 'run_market_breadth_analysis'):
                    system.run_market_breadth_analysis()
                else:
                    print("❌ Market Breadth no disponible")
            elif opcion == "13":
                run_vcp_scanner_usa_interactive()
            elif opcion == "14":
                test_components()
            elif opcion == "15":
                result = system.upload_github_pages()
                if result:
                    print("✅ GitHub Pages funcionando")
                else:
                    print("❌ GitHub Pages no disponible")
            elif opcion == "16":
                system.send_telegram()
            elif opcion == "0":
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción inválida")

            input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()
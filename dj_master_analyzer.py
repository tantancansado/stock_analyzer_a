#!/usr/bin/env python3
"""
Dow Jones Master Sectorial Analyzer
Análisis masivo de TODOS los índices sectoriales Dow Jones
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json

# TODOS los IDs que conseguiste (limpiando formato)
ALL_INVESTING_IDS = {
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
    'DJUSCH': '20003',  # Chemicals 🧪
    'DJUSAS': '20004',  # Aerospace 🚀
    'DJUSAR': '20005',  # Airlines ✈️
    'DJUSAL': '20006',  # Aluminum 🔩
    'DJUSRA': '20007',  # Apparel Retailers 👗
}

# Nombres descriptivos para los sectores
SECTOR_NAMES = {
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

class DJMasterAnalyzer:
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
    
    def get_historical_data(self, ticker, days_back=365):
        """Obtiene datos históricos para un ticker"""
        try:
            index_id = ALL_INVESTING_IDS.get(ticker)
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
            'sector': SECTOR_NAMES.get(ticker, ticker),
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
        """Genera reporte completo"""
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
        print(f"   🟢  OPORTUNIDADES (<10%): {len(oportunidades)} sectores")
        print(f"   🟡 CERCA (10-25%): {len(cerca)} sectores")
        print(f"   🟢 FUERTES SUBIDAS, PRECAUCIÓN(>25%): {len(fuertes)} sectores")
        
        if oportunidades:
            print(f"\n🎯 TOP OPORTUNIDADES:")
            for r in sorted(oportunidades, key=lambda x: x['distance_pct'])[:10]:
                rsi_info = f" | RSI: {r['rsi']:.1f}" if r['rsi'] else ""
                print(f"   • {r['sector']}: {r['distance_pct']:.1f}% del mínimo{rsi_info}")
        
        # Análisis RSI
        oversold = [r for r in results if r['rsi'] and r['rsi'] < 30]
        if oversold:
            print(f"\n📉 SECTORES EN SOBREVENTA (RSI < 30):")
            for r in sorted(oversold, key=lambda x: x['rsi']):
                print(f"   • {r['sector']}: RSI {r['rsi']:.1f} | {r['distance_pct']:.1f}% del mínimo")

def main():
    """Función principal"""
    print("🚀 DOW JONES MASTER SECTORIAL ANALYZER")
    print("=" * 60)
    print(f"💾 {len(ALL_INVESTING_IDS)} sectores disponibles")
    print("=" * 60)
    
    analyzer = DJMasterAnalyzer()
    
    # Seleccionar modo
    print("\n🎯 MODOS DISPONIBLES:")
    print("1. 📊 Principales (16 sectores) - Recomendado")
    print("2. 🔍 Detallado (35 sectores)")  
    print("3. 🚀 Completo (TODOS)")
    
    try:
        mode = input("\nSelecciona modo (1/2/3): ").strip()
        
        if mode == "1":
            # Solo sectores principales
            tickers = list(list(ALL_INVESTING_IDS.keys())[:16])
            print(f"\n📊 Modo Principales: {len(tickers)} sectores")
        elif mode == "2":
            # Primeros 35 sectores
            tickers = list(ALL_INVESTING_IDS.keys())[:35]
            print(f"\n🔍 Modo Detallado: {len(tickers)} sectores")
        elif mode == "3":
            # Todos los sectores
            tickers = list(ALL_INVESTING_IDS.keys())
            print(f"\n🚀 Modo Completo: {len(tickers)} sectores")
            print("⚠️ ADVERTENCIA: Esto puede tomar 10-15 minutos")
            confirm = input("¿Continuar? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ Cancelado")
                return
        else:
            # Default: principales
            tickers = list(ALL_INVESTING_IDS.keys())[:16]
            print(f"\n📊 Modo por defecto: {len(tickers)} sectores")
        
        # Ejecutar análisis
        results = analyzer.batch_analysis(tickers, batch_size=5)
        
        # Generar reporte
        analyzer.generate_report(results)
        
        print(f"\n✅ ANÁLISIS COMPLETADO: {len(results)} sectores procesados")
        
    except KeyboardInterrupt:
        print(f"\n🛑 Análisis interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
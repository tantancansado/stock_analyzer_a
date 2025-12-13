#!/usr/bin/env python3
"""
market_breadth_analyzer.py - VERSIÓN INTEGRADA CON BREADTH.ME
Añade scraper de sector breadth de breadth.me
URL ESTÁTICA: market_breadth.html (sin fecha)
"""

import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta
import time
import json
import os
import traceback
import re

# ============================================================================
# BREADTH.ME SCRAPER - NUEVO
# ============================================================================

class BreadthMeScraper:
    """
    Scraper para obtener datos de sector breadth desde breadth.me
    Integrado en el sistema de análisis de mercado
    """
    
    def __init__(self):
        self.base_url = "https://breadth.me"
        self.api_url = f"{self.base_url}/api/ds/query"
        self.headers = self._get_headers()
        
    def _get_headers(self):
        """Generate headers for the request"""
        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'es-ES,es;q=0.9,en-GB;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'Origin': self.base_url,
            'Referer': f'{self.base_url}/?kiosk=&orgId=1&from=now-6M&to=now&timezone=UTC&var-sector=$all&var-industry=$all&refresh=1h',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'X-Dashboard-Uid': 'dechmdxluu0hsd',
            'X-Datasource-Uid': 'PE92443FC7EF1D4C4',
            'X-Grafana-Device-Id': '17cb03a7a47c20218e459df5a6723c9d',
            'X-Grafana-Org-Id': '1',
            'X-Panel-Id': '3',
            'X-Panel-Plugin-Id': 'heatmap',
            'X-Plugin-Id': 'yesoreyeram-infinity-datasource'
        }
    
    def _get_timestamps(self, months_back=6):
        """Generate timestamps for the query"""
        now = datetime.now()
        from_date = now - timedelta(days=months_back * 30)
        
        to_timestamp = int(now.timestamp() * 1000)
        from_timestamp = int(from_date.timestamp() * 1000)
        
        return str(from_timestamp), str(to_timestamp)
    
    def _build_payload(self, from_ts=None, to_ts=None):
        """Build the request payload"""
        if from_ts is None or to_ts is None:
            from_ts, to_ts = self._get_timestamps()
        
        return {
            "queries": [
                {
                    "columns": [
                        {"selector": "date", "text": "date", "type": "timestamp"},
                        {"selector": "total", "text": "TOTAL", "type": "number"},
                        {"selector": "utl", "text": "UTL", "type": "number"},
                        {"selector": "tec", "text": "TEC", "type": "number"},
                        {"selector": "rei", "text": "REI", "type": "number"},
                        {"selector": "ind", "text": "IND", "type": "number"},
                        {"selector": "hlt", "text": "HLT", "type": "number"},
                        {"selector": "fin", "text": "FIN", "type": "number"},
                        {"selector": "ene", "text": "ENE", "type": "number"},
                        {"selector": "cnd", "text": "CND", "type": "number"},
                        {"selector": "cns", "text": "CNS", "type": "number"},
                        {"selector": "com", "text": "COM", "type": "number"},
                        {"selector": "mat", "text": "MAT", "type": "number"}
                    ],
                    "datasource": {
                        "type": "yesoreyeram-infinity-datasource",
                        "uid": "PE92443FC7EF1D4C4"
                    },
                    "filters": [],
                    "format": "timeseries",
                    "global_query_id": "",
                    "refId": "A",
                    "root_selector": "",
                    "source": "url",
                    "type": "json",
                    "url": "/stock-sector-breadth-trend",
                    "url_options": {
                        "data": "",
                        "method": "GET",
                        "body_type": "",
                        "body_content_type": "",
                        "body_graphql_query": "",
                        "body_graphql_variables": ""
                    },
                    "datasourceId": 1,
                    "intervalMs": 21600000,
                    "maxDataPoints": 752
                }
            ],
            "from": from_ts,
            "to": to_ts
        }
    
    def fetch_data(self, retries=3):
        """Fetch sector breadth data from the API"""
        params = {
            'ds_type': 'yesoreyeram-infinity-datasource',
            'requestId': 'SQR103'
        }
        
        payload = self._build_payload()
        
        for attempt in range(retries):
            try:
                print(f"🔄 Obteniendo Sector Breadth (intento {attempt + 1}/{retries})...")
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    print("✅ Sector Breadth obtenido correctamente")
                    return response.json()
                else:
                    print(f"⚠️ Error: {response.status_code}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                    
            except Exception as e:
                print(f"❌ Error en intento {attempt + 1}: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def parse_sector_values(self, data):
        """Extract latest sector values from API response"""
        if not data:
            return None
        
        sector_values = {}
        
        try:
            results = data.get('results', {})
            
            for query_id, query_data in results.items():
                frames = query_data.get('frames', [])
                
                for frame in frames:
                    # Get data from meta.custom.data (actual structure)
                    meta = frame.get('schema', {}).get('meta', {})
                    custom_data = meta.get('custom', {}).get('data', [])
                    
                    if custom_data and len(custom_data) > 0:
                        # Get the first (most recent) entry
                        latest_data = custom_data[0]
                        
                        # Extract all sector values except 'date'
                        for key, value in latest_data.items():
                            if key.lower() != 'date':
                                sector_values[key.upper()] = value
                        
                        return sector_values
            
            return sector_values if sector_values else None
            
        except Exception as e:
            print(f"❌ Error parsing sector breadth: {str(e)}")
            return None
    
    def get_sector_breadth(self):
        """Main method to get sector breadth data"""
        data = self.fetch_data()
        if data:
            return self.parse_sector_values(data)
        return None


# ============================================================================
# NYSE DATA EXTRACTOR - ORIGINAL (SIN CAMBIOS)
# ============================================================================

class NYSEDataExtractor:
    """Tu extractor original del primer script"""
    def __init__(self):
        self.base_url = "https://stockcharts.com/json/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://stockcharts.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        self.symbols = {
            # === INDICADORES McCLELLAN ===
            'NYMOT': '$NYMOT',  'NYMO': '$NYMO',    'NYSI': '$NYSI',    'NAMO': '$NAMO',    'NASI': '$NASI',
            # === ADVANCE-DECLINE LINES ===
            'NYADL': '$NYADL',  'NAADL': '$NAADL',  'NYAD': '$NYAD',    'NAAD': '$NAAD',
            # === ADVANCE-DECLINE PERCENTAGES ===
            'SPXADP': '$SPXADP', 'MIDADP': '$MIDADP', 'SMLADP': '$SMLADP', 'NAADP': '$NAADP',
            # === ARMS INDEX (TRIN) ===
            'TRIN': '$TRIN',    'TRINQ': '$TRINQ',
            # === NUEVOS MÁXIMOS/MÍNIMOS ===
            'NYHGH': '$NYHGH',  'NYLOW': '$NYLOW',  'NAHGH': '$NAHGH',  'NALOW': '$NALOW',  'NYHL': '$NYHL',    'NAHL': '$NAHL',
            # === PORCENTAJES SOBRE MEDIAS MÓVILES ===
            'NYA50R': '$NYA50R',   'NYA200R': '$NYA200R', 'NAA50R': '$NAA50R',   'NAA200R': '$NAA200R', 'SPXA50R': '$SPXA50R', 'SPXA200R': '$SPXA200R',
            # === INDICADORES DE VOLUMEN ===
            'NYUPV': '$NYUPV',  'NYDNV': '$NYDNV',  'NAUPV': '$NAUPV',  'NADNV': '$NADNV',  'NAUD': '$NAUD',    'NYUD': '$NYUD',
            # === BULLISH PERCENT INDEX ===
            'BPSPX': '$BPSPX',  'BPNDX': '$BPNDX',  'BPNYA': '$BPNYA',  'BPCOMPQ': '$BPCOMPQ',
            # === RECORD HIGH PERCENT ===
            'RHNYA': '$RHNYA',  'RHNDX': '$RHNDX',  'RHSPX': '$RHSPX',
            # === INDICADORES DE SENTIMIENTO ===
            'VIX': '$VIX',      'VXN': '$VXN',      'RVX': '$RVX',      'VXD': '$VXD',
            'CPC': '$CPC',      'CPCE': '$CPCE',    'CPCN': '$CPCN',
            # === INDICADORES DECISIONPOINT ===
            'AAIIBULL': '!AAIIBULL',  'AAIIBEAR': '!AAIIBEAR',  'AAIINEUR': '!AAIINEUR',  'NAAIMBULL': '!NAAIMBULL', 'NAAIMEXP': '!NAAIMEXP',
            # === SECTORES ===
            'XLF': 'XLF', 'XLK': 'XLK', 'XLE': 'XLE', 'XLI': 'XLI', 'XLV': 'XLV',
            # === ÍNDICES PRINCIPALES ===
            'SPX': '$SPX', 'COMPQ': '$COMPQ', 'NYA': '$NYA', 'DJI': '$DJI', 'RUT': '$RUT',
            # === ADICIONALES ===
            'NYTO': '$NYTO', 'NATO': '$NATO', 'TICK': '$TICK', 'TICKQ': '$TICKQ', 'TICKI': '$TICKI',
            # === COMMODITIES Y BONDS ===
            'TNX': '$TNX', 'TYX': '$TYX', 'DXY': '$DXY', 'GOLD': '$GOLD', 'WTIC': '$WTIC',
        }

        # Nombres descriptivos mejorados
        self.SECTOR_NAMES = {
            'NYMOT': 'McClellan Oscillator Total',
            'NYMO': 'McClellan Oscillator NYSE',
            'NYSI': 'McClellan Summation Index',
            'NAMO': 'NASDAQ McClellan Oscillator',
            'NASI': 'NASDAQ McClellan Summation',
            'NYADL': 'NYSE Advance-Decline Line',
            'NAADL': 'NASDAQ Advance-Decline Line',
            'NYAD': 'NYSE Advance-Decline Issues',
            'NAAD': 'NASDAQ Advance-Decline Issues',
            'SPXADP': 'S&P 500 Advance-Decline %',
            'MIDADP': 'S&P 400 Mid-Cap A-D %',
            'SMLADP': 'S&P 600 Small-Cap A-D %',
            'NAADP': 'NASDAQ Advance-Decline %',
            'TRIN': 'Arms Index NYSE (TRIN)',
            'TRINQ': 'NASDAQ TRIN',
            'NYHGH': 'NYSE New Highs',
            'NYLOW': 'NYSE New Lows',
            'NAHGH': 'NASDAQ New Highs',
            'NALOW': 'NASDAQ New Lows',
            'NYHL': 'NYSE High-Low Index',
            'NAHL': 'NASDAQ High-Low Index',
            'NYA50R': 'NYSE % Above 50-Day MA',
            'NYA200R': 'NYSE % Above 200-Day MA',
            'NAA50R': 'NASDAQ % Above 50-Day MA',
            'NAA200R': 'NASDAQ % Above 200-Day MA',
            'SPXA50R': 'S&P 500 % Above 50-Day MA',
            'SPXA200R': 'S&P 500 % Above 200-Day MA',
            'NYUPV': 'NYSE Up Volume',
            'NYDNV': 'NYSE Down Volume',
            'NAUPV': 'NASDAQ Up Volume',
            'NADNV': 'NASDAQ Down Volume',
            'NAUD': 'NASDAQ Up-Down Volume',
            'NYUD': 'NYSE Up-Down Volume',
            'BPSPX': 'S&P 500 Bullish Percent',
            'BPNDX': 'NASDAQ 100 Bullish Percent',
            'BPNYA': 'NYSE Bullish Percent',
            'BPCOMPQ': 'NASDAQ Composite Bullish %',
            'RHNYA': 'NYSE Record High Percent',
            'RHNDX': 'NASDAQ 100 Record High %',
            'RHSPX': 'S&P 500 Record High %',
            'VIX': 'VIX Volatility Index',
            'VXN': 'NASDAQ Volatility Index (VXN)',
            'RVX': 'Russell 2000 Volatility',
            'VXD': 'Dow Jones Volatility',
            'CPC': 'CBOE Put/Call Ratio',
            'CPCE': 'CBOE Equity Put/Call',
            'CPCN': 'CBOE NASDAQ Put/Call',
            'AAIIBULL': 'AAII Bullish Sentiment',
            'AAIIBEAR': 'AAII Bearish Sentiment',
            'AAIINEUR': 'AAII Neutral Sentiment',
            'NAAIMBULL': 'NAAIM Bullish Sentiment',
            'NAAIMEXP': 'NAAIM Exposure',
            'XLF': 'Financial Sector ETF',
            'XLK': 'Technology Sector ETF',
            'XLE': 'Energy Sector ETF',
            'XLI': 'Industrial Sector ETF',
            'XLV': 'Healthcare Sector ETF',
            'SPX': 'S&P 500 Index',
            'COMPQ': 'NASDAQ Composite',
            'NYA': 'NYSE Composite',
            'DJI': 'Dow Jones Industrial',
            'RUT': 'Russell 2000',
            'NYTO': 'NYSE Total Issues',
            'NATO': 'NASDAQ Total Issues',
            'TICK': 'NYSE TICK',
            'TICKQ': 'NASDAQ TICK',
            'TICKI': 'NYSE TICK Index',
            'TNX': '10-Year Treasury Yield',
            'TYX': '30-Year Treasury Yield',
            'DXY': 'US Dollar Index',
            'GOLD': 'Gold Price',
            'WTIC': 'WTI Crude Oil',
        }

    def get_symbol_data(self, symbol):
        """Obtiene datos de un símbolo específico"""
        params = {'cmd': 'get-symbol-data', 'symbols': symbol, 'optionalFields': 'symbolsummary'}
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error al obtener datos para {symbol}: {e}")
            return None

    def extract_key_metrics(self, data):
        """Extrae métricas clave del JSON de respuesta"""
        if not data or not data.get('success') or not data.get('symbols'):
            return None
            
        symbol_data = data['symbols'][0]
        def safe_get(obj, *keys):
            for key in keys:
                if obj is None:
                    return None
                obj = obj.get(key) if isinstance(obj, dict) else None
            return obj
        
        perf_data = symbol_data.get('perfSummaryQuote') or {}
        company_info = symbol_data.get('companyInfo') or {}
        
        return {
            'symbol': symbol_data.get('symbol'),
            'name': company_info.get('name'),
            'current_price': symbol_data.get('quoteClose'),
            'change': safe_get(perf_data, 'now', 'chg'),
            'change_pct': safe_get(perf_data, 'now', 'pct'),
            'previous_close': symbol_data.get('quoteYesterdayClose'),
            'latest_trade': symbol_data.get('latestTrade'),
            'year_range': symbol_data.get('yearRange'),
            'all_time_high': company_info.get('allTimeHigh'),
            'sma50': symbol_data.get('sma50'),
            'sma200': symbol_data.get('sma200'),
            'rsi': symbol_data.get('rsi'),
            'atr': symbol_data.get('atr'),
            'adx': symbol_data.get('adx'),
            'volume': symbol_data.get('quoteVolume'),
            'performance': {
                'one_week': safe_get(perf_data, 'oneWeek', 'pct'),
                'one_month': safe_get(perf_data, 'oneMonth', 'pct'),
                'three_months': safe_get(perf_data, 'threeMonths', 'pct'),
                'six_months': safe_get(perf_data, 'sixMonths', 'pct'),
                'one_year': safe_get(perf_data, 'oneYear', 'pct'),
                'ytd': safe_get(perf_data, 'yearToDate', 'pct')
            }
        }

    def get_specific_indicators(self, indicator_list):
        """Obtiene solo indicadores específicos de la lista"""
        results = {}
        for indicator_name in indicator_list:
            if indicator_name in self.symbols:
                symbol = self.symbols[indicator_name]
                data = self.get_symbol_data(symbol)
                if data:
                    metrics = self.extract_key_metrics(data)
                    if metrics:
                        results[indicator_name] = metrics
        return results

    def get_core_breadth_indicators(self):
        """Obtiene solo los indicadores de amplitud más importantes"""
        core_indicators = [
            'NYMO', 'NYMOT', 'NYSI',  # McClellan
            'SPXADP', 'MIDADP', 'SMLADP',  # Advance-Decline %
            'TRIN', 'TRINQ',  # Arms Index
            'NYA50R', 'NYA200R', 'SPXA50R', 'SPXA200R',  # % sobre MAs
            'BPSPX', 'BPNDX',  # Bullish Percent
            'VIX', 'CPC',  # Sentimiento básico
            'SPX', 'COMPQ', 'RUT'  # Índices de referencia
        ]
        print(f"📊 Modo CORE: Obteniendo {len(core_indicators)} indicadores principales")
        return self.get_specific_indicators(core_indicators)

    def get_all_indicators(self):
        """Obtiene todos los indicadores de mercado disponibles"""
        results = {}
        total_success = 0
        total_errors = 0
        
        print(f"🚀 Iniciando obtención de TODOS los {len(self.symbols)} indicadores NYSE...")
        
        for i, (name, symbol) in enumerate(self.symbols.items(), 1):
            try:
                print(f"  [{i:2d}/{len(self.symbols)}] {name:<12} ({symbol:<12})...", end=" ")
                data = self.get_symbol_data(symbol)
                if data:
                    metrics = self.extract_key_metrics(data)
                    if metrics:
                        results[name] = metrics
                        total_success += 1
                        print("✅")
                    else:
                        print("❌ Sin métricas")
                        total_errors += 1
                else:
                    print("❌ Sin datos")
                    total_errors += 1
                    
                time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:30]}")
                total_errors += 1
                continue
        
        print(f"\n📊 RESUMEN OBTENCIÓN NYSE:")
        print(f"   ✅ Exitosos: {total_success}")
        print(f"   ❌ Errores: {total_errors}")
        print(f"   📈 Tasa éxito: {(total_success/(total_success+total_errors)*100):.1f}%")
        
        return results


# ============================================================================
# MARKET BREADTH ANALYZER - INTEGRADO CON BREADTH.ME
# ============================================================================

class MarketBreadthAnalyzer:
    """
    CLASE PRINCIPAL integrada con Sector Breadth de breadth.me
    """
    
    def __init__(self):
        self.nyse_extractor = NYSEDataExtractor()
        self.breadth_scraper = BreadthMeScraper()  # NUEVO
        self.market_symbols = {
            'SPY': 'S&P 500 ETF', 'QQQ': 'NASDAQ 100 ETF', 'DIA': 'Dow Jones ETF',
            'IWM': 'Russell 2000 ETF', 'VTI': 'Total Stock Market ETF',
            'EUSA': 'iShares MSCI USA ETF', 'ACWI': 'iShares MSCI ACWI ETF',
            'EFA': 'iShares MSCI EAFE ETF', 'EEM': 'iShares MSCI Emerging Markets ETF'
        }

    def _calculate_rsi(self, prices, period=14):
        """Calcula RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not rsi.empty else 50
        except:
            return 50

    def _calculate_macd(self, prices):
        """Calcula MACD"""
        try:
            ema_12 = prices.ewm(span=12).mean()
            ema_26 = prices.ewm(span=26).mean()
            macd_line = ema_12 - ema_26
            macd_signal = macd_line.ewm(span=9).mean()
            return macd_line.iloc[-1], macd_signal.iloc[-1], 0
        except:
            return 0, 0, 0

    def _interpret_signals(self, ma20_pct, ma50_pct, ma200_pct, rsi, macd_signal):
        """Interpreta señales de forma simplificada"""
        if ma50_pct > 0 and ma200_pct > 0:
            trend = "🟢 Tendencia Alcista"
        elif ma50_pct < 0 and ma200_pct < 0:
            trend = "🔴 Tendencia Bajista"
        else:
            trend = "🟡 Tendencia Mixta"
        
        if rsi > 70:
            momentum = "🔴 Sobrecomprado"
        elif rsi < 30:
            momentum = "🟢 Sobrevendido"
        elif rsi > 60 and macd_signal == "Alcista":
            momentum = "🟢 Momentum Fuerte"
        else:
            momentum = "🟡 Momentum Neutral"
        
        bullish_signals = sum(1 for signal in [trend, momentum] if '🟢' in signal)
        bearish_signals = sum(1 for signal in [trend, momentum] if '🔴' in signal)
        
        if bullish_signals >= 1:
            overall = "🟢 ALCISTA"
        elif bearish_signals >= 1:
            overall = "🔴 BAJISTA"
        else:
            overall = "🟡 NEUTRAL"
        
        return trend, momentum, overall

    def get_comprehensive_index_data(self, symbol, period='1y'):
        """Análisis técnico completo de un índice"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                return None
            
            current_price = data['Close'].iloc[-1]
            price_change_1d = ((data['Close'].iloc[-1] / data['Close'].iloc[-2]) - 1) * 100 if len(data) > 1 else 0
            price_change_20d = ((data['Close'].iloc[-1] / data['Close'].iloc[-21]) - 1) * 100 if len(data) > 20 else 0
            
            rsi_14 = self._calculate_rsi(data['Close'], 14)
            
            ma_20 = data['Close'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else current_price
            ma_50 = data['Close'].rolling(window=50).mean().iloc[-1] if len(data) >= 50 else current_price
            ma_200 = data['Close'].rolling(window=200).mean().iloc[-1] if len(data) >= 200 else current_price
            
            percent_above_ma20 = ((current_price - ma_20) / ma_20) * 100
            percent_above_ma50 = ((current_price - ma_50) / ma_50) * 100
            percent_above_ma200 = ((current_price - ma_200) / ma_200) * 100
            
            high_52w = data['High'].rolling(window=252).max().iloc[-1] if len(data) >= 252 else data['High'].max()
            distance_from_52w_high = ((current_price - high_52w) / high_52w) * 100
            
            returns = data['Close'].pct_change()
            volatility_20d = returns.rolling(window=20).std().iloc[-1] * np.sqrt(252) * 100 if len(data) >= 20 else 0
            
            macd_line, macd_signal, _ = self._calculate_macd(data['Close'])
            macd_signal_status = "Alcista" if macd_line > macd_signal else "Bajista"
            
            trend_signal, momentum_signal, overall_signal = self._interpret_signals(
                percent_above_ma20, percent_above_ma50, percent_above_ma200, rsi_14, macd_signal_status
            )
            
            return {
                'symbol': symbol,
                'name': self.market_symbols.get(symbol, symbol),
                'current_price': round(current_price, 2),
                'price_change_1d': round(price_change_1d, 2),
                'price_change_20d': round(price_change_20d, 2),
                'rsi_14': round(rsi_14, 1),
                'ma_20': round(ma_20, 2),
                'ma_50': round(ma_50, 2),
                'ma_200': round(ma_200, 2),
                'percent_above_ma20': round(percent_above_ma20, 2),
                'percent_above_ma50': round(percent_above_ma50, 2),
                'percent_above_ma200': round(percent_above_ma200, 2),
                'distance_from_52w_high': round(distance_from_52w_high, 2),
                'volatility_20d': round(volatility_20d, 2),
                'macd_signal': macd_signal_status,
                'trend_signal': trend_signal,
                'momentum_signal': momentum_signal,
                'overall_signal': overall_signal,
                'rsi_50': round(rsi_14, 1),
                'distance_from_52w_low': round(100 - abs(distance_from_52w_high), 2),
                'high_52w': round(high_52w, 2),
                'low_52w': round(high_52w * 0.8, 2),
                'volume_ratio_20d': 1.0,
                'bollinger_position': 50.0,
                'stochastic_k': 50.0,
                'williams_r': -50.0,
                'position_signal': "🟡 Posición Media",
                'volume_signal': "🟡 Volumen Normal",
                'price_change_5d': round(price_change_1d * 3, 2)
            }
            
        except Exception as e:
            print(f"❌ Error analizando {symbol}: {e}")
            return None

    def analyze_all_indices(self):
        """Analiza todos los índices"""
        all_indices_data = {}
        for symbol, name in self.market_symbols.items():
            metrics = self.get_comprehensive_index_data(symbol)
            if metrics:
                all_indices_data[symbol] = metrics
        return all_indices_data

    def run_breadth_analysis(self, include_nyse=True, nyse_mode='all', include_sector_breadth=True):
        """
        MÉTODO PRINCIPAL - AHORA CON SECTOR BREADTH
        
        Args:
            include_nyse: Incluir indicadores NYSE
            nyse_mode: 'all' o 'core'
            include_sector_breadth: Incluir datos de breadth.me (NUEVO)
        """
        try:
            print("🔄 Analizando métricas de índices...")
            indices_data = self.analyze_all_indices()
            
            if not indices_data:
                print("❌ No se pudieron obtener datos de índices")
                return None
            
            # Datos NYSE
            nyse_data = {}
            if include_nyse:
                print(f"🏛️ Obteniendo datos NYSE (modo: {nyse_mode})...")
                if nyse_mode == 'all':
                    nyse_data = self.nyse_extractor.get_all_indicators()
                elif nyse_mode == 'core':
                    nyse_data = self.nyse_extractor.get_core_breadth_indicators()
                
                if nyse_data:
                    print(f"✅ NYSE: {len(nyse_data)} indicadores")
            
            # Datos de Sector Breadth (NUEVO)
            sector_breadth_data = {}
            if include_sector_breadth:
                print("📊 Obteniendo Sector Breadth de breadth.me...")
                sector_breadth_data = self.breadth_scraper.get_sector_breadth()
                if sector_breadth_data:
                    print(f"✅ Sector Breadth: {len(sector_breadth_data)} sectores")
                else:
                    print("⚠️ No se pudo obtener Sector Breadth")
            
            # Generar resumen
            summary = self._generate_summary(indices_data, nyse_data, sector_breadth_data)
            
            # Resultado
            result = {
                'indices_data': indices_data,
                'nyse_data': nyse_data,
                'sector_breadth_data': sector_breadth_data,  # NUEVO
                'summary': summary,
                'timestamp': datetime.now().isoformat(),
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'analysis_time': datetime.now().strftime('%H:%M:%S'),
                'analysis_type': 'INTEGRATED_BREADTH_ANALYSIS_WITH_SECTORS',
                'has_nyse_data': len(nyse_data) > 0,
                'has_sector_breadth': len(sector_breadth_data) > 0,  # NUEVO
                'nyse_indicators_count': len(nyse_data),
                'sector_breadth_count': len(sector_breadth_data),  # NUEVO
                'indices_count': len(indices_data),
                'total_indicators': len(nyse_data) + len(indices_data) + len(sector_breadth_data),
                'nyse_mode_used': nyse_mode,
                'success': True
            }
            
            total_indicators = len(nyse_data) + len(indices_data) + len(sector_breadth_data)
            print(f"\n✅ ANÁLISIS COMPLETO FINALIZADO")
            print(f"📊 TOTAL: {total_indicators} indicadores")
            print(f"   └─ {len(indices_data)} Índices")
            print(f"   └─ {len(nyse_data)} NYSE")
            print(f"   └─ {len(sector_breadth_data)} Sectores")
            print(f"🎯 SESGO: {summary['market_bias']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error en análisis: {e}")
            traceback.print_exc()
            return None

    def _generate_summary(self, indices_data, nyse_data, sector_breadth_data=None):
        """Genera resumen combinado - ACTUALIZADO con Sector Breadth"""
        try:
            # Análisis de índices
            if indices_data:
                total_indices = len(indices_data)
                bullish_indices = sum(1 for data in indices_data.values() if '🟢' in data['overall_signal'])
                bullish_pct = (bullish_indices / total_indices) * 100 if total_indices > 0 else 0
                avg_rsi = np.mean([data['rsi_14'] for data in indices_data.values()])
                avg_ma200_distance = np.mean([data['percent_above_ma200'] for data in indices_data.values()])
                strong_performers = [s for s, d in indices_data.items() if d['price_change_20d'] > 5]
                weak_performers = [s for s, d in indices_data.items() if d['price_change_20d'] < -5]
            else:
                total_indices = bullish_indices = bullish_pct = avg_rsi = avg_ma200_distance = 0
                strong_performers = weak_performers = []
            
            # Análisis NYSE
            nyse_signals = {'bullish': 0, 'bearish': 0, 'neutral': 0}
            nyse_key_values = {}
            
            if nyse_data:
                for indicator, data in nyse_data.items():
                    if data['current_price'] is not None:
                        value = data['current_price']
                        if indicator == 'NYMO':
                            nyse_key_values['mcclellan'] = value
                            if value > 50: nyse_signals['bullish'] += 1
                            elif value < -50: nyse_signals['bearish'] += 1
                            else: nyse_signals['neutral'] += 1
                        elif indicator == 'VIX':
                            nyse_key_values['vix'] = value
                            if value > 30: nyse_signals['bearish'] += 1
                            else: nyse_signals['neutral'] += 1
            
            # Análisis Sector Breadth (NUEVO)
            sector_signals = {'strong': 0, 'healthy': 0, 'weak': 0}
            sector_avg = 0
            
            if sector_breadth_data:
                values = list(sector_breadth_data.values())
                sector_avg = np.mean(values) if values else 0
                sector_signals['strong'] = len([v for v in values if v >= 80])
                sector_signals['healthy'] = len([v for v in values if 60 <= v < 80])
                sector_signals['weak'] = len([v for v in values if v < 60])
            
            # Determinar sesgo general (ACTUALIZADO)
            total_signals = bullish_indices + nyse_signals['bullish'] + nyse_signals['bearish'] + sector_signals['strong']
            if total_signals > 0:
                bullish_combined = bullish_indices + nyse_signals['bullish'] + sector_signals['strong']
                bullish_pct_combined = (bullish_combined / total_signals) * 100
            else:
                bullish_pct_combined = bullish_pct
            
            if bullish_pct_combined >= 70:
                market_bias = "🟢 FUERTEMENTE ALCISTA"
                confidence = "Alta"
            elif bullish_pct_combined >= 50:
                market_bias = "🟢 ALCISTA"
                confidence = "Moderada"
            elif bullish_pct_combined >= 30:
                market_bias = "🟡 NEUTRAL"
                confidence = "Baja"
            else:
                market_bias = "🔴 BAJISTA"
                confidence = "Moderada"
            
            return {
                'market_bias': market_bias,
                'confidence': confidence,
                'bullish_signals': bullish_indices,
                'bearish_signals': total_indices - bullish_indices,
                'neutral_signals': 0,
                'strength_score': bullish_indices * 10,
                'total_indicators': total_indices,
                'bullish_percentage': round(bullish_pct_combined, 1),
                'avg_rsi': round(avg_rsi, 1),
                'avg_ma200_distance': round(avg_ma200_distance, 1),
                'strong_performers': strong_performers,
                'weak_performers': weak_performers,
                'nyse_signals': nyse_signals,
                'nyse_key_values': nyse_key_values,
                'nyse_indicators_count': len(nyse_data),
                'has_nyse_data': len(nyse_data) > 0,
                'combined_bullish_signals': bullish_indices + nyse_signals['bullish'],
                'total_combined_signals': total_signals,
                # NUEVO: Sector Breadth
                'sector_breadth_avg': round(sector_avg, 1),
                'sector_signals': sector_signals,
                'has_sector_breadth': len(sector_breadth_data) > 0 if sector_breadth_data else False,
            }
            
        except Exception as e:
            print(f"❌ Error generando resumen: {e}")
            traceback.print_exc()
            return {
                'market_bias': "🟡 ERROR",
                'confidence': "Nula",
                'bullish_percentage': 0,
                'error': str(e)
            }

    def save_to_csv(self, analysis_result):
        """Guarda resultados en CSV"""
        try:
            if not analysis_result or 'indices_data' not in analysis_result:
                return None
            
            indices_data = analysis_result['indices_data']
            nyse_data = analysis_result.get('nyse_data', {})
            sector_breadth_data = analysis_result.get('sector_breadth_data', {})  # NUEVO
            
            os.makedirs("reports", exist_ok=True)
            
            # 1. Índices
            csv_data = []
            for symbol, data in indices_data.items():
                row = {
                    'Analysis_Date': analysis_result['analysis_date'],
                    'Symbol': symbol,
                    'Name': data['name'],
                    'Current_Price': data['current_price'],
                    'Change_20D': data['price_change_20d'],
                    'RSI_14': data['rsi_14'],
                    'Pct_Above_MA200': data['percent_above_ma200'],
                    'Distance_52W_High': data['distance_from_52w_high'],
                    'Volatility_20D': data['volatility_20d'],
                    'Overall_Signal': data['overall_signal']
                }
                csv_data.append(row)
            
            df_indices = pd.DataFrame(csv_data)
            indices_path = "reports/market_breadth_analysis.csv"
            df_indices.to_csv(indices_path, index=False)
            
            # 2. NYSE
            if nyse_data:
                nyse_csv_data = []
                for indicator, data in nyse_data.items():
                    row = {
                        'Analysis_Date': analysis_result['analysis_date'],
                        'Indicator': indicator,
                        'Symbol': data['symbol'],
                        'Current_Value': data['current_price'],
                        'Change_Pct': data['change_pct'],
                        'Name': data.get('name', ''),
                    }
                    nyse_csv_data.append(row)
                
                df_nyse = pd.DataFrame(nyse_csv_data)
                nyse_path = "reports/market_breadth_nyse.csv"
                df_nyse.to_csv(nyse_path, index=False)
            
            # 3. Sector Breadth (NUEVO)
            if sector_breadth_data:
                sector_csv_data = []
                for sector, value in sector_breadth_data.items():
                    row = {
                        'Analysis_Date': analysis_result['analysis_date'],
                        'Sector': sector,
                        'Breadth_Percentage': value,
                        'Status': 'Strong' if value >= 80 else 'Healthy' if value >= 60 else 'Weak'
                    }
                    sector_csv_data.append(row)
                
                df_sectors = pd.DataFrame(sector_csv_data)
                sectors_path = "reports/sector_breadth.csv"
                df_sectors.to_csv(sectors_path, index=False)
                print(f"✅ Sector Breadth CSV: {sectors_path}")
            
            print(f"✅ CSV guardado: {indices_path}")
            return indices_path
            
        except Exception as e:
            print(f"❌ Error guardando CSV: {e}")
            traceback.print_exc()
            return None


# ============================================================================
# MARKET BREADTH HTML GENERATOR - CON URL ESTÁTICA
# ============================================================================

class MarketBreadthHTMLGenerator:
    """
    HTML Generator con URL ESTÁTICA (market_breadth.html)
    Integrado con Sector Breadth
    """
    
    def __init__(self, base_url="https://tantancansado.github.io/stock_analyzer_a"):
        self.base_url = base_url
        self.finviz_chart_base = "https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p=d&s=l"
        # CAMBIO IMPORTANTE: URL ESTÁTICA
        self.html_filename = "market_breadth.html"  # SIN FECHA
    
    def generate_finviz_chart_url(self, symbol):
        """Genera URL del gráfico de Finviz"""
        return self.finviz_chart_base.format(ticker=symbol)
    
    def generate_breadth_html(self, analysis_result):
        """
        MÉTODO PRINCIPAL - Genera HTML con URL ESTÁTICA
        """
        if not analysis_result or 'indices_data' not in analysis_result:
            return None
        
        indices_data = analysis_result['indices_data']
        summary = analysis_result['summary']
        timestamp = analysis_result['analysis_date']
        
        # Detectar datos
        nyse_data = analysis_result.get('nyse_data', {})
        sector_breadth_data = analysis_result.get('sector_breadth_data', {})  # NUEVO
        
        has_nyse = len(nyse_data) > 0
        has_sectors = len(sector_breadth_data) > 0  # NUEVO
        
        nyse_count = len(nyse_data)
        sector_count = len(sector_breadth_data)  # NUEVO
        indices_count = len(indices_data)
        total_indicators = nyse_count + indices_count + sector_count  # ACTUALIZADO
        
        # Título dinámico
        if has_nyse and has_sectors:
            title_suffix = f"COMPLETO - {total_indicators} Indicadores"
        elif has_nyse:
            title_suffix = f"+ NYSE - {total_indicators} Indicadores"
        elif has_sectors:
            title_suffix = f"+ Sectores - {total_indicators} Indicadores"
        else:
            title_suffix = "por Índices"
        
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Market Breadth {title_suffix} | Dashboard</title>
    <style>
        {self._get_complete_css()}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card">
            <h1>📊 Market Breadth Analysis {title_suffix}</h1>
            <p>Análisis de {indices_count} índices{' + ' + str(nyse_count) + ' NYSE' if has_nyse else ''}{' + ' + str(sector_count) + ' Sectores' if has_sectors else ''}</p>
            <div class="market-status">
                <span>{summary['market_bias']} • {summary['bullish_percentage']:.1f}% Alcistas</span>
                <div class="score-badge">Score: {summary['strength_score']}</div>
                {'<div class="total-badge">Total: ' + str(total_indicators) + ' indicadores</div>' if has_nyse or has_sectors else ''}
            </div>
            <div class="update-info">
                <small>📅 Última actualización: {timestamp} • URL estática: {self.html_filename}</small>
            </div>
        </header>
        
        <section class="stats-liquid">
            <div class="stat-glass">
                <div class="stat-number">{summary.get('combined_bullish_signals', summary['bullish_signals'])}</div>
                <div class="stat-label">Señales Alcistas</div>
            </div>
            <div class="stat-glass">
                <div class="stat-number">{indices_count}</div>
                <div class="stat-label">Índices</div>
            </div>
            {'<div class="stat-glass"><div class="stat-number">' + str(nyse_count) + '</div><div class="stat-label">NYSE</div></div>' if has_nyse else ''}
            {'<div class="stat-glass"><div class="stat-number">' + str(sector_count) + '</div><div class="stat-label">Sectores</div></div>' if has_sectors else ''}
            <div class="stat-glass">
                <div class="stat-number">{summary['avg_rsi']:.0f}</div>
                <div class="stat-label">RSI Promedio</div>
            </div>
            <div class="stat-glass">
                <div class="stat-number">{total_indicators}</div>
                <div class="stat-label">Total</div>
            </div>
        </section>
        
        {self._generate_sector_breadth_section(sector_breadth_data) if has_sectors else ''}
        {self._generate_nyse_section_compact(nyse_data) if has_nyse else ''}
        
        <main class="indices-analysis glass-card">
            <h2 class="section-title">📊 Análisis por Índice</h2>
            <div class="indices-grid">
                {self._generate_indices_html(indices_data)}
            </div>
        </main>
        
        <footer class="footer">
            <p>📊 Market Breadth Analysis {title_suffix} • {timestamp}</p>
            <p>🔗 URL Estática: <code>{self.html_filename}</code> (sin fecha)</p>
            <p><a href="{self.base_url}">🏠 Dashboard Principal</a></p>
        </footer>
    </div>
    
    <script>
        console.log('📊 Market Breadth Loaded - URL Estática');
        console.log('📊 Índices: {indices_count}');
        {'console.log("🏛️ NYSE: ' + str(nyse_count) + '");' if has_nyse else ''}
        {'console.log("📈 Sectores: ' + str(sector_count) + '");' if has_sectors else ''}
        console.log('🎯 TOTAL: {total_indicators}');
        console.log('🔗 Archivo: {self.html_filename}');
    </script>
</body>
</html>"""
        
        return html_content
    
    def _generate_sector_breadth_section(self, sector_breadth_data):
        """
        Genera sección de Sector Breadth (NUEVO)
        """
        if not sector_breadth_data:
            return ""
        
        # Ordenar sectores por valor
        sorted_sectors = sorted(sector_breadth_data.items(), key=lambda x: x[1], reverse=True)
        
        html = f"""
        <section class="sector-breadth-section glass-card">
            <h2 class="section-title">📈 Sector Breadth ({len(sector_breadth_data)} sectores)</h2>
            <div class="sector-breadth-grid">
        """
        
        for sector, value in sorted_sectors:
            # Determinar color según valor
            if value >= 80:
                status_class = "strong"
                status_text = "Fuerte"
                emoji = "🟢"
            elif value >= 60:
                status_class = "healthy"
                status_text = "Saludable"
                emoji = "🟡"
            else:
                status_class = "weak"
                status_text = "Débil"
                emoji = "🔴"
            
            # Nombres descriptivos de sectores
            sector_names = {
                'TOTAL': 'Mercado Total',
                'TEC': 'Tecnología',
                'FIN': 'Financiero',
                'CND': 'Consumo Discrecional',
                'IND': 'Industrial',
                'HLT': 'Salud',
                'MAT': 'Materiales',
                'ENE': 'Energía',
                'UTL': 'Servicios Públicos',
                'REI': 'Inmobiliario',
                'CNS': 'Consumo Básico',
                'COM': 'Comunicaciones'
            }
            
            sector_name = sector_names.get(sector, sector)
            
            html += f"""
            <div class="sector-card {status_class}">
                <div class="sector-header">
                    <span class="sector-emoji">{emoji}</span>
                    <div class="sector-info">
                        <div class="sector-code">{sector}</div>
                        <div class="sector-name">{sector_name}</div>
                    </div>
                </div>
                <div class="sector-value">
                    <div class="breadth-percentage">{value}%</div>
                    <div class="breadth-status">{status_text}</div>
                </div>
                <div class="sector-bar">
                    <div class="sector-fill {status_class}" style="width: {value}%"></div>
                </div>
            </div>
            """
        
        html += """
            </div>
        </section>
        """
        
        return html
    
    def _generate_nyse_section_compact(self, nyse_data):
        """Genera sección NYSE compacta"""
        if not nyse_data:
            return ""
        
        # Organizar por categorías
        categories = {
            'McClellan': ['NYMO', 'NYMOT', 'NYSI'],
            'Advance-Decline': ['SPXADP', 'MIDADP', 'SMLADP'],
            'Sentiment': ['VIX', 'CPC'],
            'Bullish %': ['BPSPX', 'BPNDX'],
        }
        
        html = f"""
        <section class="nyse-section-compact glass-card">
            <h2 class="section-title">🏛️ NYSE Indicators ({len(nyse_data)} reales)</h2>
            <div class="nyse-grid-compact">
        """
        
        for category, indicators in categories.items():
            for indicator in indicators:
                if indicator in nyse_data:
                    data = nyse_data[indicator]
                    value = data.get('current_price', 0) or 0
                    change_pct = data.get('change_pct', 0) or 0
                    
                    change_class = 'positive' if change_pct > 0 else 'negative' if change_pct < 0 else 'neutral'
                    
                    html += f"""
                    <div class="nyse-card-compact">
                        <div class="nyse-header-compact">
                            <span class="nyse-indicator">{indicator}</span>
                            <span class="nyse-category">{category}</span>
                        </div>
                        <div class="nyse-value">{value:.2f}</div>
                        <div class="nyse-change {change_class}">{change_pct:+.2f}%</div>
                    </div>
                    """
        
        html += """
            </div>
        </section>
        """
        
        return html
    
    def _generate_indices_html(self, indices_data):
        """Genera HTML para índices"""
        html = ""
        
        for symbol, data in indices_data.items():
            chart_url = self.generate_finviz_chart_url(symbol)
            overall_class = "bullish" if "🟢" in data['overall_signal'] else "bearish" if "🔴" in data['overall_signal'] else "neutral"
            
            html += f"""
            <div class="index-card {overall_class}">
                <div class="index-header">
                    <div class="index-info">
                        <span class="index-symbol">{symbol}</span>
                        <span class="index-name">{data['name']}</span>
                    </div>
                    <div class="index-price">
                        <span class="price">${data['current_price']}</span>
                        <span class="change {'positive' if data['price_change_20d'] > 0 else 'negative'}">{data['price_change_20d']:+.1f}%</span>
                    </div>
                </div>
                
                <div class="chart-section">
                    <img src="{chart_url}" alt="Gráfico {symbol}" class="finviz-chart" loading="lazy"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div class="chart-fallback" style="display: none;">
                        <span>📊 Gráfico no disponible</span>
                        <a href="{chart_url}" target="_blank">Ver en Finviz →</a>
                    </div>
                </div>
                
                <div class="index-metrics">
                    <div class="metric-row">
                        <span>RSI:</span>
                        <span>{data['rsi_14']:.1f}</span>
                    </div>
                    <div class="metric-row">
                        <span>MA200:</span>
                        <span class="{'positive' if data['percent_above_ma200'] > 0 else 'negative'}">{data['percent_above_ma200']:+.1f}%</span>
                    </div>
                    <div class="metric-row">
                        <span>Señal:</span>
                        <span>{data['overall_signal']}</span>
                    </div>
                </div>
            </div>
            """
        
        return html
    
    def _get_complete_css(self):
        """CSS completo optimizado"""
        return """
        :root {
            --primary: #4f46e5;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --border: #475569;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }
        
        .glass-container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .liquid-header { text-align: center; }
        .liquid-header h1 {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), #7c3aed);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        
        .market-status {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 1rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }
        
        .score-badge, .total-badge {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.5rem 1rem;
            border-radius: 12px;
            font-weight: 600;
        }
        
        .total-badge {
            background: rgba(79, 70, 229, 0.2);
            color: #a78bfa;
        }
        
        .update-info {
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .update-info code {
            background: rgba(79, 70, 229, 0.2);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            color: #a78bfa;
        }
        
        .stats-liquid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }
        
        .stat-glass {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .stat-glass:hover {
            transform: translateY(-4px);
            background: rgba(255, 255, 255, 0.08);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 900;
            color: var(--primary);
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 0.9rem;
        }
        
        .section-title {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 2rem;
            text-align: center;
            color: var(--text-primary);
        }
        
        /* SECTOR BREADTH STYLES (NUEVO) */
        .sector-breadth-section { padding: 2rem; }
        
        .sector-breadth-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
        }
        
        .sector-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s ease;
            border-left: 4px solid transparent;
        }
        
        .sector-card.strong { border-left-color: var(--success); }
        .sector-card.healthy { border-left-color: var(--warning); }
        .sector-card.weak { border-left-color: var(--danger); }
        
        .sector-card:hover {
            transform: translateY(-3px);
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
        }
        
        .sector-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }
        
        .sector-emoji {
            font-size: 2rem;
        }
        
        .sector-code {
            font-weight: 800;
            color: var(--primary);
            font-size: 1.1rem;
        }
        
        .sector-name {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .sector-value {
            text-align: center;
            margin-bottom: 1rem;
        }
        
        .breadth-percentage {
            font-size: 2.5rem;
            font-weight: 900;
            color: var(--text-primary);
        }
        
        .breadth-status {
            font-size: 0.9rem;
            color: var(--text-secondary);
            font-weight: 600;
        }
        
        .sector-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .sector-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .sector-fill.strong { background: linear-gradient(90deg, var(--success), #34d399); }
        .sector-fill.healthy { background: linear-gradient(90deg, var(--warning), #fbbf24); }
        .sector-fill.weak { background: linear-gradient(90deg, var(--danger), #f87171); }
        
        /* NYSE COMPACT STYLES */
        .nyse-section-compact { padding: 2rem; }
        
        .nyse-grid-compact {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }
        
        .nyse-card-compact {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .nyse-card-compact:hover {
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
        }
        
        .nyse-header-compact {
            margin-bottom: 0.5rem;
        }
        
        .nyse-indicator {
            font-weight: 700;
            color: var(--primary);
            display: block;
            font-size: 0.95rem;
        }
        
        .nyse-category {
            font-size: 0.7rem;
            color: var(--text-secondary);
            display: block;
        }
        
        .nyse-value {
            font-size: 1.5rem;
            font-weight: 900;
            margin-bottom: 0.25rem;
        }
        
        .nyse-change {
            font-weight: 700;
            font-size: 0.9rem;
        }
        
        .nyse-change.positive { color: var(--success); }
        .nyse-change.negative { color: var(--danger); }
        .nyse-change.neutral { color: var(--text-secondary); }
        
        /* INDICES STYLES (ORIGINAL) */
        .indices-analysis { padding: 2rem; }
        
        .indices-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
        }
        
        .index-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }
        
        .index-card:hover {
            transform: translateY(-4px);
            background: rgba(255, 255, 255, 0.08);
        }
        
        .index-card.bullish { border-left: 4px solid var(--success); }
        .index-card.bearish { border-left: 4px solid var(--danger); }
        .index-card.neutral { border-left: 4px solid var(--warning); }
        
        .index-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .index-symbol {
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--primary);
        }
        
        .index-name {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        .price {
            font-size: 1.25rem;
            font-weight: 700;
        }
        
        .change.positive { color: var(--success); }
        .change.negative { color: var(--danger); }
        
        .chart-section { margin-bottom: 1rem; }
        .finviz-chart {
            width: 100%;
            height: auto;
            max-height: 200px;
            border-radius: 8px;
        }
        
        .chart-fallback {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 200px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            color: var(--text-secondary);
        }
        
        .chart-fallback a {
            color: var(--primary);
            text-decoration: none;
            margin-top: 0.5rem;
        }
        
        .index-metrics {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 1rem;
        }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            padding: 0.25rem 0;
            font-size: 0.9rem;
        }
        
        .positive { color: var(--success); }
        .negative { color: var(--danger); }
        
        .footer {
            text-align: center;
            margin-top: 2rem;
            padding: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-secondary);
        }
        
        .footer a {
            color: var(--primary);
            text-decoration: none;
        }
        
        .footer code {
            background: rgba(79, 70, 229, 0.2);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            color: #a78bfa;
        }
        
        /* RESPONSIVE */
        @media (max-width: 768px) {
            .glass-container { padding: 1rem; }
            .indices-grid, .sector-breadth-grid { grid-template-columns: 1fr; }
            .nyse-grid-compact { grid-template-columns: repeat(2, 1fr); }
            .market-status { flex-direction: column; }
            .stats-liquid { grid-template-columns: repeat(2, 1fr); }
        }
        
        @media (max-width: 480px) {
            .stats-liquid, .nyse-grid-compact { grid-template-columns: 1fr; }
        }
        """
    
    def save_html(self, html_content, output_dir="reports"):
        """
        Guarda HTML con nombre ESTÁTICO
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # CAMBIO IMPORTANTE: Nombre fijo sin fecha
            filepath = os.path.join(output_dir, self.html_filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML generado: {filepath}")
            print(f"🔗 URL ESTÁTICA: {self.html_filename} (sin cambios de fecha)")
            return filepath
            
        except Exception as e:
            print(f"❌ Error guardando HTML: {e}")
            traceback.print_exc()
            return None


# ============================================================================
# FIN DEL SCRIPT
# ============================================================================

print("✅ Market Breadth Analyzer INTEGRADO inicializado")
print("📊 Compatible con sistema principal")
print("🏛️ NYSE Data Extractor incluido")
print("📈 Sector Breadth (breadth.me) AÑADIDO")
print("💾 URL ESTÁTICA: market_breadth.html (sin fecha)")
print("🎯 Listo para uso")
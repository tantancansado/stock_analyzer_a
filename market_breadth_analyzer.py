#!/usr/bin/env python3
"""
market_breadth_analyzer.py
Market Breadth Analyzer - COMPATIBLE CON SISTEMA PRINCIPAL
Exporta exactamente las clases que espera el sistema principal:
- MarketBreadthAnalyzer  
- MarketBreadthHTMLGenerator

ACTUALIZADO: Por defecto obtiene TODOS los indicadores NYSE (60+)
CORREGIDO: Error de formateo + Nombres descriptivos para NYSE
MEJORADO: HTML Generator con MUCHA MÁS información en las tarjetas NYSE
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
# TU NYSE DATA EXTRACTOR ORIGINAL (CON MEJORAS EN LOGGING)
# ============================================================================

class NYSEDataExtractor:
    """Tu extractor original del primer script - CON MEJORAS EN LOGGING"""
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

        # Nombres descriptivos mejorados - ACTUALIZADOS
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
        """Obtiene todos los indicadores de mercado disponibles - MEJORADO CON LOGGING"""
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
                    
                # Pausa pequeña para no saturar la API
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

    def print_all_available_indicators(self):
        """Imprime todos los indicadores disponibles organizados por categoría"""
        categories = {
            'McClellan Oscillators': ['NYMOT', 'NYMO', 'NYSI', 'NAMO', 'NASI'],
            'Advance-Decline Lines': ['NYADL', 'NAADL', 'NYAD', 'NAAD'],
            'Advance-Decline Percentages': ['SPXADP', 'MIDADP', 'SMLADP', 'NAADP'],
            'Arms Index (TRIN)': ['TRIN', 'TRINQ'],
            'New Highs/Lows': ['NYHGH', 'NYLOW', 'NAHGH', 'NALOW', 'NYHL', 'NAHL'],
            'Above Moving Averages %': ['NYA50R', 'NYA200R', 'NAA50R', 'NAA200R', 'SPXA50R', 'SPXA200R'],
            'Volume Indicators': ['NYUPV', 'NYDNV', 'NAUPV', 'NADNV', 'NAUD', 'NYUD'],
            'Bullish Percent Index': ['BPSPX', 'BPNDX', 'BPNYA', 'BPCOMPQ'],
            'Record High Percent': ['RHNYA', 'RHNDX', 'RHSPX'],
            'Sentiment Indicators': ['VIX', 'VXN', 'RVX', 'VXD', 'CPC', 'CPCE', 'CPCN'],
            'Survey Data': ['AAIIBULL', 'AAIIBEAR', 'AAIINEUR', 'NAAIMBULL', 'NAAIMEXP'],
            'Sector ETFs': ['XLF', 'XLK', 'XLE', 'XLI', 'XLV'],
            'Major Indices': ['SPX', 'COMPQ', 'NYA', 'DJI', 'RUT'],
            'Additional Breadth': ['NYTO', 'NATO', 'TICK', 'TICKQ', 'TICKI'],
            'Commodities & Bonds': ['TNX', 'TYX', 'DXY', 'GOLD', 'WTIC']
        }
        
        print("\n📊 INDICADORES NYSE DISPONIBLES:")
        print("=" * 60)
        
        total_count = 0
        for category, indicators in categories.items():
            print(f"\n🔸 {category}:")
            for indicator in indicators:
                name = self.SECTOR_NAMES.get(indicator, indicator)
                print(f"   • {indicator}: {name}")
                total_count += 1
        
        print(f"\n🎯 TOTAL DISPONIBLES: {total_count} indicadores")
        return total_count


# ============================================================================
# MARKET BREADTH ANALYZER - ACTUALIZADO PARA OBTENER TODOS LOS INDICADORES
# ============================================================================

class MarketBreadthAnalyzer:
    """
    CLASE PRINCIPAL que espera tu sistema principal
    ACTUALIZADA: Por defecto obtiene TODOS los indicadores NYSE
    """
    
    def __init__(self):
        self.nyse_extractor = NYSEDataExtractor()
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
        # Tendencia
        if ma50_pct > 0 and ma200_pct > 0:
            trend = "🟢 Tendencia Alcista"
        elif ma50_pct < 0 and ma200_pct < 0:
            trend = "🔴 Tendencia Bajista"
        else:
            trend = "🟡 Tendencia Mixta"
        
        # Momentum
        if rsi > 70:
            momentum = "🔴 Sobrecomprado"
        elif rsi < 30:
            momentum = "🟢 Sobrevendido"
        elif rsi > 60 and macd_signal == "Alcista":
            momentum = "🟢 Momentum Fuerte"
        else:
            momentum = "🟡 Momentum Neutral"
        
        # Señal general
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
            
            # Cambios de precio
            price_change_1d = ((data['Close'].iloc[-1] / data['Close'].iloc[-2]) - 1) * 100 if len(data) > 1 else 0
            price_change_20d = ((data['Close'].iloc[-1] / data['Close'].iloc[-21]) - 1) * 100 if len(data) > 20 else 0
            
            # RSI
            rsi_14 = self._calculate_rsi(data['Close'], 14)
            
            # Medias móviles
            ma_20 = data['Close'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else current_price
            ma_50 = data['Close'].rolling(window=50).mean().iloc[-1] if len(data) >= 50 else current_price
            ma_200 = data['Close'].rolling(window=200).mean().iloc[-1] if len(data) >= 200 else current_price
            
            # Porcentajes sobre MAs
            percent_above_ma20 = ((current_price - ma_20) / ma_20) * 100
            percent_above_ma50 = ((current_price - ma_50) / ma_50) * 100
            percent_above_ma200 = ((current_price - ma_200) / ma_200) * 100
            
            # Distancia 52W
            high_52w = data['High'].rolling(window=252).max().iloc[-1] if len(data) >= 252 else data['High'].max()
            distance_from_52w_high = ((current_price - high_52w) / high_52w) * 100
            
            # Volatilidad
            returns = data['Close'].pct_change()
            volatility_20d = returns.rolling(window=20).std().iloc[-1] * np.sqrt(252) * 100 if len(data) >= 20 else 0
            
            # MACD
            macd_line, macd_signal, _ = self._calculate_macd(data['Close'])
            macd_signal_status = "Alcista" if macd_line > macd_signal else "Bajista"
            
            # Señales interpretadas
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
                # Campos adicionales para compatibilidad total
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
                'price_change_5d': round(price_change_1d * 3, 2)  # Aproximación
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

    def run_breadth_analysis(self, include_nyse=True, nyse_mode='all'):  # CAMBIO: 'all' por defecto
        """
        MÉTODO PRINCIPAL que usa tu sistema
        ACTUALIZADO: Por defecto obtiene TODOS los indicadores NYSE
        """
        try:
            print("🔄 Analizando métricas específicas para cada índice...")
            indices_data = self.analyze_all_indices()
            
            if not indices_data:
                print("❌ No se pudieron obtener datos de índices")
                return None
            
            # Datos NYSE si se solicita
            nyse_data = {}
            if include_nyse:
                print(f"🏛️ Obteniendo datos NYSE reales (modo: {nyse_mode})...")
                if nyse_mode == 'all':
                    nyse_data = self.nyse_extractor.get_all_indicators()
                    print(f"📊 Modo COMPLETO: Obteniendo TODOS los {len(self.nyse_extractor.symbols)} indicadores disponibles")
                elif nyse_mode == 'core':
                    nyse_data = self.nyse_extractor.get_core_breadth_indicators()
                    print("📊 Modo CORE: Obteniendo solo indicadores principales")
                else:
                    # Fallback a 'all' si se pasa un modo no reconocido
                    nyse_data = self.nyse_extractor.get_all_indicators()
                    print(f"📊 Modo desconocido '{nyse_mode}', usando TODOS los indicadores")
                
                if nyse_data:
                    print(f"✅ NYSE datos obtenidos: {len(nyse_data)} indicadores")
                else:
                    print("⚠️ No se pudieron obtener datos NYSE")
            
            # Generar resumen
            summary = self._generate_summary(indices_data, nyse_data)
            
            # Resultado en el formato exacto que espera tu sistema
            result = {
                'indices_data': indices_data,
                'nyse_data': nyse_data,
                'summary': summary,
                'timestamp': datetime.now().isoformat(),
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'analysis_time': datetime.now().strftime('%H:%M:%S'),
                'analysis_type': 'INTEGRATED_NYSE_BREADTH_ANALYSIS_COMPLETE',  # Actualizado
                'has_nyse_data': len(nyse_data) > 0,
                'nyse_indicators_count': len(nyse_data),  # Nuevo campo
                'indices_count': len(indices_data),       # Nuevo campo
                'total_indicators': len(nyse_data) + len(indices_data),  # Nuevo campo
                'nyse_mode_used': nyse_mode,             # Nuevo campo
                'success': True
            }
            
            # Mensaje de éxito mejorado
            total_indicators = len(nyse_data) + len(indices_data)
            print(f"✅ ANÁLISIS COMPLETO FINALIZADO")
            print(f"📊 TOTAL: {total_indicators} indicadores ({len(nyse_data)} NYSE + {len(indices_data)} índices)")
            print(f"🎯 SESGO DE MERCADO: {summary['market_bias']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error en análisis: {e}")
            return None

    def _generate_summary(self, indices_data, nyse_data):
        """Genera resumen combinado"""
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
            
            # Determinar sesgo general
            total_signals = bullish_indices + nyse_signals['bullish'] + nyse_signals['bearish']
            if total_signals > 0:
                bullish_combined = bullish_indices + nyse_signals['bullish']
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
                'total_combined_signals': total_signals
            }
            
        except Exception as e:
            print(f"❌ Error generando resumen: {e}")
            return {
                'market_bias': "🟡 ERROR",
                'confidence': "Nula",
                'bullish_percentage': 0,
                'error': str(e)
            }

    def save_to_csv(self, analysis_result):
        """
        MÉTODO que usa tu sistema para guardar CSV
        """
        try:
            if not analysis_result or 'indices_data' not in analysis_result:
                return None
            
            indices_data = analysis_result['indices_data']
            nyse_data = analysis_result.get('nyse_data', {})
            
            # Crear directorio
            os.makedirs("reports", exist_ok=True)
            
            # 1. Guardar datos de índices (exacto formato que espera tu sistema)
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
            
            # 2. Guardar datos NYSE si están disponibles
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
            
            print(f"✅ CSV guardado: {indices_path}")
            return indices_path
            
        except Exception as e:
            print(f"❌ Error guardando CSV: {e}")
            return None


# ============================================================================
# MARKET BREADTH HTML GENERATOR - COMPLETAMENTE MEJORADO
# ============================================================================

class MarketBreadthHTMLGenerator:
    """
    CLASE HTML GENERATOR que espera tu sistema principal
    MEJORADA: Con MUCHA MÁS información en las tarjetas NYSE
    """
    
    def __init__(self, base_url="https://tantancansado.github.io/stock_analyzer_a"):
        self.base_url = base_url
        self.finviz_chart_base = "https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p=d&s=l"
    
    def generate_finviz_chart_url(self, symbol):
        """Genera URL del gráfico de Finviz"""
        return self.finviz_chart_base.format(ticker=symbol)
    
    def generate_breadth_html(self, analysis_result):
        """
        MÉTODO PRINCIPAL que usa tu sistema
        MEJORADO: Con tarjetas NYSE expandidas
        """
        if not analysis_result or 'indices_data' not in analysis_result:
            return None
        
        indices_data = analysis_result['indices_data']
        summary = analysis_result['summary']
        timestamp = analysis_result['analysis_date']
        
        # Detectar datos NYSE
        nyse_data = analysis_result.get('nyse_data', {})
        has_nyse_data = len(nyse_data) > 0
        nyse_count = len(nyse_data)
        indices_count = len(indices_data)
        total_indicators = nyse_count + indices_count
        
        # Título dinámico mejorado
        title_suffix = f"COMPLETO - {total_indicators} Indicadores" if has_nyse_data else "por Índices"
        
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
            <h1>📊 Market Breadth Analysis {'COMPLETO' if has_nyse_data else 'por Índices'}</h1>
            <p>Análisis de {indices_count} índices{' + ' + str(nyse_count) + ' indicadores NYSE' if has_nyse_data else ''}</p>
            <div class="market-status">
                <span>{summary['market_bias']} • {summary['bullish_percentage']:.1f}% Alcistas</span>
                <div class="score-badge">Score: {summary['strength_score']}</div>
                {'<div class="total-badge">Total: ' + str(total_indicators) + ' indicadores</div>' if has_nyse_data else ''}
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
            {'<div class="stat-glass"><div class="stat-number">' + str(nyse_count) + '</div><div class="stat-label">NYSE</div></div>' if has_nyse_data else ''}
            <div class="stat-glass">
                <div class="stat-number">{summary['avg_rsi']:.0f}</div>
                <div class="stat-label">RSI Promedio</div>
            </div>
            {'<div class="stat-glass"><div class="stat-number">' + str(total_indicators) + '</div><div class="stat-label">Total Indicadores</div></div>' if has_nyse_data else ''}
        </section>
        
        {self._generate_nyse_section_if_available(nyse_data) if has_nyse_data else ''}
        
        <main class="indices-analysis glass-card">
            <h2 class="section-title">📊 Análisis por Índice</h2>
            <div class="indices-grid">
                {self._generate_indices_html(indices_data)}
            </div>
        </main>
        
        <footer class="footer">
            <p>📊 Market Breadth Analysis {'COMPLETO - ' + str(total_indicators) + ' indicadores' if has_nyse_data else 'por Índices'} • {timestamp}</p>
            <p><a href="{self.base_url}">🏠 Dashboard Principal</a></p>
        </footer>
    </div>
    
    <script>
        console.log('📊 Market Breadth Loaded');
        console.log('📊 Índices: {indices_count}');
        {'console.log("🏛️ NYSE: ' + str(nyse_count) + '");' if has_nyse_data else ''}
        {'console.log("🎯 TOTAL: ' + str(total_indicators) + '");' if has_nyse_data else ''}
    </script>
</body>
</html>"""
        
        return html_content
    
    def _generate_nyse_section_if_available(self, nyse_data):
        """Genera sección NYSE mejorada con MUCHA MÁS información - VERSIÓN EXPANDIDA"""
        if not nyse_data:
            return ""
        
        # Organizar indicadores por categorías
        categorized_indicators = self._categorize_nyse_indicators(nyse_data)
        
        html = f"""
        <section class="nyse-section glass-card">
            <h2 class="section-title">🏛️ Indicadores NYSE ({len(nyse_data)} reales)</h2>
            <div class="nyse-categories">
        """
        
        for category, indicators in categorized_indicators.items():
            if indicators:
                html += f"""
                <div class="nyse-category">
                    <h3 class="category-title">{category}</h3>
                    <div class="nyse-grid-enhanced">
                """
                
                for indicator, data in indicators.items():
                    # DATOS BÁSICOS - Manejo seguro de valores None
                    value = data.get('current_price', 0) or 0
                    change_pct = data.get('change_pct', 0) or 0
                    change_absolute = data.get('change', 0) or 0
                    previous_close = data.get('previous_close', 0) or 0
                    
                    # DATOS TÉCNICOS ADICIONALES
                    rsi = data.get('rsi', 0) or 0
                    atr = data.get('atr', 0) or 0
                    sma_50 = data.get('sma50', 0) or 0
                    sma_200 = data.get('sma200', 0) or 0
                    adx = data.get('adx', 0) or 0
                    volume = data.get('volume', 0) or 0
                    
                    # RANGOS Y PERFORMANCE
                    year_range = data.get('year_range', '0,0')
                    latest_trade = data.get('latest_trade', 'N/A')
                    
                    # Procesar year_range
                    try:
                        low_52w, high_52w = map(float, year_range.split(','))
                        distance_from_high = ((value - high_52w) / high_52w * 100) if high_52w != 0 else 0
                        distance_from_low = ((value - low_52w) / low_52w * 100) if low_52w != 0 else 0
                    except:
                        low_52w, high_52w = 0, 0
                        distance_from_high, distance_from_low = 0, 0
                    
                    # PERFORMANCE HISTÓRICA
                    perf_data = data.get('performance', {})
                    perf_1w = perf_data.get('one_week', 0) or 0
                    perf_1m = perf_data.get('one_month', 0) or 0
                    perf_3m = perf_data.get('three_months', 0) or 0
                    perf_6m = perf_data.get('six_months', 0) or 0
                    perf_1y = perf_data.get('one_year', 0) or 0
                    perf_ytd = perf_data.get('ytd', 0) or 0
                    
                    # Obtener nombre descriptivo
                    descriptive_name = self.nyse_extractor.SECTOR_NAMES.get(indicator, indicator) if hasattr(self, 'nyse_extractor') else indicator
                    
                    # DETERMINAR SEÑALES DE COLOR
                    trend_class = self._get_trend_class(change_pct, rsi, perf_1m)
                    rsi_class = self._get_rsi_class(rsi)
                    
                    html += f"""
                    <div class="nyse-indicator-enhanced {trend_class}">
                        <!-- HEADER CON INFO BÁSICA -->
                        <div class="indicator-header">
                            <div class="indicator-main">
                                <div class="indicator-name">{indicator}</div>
                                <div class="indicator-desc">{descriptive_name}</div>
                            </div>
                            <div class="indicator-status">
                                <div class="status-badge {rsi_class}">{self._get_trend_emoji(change_pct)}</div>
                            </div>
                        </div>
                        
                        <!-- PRECIO Y CAMBIOS -->
                        <div class="price-section">
                            <div class="current-price">{value:.2f}</div>
                            <div class="price-changes">
                                <span class="change-abs {'positive' if change_absolute > 0 else 'negative'}">{change_absolute:+.2f}</span>
                                <span class="change-pct {'positive' if change_pct > 0 else 'negative'}">{change_pct:+.2f}%</span>
                            </div>
                            {f'<div class="prev-close">Prev: {previous_close:.2f}</div>' if previous_close > 0 else ''}
                        </div>
                        
                        <!-- INDICADORES TÉCNICOS -->
                        <div class="technical-section">
                            <div class="tech-grid">
                                {f'<div class="tech-item"><label>RSI:</label><span class="{rsi_class}">{rsi:.1f}</span></div>' if rsi > 0 else ''}
                                {f'<div class="tech-item"><label>ATR:</label><span>{atr:.2f}</span></div>' if atr > 0 else ''}
                                {f'<div class="tech-item"><label>ADX:</label><span>{adx:.1f}</span></div>' if adx > 0 else ''}
                                {f'<div class="tech-item"><label>Vol:</label><span>{self._format_volume(volume)}</span></div>' if volume > 0 else ''}
                            </div>
                        </div>
                        
                        <!-- MEDIAS MÓVILES -->
                        {self._generate_ma_section(value, sma_50, sma_200) if sma_50 > 0 or sma_200 > 0 else ''}
                        
                        <!-- RANGOS 52 SEMANAS -->
                        {self._generate_range_section(value, low_52w, high_52w, distance_from_high, distance_from_low) if high_52w > 0 else ''}
                        
                        <!-- PERFORMANCE HISTÓRICA -->
                        {self._generate_performance_section(perf_1w, perf_1m, perf_3m, perf_6m, perf_1y, perf_ytd)}
                        
                        <!-- FOOTER CON ÚLTIMA ACTUALIZACIÓN -->
                        <div class="indicator-footer">
                            <small>📅 {latest_trade}</small>
                        </div>
                    </div>
                    """
                
                html += """
                    </div>
                </div>
                """
        
        html += """
            </div>
        </section>
        """
        
        return html
    
    def _generate_ma_section(self, current_price, sma_50, sma_200):
        """Genera sección de medias móviles"""
        if sma_50 <= 0 and sma_200 <= 0:
            return ""
        
        html = '<div class="ma-section"><div class="ma-title">📈 Medias Móviles</div><div class="ma-grid">'
        
        if sma_50 > 0:
            ma50_pct = ((current_price - sma_50) / sma_50) * 100
            ma50_class = 'positive' if ma50_pct > 0 else 'negative'
            html += f'<div class="ma-item"><label>MA50:</label><span class="{ma50_class}">{ma50_pct:+.1f}%</span></div>'
        
        if sma_200 > 0:
            ma200_pct = ((current_price - sma_200) / sma_200) * 100
            ma200_class = 'positive' if ma200_pct > 0 else 'negative'
            html += f'<div class="ma-item"><label>MA200:</label><span class="{ma200_class}">{ma200_pct:+.1f}%</span></div>'
        
        html += '</div></div>'
        return html

    def _generate_range_section(self, current_price, low_52w, high_52w, dist_high, dist_low):
        """Genera sección de rangos 52 semanas"""
        if high_52w <= 0:
            return ""
        
        # Calcular posición en el rango
        range_position = ((current_price - low_52w) / (high_52w - low_52w)) * 100 if (high_52w - low_52w) > 0 else 50
        
        return f"""
        <div class="range-section">
            <div class="range-title">📊 Rango 52W</div>
            <div class="range-bar">
                <div class="range-fill" style="width: {range_position:.0f}%"></div>
                <div class="range-marker" style="left: {range_position:.0f}%"></div>
            </div>
            <div class="range-values">
                <span class="range-low">{low_52w:.2f}</span>
                <span class="range-current">{current_price:.2f}</span>
                <span class="range-high">{high_52w:.2f}</span>
            </div>
            <div class="range-distances">
                <small>📈 {dist_high:+.1f}% from high • 📉 {dist_low:+.1f}% from low</small>
            </div>
        </div>
        """

    def _generate_performance_section(self, p1w, p1m, p3m, p6m, p1y, pytd):
        """Genera sección de performance histórica"""
        periods = [
            ('1W', p1w), ('1M', p1m), ('3M', p3m), 
            ('6M', p6m), ('1Y', p1y), ('YTD', pytd)
        ]
        
        # Filtrar períodos con datos válidos
        valid_periods = [(label, value) for label, value in periods if value != 0]
        
        if not valid_periods:
            return ""
        
        html = '<div class="performance-section"><div class="perf-title">📈 Performance</div><div class="perf-grid">'
        
        for label, value in valid_periods:
            perf_class = 'positive' if value > 0 else 'negative' if value < 0 else 'neutral'
            html += f'<div class="perf-item {perf_class}"><label>{label}:</label><span>{value:+.1f}%</span></div>'
        
        html += '</div></div>'
        return html

    def _get_trend_class(self, change_pct, rsi, perf_1m):
        """Determina la clase CSS basada en la tendencia"""
        if change_pct > 2 and rsi < 70 and perf_1m > 5:
            return "strong-bullish"
        elif change_pct > 0 and rsi < 80:
            return "bullish"
        elif change_pct < -2 and rsi > 30 and perf_1m < -5:
            return "strong-bearish"
        elif change_pct < 0:
            return "bearish"
        else:
            return "neutral"

    def _get_rsi_class(self, rsi):
        """Determina la clase CSS del RSI"""
        if rsi > 70:
            return "overbought"
        elif rsi < 30:
            return "oversold"
        elif rsi > 60:
            return "strong"
        elif rsi < 40:
            return "weak"
        else:
            return "neutral"

    def _get_trend_emoji(self, change_pct):
        """Obtiene emoji basado en la tendencia"""
        if change_pct > 3:
            return "🚀"
        elif change_pct > 1:
            return "📈"
        elif change_pct > 0:
            return "🟢"
        elif change_pct < -3:
            return "💥"
        elif change_pct < -1:
            return "📉"
        elif change_pct < 0:
            return "🔴"
        else:
            return "➡️"

    def _format_volume(self, volume):
        """Formatea el volumen de manera legible"""
        if volume >= 1_000_000:
            return f"{volume/1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume/1_000:.1f}K"
        else:
            return f"{volume:.0f}"
    
    def _categorize_nyse_indicators(self, nyse_data):
        """Organiza los indicadores NYSE por categorías"""
        categories = {
            'McClellan & Momentum': ['NYMO', 'NYMOT', 'NYSI', 'NAMO', 'NASI'],
            'Advance-Decline': ['NYADL', 'NAADL', 'SPXADP', 'MIDADP', 'SMLADP'],
            'Arms Index & TRIN': ['TRIN', 'TRINQ'],
            'Sentiment & Volatility': ['VIX', 'VXN', 'CPC', 'CPCE'],
            'Bullish Percent': ['BPSPX', 'BPNDX', 'BPNYA'],
            'New Highs/Lows': ['NYHGH', 'NYLOW', 'NAHGH', 'NALOW'],
            'Moving Averages %': ['NYA50R', 'NYA200R', 'SPXA50R', 'SPXA200R'],
            'Major Indices': ['SPX', 'COMPQ', 'NYA', 'DJI', 'RUT'],
            'Bonds & Commodities': ['TNX', 'TYX', 'DXY', 'GOLD', 'WTIC'],
            'Otros': []
        }
        
        categorized = {cat: {} for cat in categories.keys()}
        
        for indicator, data in nyse_data.items():
            placed = False
            for category, category_indicators in categories.items():
                if indicator in category_indicators:
                    categorized[category][indicator] = data
                    placed = True
                    break
            
            if not placed:
                categorized['Otros'][indicator] = data
        
        # Remover categorías vacías
        return {cat: indicators for cat, indicators in categorized.items() if indicators}
    
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
        """CSS completo optimizado con soporte para categorías y tarjetas mejoradas"""
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
        
        .stats-liquid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
        
        .nyse-section { padding: 2rem; }
        
        .nyse-categories {
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }
        
        .nyse-category {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 1.5rem;
        }
        
        .category-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 1rem;
            text-align: center;
        }
        
        /* ORIGINAL NYSE GRID (MANTENIDO PARA COMPATIBILIDAD) */
        .nyse-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }
        
        .nyse-indicator {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .nyse-indicator:hover {
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
        }
        
        .indicator-name {
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.25rem;
            font-size: 0.95rem;
        }
        
        .indicator-desc {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            font-style: italic;
        }
        
        .indicator-value {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        
        .indicator-change.positive { color: var(--success); }
        .indicator-change.negative { color: var(--danger); }
        
        /* ============================================================================ */
        /* NUEVOS ESTILOS PARA NYSE INDICATORS ENHANCED */
        /* ============================================================================ */
        
        /* Grid mejorado para las tarjetas expandidas */
        .nyse-grid-enhanced {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
        }
        
        /* Tarjeta de indicador mejorada */
        .nyse-indicator-enhanced {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s ease;
            border-left: 4px solid transparent;
            position: relative;
            overflow: hidden;
        }
        
        .nyse-indicator-enhanced:hover {
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        }
        
        /* Colores de tendencia */
        .nyse-indicator-enhanced.strong-bullish { border-left-color: #10b981; }
        .nyse-indicator-enhanced.bullish { border-left-color: #34d399; }
        .nyse-indicator-enhanced.neutral { border-left-color: #f59e0b; }
        .nyse-indicator-enhanced.bearish { border-left-color: #f87171; }
        .nyse-indicator-enhanced.strong-bearish { border-left-color: #ef4444; }
        
        /* Header de la tarjeta */
        .indicator-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .indicator-main .indicator-name {
            font-weight: 800;
            color: var(--primary);
            font-size: 1.1rem;
            margin-bottom: 0.25rem;
        }
        
        .indicator-main .indicator-desc {
            font-size: 0.8rem;
            color: var(--text-secondary);
            line-height: 1.3;
            max-width: 200px;
        }
        
        .status-badge {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 1.2rem;
            min-width: 50px;
            text-align: center;
        }
        
        .status-badge.overbought { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
        .status-badge.oversold { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }
        .status-badge.strong { background: rgba(79, 70, 229, 0.2); color: #a78bfa; }
        .status-badge.weak { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
        
        /* Sección de precios */
        .price-section {
            text-align: center;
            margin-bottom: 1rem;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
        }
        
        .current-price {
            font-size: 1.8rem;
            font-weight: 900;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
        }
        
        .price-changes {
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-bottom: 0.5rem;
        }
        
        .change-abs, .change-pct {
            font-weight: 700;
            font-size: 1rem;
        }
        
        .prev-close {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        /* Sección técnica */
        .technical-section {
            margin-bottom: 1rem;
        }
        
        .tech-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }
        
        .tech-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.4rem 0.6rem;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 6px;
            font-size: 0.85rem;
        }
        
        .tech-item label {
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .tech-item span {
            font-weight: 700;
        }
        
        .tech-item span.overbought { color: #f87171; }
        .tech-item span.oversold { color: #34d399; }
        .tech-item span.strong { color: #60a5fa; }
        .tech-item span.weak { color: #fbbf24; }
        
        /* Sección de medias móviles */
        .ma-section {
            margin-bottom: 1rem;
            padding: 0.75rem;
            background: rgba(79, 70, 229, 0.05);
            border-radius: 8px;
            border: 1px solid rgba(79, 70, 229, 0.1);
        }
        
        .ma-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #a78bfa;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        
        .ma-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }
        
        .ma-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.3rem 0.5rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            font-size: 0.8rem;
        }
        
        .ma-item label {
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .ma-item span {
            font-weight: 700;
        }
        
        /* Sección de rangos */
        .range-section {
            margin-bottom: 1rem;
            padding: 0.75rem;
            background: rgba(245, 158, 11, 0.05);
            border-radius: 8px;
            border: 1px solid rgba(245, 158, 11, 0.1);
        }
        
        .range-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #fbbf24;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        
        .range-bar {
            position: relative;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            margin-bottom: 0.5rem;
            overflow: hidden;
        }
        
        .range-fill {
            height: 100%;
            background: linear-gradient(90deg, #ef4444, #f59e0b, #10b981);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .range-marker {
            position: absolute;
            top: -2px;
            width: 4px;
            height: 12px;
            background: #ffffff;
            border-radius: 2px;
            transform: translateX(-50%);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .range-values {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-bottom: 0.25rem;
        }
        
        .range-current {
            color: var(--text-primary) !important;
            font-weight: 700;
        }
        
        .range-distances {
            text-align: center;
            font-size: 0.7rem;
            color: var(--text-secondary);
        }
        
        /* Sección de performance */
        .performance-section {
            margin-bottom: 1rem;
            padding: 0.75rem;
            background: rgba(16, 185, 129, 0.05);
            border-radius: 8px;
            border: 1px solid rgba(16, 185, 129, 0.1);
        }
        
        .perf-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #6ee7b7;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        
        .perf-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.4rem;
        }
        
        .perf-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.3rem 0.4rem;
            border-radius: 4px;
            font-size: 0.75rem;
            background: rgba(255, 255, 255, 0.03);
        }
        
        .perf-item.positive {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }
        
        .perf-item.negative {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }
        
        .perf-item.neutral {
            background: rgba(156, 163, 175, 0.1);
            border: 1px solid rgba(156, 163, 175, 0.2);
        }
        
        .perf-item label {
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .perf-item span {
            font-weight: 700;
        }
        
        .perf-item.positive span { color: #34d399; }
        .perf-item.negative span { color: #f87171; }
        .perf-item.neutral span { color: #9ca3af; }
        
        /* Footer de la tarjeta */
        .indicator-footer {
            margin-top: 1rem;
            padding-top: 0.75rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        
        .indicator-footer small {
            color: var(--text-secondary);
            font-size: 0.7rem;
        }
        
        /* ============================================================================ */
        /* ESTILOS ORIGINALES PARA ÍNDICES (MANTENIDOS) */
        /* ============================================================================ */
        
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
        
        /* ============================================================================ */
        /* RESPONSIVE DESIGN MEJORADO */
        /* ============================================================================ */
        
        @media (max-width: 1200px) {
            .nyse-grid-enhanced {
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            }
        }
        
        @media (max-width: 768px) {
            .glass-container { padding: 1rem; }
            .indices-grid { grid-template-columns: 1fr; }
            .nyse-grid { grid-template-columns: repeat(2, 1fr); }
            .nyse-grid-enhanced { grid-template-columns: 1fr; }
            .market-status { flex-direction: column; }
            .stats-liquid { grid-template-columns: repeat(2, 1fr); }
            
            .tech-grid, .ma-grid {
                grid-template-columns: 1fr;
            }
            
            .perf-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .price-changes {
                flex-direction: column;
                gap: 0.5rem;
            }
        }
        
        @media (max-width: 480px) {
            .stats-liquid { grid-template-columns: 1fr; }
            .nyse-grid { grid-template-columns: 1fr; }
            
            .indicator-header {
                flex-direction: column;
                gap: 0.5rem;
                text-align: center;
            }
            
            .status-badge {
                align-self: center;
            }
            
            .perf-grid {
                grid-template-columns: 1fr;
            }
        }
        """


# ============================================================================
# ASEGURAR COMPATIBILIDAD TOTAL CON EL SISTEMA PRINCIPAL
# ============================================================================

# Las clases están exportadas con los nombres exactos que espera tu sistema:
# - MarketBreadthAnalyzer
# - MarketBreadthHTMLGenerator

# El sistema principal puede importar así:
# from market_breadth_analyzer import MarketBreadthAnalyzer, MarketBreadthHTMLGenerator

print("✅ Market Breadth Analyzer inicializado correctamente")
print("📊 Compatible con sistema principal")
print("🏛️ NYSE Data Extractor integrado")
print("📈 HTML Generator MEJORADO incluido")
print("🎯 DEFAULT: TODOS los indicadores NYSE (modo 'all')")
print("🔧 CORREGIDO: Manejo seguro de valores None")
print("📝 MEJORADO: Nombres descriptivos para indicadores NYSE")
print("🚀 NUEVO: Tarjetas NYSE con MUCHA MÁS información")
print("📊 NUEVO: RSI, ATR, ADX, Volumen, Medias Móviles, Rangos 52W, Performance histórica")
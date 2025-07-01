#!/usr/bin/env python3
"""
Market Breadth Analyzer - Métricas ESPECÍFICAS por cada índice con GRÁFICOS
Calcula indicadores reales para SPY, EUSA, ACWI, etc. individualmente + gráficos Finviz
"""

import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta
import time
import json
import os
from pathlib import Path
import traceback

class MarketBreadthAnalyzer:
    """
    Analizador de amplitud con métricas ESPECÍFICAS por índice
    Calcula indicadores reales para cada ETF/índice individualmente
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # ÍNDICES PRINCIPALES con métricas específicas
        self.market_symbols = {
            'SPY': 'S&P 500 ETF',
            'QQQ': 'NASDAQ 100 ETF', 
            'DIA': 'Dow Jones ETF',
            'IWM': 'Russell 2000 ETF',
            'VTI': 'Total Stock Market ETF',
            'EUSA': 'iShares MSCI USA ETF',           # Tu solicitud específica
            'ACWI': 'iShares MSCI ACWI ETF',         # Tu solicitud específica
            'EFA': 'iShares MSCI EAFE ETF',
            'EEM': 'iShares MSCI Emerging Markets ETF'
        }
        
        # Sectores para diversificación
        self.sector_etfs = {
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples', 
            'XLE': 'Energy',
            'XLF': 'Financials',
            'XLV': 'Health Care',
            'XLI': 'Industrials',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLK': 'Technology',
            'XLC': 'Communication',
            'XLU': 'Utilities'
        }
        
        # MÉTRICAS ESPECÍFICAS que calcularemos para cada índice
        self.metrics_per_index = [
            'current_price',
            'price_change_1d',
            'price_change_5d', 
            'price_change_20d',
            'rsi_14',
            'rsi_50',
            'ma_20',
            'ma_50',
            'ma_200',
            'percent_above_ma20',
            'percent_above_ma50', 
            'percent_above_ma200',
            'distance_from_52w_high',
            'distance_from_52w_low',
            'volume_ratio_20d',
            'volatility_20d',
            'bollinger_position',
            'macd_signal',
            'stochastic_k',
            'williams_r'
        ]
        
    def get_comprehensive_index_data(self, symbol, period='1y'):
        """
        Obtiene y calcula TODAS las métricas específicas para UN índice
        """
        try:
            print(f"   📊 Analizando {symbol}...")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                print(f"⚠️ Sin datos para {symbol}")
                return None
            
            # PRECIOS BÁSICOS
            current_price = data['Close'].iloc[-1]
            
            # CAMBIOS DE PRECIO
            price_change_1d = ((data['Close'].iloc[-1] / data['Close'].iloc[-2]) - 1) * 100 if len(data) > 1 else 0
            price_change_5d = ((data['Close'].iloc[-1] / data['Close'].iloc[-6]) - 1) * 100 if len(data) > 5 else 0
            price_change_20d = ((data['Close'].iloc[-1] / data['Close'].iloc[-21]) - 1) * 100 if len(data) > 20 else 0
            
            # RSI (14 y 50 períodos)
            rsi_14 = self._calculate_rsi(data['Close'], 14)
            rsi_50 = self._calculate_rsi(data['Close'], 50) if len(data) >= 50 else 50
            
            # MEDIAS MÓVILES
            ma_20 = data['Close'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else current_price
            ma_50 = data['Close'].rolling(window=50).mean().iloc[-1] if len(data) >= 50 else current_price
            ma_200 = data['Close'].rolling(window=200).mean().iloc[-1] if len(data) >= 200 else current_price
            
            # PORCENTAJES SOBRE MAs
            percent_above_ma20 = ((current_price - ma_20) / ma_20) * 100
            percent_above_ma50 = ((current_price - ma_50) / ma_50) * 100
            percent_above_ma200 = ((current_price - ma_200) / ma_200) * 100
            
            # MÁXIMOS Y MÍNIMOS 52 SEMANAS
            high_52w = data['High'].rolling(window=252).max().iloc[-1] if len(data) >= 252 else data['High'].max()
            low_52w = data['Low'].rolling(window=252).min().iloc[-1] if len(data) >= 252 else data['Low'].min()
            
            distance_from_52w_high = ((current_price - high_52w) / high_52w) * 100
            distance_from_52w_low = ((current_price - low_52w) / low_52w) * 100
            
            # VOLUMEN
            avg_volume_20d = data['Volume'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else data['Volume'].iloc[-1]
            current_volume = data['Volume'].iloc[-1]
            volume_ratio_20d = current_volume / avg_volume_20d if avg_volume_20d > 0 else 1
            
            # VOLATILIDAD (20 días)
            returns = data['Close'].pct_change()
            volatility_20d = returns.rolling(window=20).std().iloc[-1] * np.sqrt(252) * 100 if len(data) >= 20 else 0
            
            # BANDAS DE BOLLINGER
            bollinger_middle = ma_20
            bollinger_std = data['Close'].rolling(window=20).std().iloc[-1] if len(data) >= 20 else 0
            bollinger_upper = bollinger_middle + (bollinger_std * 2)
            bollinger_lower = bollinger_middle - (bollinger_std * 2)
            
            if bollinger_upper != bollinger_lower:
                bollinger_position = (current_price - bollinger_lower) / (bollinger_upper - bollinger_lower) * 100
            else:
                bollinger_position = 50
            
            # MACD
            macd_line, macd_signal, macd_histogram = self._calculate_macd(data['Close'])
            macd_signal_status = "Alcista" if macd_line > macd_signal else "Bajista"
            
            # STOCHASTIC
            stochastic_k = self._calculate_stochastic_k(data, 14)
            
            # WILLIAMS %R
            williams_r = self._calculate_williams_r(data, 14)
            
            # COMPILAR TODAS LAS MÉTRICAS
            comprehensive_metrics = {
                'symbol': symbol,
                'name': self.market_symbols.get(symbol, symbol),
                'current_price': round(current_price, 2),
                'price_change_1d': round(price_change_1d, 2),
                'price_change_5d': round(price_change_5d, 2),
                'price_change_20d': round(price_change_20d, 2),
                'rsi_14': round(rsi_14, 1),
                'rsi_50': round(rsi_50, 1),
                'ma_20': round(ma_20, 2),
                'ma_50': round(ma_50, 2),
                'ma_200': round(ma_200, 2),
                'percent_above_ma20': round(percent_above_ma20, 2),
                'percent_above_ma50': round(percent_above_ma50, 2),
                'percent_above_ma200': round(percent_above_ma200, 2),
                'distance_from_52w_high': round(distance_from_52w_high, 2),
                'distance_from_52w_low': round(distance_from_52w_low, 2),
                'high_52w': round(high_52w, 2),
                'low_52w': round(low_52w, 2),
                'volume_ratio_20d': round(volume_ratio_20d, 2),
                'volatility_20d': round(volatility_20d, 2),
                'bollinger_position': round(bollinger_position, 1),
                'macd_signal': macd_signal_status,
                'stochastic_k': round(stochastic_k, 1),
                'williams_r': round(williams_r, 1),
                # SEÑALES INTERPRETADAS
                'trend_signal': self._interpret_trend_signal(percent_above_ma20, percent_above_ma50, percent_above_ma200),
                'momentum_signal': self._interpret_momentum_signal(rsi_14, macd_signal_status),
                'position_signal': self._interpret_position_signal(distance_from_52w_high, bollinger_position),
                'volume_signal': self._interpret_volume_signal(volume_ratio_20d),
                'overall_signal': 'Calculando...'  # Se calculará después
            }
            
            # CALCULAR SEÑAL GENERAL
            comprehensive_metrics['overall_signal'] = self._calculate_overall_signal(comprehensive_metrics)
            
            print(f"     ✅ {symbol}: ${current_price:.2f} | Trend: {comprehensive_metrics['trend_signal']} | RSI: {rsi_14:.1f}")
            
            return comprehensive_metrics
            
        except Exception as e:
            print(f"❌ Error obteniendo datos para {symbol}: {e}")
            return None
    
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
            macd_histogram = macd_line - macd_signal
            
            return macd_line.iloc[-1], macd_signal.iloc[-1], macd_histogram.iloc[-1]
        except:
            return 0, 0, 0
    
    def _calculate_stochastic_k(self, data, period=14):
        """Calcula Stochastic %K"""
        try:
            low_min = data['Low'].rolling(window=period).min()
            high_max = data['High'].rolling(window=period).max()
            k_percent = 100 * ((data['Close'] - low_min) / (high_max - low_min))
            return k_percent.iloc[-1] if not k_percent.empty else 50
        except:
            return 50
    
    def _calculate_williams_r(self, data, period=14):
        """Calcula Williams %R"""
        try:
            high_max = data['High'].rolling(window=period).max()
            low_min = data['Low'].rolling(window=period).min()
            williams_r = -100 * ((high_max - data['Close']) / (high_max - low_min))
            return williams_r.iloc[-1] if not williams_r.empty else -50
        except:
            return -50
    
    def _interpret_trend_signal(self, ma20_pct, ma50_pct, ma200_pct):
        """Interpreta señal de tendencia basada en MAs"""
        if ma20_pct > 2 and ma50_pct > 0 and ma200_pct > 0:
            return "🟢 Tendencia Muy Alcista"
        elif ma50_pct > 0 and ma200_pct > 0:
            return "🟢 Tendencia Alcista"
        elif ma20_pct < -2 and ma50_pct < 0 and ma200_pct < 0:
            return "🔴 Tendencia Muy Bajista"
        elif ma50_pct < 0 and ma200_pct < 0:
            return "🔴 Tendencia Bajista"
        else:
            return "🟡 Tendencia Mixta"
    
    def _interpret_momentum_signal(self, rsi, macd_signal):
        """Interpreta señal de momentum"""
        if rsi > 70:
            return "🔴 Sobrecomprado"
        elif rsi < 30:
            return "🟢 Sobrevendido"
        elif rsi > 60 and macd_signal == "Alcista":
            return "🟢 Momentum Fuerte"
        elif rsi < 40 and macd_signal == "Bajista":
            return "🔴 Momentum Débil"
        else:
            return "🟡 Momentum Neutral"
    
    def _interpret_position_signal(self, distance_high, bollinger_pos):
        """Interpreta señal de posición"""
        if distance_high > -5:
            return "🟢 Cerca de Máximos"
        elif distance_high < -20:
            return "🔴 Lejos de Máximos"
        elif bollinger_pos > 80:
            return "🔴 Bollinger Superior"
        elif bollinger_pos < 20:
            return "🟢 Bollinger Inferior"
        else:
            return "🟡 Posición Media"
    
    def _interpret_volume_signal(self, volume_ratio):
        """Interpreta señal de volumen"""
        if volume_ratio > 1.5:
            return "🟢 Volumen Alto"
        elif volume_ratio < 0.7:
            return "🔴 Volumen Bajo"
        else:
            return "🟡 Volumen Normal"
    
    def _calculate_overall_signal(self, metrics):
        """Calcula señal general del índice"""
        signals = [
            metrics['trend_signal'],
            metrics['momentum_signal'], 
            metrics['position_signal']
        ]
        
        bullish_count = sum(1 for signal in signals if '🟢' in signal)
        bearish_count = sum(1 for signal in signals if '🔴' in signal)
        
        if bullish_count >= 2:
            return "🟢 ALCISTA"
        elif bearish_count >= 2:
            return "🔴 BAJISTA"
        else:
            return "🟡 NEUTRAL"
    
    def analyze_all_indices(self):
        """
        Analiza TODOS los índices con sus métricas específicas
        """
        print("🔄 Analizando métricas específicas para cada índice...")
        
        all_indices_data = {}
        
        for symbol, name in self.market_symbols.items():
            metrics = self.get_comprehensive_index_data(symbol)
            if metrics:
                all_indices_data[symbol] = metrics
        
        return all_indices_data
    
    def generate_breadth_summary_from_indices(self, indices_data):
        """
        Genera resumen de amplitud basado en métricas REALES de índices
        """
        try:
            if not indices_data:
                return self._get_empty_summary()
            
            # CONTAR SEÑALES POR CATEGORÍA
            trend_signals = {'bullish': 0, 'bearish': 0, 'neutral': 0}
            momentum_signals = {'bullish': 0, 'bearish': 0, 'neutral': 0}
            overall_signals = {'bullish': 0, 'bearish': 0, 'neutral': 0}
            
            # MÉTRICAS PROMEDIO
            avg_rsi = []
            avg_ma200_distance = []
            avg_52w_distance = []
            strong_performers = []
            weak_performers = []
            
            for symbol, data in indices_data.items():
                # Clasificar señales
                if '🟢' in data['trend_signal']:
                    trend_signals['bullish'] += 1
                elif '🔴' in data['trend_signal']:
                    trend_signals['bearish'] += 1
                else:
                    trend_signals['neutral'] += 1
                    
                if '🟢' in data['momentum_signal']:
                    momentum_signals['bullish'] += 1
                elif '🔴' in data['momentum_signal']:
                    momentum_signals['bearish'] += 1
                else:
                    momentum_signals['neutral'] += 1
                    
                if '🟢' in data['overall_signal']:
                    overall_signals['bullish'] += 1
                elif '🔴' in data['overall_signal']:
                    overall_signals['bearish'] += 1
                else:
                    overall_signals['neutral'] += 1
                
                # Métricas para promedio
                avg_rsi.append(data['rsi_14'])
                avg_ma200_distance.append(data['percent_above_ma200'])
                avg_52w_distance.append(data['distance_from_52w_high'])
                
                # Performers
                if data['price_change_20d'] > 5:
                    strong_performers.append(symbol)
                elif data['price_change_20d'] < -5:
                    weak_performers.append(symbol)
            
            # CALCULAR MÉTRICAS GENERALES
            total_indices = len(indices_data)
            bullish_pct = (overall_signals['bullish'] / total_indices) * 100
            
            avg_rsi_value = np.mean(avg_rsi) if avg_rsi else 50
            avg_ma200_dist = np.mean(avg_ma200_distance) if avg_ma200_distance else 0
            avg_52w_dist = np.mean(avg_52w_distance) if avg_52w_distance else -20
            
            # DETERMINAR SESGO GENERAL
            if bullish_pct >= 75:
                market_bias = "🟢 EXTREMADAMENTE ALCISTA"
                bias_emoji = "🚀"
                confidence = "Muy Alta"
            elif bullish_pct >= 60:
                market_bias = "🟢 FUERTEMENTE ALCISTA" 
                bias_emoji = "📈"
                confidence = "Alta"
            elif bullish_pct >= 40:
                market_bias = "🟢 ALCISTA"
                bias_emoji = "⬆️"
                confidence = "Moderada"
            elif bullish_pct >= 25:
                market_bias = "🟡 NEUTRAL"
                bias_emoji = "⚖️"
                confidence = "Baja"
            elif bullish_pct >= 15:
                market_bias = "🔴 BAJISTA"
                bias_emoji = "⬇️"
                confidence = "Moderada"
            else:
                market_bias = "🔴 EXTREMADAMENTE BAJISTA"
                bias_emoji = "💥"
                confidence = "Muy Alta"
            
            # CALCULAR STRENGTH SCORE
            strength_score = (
                (overall_signals['bullish'] * 3) +
                (trend_signals['bullish'] * 2) +
                (momentum_signals['bullish'] * 1) -
                (overall_signals['bearish'] * 3) -
                (trend_signals['bearish'] * 2) -
                (momentum_signals['bearish'] * 1)
            )
            
            return {
                'market_bias': market_bias,
                'bias_emoji': bias_emoji,
                'confidence': confidence,
                'bullish_signals': overall_signals['bullish'],
                'bearish_signals': overall_signals['bearish'],
                'neutral_signals': overall_signals['neutral'],
                'strength_score': strength_score,
                'total_indicators': total_indices,
                'bullish_percentage': round(bullish_pct, 1),
                # MÉTRICAS ESPECÍFICAS
                'avg_rsi': round(avg_rsi_value, 1),
                'avg_ma200_distance': round(avg_ma200_dist, 1),
                'avg_52w_distance': round(avg_52w_dist, 1),
                'strong_performers': strong_performers,
                'weak_performers': weak_performers,
                'trend_breakdown': trend_signals,
                'momentum_breakdown': momentum_signals
            }
            
        except Exception as e:
            print(f"❌ Error generando resumen: {e}")
            return self._get_empty_summary()
    
    def _get_empty_summary(self):
        """Resumen vacío en caso de error"""
        return {
            'market_bias': "🟡 SIN DATOS",
            'bias_emoji': "❓",
            'confidence': "Nula",
            'bullish_signals': 0,
            'bearish_signals': 0,
            'neutral_signals': 0,
            'strength_score': 0,
            'total_indicators': 0,
            'bullish_percentage': 0,
            'avg_rsi': 50,
            'avg_ma200_distance': 0,
            'avg_52w_distance': -20,
            'strong_performers': [],
            'weak_performers': [],
            'trend_breakdown': {'bullish': 0, 'bearish': 0, 'neutral': 0},
            'momentum_breakdown': {'bullish': 0, 'bearish': 0, 'neutral': 0}
        }
    
    def run_breadth_analysis(self):
        """
        Ejecuta análisis completo basado en métricas REALES por índice
        """
        print("\n📊 INICIANDO ANÁLISIS DE BREADTH POR ÍNDICES ESPECÍFICOS")
        print("=" * 70)
        
        try:
            # 1. Analizar todos los índices individualmente
            print("🔄 Obteniendo métricas específicas para cada índice...")
            indices_data = self.analyze_all_indices()
            
            if not indices_data:
                print("❌ No se pudieron obtener datos de índices")
                return None
            
            # 2. Generar resumen de amplitud basado en datos reales
            print("📈 Generando resumen de amplitud basado en métricas reales...")
            summary = self.generate_breadth_summary_from_indices(indices_data)
            
            # 3. Preparar resultado completo
            result = {
                'indices_data': indices_data,
                'summary': summary,
                'timestamp': datetime.now().isoformat(),
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'analysis_time': datetime.now().strftime('%H:%M:%S'),
                'analysis_type': 'REAL_INDICES_METRICS'  # Identificador del tipo
            }
            
            # 4. Mostrar resumen en consola
            self._print_detailed_summary(summary, indices_data)
            
            print(f"\n✅ ANÁLISIS POR ÍNDICES COMPLETADO - {summary['market_bias']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error en análisis por índices: {e}")
            traceback.print_exc()
            return None
    
    def _print_detailed_summary(self, summary, indices_data):
        """Imprime resumen detallado en consola"""
        print(f"\n📊 RESUMEN DE AMPLITUD BASADO EN MÉTRICAS REALES")
        print("=" * 70)
        print(f"{summary['bias_emoji']} Sesgo General: {summary['market_bias']}")
        print(f"🎯 Confianza: {summary['confidence']}")
        print(f"📈 Índices Alcistas: {summary['bullish_signals']}/{summary['total_indicators']} ({summary['bullish_percentage']:.1f}%)")
        print(f"📉 Índices Bajistas: {summary['bearish_signals']}/{summary['total_indicators']}")
        print(f"💪 Strength Score: {summary['strength_score']}")
        
        print(f"\n📊 MÉTRICAS PROMEDIO:")
        print(f"   RSI Promedio: {summary['avg_rsi']:.1f}")
        print(f"   Distancia MA200: {summary['avg_ma200_distance']:+.1f}%")
        print(f"   Distancia 52W High: {summary['avg_52w_distance']:+.1f}%")
        
        if summary['strong_performers']:
            print(f"\n🚀 MEJORES PERFORMERS (20d): {', '.join(summary['strong_performers'])}")
        
        if summary['weak_performers']:
            print(f"📉 PEORES PERFORMERS (20d): {', '.join(summary['weak_performers'])}")
        
        print(f"\n🔍 DESGLOSE POR ÍNDICE:")
        for symbol, data in indices_data.items():
            print(f"   {data['overall_signal']} {symbol}: ${data['current_price']:.2f} | "
                  f"20d: {data['price_change_20d']:+.1f}% | RSI: {data['rsi_14']:.1f} | "
                  f"MA200: {data['percent_above_ma200']:+.1f}%")
    
    def save_to_csv(self, analysis_result):
        """Guarda análisis por índices en CSV"""
        try:
            if not analysis_result or 'indices_data' not in analysis_result:
                return None
            
            indices_data = analysis_result['indices_data']
            summary = analysis_result['summary']
            
            # Preparar datos principales por índice
            csv_data = []
            
            for symbol, data in indices_data.items():
                row = {
                    'Analysis_Date': analysis_result['analysis_date'],
                    'Analysis_Time': analysis_result['analysis_time'],
                    'Symbol': symbol,
                    'Name': data['name'],
                    'Current_Price': data['current_price'],
                    'Change_1D': data['price_change_1d'],
                    'Change_5D': data['price_change_5d'],
                    'Change_20D': data['price_change_20d'],
                    'RSI_14': data['rsi_14'],
                    'RSI_50': data['rsi_50'],
                    'MA_20': data['ma_20'],
                    'MA_50': data['ma_50'],
                    'MA_200': data['ma_200'],
                    'Pct_Above_MA20': data['percent_above_ma20'],
                    'Pct_Above_MA50': data['percent_above_ma50'],
                    'Pct_Above_MA200': data['percent_above_ma200'],
                    'Distance_52W_High': data['distance_from_52w_high'],
                    'Distance_52W_Low': data['distance_from_52w_low'],
                    'Volume_Ratio_20D': data['volume_ratio_20d'],
                    'Volatility_20D': data['volatility_20d'],
                    'Bollinger_Position': data['bollinger_position'],
                    'MACD_Signal': data['macd_signal'],
                    'Stochastic_K': data['stochastic_k'],
                    'Williams_R': data['williams_r'],
                    'Trend_Signal': data['trend_signal'],
                    'Momentum_Signal': data['momentum_signal'],
                    'Position_Signal': data['position_signal'],
                    'Volume_Signal': data['volume_signal'],
                    'Overall_Signal': data['overall_signal']
                }
                csv_data.append(row)
            
            # Guardar CSV principal
            df = pd.DataFrame(csv_data)
            csv_path = "reports/market_breadth_analysis.csv"
            os.makedirs("reports", exist_ok=True)
            df.to_csv(csv_path, index=False)
            
            # Guardar resumen
            summary_data = {
                'Analysis_Date': analysis_result['analysis_date'],
                'Market_Bias': summary['market_bias'],
                'Confidence': summary['confidence'],
                'Bullish_Percentage': summary['bullish_percentage'],
                'Strength_Score': summary['strength_score'],
                'Avg_RSI': summary['avg_rsi'],
                'Avg_MA200_Distance': summary['avg_ma200_distance'],
                'Strong_Performers': ', '.join(summary['strong_performers']),
                'Weak_Performers': ', '.join(summary['weak_performers'])
            }
            
            summary_path = "reports/market_breadth_signals.csv"
            pd.DataFrame([summary_data]).to_csv(summary_path, index=False)
            
            print(f"✅ CSV por índices guardado: {csv_path}")
            print(f"✅ Resumen guardado: {summary_path}")
            
            return csv_path
            
        except Exception as e:
            print(f"❌ Error guardando CSV: {e}")
            return None


# ==============================================================================
# GENERADOR HTML PARA MÉTRICAS POR ÍNDICE CON GRÁFICOS FINVIZ
# ==============================================================================

class MarketBreadthHTMLGenerator:
    """Generador HTML para análisis por índices específicos con gráficos Finviz"""
    
    def __init__(self, base_url="https://tantancansado.github.io/stock_analyzer_a"):
        self.base_url = base_url
        self.finviz_chart_base = "https://finviz.com/chart.ashx?t={ticker}&ty=c&ta=1&p=d&s=l"
    
    def generate_finviz_chart_url(self, symbol):
        """Genera URL del gráfico de Finviz para un ticker específico"""
        return self.finviz_chart_base.format(ticker=symbol)
    
    def generate_breadth_html(self, analysis_result):
        """Genera HTML para análisis por índices específicos con gráficos"""
        if not analysis_result or 'indices_data' not in analysis_result:
            return None
        
        indices_data = analysis_result['indices_data']
        summary = analysis_result['summary']
        timestamp = analysis_result['analysis_date']
        
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📊 Market Breadth - Análisis por Índices con Gráficos | Dashboard</title>
    <meta name="description" content="Análisis específico de {len(indices_data)} índices con métricas técnicas detalladas y gráficos Finviz">
    <style>
        {self._get_index_specific_css()}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
</head>
<body>
    <div class="glass-container">
        <header class="liquid-header glass-card floating-element">
            <h1>📊 Market Breadth Analysis</h1>
            <p>Análisis específico de {len(indices_data)} índices con métricas técnicas reales y gráficos</p>
            <div class="market-status">
                <div class="pulse-dot"></div>
                <span>{summary['bias_emoji']} {summary['market_bias']} • {summary['bullish_percentage']:.1f}% Alcistas</span>
                <div class="score-badge">Score: {summary['strength_score']}</div>
            </div>
        </header>
        
        <section class="stats-liquid">
            <div class="stat-glass fade-in-up" style="animation-delay: 0.1s">
                <div class="stat-number">{summary['bullish_signals']}</div>
                <div class="stat-label">Índices Alcistas</div>
                <div class="stat-percent">{summary['bullish_percentage']:.1f}%</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.2s">
                <div class="stat-number">{summary['avg_rsi']:.0f}</div>
                <div class="stat-label">RSI Promedio</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.3s">
                <div class="stat-number">{summary['avg_ma200_distance']:+.1f}%</div>
                <div class="stat-label">Distancia MA200</div>
            </div>
            <div class="stat-glass fade-in-up" style="animation-delay: 0.4s">
                <div class="stat-number">{len(indices_data)}</div>
                <div class="stat-label">Índices Analizados</div>
            </div>
        </section>
        
        <main class="indices-analysis glass-card">
            <h2 class="section-title">🎯 Análisis Detallado por Índice con Gráficos</h2>
            <div class="indices-grid">
                {self._generate_detailed_indices_with_charts_html(indices_data)}
            </div>
        </main>
        
        <section class="performers-section glass-card">
            <h2 class="section-title">🏆 Mejores y Peores Performers</h2>
            <div class="performers-grid">
                {self._generate_performers_html(summary, indices_data)}
            </div>
        </section>
        
        <section class="charts-section glass-card">
            <h2 class="section-title">📈 Análisis Visual Comparativo</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3 class="chart-title">Rendimiento 20 Días</h3>
                    <canvas id="performanceChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">RSI de Índices</h3>
                    <canvas id="rsiChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">Distancia de MA200</h3>
                    <canvas id="ma200Chart"></canvas>
                </div>
                <div class="chart-container">
                    <h3 class="chart-title">Volatilidad 20D</h3>
                    <canvas id="volatilityChart"></canvas>
                </div>
            </div>
        </section>
        
        <footer class="footer-liquid">
            <p>📊 Market Breadth Analysis por Índices • Métricas Técnicas Reales • Gráficos Finviz</p>
            <p>
                <a href="{self.base_url}">🏠 Dashboard Principal</a> • 
                <a href="dj_sectorial.html">📊 DJ Sectorial</a> • 
                <a href="insider_trading.html">🏛️ Insider Trading</a>
            </p>
        </footer>
    </div>
    
    <script>
        // Datos para gráficos específicos por índice
        const chartData = {json.dumps(self._prepare_index_chart_data(indices_data))};
        
        // Inicializar gráficos específicos
        {self._generate_index_charts_js()}
        
        // Funcionalidad de modal para gráficos Finviz
        {self._generate_chart_modal_js()}
        
        console.log('📊 Market Breadth por Índices con Gráficos Loaded');
        console.log('🎯 Índices analizados: {len(indices_data)}');
        console.log('📈 Alcistas: {summary["bullish_percentage"]:.1f}%');
        console.log('💪 Strength Score: {summary["strength_score"]}');
    </script>
</body>
</html>"""
        
        return html_content
    
    def _generate_detailed_indices_with_charts_html(self, indices_data):
        """Genera HTML detallado para cada índice CON GRÁFICOS de Finviz"""
        html = ""
        for symbol, data in indices_data.items():
            
            # Determinar clases CSS según señales
            overall_class = "bullish" if "🟢" in data['overall_signal'] else "bearish" if "🔴" in data['overall_signal'] else "neutral"
            
            # URL del gráfico de Finviz
            chart_url = self.generate_finviz_chart_url(symbol)
            
            html += f"""
            <div class="index-detailed-card-with-chart {overall_class}">
                <div class="index-header">
                    <div class="index-info">
                        <span class="index-symbol">{symbol}</span>
                        <span class="index-name">{data['name']}</span>
                    </div>
                    <div class="index-price">
                        <span class="price">${data['current_price']}</span>
                        <span class="change-20d {('positive' if data['price_change_20d'] > 0 else 'negative')}">{data['price_change_20d']:+.1f}%</span>
                    </div>
                </div>
                
                <div class="chart-section">
                    <div class="chart-wrapper">
                        <img src="{chart_url}" 
                             alt="Gráfico {symbol}" 
                             class="finviz-chart"
                             loading="lazy"
                             onclick="openChartModal('{symbol}', '{chart_url}')"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <div class="chart-fallback" style="display: none;">
                            <div class="fallback-content">
                                <span class="fallback-icon">📊</span>
                                <span class="fallback-text">Gráfico no disponible</span>
                                <a href="{chart_url}" target="_blank" class="fallback-link">Ver en Finviz →</a>
                            </div>
                        </div>
                        <div class="chart-overlay">
                            <span class="chart-expand">🔍 Click para ampliar</span>
                        </div>
                    </div>
                </div>
                
                <div class="signals-section">
                    <div class="signal-row">
                        <span class="signal-label">Tendencia:</span>
                        <span class="signal-value">{data['trend_signal']}</span>
                    </div>
                    <div class="signal-row">
                        <span class="signal-label">Momentum:</span>
                        <span class="signal-value">{data['momentum_signal']}</span>
                    </div>
                    <div class="signal-row">
                        <span class="signal-label">Posición:</span>
                        <span class="signal-value">{data['position_signal']}</span>
                    </div>
                    <div class="signal-row overall">
                        <span class="signal-label">General:</span>
                        <span class="signal-value overall">{data['overall_signal']}</span>
                    </div>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="metric-label">RSI 14:</span>
                        <span class="metric-value">{data['rsi_14']:.1f}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">MA200:</span>
                        <span class="metric-value {('positive' if data['percent_above_ma200'] > 0 else 'negative')}">{data['percent_above_ma200']:+.1f}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">52W High:</span>
                        <span class="metric-value">{data['distance_from_52w_high']:+.1f}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Volatilidad:</span>
                        <span class="metric-value">{data['volatility_20d']:.1f}%</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Volumen:</span>
                        <span class="metric-value">{data['volume_ratio_20d']:.1f}x</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Bollinger:</span>
                        <span class="metric-value">{data['bollinger_position']:.0f}%</span>
                    </div>
                </div>
            </div>
            """
        
        return html
    
    def _generate_performers_html(self, summary, indices_data):
        """Genera HTML para mejores y peores performers"""
        
        # Ordenar por performance 20d
        sorted_indices = sorted(indices_data.items(), key=lambda x: x[1]['price_change_20d'], reverse=True)
        
        best_performers = sorted_indices[:3]
        worst_performers = sorted_indices[-3:]
        
        html = f"""
        <div class="performers-column">
            <h3 class="performers-title">🚀 Mejores Performers (20d)</h3>
            <div class="performers-list">
        """
        
        for symbol, data in best_performers:
            html += f"""
                <div class="performer-item best">
                    <span class="performer-symbol">{symbol}</span>
                    <span class="performer-change">{data['price_change_20d']:+.1f}%</span>
                </div>
            """
        
        html += """
            </div>
        </div>
        
        <div class="performers-column">
            <h3 class="performers-title">📉 Peores Performers (20d)</h3>
            <div class="performers-list">
        """
        
        for symbol, data in worst_performers:
            html += f"""
                <div class="performer-item worst">
                    <span class="performer-symbol">{symbol}</span>
                    <span class="performer-change">{data['price_change_20d']:+.1f}%</span>
                </div>
            """
        
        html += """
            </div>
        </div>
        """
        
        return html
    
    def _prepare_index_chart_data(self, indices_data):
        """Prepara datos para gráficos específicos de índices"""
        symbols = list(indices_data.keys())
        
        return {
            'symbols': symbols,
            'performance_20d': [indices_data[s]['price_change_20d'] for s in symbols],
            'rsi_values': [indices_data[s]['rsi_14'] for s in symbols],
            'ma200_distance': [indices_data[s]['percent_above_ma200'] for s in symbols],
            'volatility': [indices_data[s]['volatility_20d'] for s in symbols],
            'prices': [indices_data[s]['current_price'] for s in symbols]
        }
    
    def _generate_index_charts_js(self):
        """Genera JavaScript para gráficos específicos de índices"""
        return """
        // Configuración de gráficos
        const chartConfig = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: 'white' } } },
            scales: {
                x: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                y: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } }
            }
        };
        
        window.addEventListener('load', function() {
            // Performance Chart
            new Chart(document.getElementById('performanceChart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'Rendimiento 20d (%)',
                        data: chartData.performance_20d,
                        backgroundColor: chartData.performance_20d.map(val => 
                            val > 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // RSI Chart
            new Chart(document.getElementById('rsiChart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'RSI 14',
                        data: chartData.rsi_values,
                        backgroundColor: chartData.rsi_values.map(val => 
                            val > 70 ? 'rgba(239, 68, 68, 0.8)' : 
                            val < 30 ? 'rgba(34, 197, 94, 0.8)' : 
                            'rgba(99, 102, 241, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // MA200 Chart
            new Chart(document.getElementById('ma200Chart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'Distancia MA200 (%)',
                        data: chartData.ma200_distance,
                        backgroundColor: chartData.ma200_distance.map(val => 
                            val > 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)'
                        )
                    }]
                },
                options: chartConfig
            });
            
            // Volatility Chart
            new Chart(document.getElementById('volatilityChart'), {
                type: 'bar',
                data: {
                    labels: chartData.symbols,
                    datasets: [{
                        label: 'Volatilidad 20d (%)',
                        data: chartData.volatility,
                        backgroundColor: 'rgba(251, 191, 36, 0.8)'
                    }]
                },
                options: chartConfig
            });
        });
        """
    
    def _generate_chart_modal_js(self):
        """Genera JavaScript para modal de gráficos Finviz"""
        return """
        // Modal para gráficos Finviz
        function openChartModal(symbol, chartUrl) {
            // Crear modal si no existe
            let modal = document.getElementById('chartModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'chartModal';
                modal.className = 'chart-modal';
                modal.innerHTML = `
                    <div class="modal-backdrop" onclick="closeChartModal()"></div>
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3 id="modalTitle">Gráfico</h3>
                            <button class="modal-close" onclick="closeChartModal()">×</button>
                        </div>
                        <div class="modal-body">
                            <img id="modalChart" src="" alt="Gráfico ampliado" />
                            <div class="modal-actions">
                                <a id="finvizLink" href="" target="_blank" class="btn-finviz">
                                    Ver en Finviz →
                                </a>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
            }
            
            // Actualizar contenido del modal
            document.getElementById('modalTitle').textContent = `Gráfico ${symbol}`;
            document.getElementById('modalChart').src = chartUrl;
            document.getElementById('finvizLink').href = chartUrl;
            
            // Mostrar modal
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
        
        function closeChartModal() {
            const modal = document.getElementById('chartModal');
            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        }
        
        // Cerrar modal con ESC
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeChartModal();
            }
        });
        """
    
    def _get_index_specific_css(self):
        """CSS específico para análisis por índices con gráficos"""
        return """
        /* CSS para análisis por índices específicos CON GRÁFICOS */
        :root {
            --glass-primary: rgba(99, 102, 241, 0.9);
            --glass-secondary: rgba(139, 92, 246, 0.8);
            --glass-accent: rgba(59, 130, 246, 1);
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-bg-hover: rgba(255, 255, 255, 0.12);
            --glass-border: rgba(255, 255, 255, 0.15);
            --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.75);
            --success: rgba(72, 187, 120, 0.9);
            --warning: rgba(251, 191, 36, 0.9);
            --danger: rgba(239, 68, 68, 0.9);
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            background: #020617;
            background-image: radial-gradient(ellipse at top, rgba(16, 23, 42, 0.9) 0%, rgba(2, 6, 23, 0.95) 50%, rgba(0, 0, 0, 0.98) 100%);
            background-attachment: fixed;
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
            min-height: 100vh;
        }
        
        .glass-container { max-width: 1600px; margin: 0 auto; padding: 2rem; }
        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            box-shadow: var(--glass-shadow);
            transition: all 0.4s ease;
            position: relative;
            overflow: hidden;
        }
        
        .liquid-header { text-align: center; padding: 3rem 2rem; margin-bottom: 2rem; }
        .liquid-header h1 {
            font-size: clamp(2rem, 5vw, 3.5rem);
            font-weight: 800;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-secondary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        
        .market-status {
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1.5rem;
            border-radius: 50px;
            font-weight: 600;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(72, 187, 120, 0.3);
            background: rgba(72, 187, 120, 0.1);
            color: var(--success);
        }
        
        .score-badge {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.9rem;
            margin-left: 0.5rem;
        }
        
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #48bb78;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.3; transform: scale(1.2); }
        }
        
        .stats-liquid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .stat-glass {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            text-align: center;
            transition: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        
        .stat-glass:hover {
            transform: translateY(-12px) scale(1.05);
            box-shadow: 0 20px 60px rgba(99, 102, 241, 0.3);
        }
        
        .stat-number {
            font-size: 3rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--glass-accent), var(--glass-primary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }
        
        .stat-percent {
            color: var(--glass-accent);
            font-size: 0.9rem;
            font-weight: 600;
            margin-top: 0.25rem;
        }
        
        .indices-analysis { padding: 2.5rem; margin-bottom: 2rem; }
        
        .section-title {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 2rem;
            text-align: center;
            position: relative;
        }
        
        .section-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 60px;
            height: 3px;
            background: linear-gradient(90deg, var(--glass-primary), var(--glass-secondary));
            border-radius: 2px;
        }
        
        .indices-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 2rem;
        }
        
        /* ESTILOS ESPECÍFICOS PARA CARDS CON GRÁFICOS */
        .index-detailed-card-with-chart {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            transition: all 0.4s ease;
            overflow: hidden;
        }
        
        .index-detailed-card-with-chart:hover {
            transform: translateY(-8px);
            background: var(--glass-bg-hover);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }
        
        .index-detailed-card-with-chart.bullish { border-left: 4px solid var(--success); }
        .index-detailed-card-with-chart.bearish { border-left: 4px solid var(--danger); }
        .index-detailed-card-with-chart.neutral { border-left: 4px solid var(--warning); }
        
        .index-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--glass-border);
        }
        
        .index-symbol {
            font-size: 1.4rem;
            font-weight: 800;
            color: var(--glass-primary);
        }
        
        .index-name {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }
        
        .price {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .change-20d {
            font-size: 1.1rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }
        
        .positive { color: var(--success); }
        .negative { color: var(--danger); }
        
        /* ESTILOS PARA GRÁFICOS FINVIZ */
        .chart-section {
            margin-bottom: 1.5rem;
            position: relative;
        }
        
        .chart-wrapper {
            position: relative;
            border-radius: 12px;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.3);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .chart-wrapper:hover {
            transform: scale(1.02);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.3);
        }
        
        .finviz-chart {
            width: 100%;
            height: auto;
            max-height: 200px;
            object-fit: cover;
            display: block;
            transition: all 0.3s ease;
        }
        
        .chart-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: all 0.3s ease;
        }
        
        .chart-wrapper:hover .chart-overlay {
            opacity: 1;
        }
        
        .chart-expand {
            color: white;
            font-weight: 600;
            font-size: 0.9rem;
            background: rgba(99, 102, 241, 0.8);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .chart-fallback {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 200px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 2px dashed var(--glass-border);
        }
        
        .fallback-content {
            text-align: center;
            color: var(--text-secondary);
        }
        
        .fallback-icon {
            font-size: 2rem;
            display: block;
            margin-bottom: 0.5rem;
        }
        
        .fallback-text {
            display: block;
            margin-bottom: 0.75rem;
            font-size: 0.9rem;
        }
        
        .fallback-link {
            color: var(--glass-accent);
            text-decoration: none;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 0.25rem 0.5rem;
            border: 1px solid var(--glass-accent);
            border-radius: 6px;
            transition: all 0.3s ease;
        }
        
        .fallback-link:hover {
            background: var(--glass-accent);
            color: white;
        }
        
        /* MODAL PARA GRÁFICOS */
        .chart-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }
        
        .modal-backdrop {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }
        
        .modal-content {
            position: relative;
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 0;
            max-width: 90vw;
            max-height: 90vh;
            overflow: hidden;
            box-shadow: var(--glass-shadow);
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem;
            border-bottom: 1px solid var(--glass-border);
            background: rgba(255, 255, 255, 0.05);
        }
        
        .modal-header h3 {
            color: var(--text-primary);
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .modal-close {
            background: none;
            border: none;
            color: var(--text-primary);
            font-size: 2rem;
            cursor: pointer;
            padding: 0.25rem;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        
        .modal-close:hover {
            background: rgba(255, 255, 255, 0.1);
            color: var(--danger);
        }
        
        .modal-body {
            padding: 1.5rem;
            text-align: center;
        }
        
        .modal-body img {
            max-width: 100%;
            max-height: 70vh;
            border-radius: 12px;
            margin-bottom: 1rem;
        }
        
        .modal-actions {
            margin-top: 1rem;
        }
        
        .btn-finviz {
            display: inline-block;
            color: white;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-secondary));
            text-decoration: none;
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
            border: 1px solid var(--glass-border);
        }
        
        .btn-finviz:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        }
        
        .signals-section { margin-bottom: 1.5rem; }
        
        .signal-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            padding: 0.5rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 8px;
        }
        
        .signal-row.overall {
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            font-weight: 600;
        }
        
        .signal-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        
        .signal-value {
            font-size: 0.9rem;
            font-weight: 500;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }
        
        .metric-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 6px;
            font-size: 0.85rem;
        }
        
        .metric-label { color: var(--text-secondary); }
        .metric-value { font-weight: 600; }
        
        .performers-section { padding: 2.5rem; margin-bottom: 2rem; }
        
        .performers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }
        
        .performers-column {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--glass-border);
        }
        
        .performers-title {
            color: var(--glass-primary);
            margin-bottom: 1rem;
            text-align: center;
        }
        
        .performer-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            margin-bottom: 0.5rem;
            border-radius: 12px;
            font-weight: 600;
        }
        
        .performer-item.best {
            background: rgba(72, 187, 120, 0.1);
            border: 1px solid rgba(72, 187, 120, 0.3);
        }
        
        .performer-item.worst {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .charts-section { padding: 2.5rem; margin-bottom: 2rem; }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
        }
        
        .chart-container {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--glass-border);
        }
        
        .chart-title {
            color: var(--glass-primary);
            font-weight: 600;
            margin-bottom: 1rem;
            text-align: center;
        }
        
        canvas {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            height: 250px !important;
        }
        
        .floating-element { animation: float 6s ease-in-out infinite; }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        .fade-in-up {
            opacity: 0;
            transform: translateY(30px);
            animation: fadeInUp 0.8s ease-out forwards;
        }
        
        @keyframes fadeInUp {
            to { opacity: 1; transform: translateY(0); }
        }
        
        .footer-liquid {
            text-align: center;
            margin-top: 4rem;
            padding: 2rem 0;
            border-top: 1px solid var(--glass-border);
            color: var(--text-secondary);
        }
        
        .footer-liquid a {
            color: var(--glass-accent);
            text-decoration: none;
            transition: all 0.3s ease;
        }
        
        @media (max-width: 768px) {
            .glass-container { padding: 1rem; }
            .indices-grid { grid-template-columns: 1fr; }
            .charts-grid { grid-template-columns: 1fr; }
            .performers-grid { grid-template-columns: 1fr; }
            .metrics-grid { grid-template-columns: 1fr; }
            
            .modal-content {
                max-width: 95vw;
                max-height: 95vh;
            }
            
            .modal-body img {
                max-height: 60vh;
            }
        }
        """


# ==============================================================================
# INTEGRACIÓN CON EL SISTEMA PRINCIPAL
# ==============================================================================

def add_market_breadth_to_system():
    """
    Función para añadir Market Breadth POR ÍNDICES al sistema principal
    """
    
    def run_market_breadth_analysis(self):
        """Ejecuta análisis de amplitud POR ÍNDICES ESPECÍFICOS"""
        print("\n📊 EJECUTANDO ANÁLISIS DE BREADTH POR ÍNDICES CON GRÁFICOS")
        print("=" * 60)
        
        try:
            analyzer = MarketBreadthAnalyzer()
            analysis_result = analyzer.run_breadth_analysis()
            
            if analysis_result:
                # Guardar CSV
                csv_path = analyzer.save_to_csv(analysis_result)
                
                # Generar HTML con gráficos
                html_generator = MarketBreadthHTMLGenerator(self.github_uploader.base_url)
                html_content = html_generator.generate_breadth_html(analysis_result)
                
                if html_content:
                    html_path = "reports/market_breadth_report.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print(f"✅ HTML con gráficos generado: {html_path}")
                    
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
            print(f"❌ Error en análisis por índices: {e}")
            traceback.print_exc()
            return None
    
    def upload_breadth_to_github_pages(self, breadth_results):
        """Sube análisis por índices a GitHub Pages"""
        try:
            if not breadth_results:
                return None
            
            analysis_result = breadth_results['analysis_result']
            summary = analysis_result['summary']
            timestamp = analysis_result['analysis_date']
            
            title = f"📊 Market Breadth por Índices con Gráficos - {summary['market_bias']} - {timestamp}"
            description = f"Análisis de {summary['total_indicators']} índices: {summary['bullish_percentage']:.1f}% alcistas | Score: {summary['strength_score']} | Gráficos Finviz"
            
            result = self.github_uploader.upload_report(
                breadth_results['html_path'],
                breadth_results['csv_path'],
                title,
                description
            )
            
            if result:
                print(f"✅ Market Breadth con gráficos subido: {result['github_url']}")
                return result
            else:
                print("❌ Error subiendo Market Breadth")
                return None
                
        except Exception as e:
            print(f"❌ Error subiendo Market Breadth: {e}")
            return None
    
    return {
        'run_market_breadth_analysis': run_market_breadth_analysis,
        'upload_breadth_to_github_pages': upload_breadth_to_github_pages
    }

if __name__ == "__main__":
    # Test específico por índices CON GRÁFICOS
    print("🧪 TESTING MARKET BREADTH POR ÍNDICES CON GRÁFICOS FINVIZ")
    print("=" * 60)
    
    analyzer = MarketBreadthAnalyzer()
    result = analyzer.run_breadth_analysis()
    
    if result:
        print("\n✅ Test por índices completado exitosamente")
        
        # Test HTML generator con gráficos
        html_gen = MarketBreadthHTMLGenerator()
        html = html_gen.generate_breadth_html(result)
        
        if html:
            with open("test_market_breadth_with_charts.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("✅ HTML con gráficos generado: test_market_breadth_with_charts.html")
        
        # Test CSV
        csv_path = analyzer.save_to_csv(result)
        if csv_path:
            print(f"✅ CSV por índices generado: {csv_path}")
            
        print("\n🎯 NUEVAS CARACTERÍSTICAS:")
        print("   ✓ Gráficos Finviz integrados en cada caja")
        print("   ✓ Modal para ampliar gráficos")
        print("   ✓ Fallback si gráfico no carga")
        print("   ✓ Links directos a Finviz")
        print("   ✓ Hover effects en gráficos")
        print("   ✓ Responsive design para móviles")
        print("   ✓ Métricas REALES + visualización")
        
    else:
        print("❌ Test fallido")
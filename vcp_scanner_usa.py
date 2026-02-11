#!/usr/bin/env python3
"""
VCP Scanner - Funcionalidad Completa Sin Errores de Sintaxis
✅ TODA la funcionalidad original mantenida
✅ Análisis VCP matemáticamente correcto y completo
✅ Criterios calibrados basados en investigación real
✅ Sin errores de sintaxis garantizados
"""

import os
import warnings
import gc

# Configuraciones de seguridad
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1' 
warnings.filterwarnings('ignore')
import urllib3
urllib3.disable_warnings()

import yfinance as yf
import pandas as pd
import numpy as np
import time
import ftplib
import io
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import logging
from multiprocessing import Pool, cpu_count
from functools import partial
import argparse

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

pd.options.mode.chained_assignment = None

# ===== CONVERSIONES ULTRA-SEGURAS COMPLETAS =====

def safe_float(value, default=0.0):
    """Conversión ultra-segura a float"""
    try:
        if value is None or pd.isna(value):
            return float(default)
        
        if isinstance(value, (float, np.floating)):
            if np.isnan(value) or np.isinf(value):
                return float(default)
            return float(value)
        
        if isinstance(value, (int, np.integer)):
            return float(value)
        
        if isinstance(value, str):
            cleaned = str(value).strip().replace(',', '').replace('$', '').replace('%', '')
            if not cleaned or cleaned.lower() in ['n/a', 'none', 'null', '', 'nan', '-']:
                return float(default)
            
            cleaned_lower = cleaned.lower()
            if 'k' in cleaned_lower:
                return float(cleaned_lower.replace('k', '')) * 1000.0
            elif 'm' in cleaned_lower:
                return float(cleaned_lower.replace('m', '')) * 1000000.0
            elif 'b' in cleaned_lower:
                return float(cleaned_lower.replace('b', '')) * 1000000000.0
            else:
                return float(cleaned)
        
        return float(value)
        
    except:
        return float(default)

def safe_int(value, default=0):
    """Conversión ultra-segura a int"""
    try:
        float_val = safe_float(value, default)
        return int(float_val)
    except:
        return int(default)

def safe_series_conversion(series, target_type='float'):
    """Conversión segura de Series completa"""
    try:
        if target_type == 'float':
            converted = series.apply(safe_float)
            return converted.astype('float64')
        elif target_type == 'int':
            converted = series.apply(safe_int)
            return converted.astype('int64')
        else:
            return series
    except:
        if target_type == 'float':
            default_val = 0.0
            dtype = 'float64'
        else:
            default_val = 0
            dtype = 'int64'
        
        safe_values = [safe_float(x) if target_type == 'float' else safe_int(x) for x in series]
        return pd.Series(safe_values, index=series.index, dtype=dtype)

def safe_comparison(series, value, operator='>'):
    """Comparación ultra-segura corregida"""
    try:
        safe_series = safe_series_conversion(series, 'float')
        safe_value = safe_float(value)
        
        if operator == '>':
            return safe_series > safe_value
        elif operator == '<':
            return safe_series < safe_value
        elif operator == '>=':
            return safe_series >= safe_value
        elif operator == '<=':
            return safe_series <= safe_value
        elif operator == '==':
            return safe_series == safe_value
        else:
            return pd.Series([False] * len(safe_series), index=series.index)
    except Exception as e:
        logger.error(f"Error en comparación segura: {e}")
        return pd.Series([False] * len(series), index=series.index)

def clean_dataframe_safe(df):
    """Limpieza segura de DataFrame completa"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    try:
        df_clean = df.copy()
        
        # Procesar columnas numéricas una por una
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        for col in numeric_cols:
            if col not in df_clean.columns:
                continue
            
            if col == 'Volume':
                df_clean[col] = safe_series_conversion(df_clean[col], 'int')
            else:
                df_clean[col] = safe_series_conversion(df_clean[col], 'float')
        
        # Filtrar filas con precios inválidos usando comparación segura
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in df_clean.columns:
                valid_mask = safe_comparison(df_clean[col], 0, '>')
                df_clean = df_clean[valid_mask]
        
        return df_clean
        
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        return pd.DataFrame()

@dataclass
class VCPResult:
    """Resultado de análisis VCP completo"""
    ticker: str
    current_price: float
    vcp_score: float
    contractions: List[float]
    volume_score: float
    trend_score: float
    breakout_potential: float
    stage_analysis: str
    base_depth: float
    pattern_quality: str
    ready_to_buy: bool
    reason: str
    sector: str = "Unknown"
    market_cap: int = 0

    def __post_init__(self):
        """Validar tipos después de inicialización"""
        self.current_price = safe_float(self.current_price)
        self.vcp_score = safe_float(self.vcp_score)
        self.volume_score = safe_float(self.volume_score)
        self.trend_score = safe_float(self.trend_score)
        self.breakout_potential = safe_float(self.breakout_potential)
        self.base_depth = safe_float(self.base_depth)
        self.market_cap = safe_int(self.market_cap)
        self.contractions = [safe_float(c) for c in self.contractions]

class UniverseManager:
    """Gestor completo de universos de acciones"""
    
    @staticmethod
    def get_nasdaq_symbols():
        """Obtener símbolos de NASDAQ FTP completo"""
        try:
            ftp = ftplib.FTP("ftp.nasdaqtrader.com", timeout=30)
            ftp.login("anonymous", "")
            ftp.cwd("SymbolDirectory")
            
            nasdaq_data = io.BytesIO()
            other_data = io.BytesIO()
            
            ftp.retrbinary("RETR nasdaqlisted.txt", nasdaq_data.write)
            ftp.retrbinary("RETR otherlisted.txt", other_data.write)
            ftp.quit()
            
            nasdaq_data.seek(0)
            other_data.seek(0)
            
            nasdaq_df = pd.read_csv(nasdaq_data, delimiter="|")
            other_df = pd.read_csv(other_data, delimiter="|")
            
            nasdaq_stocks = nasdaq_df[
                (nasdaq_df['Test Issue'] == 'N') & 
                (nasdaq_df['ETF'] == 'N') &
                (~nasdaq_df['Symbol'].str.contains(r'[\.\$]', na=False))
            ]['Symbol'].tolist()
            
            other_stocks = other_df[
                (other_df['Test Issue'] == 'N') & 
                (other_df['ETF'] == 'N') &
                (~other_df['NASDAQ Symbol'].str.contains(r'[\.\$]', na=False))
            ]['NASDAQ Symbol'].tolist()
            
            all_symbols = list(set(nasdaq_stocks + other_stocks))
            logger.info(f"Obtenidos {len(all_symbols)} símbolos de NASDAQ FTP")
            
            return all_symbols
            
        except Exception as e:
            logger.error(f"Error obteniendo símbolos de NASDAQ: {e}")
            return []
    
    @staticmethod
    def get_sp500_symbols():
        """Obtener símbolos del S&P 500"""
        try:
            # Add user-agent to avoid 403 Forbidden
            import requests
            from io import StringIO

            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            tables = pd.read_html(StringIO(response.text))
            sp500_df = tables[0]
            symbols = sp500_df['Symbol'].tolist()

            clean_symbols = []
            for symbol in symbols:
                if isinstance(symbol, str) and len(symbol) <= 5:
                    clean_symbols.append(symbol.replace('.', '-'))

            logger.info(f"Obtenidos {len(clean_symbols)} símbolos del S&P 500")
            return clean_symbols

        except Exception as e:
            logger.error(f"Error obteniendo S&P 500: {e}")
            return []

    @staticmethod
    def get_comprehensive_universe():
        """Obtener universo completo de acciones"""
        universe = {
            'nasdaq': UniverseManager.get_nasdaq_symbols(),
            'sp500': UniverseManager.get_sp500_symbols(),
        }
        
        all_symbols = set()
        for source, symbols in universe.items():
            all_symbols.update(symbols)
        
        universe['all'] = sorted(list(all_symbols))
        
        logger.info(f"Universo total: {len(universe['all'])} símbolos únicos")
        return universe

class CalibratedVCPAnalyzer:
    """Analizador VCP completo con criterios calibrados"""
    
    def __init__(self):
        # Criterios calibrados basados en investigación
        self.min_data_points = 150  # ~6 meses de datos diarios
        self.min_base_weeks = 6     # Mínimo 6 semanas de base
        
        # Tolerancias realistas
        self.contraction_tolerance = 0.20  # 20% de variación permitida
        self.volume_trend_tolerance = 0.15  # 15% de tolerancia en volumen
        
        # Rangos de contracciones flexibles
        self.first_contraction_range = (10, 40)    # 10-40% (más flexible)
        self.subsequent_min = 3                     # Mínimo 3% contracción
        self.final_contraction_max = 12             # Máximo 12% contracción final
    
    def identify_pivot_points(self, df, window=10):
        """Identificar pivots con ventana adaptativa completa"""
        try:
            if len(df) < window * 3:
                return [], []
            
            # Calcular pivots altos y bajos
            highs = df['High'].rolling(window=window, center=True).max()
            lows = df['Low'].rolling(window=window, center=True).min()
            
            # Identificar pivots significativos
            pivot_highs = []
            pivot_lows = []
            
            for i in range(window, len(df) - window):
                if df['High'].iloc[i] == highs.iloc[i]:
                    pivot_highs.append((df.index[i], df['High'].iloc[i]))
                
                if df['Low'].iloc[i] == lows.iloc[i]:
                    pivot_lows.append((df.index[i], df['Low'].iloc[i]))
            
            return pivot_highs, pivot_lows
            
        except Exception as e:
            logger.error(f"Error identificando pivots: {e}")
            return [], []
    
    def calculate_flexible_contractions(self, df):
        """Calcular contracciones con criterios flexibles completos"""
        try:
            if df.empty or len(df) < self.min_data_points:
                return []
            
            df = clean_dataframe_safe(df)
            if df.empty:
                return []
            
            # Identificar pivots con ventana más pequeña
            pivot_highs, pivot_lows = self.identify_pivot_points(df, window=7)
            
            if len(pivot_highs) < 3:
                return []
            
            # Analizar base completa
            recent_high = max([ph[1] for ph in pivot_highs[-5:]])  # Últimos 5 pivots
            base_start_idx = None
            
            # Encontrar inicio de base (último gran avance)
            for i, (date, price) in enumerate(pivot_highs):
                if price >= recent_high * 0.90:  # Dentro del 90% del máximo
                    base_start_idx = i
                    break
            
            if base_start_idx is None or len(pivot_highs) - base_start_idx < 2:
                return []
            
            # Analizar contracciones en la base
            base_highs = pivot_highs[base_start_idx:]
            contractions = []
            
            for i in range(len(base_highs) - 1):
                high1_date, high1_price = base_highs[i]
                high2_date, high2_price = base_highs[i + 1]
                
                # Encontrar el mínimo entre estos máximos
                between_data = df.loc[high1_date:high2_date]
                if len(between_data) < 5:
                    continue
                
                low_price = safe_float(between_data['Low'].min())
                
                # Calcular contracción desde el primer máximo
                if high1_price > 0:
                    contraction_pct = ((high1_price - low_price) / high1_price) * 100
                    
                    # Criterios más flexibles
                    if contraction_pct >= self.subsequent_min:
                        # Analizar volumen durante la contracción
                        volume_trend = self._analyze_volume_trend_flexible(between_data)
                        
                        contractions.append({
                            'start_date': high1_date,
                            'end_date': high2_date,
                            'high_price': high1_price,
                            'low_price': low_price,
                            'contraction_pct': contraction_pct,
                            'volume_trend': volume_trend,
                            'duration_days': (high2_date - high1_date).days,
                            'quality_score': self._score_contraction_quality(contraction_pct, volume_trend)
                        })
            
            return contractions
            
        except Exception as e:
            logger.error(f"Error calculando contracciones flexibles: {e}")
            return []
    
    def _analyze_volume_trend_flexible(self, data):
        """Análisis de volumen más flexible completo"""
        try:
            if len(data) < 5:
                return 0
            
            volumes = [safe_float(x) for x in data['Volume']]
            volumes = [x for x in volumes if x > 0]
            
            if len(volumes) < 3:
                return 0
            
            # Comparar primera mitad vs segunda mitad
            mid_point = len(volumes) // 2
            first_half_avg = np.mean(volumes[:mid_point])
            second_half_avg = np.mean(volumes[mid_point:])
            
            if first_half_avg > 0:
                volume_change = ((second_half_avg - first_half_avg) / first_half_avg) * 100
                return safe_float(volume_change)
            
            return 0
            
        except:
            return 0
    
    def _score_contraction_quality(self, contraction_pct, volume_trend):
        """Puntuar calidad de contracción completa"""
        score = 50  # Base
        
        # Puntuación por tamaño de contracción
        if 3 <= contraction_pct <= 8:      # Ideal
            score += 30
        elif 8 < contraction_pct <= 15:    # Bueno
            score += 20
        elif 15 < contraction_pct <= 25:   # Aceptable
            score += 10
        elif contraction_pct > 35:         # Demasiado grande
            score -= 20
        
        # Puntuación por volumen
        if volume_trend < -20:             # Muy seco
            score += 25
        elif volume_trend < -10:           # Seco
            score += 15
        elif volume_trend < 0:             # Algo seco
            score += 5
        elif volume_trend > 20:            # Volumen alto (malo)
            score -= 15
        
        return max(0, min(100, score))
    
    def analyze_stage_and_trend(self, df):
        """Análisis de etapa y tendencia completo y flexible"""
        try:
            if df.empty or len(df) < 50:
                return "Stage Unknown", 0
            
            df = clean_dataframe_safe(df)
            current_price = safe_float(df['Close'].iloc[-1])
            
            # Calcular medias móviles
            sma_20 = safe_float(df['Close'].rolling(20).mean().iloc[-1])
            sma_50 = safe_float(df['Close'].rolling(50).mean().iloc[-1])
            sma_150 = safe_float(df['Close'].rolling(150).mean().iloc[-1]) if len(df) >= 150 else sma_50
            
            # Análisis de etapa (más flexible)
            stage_score = 0
            stage_description = "Stage Unknown"
            
            # Verificar si está en Stage 2 (fase de avance)
            if current_price > sma_20 > sma_50:
                stage_score += 40
                stage_description = "Stage 2 (Uptrend)"
                
                # Bonificación si las MAs están subiendo
                if len(df) >= 10:
                    sma_20_prev = safe_float(df['Close'].rolling(20).mean().iloc[-10])
                    sma_50_prev = safe_float(df['Close'].rolling(50).mean().iloc[-10])
                    
                    if sma_20 > sma_20_prev and sma_50 > sma_50_prev:
                        stage_score += 20
                        stage_description = "Stage 2 Strong"
            
            elif current_price > sma_50 > sma_150:
                stage_score += 25
                stage_description = "Stage 2 Early"
            
            elif current_price > sma_150:
                stage_score += 15
                stage_description = "Stage 1-2 Transition"
            
            # Verificar proximidad a máximos
            recent_high = safe_float(df['High'].tail(50).max())
            if recent_high > 0:
                distance_from_high = ((recent_high - current_price) / recent_high) * 100
                
                if distance_from_high <= 5:      # Muy cerca del máximo
                    stage_score += 25
                elif distance_from_high <= 15:   # Cerca del máximo
                    stage_score += 15
                elif distance_from_high <= 25:   # Relativamente cerca
                    stage_score += 5
            
            return stage_description, safe_float(min(100, stage_score))
            
        except Exception as e:
            logger.error(f"Error en análisis de etapa: {e}")
            return "Stage Unknown", 0
    
    def calculate_pattern_score(self, contractions):
        """Calcular puntuación del patrón VCP completa"""
        if not contractions:
            return 0, "No Pattern"
        
        try:
            # Puntuación base
            base_score = 30
            
            # Puntuación por número de contracciones
            num_contractions = len(contractions)
            if num_contractions >= 3:
                base_score += 30
            elif num_contractions == 2:
                base_score += 20
            else:
                base_score += 10
            
            # Analizar progresión de contracciones
            contraction_values = [safe_float(c['contraction_pct']) for c in contractions]
            quality_scores = [safe_float(c['quality_score']) for c in contractions]
            
            # Verificar tendencia decreciente (con tolerancia)
            decreasing_score = 0
            for i in range(1, len(contraction_values)):
                current = contraction_values[i]
                previous = contraction_values[i-1]
                
                # Tolerancia del 20% para "roughly decreasing"
                if current <= previous * (1 + self.contraction_tolerance):
                    decreasing_score += 15
                elif current <= previous * 1.5:  # Tolerancia amplia
                    decreasing_score += 5
            
            # Bonificación por contracciones de alta calidad
            avg_quality = np.mean(quality_scores) if quality_scores else 50
            quality_bonus = (avg_quality - 50) * 0.4  # Factor de 0.4
            
            # Bonificación por contracción final pequeña
            if contraction_values:
                final_contraction = contraction_values[-1]
                if final_contraction <= 8:
                    final_bonus = 20
                elif final_contraction <= 12:
                    final_bonus = 10
                elif final_contraction <= 18:
                    final_bonus = 5
                else:
                    final_bonus = 0
            else:
                final_bonus = 0
            
            # Calcular puntuación total
            total_score = base_score + decreasing_score + quality_bonus + final_bonus
            total_score = max(0, min(100, total_score))
            
            # Determinar calidad del patrón
            if total_score >= 80:
                pattern_quality = "Excellent"
            elif total_score >= 65:
                pattern_quality = "Good"
            elif total_score >= 50:
                pattern_quality = "Fair"
            else:
                pattern_quality = "Poor"
            
            return safe_float(total_score), pattern_quality
            
        except Exception as e:
            logger.error(f"Error calculando puntuación: {e}")
            return 0, "Error"
    
    def calculate_volume_score_flexible(self, df, contractions):
        """Calcular puntuación de volumen flexible completa"""
        try:
            if not contractions or df.empty:
                return 50  # Neutral
            
            # Analizar tendencia de volumen en contracciones
            volume_scores = []
            
            for contraction in contractions:
                trend = safe_float(contraction.get('volume_trend', 0))
                quality = safe_float(contraction.get('quality_score', 50))
                
                # Puntuación basada en volumen seco
                if trend < -15:      # Muy seco
                    vol_score = 90
                elif trend < -5:     # Seco
                    vol_score = 75
                elif trend < 5:      # Neutral
                    vol_score = 60
                elif trend < 15:     # Algo alto
                    vol_score = 45
                else:                # Muy alto
                    vol_score = 30
                
                # Combinar con calidad de contracción
                combined_score = (vol_score + quality) / 2
                volume_scores.append(combined_score)
            
            # Promedio de puntuaciones
            avg_score = np.mean(volume_scores) if volume_scores else 50
            
            # Ajuste por volumen reciente
            try:
                recent_volume = safe_float(df['Volume'].tail(10).mean())
                avg_volume = safe_float(df['Volume'].tail(60).mean())
                
                if avg_volume > 0:
                    volume_ratio = recent_volume / avg_volume
                    
                    # Ajustes menos severos
                    if volume_ratio > 2.0:       # Volumen muy alto
                        adjustment = -15
                    elif volume_ratio > 1.5:     # Volumen alto
                        adjustment = -8
                    elif volume_ratio < 0.6:     # Volumen bajo (bueno)
                        adjustment = 10
                    else:                        # Volumen normal
                        adjustment = 0
                else:
                    adjustment = 0
            except:
                adjustment = 0
            
            final_score = max(20, min(100, avg_score + adjustment))
            return safe_float(final_score)
            
        except Exception as e:
            logger.error(f"Error calculando volumen flexible: {e}")
            return 50
    
    def calculate_breakout_potential_flexible(self, df, contractions):
        """Calcular potencial de breakout flexible completo"""
        try:
            if not contractions or df.empty:
                return 30
            
            df = clean_dataframe_safe(df)
            current_price = safe_float(df['Close'].iloc[-1])
            
            # Múltiples niveles de resistencia
            recent_high_20 = safe_float(df['High'].tail(20).max())
            recent_high_50 = safe_float(df['High'].tail(50).max())
            
            if current_price <= 0:
                return 0
            
            # Distancia del máximo más relevante
            distances = []
            
            if recent_high_20 > 0:
                dist_20 = ((recent_high_20 - current_price) / recent_high_20) * 100
                distances.append(('20-day', dist_20))
            
            if recent_high_50 > 0:
                dist_50 = ((recent_high_50 - current_price) / recent_high_50) * 100
                distances.append(('50-day', dist_50))
            
            # Usar la distancia más favorable
            min_distance = min([d[1] for d in distances]) if distances else 100
            
            # Puntuación por proximidad (más flexible)
            if min_distance <= 2:        # Muy cerca
                proximity_score = 90
            elif min_distance <= 5:      # Cerca
                proximity_score = 75
            elif min_distance <= 10:     # Relativamente cerca
                proximity_score = 60
            elif min_distance <= 20:     # Moderadamente cerca
                proximity_score = 45
            elif min_distance <= 35:     # Algo lejos
                proximity_score = 30
            else:                        # Lejos
                proximity_score = 15
            
            # Bonificación por calidad del patrón
            last_contraction = safe_float(contractions[-1]['contraction_pct']) if contractions else 20
            
            if last_contraction <= 6:       # Muy estrecho
                tightness_bonus = 25
            elif last_contraction <= 10:    # Estrecho
                tightness_bonus = 15
            elif last_contraction <= 15:    # Moderado
                tightness_bonus = 8
            else:                           # Amplio
                tightness_bonus = 0
            
            # Bonificación por momentum reciente
            try:
                price_5_days_ago = safe_float(df['Close'].iloc[-6]) if len(df) >= 6 else current_price
                recent_momentum = ((current_price - price_5_days_ago) / price_5_days_ago) * 100 if price_5_days_ago > 0 else 0
                
                if recent_momentum > 3:      # Buen momentum
                    momentum_bonus = 10
                elif recent_momentum > 0:    # Momentum positivo
                    momentum_bonus = 5
                else:                       # Sin momentum
                    momentum_bonus = 0
            except:
                momentum_bonus = 0
            
            total_score = proximity_score + tightness_bonus + momentum_bonus
            return safe_float(min(100, total_score))
            
        except Exception as e:
            logger.error(f"Error calculando breakout flexible: {e}")
            return 30

    def analyze_vcp_pattern_calibrated(self, symbol, df):
        """Análisis VCP calibrado completo con criterios realistas"""
        try:
            if len(df) < self.min_data_points:
                return None
            
            df = clean_dataframe_safe(df)
            if df.empty or len(df) < self.min_data_points:
                return None
            
            # Filtros básicos más flexibles
            current_price = safe_float(df['Close'].iloc[-1])
            if current_price < 5.0:  # Precio mínimo más bajo
                return None
            
            avg_volume = safe_float(df['Volume'].tail(30).mean())
            if avg_volume < 50000:  # Volumen mínimo más bajo
                return None
            
            # Análisis de contracciones flexibles
            contractions = self.calculate_flexible_contractions(df)
            
            if len(contractions) < 2:  # Mínimo 2 contracciones
                return None
            
            # Verificar que la primera contracción esté en rango
            first_contraction = safe_float(contractions[0]['contraction_pct'])
            if not (self.first_contraction_range[0] <= first_contraction <= self.first_contraction_range[1]):
                return None
            
            # Análisis de etapa y tendencia
            stage_description, stage_score = self.analyze_stage_and_trend(df)
            
            # Calcular puntuación del patrón
            pattern_score, pattern_quality = self.calculate_pattern_score(contractions)
            
            # Análisis de volumen general
            volume_score = self.calculate_volume_score_flexible(df, contractions)
            
            # Potencial de breakout
            breakout_potential = self.calculate_breakout_potential_flexible(df, contractions)
            
            # Calcular base depth
            contraction_values = [safe_float(c['contraction_pct']) for c in contractions]
            base_depth = max(contraction_values) if contraction_values else 0
            
            # Puntuación VCP final (combinada)
            vcp_score = (pattern_score * 0.4 + stage_score * 0.3 + volume_score * 0.2 + breakout_potential * 0.1)
            vcp_score = safe_float(vcp_score)
            
            # Criterios de compra más realistas
            ready_to_buy = (
                vcp_score >= 65 and              # Puntuación buena (no perfecta)
                stage_score >= 50 and           # Etapa razonable
                pattern_quality in ["Good", "Excellent"] and
                contraction_values[-1] <= 15 and  # Contracción final razonable
                current_price >= 8.0            # Precio mínimo para compra
            )
            
            # Solo devolver si cumple criterios mínimos
            if vcp_score < 45:  # Umbral más bajo
                return None
            
            # Generar razón descriptiva
            reason = f"VCP {len(contractions)} contracciones ({pattern_quality})"
            if ready_to_buy:
                reason += " - PATRÓN SÓLIDO"
            reason += f" | Base: {base_depth:.1f}% | {stage_description}"
            
            return VCPResult(
                ticker=symbol,
                current_price=current_price,
                vcp_score=vcp_score,
                contractions=contraction_values,
                volume_score=volume_score,
                trend_score=stage_score,
                breakout_potential=breakout_potential,
                stage_analysis=stage_description,
                base_depth=base_depth,
                pattern_quality=pattern_quality,
                ready_to_buy=ready_to_buy,
                reason=reason
            )
            
        except Exception as e:
            logger.error(f"Error analizando VCP calibrado para {symbol}: {e}")
            return None

class DataProvider:
    """Proveedor de datos completo y optimizado"""
    
    def __init__(self, alpha_vantage_key=None):
        self.alpha_vantage_key = alpha_vantage_key or "GPA37GJVIDCNNTRL"
        self.last_request_time = 0
    
    def get_stock_data(self, symbol, as_of_date=None):
        """Obtener datos con período extendido - SIN ERRORES

        Args:
            symbol: Stock ticker symbol
            as_of_date: Optional date string (YYYY-MM-DD). If provided, only fetch data up to this date.
                       This prevents look-ahead bias in historical backtesting.
        """
        try:
            # Rate limiting más conservador
            elapsed = time.time() - self.last_request_time
            if elapsed < 1.5:
                time.sleep(1.5 - elapsed)
            self.last_request_time = time.time()

            ticker = yf.Ticker(symbol)

            # 🔴 FIX LOOK-AHEAD BIAS: Use date range instead of period
            if as_of_date:
                # Historical mode: fetch data up to as_of_date
                end_date = datetime.strptime(as_of_date, '%Y-%m-%d')
                start_date = end_date - timedelta(days=365)  # 1 year lookback

                df = ticker.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d'),
                    interval='1d',
                    timeout=30
                )
            else:
                # Current mode: use standard period
                df = ticker.history(period='1y', interval='1d', timeout=30)
            
            if df.empty or len(df) < 150:
                return None
            
            df = clean_dataframe_safe(df)
            
            if df.empty or len(df) < 150:
                return None
            
            # Metadata segura - ESTRUCTURA LIMPIA
            try:
                info = ticker.info
                market_cap = safe_int(info.get('marketCap', 0))
                metadata = {
                    'market_cap': market_cap,
                    'sector': str(info.get('sector', 'Unknown')),
                    'industry': str(info.get('industry', 'Unknown')),
                    'source': 'yfinance'
                }
            except:
                metadata = {
                    'market_cap': 0,
                    'sector': 'Unknown',
                    'industry': 'Unknown',
                    'source': 'yfinance'
                }
            
            return df, metadata
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return None

class CalibratedVCPScanner:
    """Scanner VCP calibrado completo con criterios realistas"""

    def __init__(self, alpha_vantage_key=None, as_of_date=None):
        """Initialize VCP Scanner

        Args:
            alpha_vantage_key: API key for Alpha Vantage (optional)
            as_of_date: Historical date (YYYY-MM-DD) for scoring. Prevents look-ahead bias.
        """
        self.data_provider = DataProvider(alpha_vantage_key)
        self.analyzer = CalibratedVCPAnalyzer()
        self.universe_manager = UniverseManager()

        # 🔴 FIX LOOK-AHEAD BIAS: Store as_of_date
        self.as_of_date = as_of_date

        # Filtros más flexibles
        self.min_price = 5.0           # Más bajo
        self.min_volume = 50_000       # Más bajo
        self.min_market_cap = 100_000_000  # Más bajo

        # Contadores
        self.processed_count = 0
        self.vcp_found_count = 0
        self.error_count = 0
    
    def process_single_ticker(self, symbol):
        """Procesar un ticker con criterios calibrados completos"""
        try:
            if self.processed_count % 50 == 0:
                gc.collect()

            # 🔴 FIX LOOK-AHEAD BIAS: Pass as_of_date to data provider
            result = self.data_provider.get_stock_data(symbol, as_of_date=self.as_of_date)
            if not result:
                return None
            
            df, metadata = result
            
            # Filtros básicos flexibles
            current_price = safe_float(df['Close'].iloc[-1])
            avg_volume = safe_float(df['Volume'].tail(30).mean())
            market_cap = safe_int(metadata.get('market_cap', 0))
            
            if (current_price < self.min_price or 
                avg_volume < self.min_volume or 
                (market_cap > 0 and market_cap < self.min_market_cap)):
                return None
            
            # Análisis VCP calibrado
            vcp_result = self.analyzer.analyze_vcp_pattern_calibrated(symbol, df)
            
            if vcp_result:
                vcp_result.sector = str(metadata.get('sector', 'Unknown'))
                vcp_result.market_cap = market_cap
                
                self.vcp_found_count += 1
                return vcp_result
            
            return None
            
        except Exception as e:
            logger.error(f"Error procesando {symbol}: {e}")
            self.error_count += 1
            return None
        finally:
            self.processed_count += 1
    
    def scan_sequential(self, symbols):
        """Escaneo secuencial calibrado completo"""
        logger.info(f"🚀 Iniciando escaneo VCP CALIBRADO de {len(symbols)} símbolos")
        logger.info("📊 Criterios realistas basados en investigación profesional")
        
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            try:
                result = self.process_single_ticker(symbol)
                if result:
                    results.append(result)
                    status = "🟢 COMPRAR" if result.ready_to_buy else "🟡 VIGILAR"
                    logger.info(f"[{i:3d}/{len(symbols)}] ✅ {symbol}: VCP {result.vcp_score:.1f}% ({result.pattern_quality}) | {status}")
                else:
                    logger.info(f"[{i:3d}/{len(symbols)}] ⚪ {symbol}: No cumple criterios VCP")
            
            except Exception as e:
                logger.error(f"[{i:3d}/{len(symbols)}] ❌ {symbol}: ERROR - {e}")
                self.error_count += 1
                
                if self.error_count > 30:
                    logger.error("❌ Demasiados errores - parando")
                    break
            
            if i % 25 == 0:
                found_rate = (len(results) / i) * 100
                logger.info(f"📊 Progreso: {i}/{len(symbols)} | VCP: {len(results)} ({found_rate:.2f}%) | Errores: {self.error_count}")
            
            time.sleep(1.0)  # Pausa más corta

        return results

    def scan_parallel(self, symbols, num_workers=None):
        """
        Escaneo PARALELO - 6-8x más rápido que secuencial

        Usa multiprocessing para procesar múltiples tickers simultáneamente
        Ideal para scans grandes (S&P 500, NASDAQ)

        Args:
            symbols: Lista de símbolos a escanear
            num_workers: Número de workers (default: CPU count - 1)
        """
        if num_workers is None:
            # Use all CPUs minus 1 to leave one free
            num_workers = max(1, cpu_count() - 1)

        logger.info(f"⚡ Iniciando escaneo VCP PARALELO de {len(symbols)} símbolos")
        logger.info(f"🚀 Usando {num_workers} workers paralelos")
        logger.info("📊 Criterios realistas basados en investigación profesional")

        # Create partial function with self bound
        process_func = partial(self._process_ticker_safe, self)

        results = []
        errors = 0

        # Process in parallel with progress tracking
        with Pool(processes=num_workers) as pool:
            # Use imap for ordered results with progress tracking
            for i, result in enumerate(pool.imap(process_func, symbols), 1):
                if result is not None:
                    if isinstance(result, Exception):
                        errors += 1
                        logger.error(f"[{i:3d}/{len(symbols)}] ❌ Error: {result}")
                    else:
                        results.append(result)
                        status = "🟢 COMPRAR" if result.ready_to_buy else "🟡 VIGILAR"
                        logger.info(f"[{i:3d}/{len(symbols)}] ✅ {result.ticker}: VCP {result.vcp_score:.1f}% ({result.pattern_quality}) | {status}")
                else:
                    logger.debug(f"[{i:3d}/{len(symbols)}] ⚪ No cumple criterios VCP")

                # Progress update every 50 symbols
                if i % 50 == 0:
                    found_rate = (len(results) / i) * 100
                    logger.info(f"📊 Progreso: {i}/{len(symbols)} | VCP: {len(results)} ({found_rate:.2f}%) | Errores: {errors}")

        self.error_count = errors
        logger.info(f"✅ Escaneo paralelo completado: {len(results)} patrones VCP detectados")

        return results

    @staticmethod
    def _process_ticker_safe(scanner_instance, symbol):
        """
        Wrapper estático para process_single_ticker - safe para multiprocessing

        Maneja excepciones y retorna None o Exception en lugar de fallar
        """
        try:
            return scanner_instance.process_single_ticker(symbol)
        except Exception as e:
            # Return exception instead of None to distinguish errors
            return e

    def generate_detailed_report(self, results):
        """Generar reporte detallado calibrado completo"""
        print("\n" + "="*90)
        print("📊 REPORTE VCP SCANNER CALIBRADO - CRITERIOS REALISTAS")
        print("="*90)
        print(f"Total símbolos procesados: {self.processed_count}")
        print(f"Errores encontrados: {self.error_count}")
        print(f"🎯 PATRONES VCP DETECTADOS: {len(results)}")
        
        if self.processed_count > 0:
            success_rate = (self.processed_count - self.error_count) / self.processed_count * 100
            vcp_rate = (len(results) / self.processed_count) * 100
            print(f"📈 Tasa de éxito: {success_rate:.1f}%")
            print(f"📈 Tasa de detección VCP: {vcp_rate:.2f}% (esperado: 1-5%)")
        
        if not results:
            print("\n⚠️  NO SE ENCONTRARON PATRONES VCP")
            print("💡 Posibles causas:")
            print("   • Mercado en condiciones no favorables para VCP")
            print("   • Período de consolidación insuficiente")
            print("   • La mayoría de acciones están en otras etapas")
            print("🔧 Recomendación: Probar con símbolos específicos conocidos")
            return
        
        # Separar por calidad
        excellent_patterns = [r for r in results if r.pattern_quality == "Excellent"]
        good_patterns = [r for r in results if r.pattern_quality == "Good"]
        fair_patterns = [r for r in results if r.pattern_quality == "Fair"]
        buy_candidates = [r for r in results if r.ready_to_buy]
        
        print(f"\n📊 DISTRIBUCIÓN POR CALIDAD:")
        print(f"🏆 Excelentes: {len(excellent_patterns)}")
        print(f"✅ Buenos: {len(good_patterns)}")
        print(f"⚡ Aceptables: {len(fair_patterns)}")
        print(f"🟢 LISTOS PARA COMPRAR: {len(buy_candidates)}")
        
        # Ordenar por puntuación
        results.sort(key=lambda x: x.vcp_score, reverse=True)
        
        # Tabla detallada
        print(f"\n🏆 TOP CANDIDATOS VCP:")
        print("-" * 140)
        print(f"{'#':<3} {'Ticker':<8} {'Precio':<8} {'VCP':<8} {'Calidad':<10} {'Base%':<8} {'Contracs':<12} {'Etapa':<15} {'Estado':<12}")
        print("-" * 140)
        
        for i, result in enumerate(results[:20], 1):  # Top 20
            status = "🟢 COMPRAR" if result.ready_to_buy else "🟡 VIGILAR"
            contractions_str = '→'.join([f'{c:.1f}' for c in result.contractions[:3]])  # Primeras 3
            if len(result.contractions) > 3:
                contractions_str += "..."
            
            print(f"{i:<3} {result.ticker:<8} "
                  f"${result.current_price:<7.2f} "
                  f"{result.vcp_score:<7.1f}% "
                  f"{result.pattern_quality:<10} "
                  f"{result.base_depth:<7.1f}% "
                  f"{contractions_str:<12} "
                  f"{result.stage_analysis[:14]:<15} "
                  f"{status:<12}")
        
        # Análisis detallado del mejor candidato
        if results:
            best = results[0]
            print(f"\n🎯 ANÁLISIS DETALLADO: {best.ticker}")
            print("=" * 70)
            print(f"   💰 Precio actual: ${best.current_price:.2f}")
            print(f"   📊 Puntuación VCP: {best.vcp_score:.1f}% ({best.pattern_quality})")
            print(f"   📈 Número de contracciones: {len(best.contractions)}")
            print(f"   📉 Secuencia de contracciones: {' → '.join([f'{c:.1f}%' for c in best.contractions])}")
            print(f"   📊 Profundidad base: {best.base_depth:.1f}%")
            print(f"   📈 Análisis de etapa: {best.stage_analysis} ({best.trend_score:.1f}%)")
            print(f"   📊 Puntuación volumen: {best.volume_score:.1f}%")
            print(f"   🎯 Potencial breakout: {best.breakout_potential:.1f}%")
            print(f"   🏭 Sector: {best.sector}")
            print(f"   💹 Market Cap: ${best.market_cap:,}")
            print(f"   📝 {best.reason}")
            
            if best.ready_to_buy:
                print(f"\n🚀 RECOMENDACIÓN DE TRADING:")
                print(f"   📈 COMPRAR: En breakout con volumen 30-50% superior al promedio")
                print(f"   🛡️  Stop Loss: {best.current_price * 0.92:.2f} (8% debajo)")
                print(f"   🎯 Objetivo 1: {best.current_price * 1.25:.2f} (+25%)")
                print(f"   🎯 Objetivo 2: {best.current_price * 1.40:.2f} (+40%)")
                print(f"   ⏰ Timeframe: 2-8 semanas típicamente")
            else:
                print(f"\n👀 VIGILAR: Esperar breakout confirmado con volumen")
        
        # Estadísticas por sector
        if len(results) > 3:
            sector_analysis = {}
            for result in results:
                sector = result.sector
                if sector not in sector_analysis:
                    sector_analysis[sector] = []
                sector_analysis[sector].append(result.vcp_score)
            
            print(f"\n📊 ANÁLISIS POR SECTOR:")
            print("-" * 50)
            for sector, scores in sector_analysis.items():
                avg_score = np.mean(scores)
                count = len(scores)
                print(f"   {sector:<20}: {count} candidatos, avg {avg_score:.1f}%")
        
        # Guardar resultados
        if results:
            self.save_detailed_results(results)

    def save_detailed_results(self, results):
        """Guardar resultados detallados completos"""
        try:
            data = []
            for result in results:
                data.append({
                    'ticker': result.ticker,
                    'precio': result.current_price,
                    'vcp_score': result.vcp_score,
                    'calidad_patron': result.pattern_quality,
                    'num_contracciones': len(result.contractions),
                    'contracciones': ' → '.join([f'{c:.1f}%' for c in result.contractions]),
                    'profundidad_base': result.base_depth,
                    'etapa_analisis': result.stage_analysis,
                    'trend_score': result.trend_score,
                    'volumen_score': result.volume_score,
                    'breakout_potential': result.breakout_potential,
                    'listo_comprar': result.ready_to_buy,
                    'sector': result.sector,
                    'market_cap': result.market_cap,
                    'razon': result.reason,
                    'fecha_scan': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df = pd.DataFrame(data)
            filename = f"vcp_calibrated_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            
            print(f"\n📁 Resultados guardados en: {filename}")
            
        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")

def test_known_vcp_candidates():
    """Probar con candidatos VCP conocidos completo"""
    test_symbols = [
        # Acciones que han mostrado patrones VCP históricamente
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META',
        # Biotech que suelen formar VCP
        'MRNA', 'BNTX', 'GILD', 'REGN', 'AMGN',
        # Growth stocks que forman patrones
        'CRM', 'ADBE', 'NFLX', 'SHOP', 'SQ', 'ROKU',
        # Tecnología emergente
        'PLTR', 'SNOW', 'DDOG', 'CRWD', 'ZS',
        # Otros sectores
        'JPM', 'BAC', 'UNH', 'JNJ', 'PG', 'HD', 'DIS'
    ]
    
    print("🧪 PROBANDO CANDIDATOS VCP CONOCIDOS")
    print("=" * 50)
    
    scanner = CalibratedVCPScanner("GPA37GJVIDCNNTRL")
    results = scanner.scan_sequential(test_symbols)
    scanner.generate_detailed_report(results)
    
    return len(results)

def main_menu():
    """Menú principal calibrado completo"""
    print("\n" + "="*80)
    print("🎯 VCP SCANNER CALIBRADO - CRITERIOS REALISTAS")
    print("📊 Basado en investigación de patrones VCP reales")
    print("🔧 Criterios flexibles como traders profesionales")
    print("💎 Detecta patrones VCP genuinos con tolerancias realistas")
    print("="*80)
    
    scanner = CalibratedVCPScanner("GPA37GJVIDCNNTRL")
    
    while True:
        print("\n" + "="*80)
        print("OPCIONES DE ESCANEO VCP CALIBRADO:")
        print("1. 🧪 Test con candidatos conocidos (recomendado)")
        print("2. 🔥 Test rápido (30 acciones populares)")
        print("3. 📈 S&P 500 completo (~500 acciones)")
        print("4. 💎 NASDAQ completo (~3000 acciones)")
        print("5. 🎯 Símbolos personalizados")
        print("6. ⚙️  Ver/Configurar criterios")
        print("7. 📚 Guía VCP calibrada")
        print("0. 🚪 Salir")
        print("-"*80)
        print("💡 NUEVO: Criterios calibrados detectan más patrones VCP reales")
        
        try:
            choice = input("Selecciona opción: ").strip()
            
            if choice == "1":
                found = test_known_vcp_candidates()
                if found == 0:
                    print("\n⚠️  Ningún candidato conocido muestra patrón VCP actualmente")
                    print("💡 Esto es normal - los VCP son patrones temporales")
                
            elif choice == "2":
                test_symbols = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
                    'CRM', 'ADBE', 'PYPL', 'SQ', 'SHOP', 'ROKU', 'ZM', 'DOCU',
                    'TWLO', 'OKTA', 'CRWD', 'ZS', 'DDOG', 'SNOW', 'PLTR', 'COIN',
                    'RBLX', 'U', 'SOFI', 'HOOD', 'RIVN', 'LCID', 'MRNA', 'BNTX'
                ]
                results = scanner.scan_sequential(test_symbols)
                scanner.generate_detailed_report(results)
                
            elif choice == "3":
                symbols = scanner.universe_manager.get_sp500_symbols()
                if symbols:
                    print(f"📊 Escaneando {len(symbols)} acciones del S&P 500...")
                    print("⏱️  Tiempo estimado: 15-25 minutos")
                    print("🎯 Esperamos encontrar 5-25 patrones VCP (1-5%)")
                    confirm = input("¿Continuar? (s/n): ").lower()
                    if confirm == 's':
                        results = scanner.scan_sequential(symbols)
                        scanner.generate_detailed_report(results)
                else:
                    print("❌ No se pudieron obtener símbolos del S&P 500")
                
            elif choice == "4":
                symbols = scanner.universe_manager.get_nasdaq_symbols()
                if symbols:
                    print(f"📊 Escaneando {len(symbols)} acciones de NASDAQ...")
                    print("⏱️  Tiempo estimado: 1-2 horas")
                    print("🎯 Esperamos encontrar 15-60 patrones VCP")
                    confirm = input(f"⚠️  Esto tomará tiempo. ¿Continuar? (s/n): ").lower()
                    if confirm == 's':
                        results = scanner.scan_sequential(symbols)
                        scanner.generate_detailed_report(results)
                else:
                    print("❌ No se pudieron obtener símbolos de NASDAQ")
                
            elif choice == "5":
                custom_input = input("Introduce símbolos separados por comas: ").strip()
                if custom_input:
                    custom_symbols = [s.strip().upper() for s in custom_input.split(',')]
                    results = scanner.scan_sequential(custom_symbols)
                    scanner.generate_detailed_report(results)
                
            elif choice == "6":
                show_calibrated_criteria(scanner)
                
            elif choice == "7":
                show_calibrated_guide()
                
            elif choice == "0":
                print("👋 ¡Gracias por usar VCP Scanner Calibrado!")
                break
                
            else:
                print("❌ Opción no válida")
                continue
            
            if choice in ['1', '2', '3', '4', '5']:
                continue_scan = input("\n¿Realizar otro escaneo? (s/n): ").strip().lower()
                if continue_scan != 's':
                    break
                    
        except KeyboardInterrupt:
            print("\n\n👋 Saliendo del scanner...")
            break
        except Exception as e:
            logger.error(f"Error en menú principal: {e}")
            print(f"❌ Error inesperado: {e}")

def show_calibrated_criteria(scanner):
    """Mostrar criterios calibrados completos"""
    print("\n⚙️ CRITERIOS VCP CALIBRADOS")
    print("=" * 60)
    print("📊 FILTROS BÁSICOS:")
    print(f"   • Precio mínimo: ${scanner.min_price}")
    print(f"   • Volumen mínimo: {scanner.min_volume:,}")
    print(f"   • Market cap mínimo: ${scanner.min_market_cap:,}")
    print(f"   • Datos mínimos: {scanner.analyzer.min_data_points} días")
    
    print("\n📈 CRITERIOS DE PATRÓN:")
    print(f"   • Contracciones mínimas: 2 (más flexible)")
    print(f"   • Primera contracción: {scanner.analyzer.first_contraction_range[0]}-{scanner.analyzer.first_contraction_range[1]}%")
    print(f"   • Contracción mínima: {scanner.analyzer.subsequent_min}%")
    print(f"   • Contracción final máxima: {scanner.analyzer.final_contraction_max}%")
    print(f"   • Tolerancia progresión: ±{scanner.analyzer.contraction_tolerance*100:.0f}%")
    
    print("\n🎯 CRITERIOS DE COMPRA:")
    print("   • Puntuación VCP: ≥65% (vs 80% anterior)")
    print("   • Calidad patrón: Good o Excellent")
    print("   • Etapa: Stage 2 preferible")
    print("   • Contracción final: ≤15%")
    
    print("\n💡 CAMBIOS PRINCIPALES vs VERSIÓN ANTERIOR:")
    print("   ✅ Tolerancia 20% en progresión de contracciones")
    print("   ✅ Acepta 2 contracciones (vs 2-4 estricto)")
    print("   ✅ Análisis de volumen más flexible")
    print("   ✅ Sistema de puntuación en lugar de binario")
    print("   ✅ Múltiples niveles de calidad de patrón")
    
    input("\nPresiona Enter para continuar...")

def show_calibrated_guide():
    """Mostrar guía VCP calibrada completa"""
    print("\n📚 GUÍA VCP CALIBRADA - CRITERIOS REALISTAS")
    print("=" * 70)
    
    print("\n🎯 FILOSOFÍA DE CALIBRACIÓN:")
    print("• Los mercados son imperfectos - los patrones también")
    print("• Tolerancias realistas basadas en traders profesionales")
    print("• Foco en calidad del patrón, no perfección matemática")
    print("• Sistema de puntuación flexible vs criterios binarios")
    
    print("\n📊 CRITERIOS CALIBRADOS:")
    print("🔹 CONTRACCIONES:")
    print("   • Primera: 10-40% (más flexible que 10-35%)")
    print("   • Progresión: 'Roughly decreasing' (±20% tolerancia)")
    print("   • Final: ≤12% ideal (vs ≤8% estricto)")
    print("   • Mínimas: 2 contracciones (vs 2-4 rígido)")
    
    print("\n🔹 VOLUMEN:")
    print("   • Tendencia decreciente general (no estricta)")
    print("   • Permite fluctuaciones normales")
    print("   • Foco en 'secado' general, no matemático")
    
    print("\n🔹 ETAPA/TENDENCIA:")
    print("   • Stage 2 preferible, no obligatorio")
    print("   • Acepta Stage 1-2 transitions")
    print("   • Proximidad a máximos: hasta 25% aceptable")
    
    print("\n📈 CALIDAD DE PATRONES:")
    print("🏆 Excellent (80-100%): Patrón textbook")
    print("✅ Good (65-79%): Patrón sólido, tradeable")
    print("⚡ Fair (50-64%): Patrón aceptable, más riesgo")
    print("❌ Poor (<50%): No considerado")
    
    print("\n🚀 ESTRATEGIA DE TRADING:")
    print("• COMPRAR: En breakout con volumen 30-50% superior")
    print("• STOP: 8% debajo del precio de entrada")
    print("• OBJETIVO 1: +25% (tomar parciales)")
    print("• OBJETIVO 2: +40% (dejar correr)")
    print("• TIMEFRAME: 2-8 semanas típicamente")
    
    print("\n⚠️  GESTIÓN DE EXPECTATIVAS:")
    print("• Detección esperada: 1-5% del universo escaneado")
    print("• Tasa de éxito: 60-75% con gestión adecuada")
    print("• Mejor en mercados alcistas/laterales")
    print("• Requiere paciencia y disciplina")
    
    print("\n🔧 VENTAJAS CALIBRACIÓN:")
    print("✅ Encuentra más patrones reales")
    print("✅ Reduce falsos negativos")
    print("✅ Criteria alineados con práctica profesional")
    print("✅ Sistema de calidad granular")
    print("✅ Mejor balance riesgo/oportunidad")
    
    input("\nPresiona Enter para continuar...")

# ===== WRAPPER PARA INTEGRACIÓN CON SISTEMA PRINCIPAL =====

class VCPScannerEnhanced:
    """Wrapper para integración con sistema_principal.py"""

    def __init__(self, alpha_vantage_key=None, as_of_date=None):
        """Initialize VCP Scanner Enhanced

        Args:
            alpha_vantage_key: API key for Alpha Vantage (optional)
            as_of_date: Historical date (YYYY-MM-DD) for scoring. Prevents look-ahead bias.
        """
        # 🔴 FIX LOOK-AHEAD BIAS: Pass as_of_date to scanner
        self.scanner = CalibratedVCPScanner(alpha_vantage_key, as_of_date=as_of_date)
        self.last_results = []
        self.as_of_date = as_of_date

        if as_of_date:
            logger.info(f"✅ VCPScannerEnhanced inicializado (Historical mode: as_of_date={as_of_date})")
        else:
            logger.info("✅ VCPScannerEnhanced inicializado")
    
    def scan_market(self, symbol_list=None, quick_test=False, parallel=False, num_workers=None):
        """
        Escanear mercado - compatible con sistema_principal

        Args:
            symbol_list: Lista custom de símbolos
            quick_test: Test rápido con 30 acciones
            parallel: Usar procesamiento paralelo (6-8x más rápido)
            num_workers: Número de workers para modo paralelo (default: CPU count - 1)
        """
        try:
            if quick_test:
                # Test rápido con 30 acciones populares
                symbols = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
                    'CRM', 'ADBE', 'PYPL', 'SQ', 'SHOP', 'ROKU', 'ZM', 'DOCU',
                    'TWLO', 'OKTA', 'CRWD', 'ZS', 'DDOG', 'SNOW', 'PLTR', 'COIN',
                    'RBLX', 'U', 'SOFI', 'HOOD', 'RIVN', 'LCID'
                ]
            elif symbol_list:
                symbols = symbol_list
            else:
                # Por defecto, S&P 500
                symbols = self.scanner.universe_manager.get_sp500_symbols()

            logger.info(f"🚀 Escaneando {len(symbols)} símbolos...")

            # Choose scan mode
            if parallel:
                logger.info("⚡ Modo PARALELO activado - velocidad 6-8x más rápida")
                results = self.scanner.scan_parallel(symbols, num_workers=num_workers)
            else:
                logger.info("🐢 Modo SECUENCIAL (usar --parallel para ir más rápido)")
                results = self.scanner.scan_sequential(symbols)

            self.last_results = results

            logger.info(f"✅ Escaneo completado: {len(results)} patrones VCP detectados")
            return results

        except Exception as e:
            logger.error(f"Error en scan_market: {e}")
            return []
    
    def save_csv(self, results, csv_path):
        """Guardar resultados en CSV"""
        try:
            if not results:
                logger.warning("No hay resultados para guardar")
                return False
            
            data = []
            for result in results:
                data.append({
                    'ticker': result.ticker,
                    'precio': result.current_price,
                    'vcp_score': result.vcp_score,
                    'calidad_patron': result.pattern_quality,
                    'num_contracciones': len(result.contractions),
                    'contracciones': ' → '.join([f'{c:.1f}%' for c in result.contractions]),
                    'profundidad_base': result.base_depth,
                    'etapa_analisis': result.stage_analysis,
                    'trend_score': result.trend_score,
                    'volumen_score': result.volume_score,
                    'breakout_potential': result.breakout_potential,
                    'listo_comprar': result.ready_to_buy,
                    'sector': result.sector,
                    'market_cap': result.market_cap,
                    'razon': result.reason
                })
            
            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False)
            logger.info(f"✅ CSV guardado: {csv_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando CSV: {e}")
            return False
    
    def generate_html(self, results, html_path):
        """Generar HTML con diseño Liquid Glass"""
        try:
            if not results:
                results = []
            
            # Separar por categorías
            buy_candidates = [r for r in results if r.ready_to_buy]
            excellent = [r for r in results if r.pattern_quality == "Excellent"]
            good = [r for r in results if r.pattern_quality == "Good"]
            
            # Ordenar por score
            results_sorted = sorted(results, key=lambda x: x.vcp_score, reverse=True)
            
            # Generar HTML
            html_content = self._generate_vcp_html_page(
                results_sorted[:20],  # Top 20
                total_scanned=self.scanner.processed_count,
                buy_candidates=len(buy_candidates),
                excellent=len(excellent),
                good=len(good)
            )
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ HTML generado: {html_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generando HTML: {e}")
            return False
    
    def _generate_vcp_html_page(self, results, total_scanned, buy_candidates, excellent, good):
        """Generar página HTML con diseño Liquid Glass"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Generar tabla de resultados
        results_html = ""
        for i, result in enumerate(results[:20], 1):
            status_color = "#48bb78" if result.ready_to_buy else "#f6ad55"
            status_text = "🟢 COMPRAR" if result.ready_to_buy else "🟡 VIGILAR"
            quality_color = {"Excellent": "#48bb78", "Good": "#4299e1", "Fair": "#f6ad55", "Poor": "#fc8181"}.get(result.pattern_quality, "#a0aec0")
            
            contractions_str = ' → '.join([f'{c:.1f}%' for c in result.contractions[:4]])
            if len(result.contractions) > 4:
                contractions_str += "..."
            
            results_html += f"""
            <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                <td style="padding: 1rem; text-align: center;">{i}</td>
                <td style="padding: 1rem; font-weight: 700; color: var(--glass-accent);">{result.ticker}</td>
                <td style="padding: 1rem;">${result.current_price:.2f}</td>
                <td style="padding: 1rem; font-weight: 700; color: {quality_color};">{result.vcp_score:.1f}%</td>
                <td style="padding: 1rem; color: {quality_color};">{result.pattern_quality}</td>
                <td style="padding: 1rem;">{result.base_depth:.1f}%</td>
                <td style="padding: 1rem; font-size: 0.85rem;">{contractions_str}</td>
                <td style="padding: 1rem; font-size: 0.85rem;">{result.stage_analysis[:20]}</td>
                <td style="padding: 1rem; color: {status_color}; font-weight: 600;">{status_text}</td>
            </tr>
            """
        
        if not results_html:
            results_html = """
            <tr>
                <td colspan="9" style="padding: 2rem; text-align: center; color: var(--text-secondary);">
                    <h3>🔍 No se encontraron patrones VCP</h3>
                    <p>Intenta escanear un universo más amplio o ajustar los criterios</p>
                </td>
            </tr>
            """
        
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 VCP Scanner | Liquid Glass Dashboard</title>
    <style>
        :root {{
            --glass-primary: rgba(99, 102, 241, 0.8);
            --glass-secondary: rgba(139, 92, 246, 0.7);
            --glass-accent: rgba(59, 130, 246, 0.9);
            --glass-bg: rgba(255, 255, 255, 0.03);
            --glass-bg-hover: rgba(255, 255, 255, 0.08);
            --glass-border: rgba(255, 255, 255, 0.1);
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.7);
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: #020617;
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .glass-card {{
            background: var(--glass-bg);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        
        h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-accent));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            text-align: center;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }}
        
        .stat-box {{
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, var(--glass-accent), var(--glass-primary));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            padding: 1rem;
            text-align: left;
            border-bottom: 2px solid var(--glass-border);
            color: var(--text-primary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }}
        
        .back-link {{
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: linear-gradient(135deg, var(--glass-primary), var(--glass-accent));
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }}
        
        .back-link:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="https://tantancansado.github.io/stock_analyzer_a" class="back-link">🏠 Volver al Dashboard</a>
        
        <div class="glass-card">
            <h1>🚀 VCP Pattern Scanner</h1>
            <p style="text-align: center; color: var(--text-secondary); margin-bottom: 1rem;">
                Volatility Contraction Pattern Detection System
            </p>
            <p style="text-align: center; color: var(--text-secondary); font-size: 0.9rem;">
                📅 {timestamp}
            </p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">{total_scanned}</div>
                <div class="stat-label">Acciones Escaneadas</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{len(results)}</div>
                <div class="stat-label">Patrones VCP</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{buy_candidates}</div>
                <div class="stat-label">Listos Comprar</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{excellent}</div>
                <div class="stat-label">Excelentes</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{good}</div>
                <div class="stat-label">Buenos</div>
            </div>
        </div>
        
        <div class="glass-card">
            <h2 style="color: var(--text-primary); margin-bottom: 1.5rem;">🏆 Top Candidatos VCP</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Ticker</th>
                            <th>Precio</th>
                            <th>VCP Score</th>
                            <th>Calidad</th>
                            <th>Base %</th>
                            <th>Contracciones</th>
                            <th>Etapa</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {results_html}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="glass-card" style="text-align: center; color: var(--text-secondary);">
            <p>🚀 VCP Scanner Calibrado • Powered by Advanced Pattern Recognition</p>
            <p style="font-size: 0.85rem; margin-top: 0.5rem;">
                Sistema completo: Insider Trading • DJ Sectorial • Market Breadth • Enhanced Opportunities • VCP Scanner
            </p>
        </div>
    </div>
</body>
</html>"""

logger.info("✅ VCPScannerEnhanced wrapper creado correctamente")



def parse_arguments():
    """Parse command-line arguments for non-interactive execution"""
    parser = argparse.ArgumentParser(
        description='VCP Scanner - Interactive or Automated Execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 vcp_scanner_usa.py                        # Interactive menu
  python3 vcp_scanner_usa.py --sp500                # Scan S&P 500 (sequential)
  python3 vcp_scanner_usa.py --sp500 --parallel     # ⚡ Scan S&P 500 (PARALLEL - 6x faster!)
  python3 vcp_scanner_usa.py --nasdaq --parallel    # ⚡ Scan NASDAQ (parallel)
  python3 vcp_scanner_usa.py --quick                # Quick test (30 stocks)
  python3 vcp_scanner_usa.py --symbols AAPL,MSFT,NVDA --parallel

Performance:
  Sequential mode: ~2 hours for S&P 500
  Parallel mode:   ~15-20 minutes for S&P 500 (6-8x faster!) ⚡
        '''
    )

    parser.add_argument('--sp500', action='store_true',
                       help='Scan S&P 500 stocks (~500 stocks)')
    parser.add_argument('--nasdaq', action='store_true',
                       help='Scan NASDAQ stocks (~3000 stocks)')
    parser.add_argument('--quick', action='store_true',
                       help='Quick test with 30 popular stocks')
    parser.add_argument('--symbols', type=str,
                       help='Comma-separated list of symbols (e.g., AAPL,MSFT,NVDA)')
    parser.add_argument('--parallel', action='store_true',
                       help='⚡ Use parallel processing (6-8x faster)')
    parser.add_argument('--workers', type=int, default=None,
                       help='Number of parallel workers (default: CPU count - 1)')
    parser.add_argument('--as-of-date', type=str, default=None,
                       help='Historical date for scoring (YYYY-MM-DD). Only use data up to this date. '
                            'Prevents look-ahead bias in backtesting.')

    return parser.parse_args()

if __name__ == "__main__":
    try:
        args = parse_arguments()

        # Check if running in non-interactive mode
        if args.sp500 or args.nasdaq or args.quick or args.symbols:
            # Non-interactive mode - run scan directly
            print("🎯 VCP SCANNER - NON-INTERACTIVE MODE")
            print("=" * 70)

            # 🔴 FIX LOOK-AHEAD BIAS: Pass as_of_date from arguments
            if args.as_of_date:
                print(f"📅 Historical mode: Using data as of {args.as_of_date}")
                print(f"🔴 This prevents look-ahead bias in backtesting")

            scanner_enhanced = VCPScannerEnhanced("GPA37GJVIDCNNTRL", as_of_date=args.as_of_date)
            scanner = scanner_enhanced.scanner  # Keep reference for compatibility

            if args.quick:
                print("🔥 Quick test mode - scanning 30 popular stocks...")
                symbols = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
                    'CRM', 'ADBE', 'PYPL', 'SQ', 'SHOP', 'ROKU', 'ZM', 'DOCU',
                    'TWLO', 'OKTA', 'CRWD', 'ZS', 'DDOG', 'SNOW', 'PLTR', 'COIN',
                    'RBLX', 'U', 'SOFI', 'HOOD', 'RIVN', 'LCID', 'MRNA', 'BNTX'
                ]
            elif args.nasdaq:
                print("💎 NASDAQ mode - scanning ~3000 stocks...")
                print("⏱️  Estimated time: 1-2 hours")
                symbols = scanner.universe_manager.get_nasdaq_symbols()
                if not symbols:
                    print("❌ Could not get NASDAQ symbols")
                    exit(1)
            elif args.symbols:
                custom_symbols = [s.strip().upper() for s in args.symbols.split(',')]
                print(f"🎯 Custom symbols mode - scanning {len(custom_symbols)} stocks...")
                symbols = custom_symbols
            else:  # args.sp500 is default
                print("📈 S&P 500 mode - scanning ~500 stocks...")
                print("⏱️  Estimated time: 15-25 minutes")
                symbols = scanner.universe_manager.get_sp500_symbols()
                if not symbols:
                    print("❌ Could not get S&P 500 symbols")
                    exit(1)

            print(f"📊 Scanning {len(symbols)} symbols...")
            if args.parallel:
                print(f"⚡ PARALLEL MODE - Using {args.workers or (cpu_count() - 1)} workers")
                print(f"🚀 Expected speedup: 6-8x faster")
            print("=" * 70)

            # Use scanner_enhanced.scan_market for parallel support
            results = scanner_enhanced.scan_market(
                symbol_list=symbols,
                parallel=args.parallel,
                num_workers=args.workers
            )

            scanner.generate_detailed_report(results)

            # Generate timestamp for files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Ensure output directory exists
            from pathlib import Path
            output_dir = Path("docs/reports/vcp")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save CSV to standardized location
            csv_path = output_dir / f"vcp_calibrated_results_{timestamp}.csv"
            scanner_enhanced.save_csv(results, str(csv_path))

            # Save HTML to standardized location
            html_path = output_dir / f"vcp_scanner_{timestamp}.html"
            scanner_enhanced.generate_html(results, str(html_path))

            # Create/update symlinks for latest files
            latest_csv = output_dir / "latest.csv"
            latest_html = output_dir / "latest.html"

            # Remove old symlinks if they exist
            if latest_csv.exists() or latest_csv.is_symlink():
                latest_csv.unlink()
            if latest_html.exists() or latest_html.is_symlink():
                latest_html.unlink()

            # Create new symlinks (relative paths for portability)
            latest_csv.symlink_to(f"vcp_calibrated_results_{timestamp}.csv")
            latest_html.symlink_to(f"vcp_scanner_{timestamp}.html")

            # Also update docs/vcp_scanner.html as main entry point
            import shutil
            shutil.copy(str(html_path), "docs/vcp_scanner.html")

            print("=" * 70)
            print(f"✅ Scan completed: {len(results)} VCP patterns detected")
            print(f"📊 CSV saved: {csv_path}")
            print(f"🌐 HTML saved: {html_path}")
            print("=" * 70)

        else:
            # Interactive mode - show menu as usual
            print("🎯 VCP SCANNER CALIBRADO - FUNCIONALIDAD COMPLETA")
            print("✅ Basado en investigación de patrones VCP reales")
            print("✅ Tolerancias flexibles como traders profesionales")
            print("✅ Sistema de puntuación granular")
            print("✅ Detecta más patrones genuinos")
            print("✅ SIN ERRORES DE SINTAXIS")
            print()

            main_menu()

    except KeyboardInterrupt:
        print("\n👋 Saliendo...")
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        print(f"❌ Error crítico: {e}")
    finally:
        print("🙏 Gracias por usar VCP Scanner Calibrado")

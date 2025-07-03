#!/usr/bin/env python3
"""
Enhanced Trading Opportunity Analyzer
Archivo separado para análisis avanzado de oportunidades de trading
Integra datos sectoriales e insider trading con interpretaciones automáticas
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import os
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import traceback

class EnhancedTradingOpportunityAnalyzer:
    """
    Analizador MEJORADO de oportunidades que incluye interpretaciones automáticas
    """
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.insider_data_history = {}
        self.sector_data_history = {}
        self.consolidated_insider = pd.DataFrame()
        self.consolidated_sector = pd.DataFrame()
        self.analysis_results = {}
        
    def scan_directory_structure(self) -> Dict[str, List[str]]:
        """Escanear automáticamente la estructura de directorios específica del sistema"""
        structure = {
            'insider_dirs': [],
            'sector_dirs': [],
            'insider_files': [],
            'sector_files': []
        }
        
        print(f"🔍 Escaneando estructura desde: {self.base_path}")
        
        # PATRÓN ESPECÍFICO 1: reports/report_YYYY-MM-DD/data.csv (INSIDER TRADING)
        insider_pattern = 'reports/report_*/data.csv'
        insider_files = list(self.base_path.glob(insider_pattern))
        
        for file_path in insider_files:
            structure['insider_files'].append(str(file_path))
            structure['insider_dirs'].append(str(file_path.parent))
        
        # PATRÓN ESPECÍFICO 2: dj_sectorial/dj_sectorial_YYYY-MM-DD/data.csv
        sector_patterns = [
            'dj_sectorial/dj_sectorial_*/data.csv',
            'dj_sectorial_*/data.csv',
            'dj_sectorial/*/data.csv',
            'reports/dj_sectorial_analysis.csv'  # También buscar archivos generados por el sistema principal
        ]
        
        sector_files_found = []
        for pattern in sector_patterns:
            sector_files = list(self.base_path.glob(pattern))
            sector_files_found.extend(sector_files)
            
            for file_path in sector_files:
                if str(file_path) not in structure['sector_files']:
                    structure['sector_files'].append(str(file_path))
                    structure['sector_dirs'].append(str(file_path.parent))
        
        print(f"📄 Encontrados {len(insider_files)} archivos insider")
        print(f"📄 Encontrados {len(sector_files_found)} archivos sectoriales")
        
        return structure
    
    def extract_date_from_path(self, path: str) -> Optional[datetime]:
        """Extraer fecha del nombre del directorio o archivo"""
        # PATRÓN ESPECÍFICO 1: reports/report_2025-06-12/data.csv
        report_pattern = r'report[_/](\d{4}-\d{2}-\d{2})'
        match = re.search(report_pattern, path)
        if match:
            try:
                return datetime.strptime(match.group(1), '%Y-%m-%d')
            except:
                pass
        
        # PATRÓN ESPECÍFICO 2: dj_sectorial/dj_sectorial_2025-06-12/data.csv
        sectorial_pattern = r'dj_sectorial[_/](\d{4}-\d{2}-\d{2})'
        match = re.search(sectorial_pattern, path)
        if match:
            try:
                return datetime.strptime(match.group(1), '%Y-%m-%d')
            except:
                pass
        
        # Fallback: usar fecha del archivo
        try:
            file_path = Path(path)
            if file_path.exists():
                timestamp = file_path.stat().st_mtime
                return datetime.fromtimestamp(timestamp)
        except:
            pass
        
        return datetime.now()
    
    def load_historical_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Cargar datos históricos completos"""
        structure = self.scan_directory_structure()
        
        # Cargar insider data
        if structure['insider_files']:
            self.insider_data_history = self._load_insider_files(structure['insider_files'])
        
        # Cargar sector data
        if structure['sector_files']:
            self.sector_data_history = self._load_sector_files(structure['sector_files'])
        
        return self._consolidate_data()
    
    def _load_insider_files(self, file_paths: List[str]) -> Dict[str, pd.DataFrame]:
        """Cargar archivos insider con manejo mejorado"""
        historical_data = {}
        
        for file_path in file_paths:
            try:
                date = self.extract_date_from_path(file_path)
                date_key = date.strftime('%Y-%m-%d')
                
                raw_data = pd.read_csv(file_path, encoding='utf-8', sep=',', engine='python')
                
                if len(raw_data.columns) >= 10:
                    processed_data = pd.DataFrame({
                        'FileDate': date_key,
                        'ScrapedAt': raw_data.iloc[:, 0],
                        'Ticker': raw_data.iloc[:, 1],
                        'CompanyName': raw_data.iloc[:, 2],
                        'InsiderTitle': raw_data.iloc[:, 3],
                        'Type': raw_data.iloc[:, 4],
                        'Price': pd.to_numeric(raw_data.iloc[:, 5], errors='coerce'),
                        'Qty': pd.to_numeric(raw_data.iloc[:, 6], errors='coerce'),
                        'Owned': pd.to_numeric(raw_data.iloc[:, 7], errors='coerce'),
                        'Value': raw_data.iloc[:, 8],
                        'Source': raw_data.iloc[:, 9]
                    })
                    
                    processed_data['ValueNumeric'] = processed_data['Value'].apply(self._parse_value)
                    processed_data['DaysAgo'] = (datetime.now() - date).days
                    
                    # Limpiar datos
                    processed_data = processed_data.dropna(subset=['Ticker'])
                    processed_data['Ticker'] = processed_data['Ticker'].astype(str).str.strip()
                    processed_data = processed_data[
                        (processed_data['Ticker'] != 'nan') & 
                        (processed_data['Ticker'] != '') & 
                        (processed_data['Ticker'].str.len() > 0)
                    ]
                    
                    if len(processed_data) > 0:
                        historical_data[date_key] = processed_data
                
            except Exception as e:
                print(f"⚠️ Error procesando {file_path}: {e}")
        
        return historical_data
    
    def _load_sector_files(self, file_paths: List[str]) -> Dict[str, pd.DataFrame]:
        """Cargar archivos sectoriales"""
        historical_data = {}
        
        for file_path in file_paths:
            try:
                date = self.extract_date_from_path(file_path)
                date_key = date.strftime('%Y-%m-%d')
                
                sector_data = pd.read_csv(file_path, encoding='utf-8', sep=',', engine='python')
                
                # Agregar metadata temporal
                sector_data['FileDate'] = date_key
                sector_data['DaysAgo'] = (datetime.now() - date).days
                
                # Asegurar tipos correctos
                numeric_columns = ['CurrentPrice', 'Min52w', 'Max52w', 'DistanceFromMin', 'RSI', 'DataPoints']
                for col in numeric_columns:
                    if col in sector_data.columns:
                        sector_data[col] = pd.to_numeric(sector_data[col], errors='coerce')
                
                if len(sector_data) > 0:
                    historical_data[date_key] = sector_data
                
            except Exception as e:
                print(f"⚠️ Error procesando {file_path}: {e}")
        
        return historical_data
    
    def _parse_value(self, value_str) -> float:
        """Convertir strings de valor monetario a números"""
        if pd.isna(value_str) or value_str == '':
            return 0.0
        
        clean_value = str(value_str).replace('$', '').replace(',', '').replace(' ', '').replace('%', '')
        
        multipliers = {'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000}
        
        for suffix, multiplier in multipliers.items():
            if clean_value.upper().endswith(suffix):
                try:
                    num = float(clean_value[:-1])
                    return num * multiplier
                except:
                    pass
        
        try:
            return float(clean_value)
        except:
            return 0.0
    
    def _consolidate_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Consolidar datos históricos"""
        if self.insider_data_history:
            insider_frames = list(self.insider_data_history.values())
            self.consolidated_insider = pd.concat(insider_frames, ignore_index=True)
        
        if self.sector_data_history:
            sector_frames = list(self.sector_data_history.values())
            self.consolidated_sector = pd.concat(sector_frames, ignore_index=True)
        
        return self.consolidated_insider, self.consolidated_sector
    
    def analyze_enhanced_opportunities(self, recent_days: int = 30) -> Dict:
        """Análisis MEJORADO con interpretaciones automáticas"""
        insider_data, sector_data = self.load_historical_data()
        
        if sector_data.empty:
            return {'error': 'No hay datos sectoriales disponibles'}
        
        # Usar datos más recientes por sector
        latest_sectors = sector_data.loc[
            sector_data.groupby('Ticker')['DaysAgo'].idxmin()
        ].copy()
        
        # Calcular scores base
        latest_sectors['BaseScore'] = latest_sectors.apply(self._calculate_sector_score, axis=1)
        
        # Analizar insider patterns
        insider_patterns = self._analyze_insider_patterns(insider_data, recent_days)
        sector_mapping = self._create_sector_mapping(sector_data)
        
        # Análisis cruzado mejorado
        opportunities = self._perform_enhanced_cross_analysis(
            latest_sectors, insider_patterns, sector_mapping
        )
        
        # NUEVAS INTERPRETACIONES AUTOMÁTICAS
        enhanced_analysis = self._generate_enhanced_interpretations(opportunities)
        
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'opportunities': opportunities.to_dict('records'),
            'enhanced_analysis': enhanced_analysis,
            'summary': self._generate_enhanced_summary(opportunities),
            'special_patterns': self._detect_advanced_patterns(opportunities),
            'strategic_recommendations': self._generate_strategic_recommendations(opportunities),
            'risk_analysis': self._analyze_risk_distribution(opportunities),
            'upside_calculations': self._calculate_upside_potentials(opportunities),
            'sector_correlations': self._analyze_sector_correlations(opportunities),
            'trading_alerts': self._generate_trading_alerts(opportunities)
        }
    
    def _calculate_sector_score(self, row) -> int:
        """Calcular score base del sector"""
        score = 0
        
        # Proximidad al mínimo (40%)
        distance_score = max(0, 100 - row['DistanceFromMin'])
        score += distance_score * 0.4
        
        # RSI Score (30%)
        rsi = row['RSI']
        if rsi < 30:
            rsi_score = 100
        elif rsi < 40:
            rsi_score = 80
        elif rsi < 50:
            rsi_score = 60
        elif rsi < 60:
            rsi_score = 40
        else:
            rsi_score = 20
        score += rsi_score * 0.3
        
        # Clasificación (30%)
        classification = row['Classification']
        if classification == 'OPORTUNIDAD':
            class_score = 100
        elif classification == 'CERCA':
            class_score = 70
        elif classification == 'FUERTE':
            class_score = 30
        else:
            class_score = 50
        score += class_score * 0.3
        
        return round(score)
    
    def _analyze_insider_patterns(self, insider_data: pd.DataFrame, recent_days: int) -> Dict:
        """Analizar patrones de insider trading"""
        if insider_data.empty:
            return {}
        
        patterns = {}
        recent_cutoff = datetime.now() - timedelta(days=recent_days)
        
        # Filtrar actividad reciente
        recent_data = insider_data[insider_data['DaysAgo'] <= recent_days]
        
        # Agrupar por ticker
        for ticker in insider_data['Ticker'].unique():
            ticker_data = insider_data[insider_data['Ticker'] == ticker]
            ticker_recent = recent_data[recent_data['Ticker'] == ticker]
            
            total_trades = len(ticker_data)
            recent_trades = len(ticker_recent)
            
            buy_trades = len(ticker_data[
                ticker_data['Type'].str.contains('Purchase|Buy', case=False, na=False)
            ])
            recent_buys = len(ticker_recent[
                ticker_recent['Type'].str.contains('Purchase|Buy', case=False, na=False)
            ])
            
            total_value = ticker_data['ValueNumeric'].sum()
            recent_value = ticker_recent['ValueNumeric'].sum()
            
            exec_trades = len(ticker_data[
                ticker_data['InsiderTitle'].str.contains(
                    'CEO|CFO|President|Chairman|Director', case=False, na=False
                )
            ])
            
            patterns[ticker] = {
                'total_trades': total_trades,
                'recent_trades': recent_trades,
                'buy_ratio': buy_trades / max(total_trades, 1),
                'recent_buy_ratio': recent_buys / max(recent_trades, 1) if recent_trades > 0 else 0,
                'total_value': total_value,
                'recent_value': recent_value,
                'executive_trades': exec_trades,
                'activity_trend': 'INCREASING' if recent_trades > total_trades/4 else 'STABLE',
                'latest_activity_days': ticker_data['DaysAgo'].min()
            }
        
        return patterns
    
    def _create_sector_mapping(self, sector_data: pd.DataFrame) -> Dict[str, str]:
        """Crear mapeo dinámico de tickers a sectores"""
        mapping = {}
        
        if not sector_data.empty and 'Ticker' in sector_data.columns and 'Sector' in sector_data.columns:
            latest_sectors = sector_data.loc[
                sector_data.groupby('Ticker')['DaysAgo'].idxmin()
            ]
            
            for _, row in latest_sectors.iterrows():
                if pd.notna(row['Ticker']) and pd.notna(row['Sector']):
                    mapping[str(row['Ticker']).strip()] = str(row['Sector']).strip()
        
        return mapping
    
    def _perform_enhanced_cross_analysis(self, latest_sectors, insider_patterns, sector_mapping) -> pd.DataFrame:
        """Análisis cruzado mejorado"""
        # Agregar información de insider por sector
        sector_insider_activity = {}
        for ticker, trend in insider_patterns.items():
            sector = sector_mapping.get(ticker, 'Unknown')
            if sector not in sector_insider_activity:
                sector_insider_activity[sector] = {
                    'total_trades': 0,
                    'recent_trades': 0,
                    'total_value': 0,
                    'recent_value': 0,
                    'tickers_with_activity': set(),
                    'executive_activity': 0,
                    'increasing_activity': 0
                }
            
            activity = sector_insider_activity[sector]
            activity['total_trades'] += trend['total_trades']
            activity['recent_trades'] += trend['recent_trades']
            activity['total_value'] += trend['total_value']
            activity['recent_value'] += trend['recent_value']
            activity['tickers_with_activity'].add(ticker)
            activity['executive_activity'] += trend['executive_trades']
            
            if trend['activity_trend'] == 'INCREASING':
                activity['increasing_activity'] += 1
        
        # Crear análisis final con bonificaciones
        results = []
        for _, sector in latest_sectors.iterrows():
            sector_name = sector['Sector']
            base_score = sector['BaseScore']
            
            insider_activity = sector_insider_activity.get(sector_name, {})
            
            final_score = base_score
            signals = []
            urgency = 'BAJA'
            
            # Bonificaciones por actividad insider
            if insider_activity.get('recent_trades', 0) > 0:
                recent_bonus = min(insider_activity['recent_trades'] * 8, 30)
                final_score += recent_bonus
                signals.append(f"{insider_activity['recent_trades']} trades recientes")
                
                if len(insider_activity.get('tickers_with_activity', set())) > 1:
                    final_score += 15
                    signals.append('Múltiples empresas comprando')
                    urgency = 'MEDIA'
                
                if insider_activity.get('executive_activity', 0) > 0:
                    final_score += 12
                    signals.append('Actividad ejecutiva')
                    urgency = 'ALTA'
                
                if insider_activity.get('recent_value', 0) > 1_000_000:
                    final_score += 20
                    signals.append(f"${insider_activity['recent_value']/1_000_000:.1f}M volumen")
                    urgency = 'ALTA'
                
                if insider_activity.get('increasing_activity', 0) > 0:
                    final_score += 10
                    signals.append('Tendencia creciente')
            
            # Determinar urgencia final
            if final_score >= 85 and sector['DistanceFromMin'] < 15:
                urgency = 'CRÍTICA'
            elif final_score >= 75:
                urgency = 'ALTA'
            elif final_score >= 60:
                urgency = 'MEDIA'
            
            results.append({
                **sector.to_dict(),
                'BaseScore': base_score,
                'FinalScore': min(final_score, 100),
                'InsiderActivity': len(insider_activity) > 0,
                'InsiderTrades': insider_activity.get('recent_trades', 0),
                'InsiderValue': insider_activity.get('recent_value', 0),
                'Signals': signals,
                'Urgency': urgency,
                'RiskLevel': self._calculate_risk_level(sector, insider_activity)
            })
        
        results_df = pd.DataFrame(results)
        return results_df.sort_values('FinalScore', ascending=False)
    
    def _calculate_risk_level(self, sector, insider_activity) -> str:
        """Calcular nivel de riesgo"""
        risk_score = 0
        
        rsi = sector.get('RSI', 50)
        if rsi > 70:
            risk_score += 3
        elif rsi > 60:
            risk_score += 2
        elif rsi < 30:
            risk_score -= 1
        
        distance = sector.get('DistanceFromMin', 50)
        if distance > 40:
            risk_score += 2
        elif distance < 10:
            risk_score -= 1
        
        if insider_activity.get('recent_trades', 0) > 2:
            risk_score -= 2
        if insider_activity.get('executive_activity', 0) > 0:
            risk_score -= 1
        
        if risk_score <= 0:
            return 'BAJO'
        elif risk_score <= 2:
            return 'MEDIO'
        else:
            return 'ALTO'
    
    def _generate_enhanced_interpretations(self, opportunities: pd.DataFrame) -> Dict:
        """Generar interpretaciones automáticas MEJORADAS"""
        if opportunities.empty:
            return {}
        
        interpretations = {
            'market_overview': self._interpret_market_overview(opportunities),
            'top_opportunities_analysis': self._interpret_top_opportunities(opportunities),
            'insider_activity_analysis': self._interpret_insider_activity(opportunities),
            'risk_reward_analysis': self._interpret_risk_reward(opportunities),
            'sector_strength_analysis': self._interpret_sector_strengths(opportunities),
            'timing_analysis': self._interpret_timing_signals(opportunities)
        }
        
        return interpretations
    
    def _interpret_market_overview(self, opportunities: pd.DataFrame) -> Dict:
        """Interpretar panorama general del mercado"""
        total_sectors = len(opportunities)
        critical_count = len(opportunities[opportunities['Urgency'] == 'CRÍTICA'])
        high_urgency = len(opportunities[opportunities['Urgency'].isin(['CRÍTICA', 'ALTA'])])
        with_insider = len(opportunities[opportunities['InsiderActivity'] == True])
        avg_score = opportunities['FinalScore'].mean()
        
        # Interpretar el estado del mercado
        if critical_count >= 4:
            market_state = "EXCEPCIONAL"
            market_desc = f"Mercado en estado excepcional con {critical_count} oportunidades críticas detectadas"
        elif high_urgency >= 8:
            market_state = "FAVORABLE"
            market_desc = f"Mercado favorable con {high_urgency} oportunidades de alta calidad"
        elif avg_score >= 65:
            market_state = "NORMAL"
            market_desc = "Mercado en estado normal con oportunidades moderadas"
        else:
            market_state = "DESAFIANTE"
            market_desc = "Mercado desafiante con pocas oportunidades claras"
        
        return {
            'market_state': market_state,
            'description': market_desc,
            'total_sectors_analyzed': total_sectors,
            'critical_opportunities': critical_count,
            'high_quality_opportunities': high_urgency,
            'sectors_with_insider_activity': with_insider,
            'average_opportunity_score': round(avg_score, 1),
            'market_sentiment': 'BULLISH' if critical_count >= 3 else 'NEUTRAL' if high_urgency >= 5 else 'BEARISH'
        }
    
    def _interpret_top_opportunities(self, opportunities: pd.DataFrame) -> List[Dict]:
        """Interpretar las mejores oportunidades"""
        top_5 = opportunities.head(5)
        interpretations = []
        
        for _, opp in top_5.iterrows():
            # Calcular upside potential
            current_price = opp['CurrentPrice']
            max_52w = opp['Max52w']
            upside_to_max = ((max_52w - current_price) / current_price) * 100
            
            # Interpretar la oportunidad
            interpretation = {
                'sector': opp['Sector'],
                'ticker': opp['Ticker'],
                'final_score': opp['FinalScore'],
                'urgency': opp['Urgency'],
                'distance_from_min': round(opp['DistanceFromMin'], 1),
                'upside_to_max_52w': round(upside_to_max, 1),
                'current_price': current_price,
                'target_price_52w_max': max_52w,
                'insider_activity': opp['InsiderActivity'],
                'risk_level': opp['RiskLevel']
            }
            
            # Generar descripción interpretativa
            if opp['Urgency'] == 'CRÍTICA' and opp['DistanceFromMin'] < 10:
                interpretation['description'] = f"OPORTUNIDAD EXCEPCIONAL: {opp['Sector']} a solo {opp['DistanceFromMin']:.1f}% del mínimo con potencial upside de {upside_to_max:.1f}%"
                interpretation['recommendation'] = "COMPRA INMEDIATA"
            elif opp['InsiderActivity'] and opp['FinalScore'] >= 90:
                interpretation['description'] = f"SEÑAL INSIDER FUERTE: {opp['Sector']} con actividad insider reciente y score perfecto"
                interpretation['recommendation'] = "COMPRA PRIORITARIA"
            elif opp['FinalScore'] >= 80:
                interpretation['description'] = f"OPORTUNIDAD SÓLIDA: {opp['Sector']} con score alto y riesgo {opp['RiskLevel'].lower()}"
                interpretation['recommendation'] = "CONSIDERAR COMPRA"
            else:
                interpretation['description'] = f"OPORTUNIDAD MODERADA: {opp['Sector']} en seguimiento"
                interpretation['recommendation'] = "MONITOREAR"
            
            interpretations.append(interpretation)
        
        return interpretations
    
    def _interpret_insider_activity(self, opportunities: pd.DataFrame) -> Dict:
        """Interpretar actividad insider"""
        with_insider = opportunities[opportunities['InsiderActivity'] == True]
        
        if len(with_insider) == 0:
            return {
                'status': 'SIN_ACTIVIDAD',
                'description': 'No se detectó actividad insider significativa en los sectores analizados',
                'recommendation': 'Monitorear actividad insider en próximos días'
            }
        
        total_insider_volume = with_insider['InsiderValue'].sum()
        avg_insider_trades = with_insider['InsiderTrades'].mean()
        
        # Encontrar el sector con mayor actividad insider
        top_insider = with_insider.loc[with_insider['InsiderValue'].idxmax()]
        
        if len(with_insider) >= 3:
            status = 'ACTIVIDAD_ALTA'
            description = f"Alta actividad insider detectada en {len(with_insider)} sectores con volumen total de ${total_insider_volume/1_000_000:.1f}M"
        elif total_insider_volume > 2_000_000:
            status = 'VOLUMEN_ALTO'
            description = f"Volumen insider significativo de ${total_insider_volume/1_000_000:.1f}M concentrado en {len(with_insider)} sectores"
        else:
            status = 'ACTIVIDAD_MODERADA'
            description = f"Actividad insider moderada en {len(with_insider)} sectores"
        
        return {
            'status': status,
            'description': description,
            'sectors_with_activity': len(with_insider),
            'total_volume_millions': round(total_insider_volume / 1_000_000, 1),
            'average_trades_per_sector': round(avg_insider_trades, 1),
            'top_insider_sector': {
                'sector': top_insider['Sector'],
                'volume_millions': round(top_insider['InsiderValue'] / 1_000_000, 1),
                'trades': top_insider['InsiderTrades']
            },
            'recommendation': 'SEGUIMIENTO_PRIORITARIO' if status == 'ACTIVIDAD_ALTA' else 'MONITOREAR'
        }
    
    def _interpret_risk_reward(self, opportunities: pd.DataFrame) -> Dict:
        """Interpretar análisis riesgo-recompensa"""
        # Categorizar por riesgo
        low_risk = opportunities[opportunities['RiskLevel'] == 'BAJO']
        medium_risk = opportunities[opportunities['RiskLevel'] == 'MEDIO']
        high_risk = opportunities[opportunities['RiskLevel'] == 'ALTO']
        
        # Calcular métricas de upside
        opportunities_copy = opportunities.copy()
        opportunities_copy['UpsideToMax'] = ((opportunities_copy['Max52w'] - opportunities_copy['CurrentPrice']) / opportunities_copy['CurrentPrice']) * 100
        
        avg_upside_low_risk = opportunities_copy[opportunities_copy['RiskLevel'] == 'BAJO']['UpsideToMax'].mean()
        
        # Identificar las mejores relaciones riesgo-recompensa
        best_risk_reward = opportunities_copy[
            (opportunities_copy['RiskLevel'] == 'BAJO') & 
            (opportunities_copy['FinalScore'] >= 75)
        ].head(3)
        
        return {
            'risk_distribution': {
                'low_risk_count': len(low_risk),
                'medium_risk_count': len(medium_risk),
                'high_risk_count': len(high_risk)
            },
            'average_upside_low_risk': round(avg_upside_low_risk, 1) if not pd.isna(avg_upside_low_risk) else 0,
            'best_risk_reward_opportunities': [
                {
                    'sector': row['Sector'],
                    'score': row['FinalScore'],
                    'upside': round(row['UpsideToMax'], 1),
                    'risk': row['RiskLevel']
                }
                for _, row in best_risk_reward.iterrows()
            ],
            'recommendation': 'ENFOCARSE_BAJO_RIESGO' if len(low_risk) >= 5 else 'DIVERSIFICAR_RIESGO'
        }
    
    def _interpret_sector_strengths(self, opportunities: pd.DataFrame) -> List[Dict]:
        """Interpretar fortalezas sectoriales"""
        sector_analysis = []
        
        # Agrupar por sectores similares
        sector_groups = {
            'Healthcare': ['Healthcare', 'Healthcare Equipment', 'Pharmaceuticals'],
            'Technology': ['Technology', 'Software', 'Tech Hardware'],
            'Energy': ['Oil & Gas', 'Oil Producers', 'Energy'],
            'Consumer': ['Food & Beverage', 'Household Goods', 'Beverages', 'Food Producers'],
            'Financial': ['Banks', 'Financials', 'Insurance'],
            'Industrial': ['Industrial Transport', 'General Industrial', 'Support Services']
        }
        
        for group_name, sectors in sector_groups.items():
            group_opportunities = opportunities[opportunities['Sector'].isin(sectors)]
            
            if len(group_opportunities) > 0:
                avg_score = group_opportunities['FinalScore'].mean()
                critical_count = len(group_opportunities[group_opportunities['Urgency'] == 'CRÍTICA'])
                with_insider = len(group_opportunities[group_opportunities['InsiderActivity'] == True])
                
                # Determinar fortaleza del grupo
                if critical_count >= 2:
                    strength = 'MUY_FUERTE'
                elif avg_score >= 75:
                    strength = 'FUERTE'
                elif avg_score >= 60:
                    strength = 'MODERADO'
                else:
                    strength = 'DÉBIL'
                
                sector_analysis.append({
                    'sector_group': group_name,
                    'strength': strength,
                    'opportunities_count': len(group_opportunities),
                    'average_score': round(avg_score, 1),
                    'critical_opportunities': critical_count,
                    'insider_activity_count': with_insider,
                    'top_sector': group_opportunities.iloc[0]['Sector'] if len(group_opportunities) > 0 else None
                })
        
        return sorted(sector_analysis, key=lambda x: x['average_score'], reverse=True)
    
    def _interpret_timing_signals(self, opportunities: pd.DataFrame) -> Dict:
        """Interpretar señales de timing"""
        # Analizar distribución de RSI
        oversold = opportunities[opportunities['RSI'] < 30]
        neutral = opportunities[(opportunities['RSI'] >= 30) & (opportunities['RSI'] <= 70)]
        overbought = opportunities[opportunities['RSI'] > 70]
        
        # Analizar proximidad a mínimos
        very_close_to_min = opportunities[opportunities['DistanceFromMin'] < 10]
        close_to_min = opportunities[(opportunities['DistanceFromMin'] >= 10) & (opportunities['DistanceFromMin'] < 25)]
        
        # Determinar timing general del mercado
        if len(oversold) >= 3 and len(very_close_to_min) >= 3:
            timing_signal = 'EXCELENTE'
            timing_desc = 'Timing excepcional: múltiples sectores en sobreventa cerca de mínimos'
        elif len(oversold) >= 2 or len(very_close_to_min) >= 4:
            timing_signal = 'BUENO'
            timing_desc = 'Buen timing: varios sectores en zona de compra'
        elif len(overbought) >= 3:
            timing_signal = 'PRECAUCIÓN'
            timing_desc = 'Timing de precaución: varios sectores sobrecomprados'
        else:
            timing_signal = 'NEUTRAL'
            timing_desc = 'Timing neutral: mercado en zona equilibrada'
        
        return {
            'overall_timing': timing_signal,
            'description': timing_desc,
            'oversold_count': len(oversold),
            'very_close_to_min_count': len(very_close_to_min),
            'overbought_count': len(overbought),
            'recommendation': 'ACTUAR_AHORA' if timing_signal == 'EXCELENTE' else 'ESPERAR' if timing_signal == 'PRECAUCIÓN' else 'SELECTIVO'
        }
    
    def _generate_enhanced_summary(self, opportunities: pd.DataFrame) -> Dict:
        """Generar resumen mejorado"""
        if opportunities.empty:
            return {}
        
        return {
            'total_opportunities': len(opportunities),
            'critical_count': len(opportunities[opportunities['Urgency'] == 'CRÍTICA']),
            'high_urgency_count': len(opportunities[opportunities['Urgency'].isin(['CRÍTICA', 'ALTA'])]),
            'with_insider_activity': len(opportunities[opportunities['InsiderActivity'] == True]),
            'average_score': round(opportunities['FinalScore'].mean(), 1),
            'top_score': opportunities['FinalScore'].max(),
            'low_risk_opportunities': len(opportunities[opportunities['RiskLevel'] == 'BAJO']),
            'sectors_near_minimum': len(opportunities[opportunities['DistanceFromMin'] < 10]),
            'total_insider_volume_millions': round(opportunities['InsiderValue'].sum() / 1_000_000, 1)
        }
    
    def _detect_advanced_patterns(self, opportunities: pd.DataFrame) -> List[Dict]:
        """Detectar patrones avanzados"""
        patterns = []
        
        for _, opp in opportunities.iterrows():
            # Golden Cross Pattern
            if (opp['InsiderActivity'] and 
                opp['InsiderTrades'] >= 2 and 
                opp['DistanceFromMin'] < 12 and
                opp['Classification'] == 'OPORTUNIDAD'):
                patterns.append({
                    'type': 'GOLDEN_CROSS',
                    'sector': opp['Sector'],
                    'description': f'Patrón Golden Cross: Insider trading + cerca del mínimo ({opp["DistanceFromMin"]:.1f}%)',
                    'urgency': 'CRÍTICA',
                    'score': opp['FinalScore'],
                    'confidence': 'ALTA'
                })
            
            # Volume Explosion Pattern
            if opp['InsiderValue'] > 2_000_000 and opp['InsiderTrades'] >= 3:
                patterns.append({
                    'type': 'VOLUME_EXPLOSION',
                    'sector': opp['Sector'],
                    'description': f'Explosión de volumen: ${opp["InsiderValue"]/1_000_000:.1f}M con {opp["InsiderTrades"]} trades',
                    'urgency': 'ALTA',
                    'score': opp['FinalScore'],
                    'confidence': 'ALTA'
                })
            
            # Oversold Insider Rally Pattern
            if (opp['RSI'] < 35 and 
                opp['InsiderTrades'] > 0 and 
                'Actividad ejecutiva' in str(opp['Signals'])):
                patterns.append({
                    'type': 'OVERSOLD_INSIDER_RALLY',
                    'sector': opp['Sector'],
                    'description': f'Rally desde sobreventa: RSI {opp["RSI"]:.1f} + ejecutivos comprando',
                    'urgency': 'ALTA',
                    'score': opp['FinalScore'],
                    'confidence': 'MEDIA'
                })
        
        return sorted(patterns, key=lambda x: x['score'], reverse=True)
    
    def _generate_strategic_recommendations(self, opportunities: pd.DataFrame) -> Dict:
        """Generar recomendaciones estratégicas"""
        if opportunities.empty:
            return {}
        
        top_10 = opportunities.head(10)
        
        # Estrategias por plazo
        short_term = top_10[
            (top_10['Urgency'].isin(['CRÍTICA', 'ALTA'])) &
            (top_10['InsiderActivity'] == True)
        ].head(3)
        
        medium_term = top_10[
            (top_10['RiskLevel'] == 'BAJO') &
            (top_10['DistanceFromMin'] < 15)
        ].head(5)
        
        long_term = top_10[top_10['Classification'] == 'OPORTUNIDAD'].head(5)
        
        return {
            'short_term_strategy': {
                'timeframe': '1-3 meses',
                'focus': 'Aprovechar actividad insider y momentum',
                'recommended_sectors': short_term['Sector'].tolist(),
                'allocation_suggestion': '30-40% del capital disponible'
            },
            'medium_term_strategy': {
                'timeframe': '3-12 meses',
                'focus': 'Sectores defensivos cerca de mínimos',
                'recommended_sectors': medium_term['Sector'].tolist(),
                'allocation_suggestion': '40-50% del capital disponible'
            },
            'long_term_strategy': {
                'timeframe': '12+ meses',
                'focus': 'Sectores fundamentalmente sólidos',
                'recommended_sectors': long_term['Sector'].tolist(),
                'allocation_suggestion': '20-30% del capital disponible'
            }
        }
    
    def _analyze_risk_distribution(self, opportunities: pd.DataFrame) -> Dict:
        """Analizar distribución de riesgo"""
        risk_dist = opportunities['RiskLevel'].value_counts().to_dict()
        
        return {
            'distribution': risk_dist,
            'low_risk_percentage': round((risk_dist.get('BAJO', 0) / len(opportunities)) * 100, 1),
            'concentration_risk': 'ALTO' if len(opportunities[:5]['Sector'].unique()) < 4 else 'BAJO',
            'diversification_recommendation': 'Diversificar entre sectores' if len(opportunities[:10]['Sector'].unique()) < 6 else 'Buena diversificación disponible'
        }
    
    def _calculate_upside_potentials(self, opportunities: pd.DataFrame) -> List[Dict]:
        """Calcular potenciales de upside"""
        upside_analysis = []
        
        for _, opp in opportunities.head(10).iterrows():
            current_price = opp['CurrentPrice']
            max_52w = opp['Max52w']
            min_52w = opp['Min52w']
            
            upside_to_max = ((max_52w - current_price) / current_price) * 100
            upside_to_avg = ((((max_52w + min_52w) / 2) - current_price) / current_price) * 100
            
            upside_analysis.append({
                'sector': opp['Sector'],
                'current_price': current_price,
                'upside_to_52w_max_percent': round(upside_to_max, 1),
                'upside_to_52w_avg_percent': round(upside_to_avg, 1),
                'target_price_max': max_52w,
                'target_price_avg': round((max_52w + min_52w) / 2, 2),
                'risk_adjusted_upside': round(upside_to_max * (1 if opp['RiskLevel'] == 'BAJO' else 0.7 if opp['RiskLevel'] == 'MEDIO' else 0.5), 1)
            })
        
        return upside_analysis
    
    def _analyze_sector_correlations(self, opportunities: pd.DataFrame) -> Dict:
        """Analizar correlaciones sectoriales"""
        # Análisis simplificado de correlaciones
        sectors_by_group = {}
        
        for _, opp in opportunities.iterrows():
            sector = opp['Sector']
            
            # Clasificar por grupos
            if any(word in sector.lower() for word in ['healthcare', 'pharmaceutical', 'health']):
                group = 'Healthcare'
            elif any(word in sector.lower() for word in ['technology', 'software', 'tech']):
                group = 'Technology'
            elif any(word in sector.lower() for word in ['oil', 'gas', 'energy']):
                group = 'Energy'
            elif any(word in sector.lower() for word in ['food', 'beverage', 'household']):
                group = 'Consumer'
            elif any(word in sector.lower() for word in ['bank', 'financial', 'insurance']):
                group = 'Financial'
            else:
                group = 'Other'
            
            if group not in sectors_by_group:
                sectors_by_group[group] = []
            sectors_by_group[group].append(opp['FinalScore'])
        
        # Calcular scores promedio por grupo
        group_scores = {
            group: round(np.mean(scores), 1) 
            for group, scores in sectors_by_group.items()
        }
        
        return {
            'sector_groups': {k: len(v) for k, v in sectors_by_group.items()},
            'group_average_scores': group_scores,
            'strongest_sector_group': max(group_scores.items(), key=lambda x: x[1])[0] if group_scores else None,
            'diversification_available': len(group_scores) >= 4
        }
    
    def _generate_trading_alerts(self, opportunities: pd.DataFrame) -> List[Dict]:
        """Generar alertas de trading"""
        alerts = []
        
        # Alertas críticas
        critical_opps = opportunities[opportunities['Urgency'] == 'CRÍTICA']
        for _, opp in critical_opps.iterrows():
            alerts.append({
                'type': 'CRITICAL_OPPORTUNITY',
                'sector': opp['Sector'],
                'message': f"Oportunidad crítica: {opp['Sector']} a {opp['DistanceFromMin']:.1f}% del mínimo",
                'action': 'COMPRAR_INMEDIATAMENTE',
                'score': opp['FinalScore'],
                'urgency': 'CRÍTICA'
            })
        
        # Alertas de insider
        insider_opps = opportunities[(opportunities['InsiderActivity'] == True) & (opportunities['InsiderValue'] > 1_000_000)]
        for _, opp in insider_opps.iterrows():
            alerts.append({
                'type': 'INSIDER_ACTIVITY',
                'sector': opp['Sector'],
                'message': f"Actividad insider significativa: ${opp['InsiderValue']/1_000_000:.1f}M en {opp['Sector']}",
                'action': 'MONITOREAR_PROXIMAMENTE',
                'score': opp['FinalScore'],
                'urgency': 'ALTA'
            })
        
        # Alertas de timing
        oversold_opps = opportunities[(opportunities['RSI'] < 30) & (opportunities['FinalScore'] >= 70)]
        for _, opp in oversold_opps.iterrows():
            alerts.append({
                'type': 'OVERSOLD_OPPORTUNITY',
                'sector': opp['Sector'],
                'message': f"Sobreventa extrema: {opp['Sector']} con RSI {opp['RSI']:.1f}",
                'action': 'CONSIDERAR_ENTRADA',
                'score': opp['FinalScore'],
                'urgency': 'MEDIA'
            })
        
        return sorted(alerts, key=lambda x: x['score'], reverse=True)
    
    def generate_enhanced_html_report(self, analysis_results: Dict) -> str:
        """Generar reporte HTML mejorado con todas las interpretaciones"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if 'error' in analysis_results:
            return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Error en Análisis</title></head>
<body><h1>Error: {analysis_results['error']}</h1></body></html>"""
        
        enhanced_analysis = analysis_results.get('enhanced_analysis', {})
        opportunities = analysis_results.get('opportunities', [])
        summary = analysis_results.get('summary', {})
        patterns = analysis_results.get('special_patterns', [])
        strategic_recs = analysis_results.get('strategic_recommendations', {})
        upside_calcs = analysis_results.get('upside_calculations', [])
        trading_alerts = analysis_results.get('trading_alerts', [])
        
        # Generar HTML moderno
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Enhanced Trading Opportunities Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0c1426 0%, #1a202c 100%);
            color: #ffffff;
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .header h1 {{
            font-size: 3rem;
            background: linear-gradient(45deg, #4f9cf9, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .timestamp {{
            color: #a0aec0;
            font-size: 1.1rem;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }}
        
        .card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(79, 156, 249, 0.1);
        }}
        
        .card h3 {{
            color: #4f9cf9;
            margin-bottom: 15px;
            font-size: 1.3rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stat {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .stat:last-child {{
            border-bottom: none;
        }}
        
        .stat-value {{
            font-weight: bold;
            color: #00d4ff;
        }}
        
        .opportunities-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 15px;
            overflow: hidden;
        }}
        
        .opportunities-table th,
        .opportunities-table td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .opportunities-table th {{
            background: rgba(79, 156, 249, 0.2);
            font-weight: 600;
            color: #4f9cf9;
        }}
        
        .opportunities-table tr:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .urgency-crítica {{
            background: linear-gradient(45deg, #ff4757, #ff6b7a);
            color: white;
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .urgency-alta {{
            background: linear-gradient(45deg, #ffa726, #ffcc02);
            color: white;
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .urgency-media {{
            background: linear-gradient(45deg, #26c6da, #00acc1);
            color: white;
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .risk-bajo {{
            color: #4caf50;
            font-weight: bold;
        }}
        
        .risk-medio {{
            color: #ff9800;
            font-weight: bold;
        }}
        
        .risk-alto {{
            color: #f44336;
            font-weight: bold;
        }}
        
        .alert {{
            background: linear-gradient(45deg, #ff4757, #ff6b7a);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #ff4757;
        }}
        
        .pattern {{
            background: linear-gradient(45deg, #4f9cf9, #00d4ff);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            color: #0c1426;
            font-weight: bold;
        }}
        
        .interpretation {{
            background: rgba(255, 255, 255, 0.03);
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid #4f9cf9;
        }}
        
        .upside-positive {{
            color: #4caf50;
            font-weight: bold;
        }}
        
        .section {{
            margin: 40px 0;
        }}
        
        .section h2 {{
            color: #4f9cf9;
            margin-bottom: 20px;
            font-size: 2rem;
            border-bottom: 2px solid #4f9cf9;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Enhanced Trading Opportunities Dashboard</h1>
            <div class="timestamp">📅 Generado: {timestamp}</div>
        </div>"""
        
        # Resumen ejecutivo
        market_overview = enhanced_analysis.get('market_overview', {})
        if market_overview:
            html_content += f"""
        <div class="section">
            <h2>🎯 Resumen Ejecutivo</h2>
            <div class="grid">
                <div class="card">
                    <h3>📊 Estado del Mercado</h3>
                    <div class="stat">
                        <span>Estado General:</span>
                        <span class="stat-value">{market_overview.get('market_state', 'N/A')}</span>
                    </div>
                    <div class="stat">
                        <span>Sentimiento:</span>
                        <span class="stat-value">{market_overview.get('market_sentiment', 'N/A')}</span>
                    </div>
                    <div class="interpretation">
                        {market_overview.get('description', 'No disponible')}
                    </div>
                </div>
                
                <div class="card">
                    <h3>📈 Estadísticas Clave</h3>
                    <div class="stat">
                        <span>Total Oportunidades:</span>
                        <span class="stat-value">{summary.get('total_opportunities', 0)}</span>
                    </div>
                    <div class="stat">
                        <span>Críticas:</span>
                        <span class="stat-value">{summary.get('critical_count', 0)}</span>
                    </div>
                    <div class="stat">
                        <span>Alta Urgencia:</span>
                        <span class="stat-value">{summary.get('high_urgency_count', 0)}</span>
                    </div>
                    <div class="stat">
                        <span>Con Insider Activity:</span>
                        <span class="stat-value">{summary.get('with_insider_activity', 0)}</span>
                    </div>
                    <div class="stat">
                        <span>Score Promedio:</span>
                        <span class="stat-value">{summary.get('average_score', 0)}/100</span>
                    </div>
                </div>
            </div>
        </div>"""
        
        # Top opportunities con interpretaciones
        top_opportunities = enhanced_analysis.get('top_opportunities_analysis', [])
        if top_opportunities:
            html_content += f"""
        <div class="section">
            <h2>🏆 Top Oportunidades Analizadas</h2>"""
            
            for i, opp in enumerate(top_opportunities[:5]):
                urgency_class = f"urgency-{opp['urgency'].lower()}"
                risk_class = f"risk-{opp['risk_level'].lower()}"
                
                html_content += f"""
            <div class="card">
                <h3>#{i+1} {opp['sector']} ({opp['ticker']})</h3>
                <div class="grid" style="grid-template-columns: 1fr 1fr;">
                    <div>
                        <div class="stat">
                            <span>Score Final:</span>
                            <span class="stat-value">{opp['final_score']}/100</span>
                        </div>
                        <div class="stat">
                            <span>Precio Actual:</span>
                            <span class="stat-value">${opp['current_price']:.2f}</span>
                        </div>
                        <div class="stat">
                            <span>Dist. del Mínimo:</span>
                            <span class="stat-value">{opp['distance_from_min']}%</span>
                        </div>
                    </div>
                    <div>
                        <div class="stat">
                            <span>Upside Potencial:</span>
                            <span class="stat-value upside-positive">+{opp['upside_to_max_52w']:.1f}%</span>
                        </div>
                        <div class="stat">
                            <span>Urgencia:</span>
                            <span class="{urgency_class}">{opp['urgency']}</span>
                        </div>
                        <div class="stat">
                            <span>Riesgo:</span>
                            <span class="{risk_class}">{opp['risk_level']}</span>
                        </div>
                    </div>
                </div>
                <div class="interpretation">
                    <strong>{opp['recommendation']}</strong><br>
                    {opp['description']}
                </div>
            </div>"""
            
            html_content += "</div>"
        
        # Tabla de todas las oportunidades
        if opportunities:
            html_content += f"""
        <div class="section">
            <h2>📋 Todas las Oportunidades</h2>
            <div style="overflow-x: auto;">
                <table class="opportunities-table">
                    <thead>
                        <tr>
                            <th>Sector</th>
                            <th>Score</th>
                            <th>Precio</th>
                            <th>Dist. Min %</th>
                            <th>RSI</th>
                            <th>Urgencia</th>
                            <th>Riesgo</th>
                            <th>Insider</th>
                        </tr>
                    </thead>
                    <tbody>"""
            
            for opp in opportunities[:15]:
                urgency_class = f"urgency-{opp.get('Urgency', '').lower()}"
                risk_class = f"risk-{opp.get('RiskLevel', '').lower()}"
                insider_icon = "✅" if opp.get('InsiderActivity', False) else "❌"
                
                html_content += f"""
                        <tr>
                            <td><strong>{opp.get('Sector', 'N/A')}</strong></td>
                            <td><strong>{opp.get('FinalScore', 0)}</strong></td>
                            <td>${opp.get('CurrentPrice', 0):.2f}</td>
                            <td>{opp.get('DistanceFromMin', 0):.1f}%</td>
                            <td>{opp.get('RSI', 0):.1f}</td>
                            <td><span class="{urgency_class}">{opp.get('Urgency', 'N/A')}</span></td>
                            <td><span class="{risk_class}">{opp.get('RiskLevel', 'N/A')}</span></td>
                            <td>{insider_icon}</td>
                        </tr>"""
            
            html_content += """
                    </tbody>
                </table>
            </div>
        </div>"""
        
        # Patrones especiales
        if patterns:
            html_content += f"""
        <div class="section">
            <h2>🚨 Patrones Especiales Detectados</h2>"""
            
            for pattern in patterns[:5]:
                html_content += f"""
            <div class="pattern">
                <strong>{pattern['type']}: {pattern['sector']}</strong><br>
                {pattern['description']} | Urgencia: {pattern['urgency']} | Score: {pattern['score']}
            </div>"""
            
            html_content += "</div>"
        
        # Alertas de trading
        if trading_alerts:
            html_content += f"""
        <div class="section">
            <h2>⚠️ Alertas de Trading</h2>"""
            
            for alert in trading_alerts[:8]:
                html_content += f"""
            <div class="alert">
                <strong>{alert['type']}: {alert['sector']}</strong><br>
                {alert['message']}<br>
                <strong>Acción recomendada: {alert['action']}</strong>
            </div>"""
            
            html_content += "</div>"
        
        # Footer
        html_content += f"""
        <div class="section">
            <div class="card" style="text-align: center;">
                <h3>🎯 Enhanced Trading Opportunities System</h3>
                <p>Análisis generado automáticamente con interpretaciones avanzadas</p>
                <p>Timestamp: {timestamp}</p>
                <p style="color: #a0aec0; font-size: 0.9rem;">
                    ⚠️ Este análisis es solo para fines informativos. No constituye asesoramiento financiero.
                </p>
            </div>
        </div>
        
    </div>
</body>
</html>"""
        
        return html_content
    
    def save_enhanced_analysis(self, analysis_results: Dict, base_filename: str = "enhanced_trading_analysis") -> Tuple[str, str]:
        """Guardar análisis mejorado en CSV y HTML"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Guardar CSV
        csv_filename = f"reports/{base_filename}_{timestamp}.csv"
        if 'opportunities' in analysis_results:
            df = pd.DataFrame(analysis_results['opportunities'])
            os.makedirs('reports', exist_ok=True)
            df.to_csv(csv_filename, index=False)
        
        # Guardar HTML
        html_filename = f"reports/{base_filename}_{timestamp}.html"
        html_content = self.generate_enhanced_html_report(analysis_results)
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Guardar JSON completo
        json_filename = f"reports/{base_filename}_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ Análisis guardado:")
        print(f"   📄 CSV: {csv_filename}")
        print(f"   🌐 HTML: {html_filename}")
        print(f"   📋 JSON: {json_filename}")
        
        return html_filename, csv_filename
    
    def run_enhanced_analysis(self, recent_days: int = 14) -> Dict:
        """Ejecutar análisis completo mejorado"""
        print("🚀 INICIANDO ANÁLISIS MEJORADO DE OPORTUNIDADES")
        print("=" * 60)
        
        try:
            # Realizar análisis
            analysis_results = self.analyze_enhanced_opportunities(recent_days)
            
            if 'error' in analysis_results:
                print(f"❌ Error en análisis: {analysis_results['error']}")
                return analysis_results
            
            # Mostrar resumen en consola
            summary = analysis_results.get('summary', {})
            enhanced_analysis = analysis_results.get('enhanced_analysis', {})
            
            print(f"\n📊 RESUMEN DEL ANÁLISIS:")
            print(f"   🎯 Total oportunidades: {summary.get('total_opportunities', 0)}")
            print(f"   🚨 Oportunidades críticas: {summary.get('critical_count', 0)}")
            print(f"   ⚠️ Alta urgencia: {summary.get('high_urgency_count', 0)}")
            print(f"   👥 Con actividad insider: {summary.get('with_insider_activity', 0)}")
            print(f"   ⭐ Score promedio: {summary.get('average_score', 0)}/100")
            
            # Mostrar estado del mercado
            market_overview = enhanced_analysis.get('market_overview', {})
            if market_overview:
                print(f"\n🎯 ESTADO DEL MERCADO: {market_overview.get('market_state', 'N/A')}")
                print(f"   📈 Sentimiento: {market_overview.get('market_sentiment', 'N/A')}")
                print(f"   📝 {market_overview.get('description', 'No disponible')}")
            
            # Mostrar top 3 oportunidades
            top_opportunities = enhanced_analysis.get('top_opportunities_analysis', [])
            if top_opportunities:
                print(f"\n🏆 TOP 3 OPORTUNIDADES:")
                for i, opp in enumerate(top_opportunities[:3]):
                    print(f"   {i+1}. {opp['sector']} - Score: {opp['final_score']} - {opp['recommendation']}")
                    print(f"      💰 Upside: +{opp['upside_to_max_52w']:.1f}% | Riesgo: {opp['risk_level']}")
            
            # Guardar archivos
            html_path, csv_path = self.save_enhanced_analysis(analysis_results)
            analysis_results['html_path'] = html_path
            analysis_results['csv_path'] = csv_path
            
            print(f"\n✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
            return analysis_results
            
        except Exception as e:
            print(f"❌ Error en análisis mejorado: {e}")
            traceback.print_exc()
            return {'error': str(e)}


# EJEMPLO DE USO STANDALONE
if __name__ == "__main__":
    analyzer = EnhancedTradingOpportunityAnalyzer(".")
    results = analyzer.run_enhanced_analysis(recent_days=14)
    
    if 'error' not in results:
        print("\n🎉 Análisis completado. Revisa los archivos generados.")
    else:
        print(f"\n❌ Error: {results['error']}")
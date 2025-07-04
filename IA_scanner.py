import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import os
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

class AdvancedTradingScanner:
    """
    Escáner avanzado de oportunidades de trading que:
    - Recorre automáticamente directorios de datos históricos
    - Analiza tendencias temporales de insider trading
    - Detecta patrones cross-sectoriales evolutivos
    - Se integra en sistemas mayores con estructura dinámica de carpetas
    - MEJORADO: Mapeo robusto de tickers individuales a sectores DJ
    """
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.insider_data_history = {}  # {fecha: DataFrame}
        self.sector_data_history = {}   # {fecha: DataFrame}
        self.consolidated_insider = pd.DataFrame()
        self.consolidated_sector = pd.DataFrame()
        self.analysis_results = {}
        
        # NUEVO: Mapeo comprehensivo de tickers a sectores DJ
        self.comprehensive_ticker_mapping = {
            # TECHNOLOGY (DJUSTC)
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
            'AMZN': 'Technology', 'META': 'Technology', 'NVDA': 'Technology', 'TSLA': 'Technology',
            'NFLX': 'Technology', 'CRM': 'Technology', 'ORCL': 'Technology', 'ADBE': 'Technology',
            'INTC': 'Technology', 'AMD': 'Technology', 'QCOM': 'Technology', 'AVGO': 'Technology',
            'TXN': 'Technology', 'IBM': 'Technology', 'CSCO': 'Technology', 'NOW': 'Technology',
            'SNOW': 'Technology', 'PLTR': 'Technology', 'COIN': 'Technology', 'RBLX': 'Technology',
            'SHOP': 'Technology', 'SQ': 'Technology', 'BLOCK': 'Technology', 'ZM': 'Technology',
            'DOCU': 'Technology', 'TEAM': 'Technology', 'OKTA': 'Technology', 'TWLO': 'Technology',
            
            # BANKS (DJUSBK)
            'JPM': 'Banks', 'BAC': 'Banks', 'WFC': 'Banks', 'C': 'Banks', 'GS': 'Banks',
            'MS': 'Banks', 'USB': 'Banks', 'PNC': 'Banks', 'TFC': 'Banks', 'COF': 'Banks',
            'BK': 'Banks', 'STT': 'Banks', 'SCHW': 'Banks', 'AXP': 'Banks', 'MA': 'Banks',
            'V': 'Banks', 'PYPL': 'Banks', 'DFS': 'Banks', 'SYF': 'Banks', 'ALLY': 'Banks',
            'FITB': 'Banks', 'HBAN': 'Banks', 'RF': 'Banks', 'KEY': 'Banks', 'CFG': 'Banks',
            
            # HEALTHCARE (DJUSHC)
            'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare', 'ABBV': 'Healthcare',
            'TMO': 'Healthcare', 'ABT': 'Healthcare', 'DHR': 'Healthcare', 'BMY': 'Healthcare',
            'LLY': 'Healthcare', 'MDT': 'Healthcare', 'GILD': 'Healthcare', 'AMGN': 'Healthcare',
            'CVS': 'Healthcare', 'CI': 'Healthcare', 'HUM': 'Healthcare', 'ANTM': 'Healthcare',
            'ELV': 'Healthcare', 'CNC': 'Healthcare', 'MOH': 'Healthcare', 'HCA': 'Healthcare',
            'ISRG': 'Healthcare', 'SYK': 'Healthcare', 'EW': 'Healthcare', 'ZBH': 'Healthcare',
            'MRNA': 'Healthcare', 'BNTX': 'Healthcare', 'VRTX': 'Healthcare', 'REGN': 'Healthcare',
            
            # OIL & GAS (DJUSEN)
            'XOM': 'Oil & Gas', 'CVX': 'Oil & Gas', 'COP': 'Oil & Gas', 'SLB': 'Oil & Gas',
            'EOG': 'Oil & Gas', 'PSX': 'Oil & Gas', 'VLO': 'Oil & Gas', 'MPC': 'Oil & Gas',
            'KMI': 'Oil & Gas', 'OKE': 'Oil & Gas', 'WMB': 'Oil & Gas', 'EPD': 'Oil & Gas',
            'ET': 'Oil & Gas', 'MPLX': 'Oil & Gas', 'DVN': 'Oil & Gas', 'FANG': 'Oil & Gas',
            'MRO': 'Oil & Gas', 'APA': 'Oil & Gas', 'HAL': 'Oil & Gas', 'BKR': 'Oil & Gas',
            'OXY': 'Oil & Gas', 'PXD': 'Oil & Gas', 'CTRA': 'Oil & Gas', 'EQT': 'Oil & Gas',
            
            # REAL ESTATE (DJUSRE)
            'AMT': 'Real Estate', 'CCI': 'Real Estate', 'EQIX': 'Real Estate', 'PLD': 'Real Estate',
            'SPG': 'Real Estate', 'EXR': 'Real Estate', 'AVB': 'Real Estate', 'EQR': 'Real Estate',
            'WELL': 'Real Estate', 'DLR': 'Real Estate', 'PSA': 'Real Estate', 'O': 'Real Estate',
            'SBAC': 'Real Estate', 'VTR': 'Real Estate', 'ESS': 'Real Estate', 'MAA': 'Real Estate',
            'AIV': 'Real Estate', 'BXP': 'Real Estate', 'HST': 'Real Estate', 'KIM': 'Real Estate',
            
            # RETAIL (DJUSRT)
            'WMT': 'Retail', 'HD': 'Retail', 'COST': 'Retail', 'LOW': 'Retail', 'TGT': 'Retail',
            'TJX': 'Retail', 'SBUX': 'Retail', 'NKE': 'Retail', 'MCD': 'Retail', 'BKNG': 'Retail',
            'EBAY': 'Retail', 'ETSY': 'Retail', 'W': 'Retail', 'RH': 'Retail', 'BBY': 'Retail',
            'DG': 'Retail', 'DLTR': 'Retail', 'ROST': 'Retail', 'GPS': 'Retail', 'ANF': 'Retail',
            
            # UTILITIES (DJUSUT)
            'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities', 'D': 'Utilities',
            'EXC': 'Utilities', 'XEL': 'Utilities', 'SRE': 'Utilities', 'PEG': 'Utilities',
            'AWK': 'Utilities', 'AEP': 'Utilities', 'ED': 'Utilities', 'ES': 'Utilities',
            'PPL': 'Utilities', 'FE': 'Utilities', 'ETR': 'Utilities', 'CNP': 'Utilities',
            
            # CHEMICALS (DJUSCH)
            'LIN': 'Chemicals', 'APD': 'Chemicals', 'DD': 'Chemicals', 'DOW': 'Chemicals',
            'ECL': 'Chemicals', 'EMN': 'Chemicals', 'LYB': 'Chemicals', 'CF': 'Chemicals',
            'FMC': 'Chemicals', 'ALB': 'Chemicals', 'CE': 'Chemicals', 'PPG': 'Chemicals',
            'SHW': 'Chemicals', 'IFF': 'Chemicals', 'RPM': 'Chemicals', 'FCX': 'Chemicals',
            
            # INDUSTRIAL GOODS (DJUSIG)
            'BA': 'Industrial Goods', 'CAT': 'Industrial Goods', 'DE': 'Industrial Goods',
            'HON': 'Industrial Goods', 'GE': 'Industrial Goods', 'MMM': 'Industrial Goods',
            'RTX': 'Industrial Goods', 'LMT': 'Industrial Goods', 'NOC': 'Industrial Goods',
            'GD': 'Industrial Goods', 'UPS': 'Industrial Goods', 'FDX': 'Industrial Goods',
            'CSX': 'Industrial Goods', 'UNP': 'Industrial Goods', 'NSC': 'Industrial Goods',
            
            # MEDIA (DJUSME)
            'DIS': 'Media', 'CMCSA': 'Media', 'NFLX': 'Media', 'T': 'Media', 'VZ': 'Media',
            'CHTR': 'Media', 'TMUS': 'Media', 'WBD': 'Media', 'PARA': 'Media', 'FOX': 'Media',
            
            # FOOD & BEVERAGE (DJUSFB)
            'PEP': 'Food & Beverage', 'KO': 'Food & Beverage', 'PG': 'Food & Beverage',
            'UL': 'Food & Beverage', 'MDLZ': 'Food & Beverage', 'GIS': 'Food & Beverage',
            'K': 'Food & Beverage', 'CPB': 'Food & Beverage', 'CAG': 'Food & Beverage',
            'TSN': 'Food & Beverage', 'KR': 'Food & Beverage', 'WBA': 'Food & Beverage',
            'CL': 'Food & Beverage', 'KMB': 'Food & Beverage', 'CHD': 'Food & Beverage',
            
            # AUTOMOBILES & PARTS (DJUSAP)
            'TSLA': 'Auto & Parts', 'F': 'Auto & Parts', 'GM': 'Auto & Parts',
            'RIVN': 'Auto & Parts', 'LCID': 'Auto & Parts', 'NIO': 'Auto & Parts',
            'XPEV': 'Auto & Parts', 'LI': 'Auto & Parts', 'APTV': 'Auto & Parts',
            
            # TELECOMMUNICATIONS (DJUSTL)
            'VZ': 'Telecommunications', 'T': 'Telecommunications', 'TMUS': 'Telecommunications',
            'CHTR': 'Telecommunications', 'CMCSA': 'Telecommunications',
            
            # BASIC RESOURCES (DJUSBS)
            'BHP': 'Basic Resources', 'RIO': 'Basic Resources', 'FCX': 'Basic Resources',
            'NEM': 'Basic Resources', 'GOLD': 'Basic Resources', 'AA': 'Basic Resources',
            
            # CONSTRUCTION & MATERIALS (DJUSCN)
            'CAT': 'Construction', 'VMC': 'Construction', 'MLM': 'Construction',
            'NUE': 'Construction', 'STLD': 'Construction', 'X': 'Construction',
            
            # AEROSPACE (DJUSAS)
            'BA': 'Aerospace', 'LMT': 'Aerospace', 'RTX': 'Aerospace', 'NOC': 'Aerospace',
            'GD': 'Aerospace', 'TXT': 'Aerospace', 'HWM': 'Aerospace',
            
            # AIRLINES (DJUSAR)
            'DAL': 'Airlines', 'AAL': 'Airlines', 'UAL': 'Airlines', 'LUV': 'Airlines',
            'JBLU': 'Airlines', 'ALK': 'Airlines', 'SAVE': 'Airlines',
            
            # INSURANCE (DJUSIX)
            'BRK.A': 'Insurance', 'BRK.B': 'Insurance', 'PGR': 'Insurance', 'TRV': 'Insurance',
            'AIG': 'Insurance', 'MET': 'Insurance', 'PRU': 'Insurance', 'ALL': 'Insurance',
            
            # SOFTWARE (DJUSSV)
            'MSFT': 'Software', 'ORCL': 'Software', 'CRM': 'Software', 'ADBE': 'Software',
            'NOW': 'Software', 'SNOW': 'Software', 'PLTR': 'Software', 'TEAM': 'Software',
            
            # PERSONAL GOODS (DJUSPG)
            'NKE': 'Personal Goods', 'LULU': 'Personal Goods', 'ADDYY': 'Personal Goods',
            'UAA': 'Personal Goods', 'CROX': 'Personal Goods', 'DECK': 'Personal Goods',
        }
        
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
        
        print(f"📄 Encontrados {len(insider_files)} archivos insider en reports/report_*/")
        
        # PATRÓN ESPECÍFICO 2: dj_sectorial/dj_sectorial_YYYY-MM-DD/data.csv (DATOS SECTORIALES)
        sector_patterns = [
            'dj_sectorial/dj_sectorial_*/data.csv',
            'dj_sectorial_*/data.csv',
            'dj_sectorial/*/data.csv'
        ]
        
        sector_files_found = []
        for pattern in sector_patterns:
            sector_files = list(self.base_path.glob(pattern))
            sector_files_found.extend(sector_files)
            
            for file_path in sector_files:
                if str(file_path) not in structure['sector_files']:  # Evitar duplicados
                    structure['sector_files'].append(str(file_path))
                    structure['sector_dirs'].append(str(file_path.parent))
        
        print(f"📄 Encontrados {len(sector_files_found)} archivos sectoriales")
        
        # PATRÓN FALLBACK: Buscar cualquier data.csv en subdirectorios
        if len(structure['insider_files']) == 0 and len(structure['sector_files']) == 0:
            print("⚠️  No se encontraron archivos con patrones específicos, buscando data.csv genéricos...")
            
            all_data_csvs = list(self.base_path.glob('**/data.csv'))
            
            for file_path in all_data_csvs:
                # Intentar clasificar por nombre de directorio padre
                parent_name = file_path.parent.name.lower()
                
                if 'report' in parent_name or 'insider' in parent_name:
                    structure['insider_files'].append(str(file_path))
                    structure['insider_dirs'].append(str(file_path.parent))
                elif 'sectorial' in parent_name or 'sector' in parent_name:
                    structure['sector_files'].append(str(file_path))
                    structure['sector_dirs'].append(str(file_path.parent))
                else:
                    # Si no está claro, agregar a ambos para análisis posterior
                    print(f"🤔 Archivo ambiguo encontrado: {file_path}")
        
        # DEBUGGING: Mostrar archivos encontrados
        if structure['insider_files']:
            print(f"\n📊 ARCHIVOS INSIDER ENCONTRADOS:")
            for file_path in structure['insider_files'][:5]:  # Mostrar solo primeros 5
                print(f"   📄 {file_path}")
            if len(structure['insider_files']) > 5:
                print(f"   ... y {len(structure['insider_files']) - 5} más")
        
        if structure['sector_files']:
            print(f"\n📊 ARCHIVOS SECTORIALES ENCONTRADOS:")
            for file_path in structure['sector_files'][:5]:
                print(f"   📄 {file_path}")
            if len(structure['sector_files']) > 5:
                print(f"   ... y {len(structure['sector_files']) - 5} más")
        
        # RESUMEN
        structure['insider_dirs'] = list(set(structure['insider_dirs']))  # Remover duplicados
        structure['sector_dirs'] = list(set(structure['sector_dirs']))
        
        print(f"\n📁 RESUMEN:")
        print(f"📁 {len(structure['insider_dirs'])} directorios insider únicos")
        print(f"📁 {len(structure['sector_dirs'])} directorios sectoriales únicos")
        print(f"📄 {len(structure['insider_files'])} archivos CSV insider")
        print(f"📄 {len(structure['sector_files'])} archivos CSV sectoriales")
        
        return structure
    
    def extract_date_from_path(self, path: str) -> Optional[datetime]:
        """Extraer fecha del nombre del directorio o archivo - Adaptado a tu estructura específica"""
        
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
        
        # PATRONES GENÉRICOS de fecha (fallback)
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',    # 2025-06-12
            r'(\d{4}_\d{2}_\d{2})',    # 2025_06_12
            r'(\d{4}\d{2}\d{2})',      # 20250612
            r'(\d{2}-\d{2}-\d{4})',    # 12-06-2025
            r'(\d{2}_\d{2}_\d{4})'     # 12_06_2025
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, path)
            if match:
                date_str = match.group(1)
                
                # Intentar diferentes formatos
                formats_to_try = ['%Y-%m-%d', '%Y_%m_%d', '%Y%m%d', '%d-%m-%Y', '%d_%m_%Y']
                
                for fmt in formats_to_try:
                    try:
                        date_str_normalized = date_str.replace('_', '-')
                        return datetime.strptime(date_str_normalized, fmt)
                    except:
                        continue
        
        # Si no encuentra fecha en el path, usar fecha del archivo (última modificación)
        try:
            file_path = Path(path)
            if file_path.exists():
                timestamp = file_path.stat().st_mtime
                return datetime.fromtimestamp(timestamp)
        except:
            pass
        
        # Fallback final: fecha actual
        print(f"⚠️  No se pudo extraer fecha de: {path}, usando fecha actual")
        return datetime.now()
    
    def load_historical_insider_data(self, file_paths: List[str]) -> Dict[str, pd.DataFrame]:
        """Cargar datos históricos de insider trading"""
        historical_data = {}
        
        for file_path in file_paths:
            try:
                # Extraer fecha del path
                date = self.extract_date_from_path(file_path)
                if not date:
                    date = datetime.now()  # Fallback para archivos sin fecha clara
                
                date_key = date.strftime('%Y-%m-%d')
                
                # Leer archivo
                raw_data = pd.read_csv(file_path, encoding='utf-8', sep=',', engine='python')
                
                # Aplicar mapeo de columnas corregido
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
                    
                    # Procesar valores monetarios
                    processed_data['ValueNumeric'] = processed_data['Value'].apply(self._parse_value)
                    
                    # Calcular días transcurridos
                    processed_data['DaysAgo'] = (datetime.now() - date).days
                    
                    # Limpiar datos
                    processed_data = processed_data.dropna(subset=['Ticker'])
                    processed_data['Ticker'] = processed_data['Ticker'].astype(str).str.strip()
                    processed_data['Type'] = processed_data['Type'].astype(str).str.strip()
                    
                    historical_data[date_key] = processed_data
                    print(f"✅ {file_path}: {len(processed_data)} registros ({date_key})")
                
            except Exception as e:
                print(f"❌ Error procesando {file_path}: {e}")
                continue
        
        return historical_data
    
    def load_historical_sector_data(self, file_paths: List[str]) -> Dict[str, pd.DataFrame]:
        """Cargar datos históricos sectoriales"""
        historical_data = {}
        errors = []
        
        print(f"\n📊 PROCESANDO {len(file_paths)} ARCHIVOS SECTORIALES...")
        
        for i, file_path in enumerate(file_paths):
            try:
                print(f"   📄 Procesando ({i+1}/{len(file_paths)}): {file_path}")
                
                # Extraer fecha
                date = self.extract_date_from_path(file_path)
                date_key = date.strftime('%Y-%m-%d')
                
                # Verificar que el archivo existe
                if not Path(file_path).exists():
                    print(f"   ❌ Archivo no existe: {file_path}")
                    continue
                
                # Leer datos sectoriales con manejo de encoding
                try:
                    sector_data = pd.read_csv(file_path, encoding='utf-8', sep=',', engine='python')
                except UnicodeDecodeError:
                    sector_data = pd.read_csv(file_path, encoding='latin-1', sep=',', engine='python')
                
                print(f"   📋 Leídas {len(sector_data)} filas, {len(sector_data.columns)} columnas")
                print(f"   📋 Columnas: {list(sector_data.columns)}")
                
                # Verificar que tiene las columnas esperadas para datos sectoriales
                expected_columns = ['Ticker', 'Sector', 'CurrentPrice', 'DistanceFromMin', 'RSI']
                missing_columns = [col for col in expected_columns if col not in sector_data.columns]
                
                if missing_columns:
                    print(f"   ⚠️  Faltan columnas esperadas: {missing_columns}")
                    print(f"   🔍 Columnas disponibles: {list(sector_data.columns)}")
                    # Continuar de todos modos, puede ser que las columnas tengan nombres ligeramente diferentes
                
                # Agregar metadata temporal
                sector_data['FileDate'] = date_key
                sector_data['DaysAgo'] = (datetime.now() - date).days
                
                # Asegurar tipos correctos para columnas numéricas
                numeric_columns = ['CurrentPrice', 'Min52w', 'Max52w', 'DistanceFromMin', 'RSI', 'DataPoints']
                for col in numeric_columns:
                    if col in sector_data.columns:
                        sector_data[col] = pd.to_numeric(sector_data[col], errors='coerce')
                
                # Limpiar campos de texto
                text_columns = ['Ticker', 'Sector', 'Estado', 'Classification']
                for col in text_columns:
                    if col in sector_data.columns:
                        sector_data[col] = sector_data[col].astype(str).str.strip()
                
                # Convertir fecha de análisis si existe
                if 'AnalysisDate' in sector_data.columns:
                    sector_data['AnalysisDate'] = pd.to_datetime(sector_data['AnalysisDate'], errors='coerce')
                
                # Filtrar filas válidas
                if 'Ticker' in sector_data.columns and 'Sector' in sector_data.columns:
                    sector_data = sector_data.dropna(subset=['Ticker', 'Sector'])
                    sector_data = sector_data[
                        (sector_data['Ticker'] != 'nan') & 
                        (sector_data['Ticker'] != '') &
                        (sector_data['Sector'] != 'nan') & 
                        (sector_data['Sector'] != '')
                    ]
                
                if len(sector_data) > 0:
                    historical_data[date_key] = sector_data
                    print(f"   ✅ Procesados {len(sector_data)} sectores válidos ({date_key})")
                    
                    # Mostrar muestra de sectores
                    if 'Sector' in sector_data.columns:
                        sample_sectors = sector_data['Sector'].unique()[:3]
                        print(f"   📊 Sectores de muestra: {', '.join(sample_sectors)}")
                else:
                    print(f"   ⚠️  No se encontraron registros válidos después de la limpieza")
                
            except Exception as e:
                error_msg = f"Error procesando {file_path}: {str(e)}"
                errors.append(error_msg)
                print(f"   ❌ {error_msg}")
                continue
        
        # Resumen final
        total_records = sum(len(df) for df in historical_data.values())
        unique_dates = len(historical_data)
        
        print(f"\n📈 RESUMEN SECTOR DATA:")
        print(f"   ✅ {len(file_paths)} archivos procesados")
        print(f"   📊 {unique_dates} fechas únicas cargadas")
        print(f"   📋 {total_records} registros sectoriales totales")
        
        if errors:
            print(f"   ⚠️  {len(errors)} archivos con errores")
            for error in errors[:3]:
                print(f"      • {error}")
        
        return historical_data
    
    def _parse_value(self, value_str) -> float:
        """Convertir strings de valor monetario a números"""
        if pd.isna(value_str) or value_str == '':
            return 0.0
        
        clean_value = str(value_str).replace('$', '').replace(',', '').replace(' ', '').replace('%', '')
        
        # Manejar multiplicadores
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
    
    def consolidate_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Consolidar todos los datos históricos"""
        
        # Consolidar insider data
        if self.insider_data_history:
            insider_frames = list(self.insider_data_history.values())
            self.consolidated_insider = pd.concat(insider_frames, ignore_index=True)
            print(f"📊 Consolidados {len(self.consolidated_insider)} registros insider")
        
        # Consolidar sector data
        if self.sector_data_history:
            sector_frames = list(self.sector_data_history.values())
            self.consolidated_sector = pd.concat(sector_frames, ignore_index=True)
            print(f"📊 Consolidados {len(self.consolidated_sector)} registros sectoriales")
        
        return self.consolidated_insider, self.consolidated_sector
    
    def analyze_insider_trends(self, days_recent: int = 7) -> Dict:
        """Analizar tendencias de insider trading"""
        if self.consolidated_insider.empty:
            return {}
        
        trends = {}
        recent_cutoff = datetime.now() - timedelta(days=days_recent)
        
        # Filtrar actividad reciente
        recent_data = self.consolidated_insider[
            self.consolidated_insider['DaysAgo'] <= days_recent
        ]
        
        # Agrupar por ticker
        for ticker in self.consolidated_insider['Ticker'].unique():
            ticker_data = self.consolidated_insider[
                self.consolidated_insider['Ticker'] == ticker
            ]
            ticker_recent = recent_data[recent_data['Ticker'] == ticker]
            
            # Analizar tipos de transacción
            total_trades = len(ticker_data)
            recent_trades = len(ticker_recent)
            
            buy_trades = len(ticker_data[
                ticker_data['Type'].str.contains('Purchase|Buy', case=False, na=False)
            ])
            recent_buys = len(ticker_recent[
                ticker_recent['Type'].str.contains('Purchase|Buy', case=False, na=False)
            ])
            
            # Calcular valores
            total_value = ticker_data['ValueNumeric'].sum()
            recent_value = ticker_recent['ValueNumeric'].sum()
            
            # Detectar ejecutivos
            exec_trades = len(ticker_data[
                ticker_data['InsiderTitle'].str.contains(
                    'CEO|CFO|President|Chairman|Director', case=False, na=False
                )
            ])
            
            trends[ticker] = {
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
        
        return trends
    
    def create_sector_mapping(self) -> Dict[str, str]:
        """Crear mapeo dinámico de tickers a sectores - MEJORADO"""
        mapping = {}
        
        # PASO 1: Usar el mapeo comprehensivo como base
        mapping.update(self.comprehensive_ticker_mapping)
        
        # PASO 2: Sobrescribir con datos dinámicos si están disponibles
        if not self.consolidated_sector.empty:
            # Usar datos sectoriales más recientes
            latest_sectors = self.consolidated_sector.loc[
                self.consolidated_sector.groupby('Ticker')['DaysAgo'].idxmin()
            ]
            
            for _, row in latest_sectors.iterrows():
                if pd.notna(row['Ticker']) and pd.notna(row['Sector']):
                    mapping[str(row['Ticker']).strip()] = str(row['Sector']).strip()
        
        print(f"🎯 Mapeo de sectores creado: {len(mapping)} tickers mapeados")
        return mapping
    
    def cross_analyze_opportunities(self, recent_days: int = 30) -> pd.DataFrame:
        """Análisis cruzado MEJORADO con mapeo robusto"""
        if self.consolidated_sector.empty:
            print("❌ No hay datos sectoriales para analizar")
            return pd.DataFrame()
        
        # Usar datos sectoriales más recientes por ticker
        latest_sectors = self.consolidated_sector.loc[
            self.consolidated_sector.groupby('Ticker')['DaysAgo'].idxmin()
        ].copy()
        
        # Calcular scores base
        latest_sectors['BaseScore'] = latest_sectors.apply(self._calculate_sector_score, axis=1)
        
        # Analizar tendencias insider
        insider_trends = self.analyze_insider_trends(recent_days)
        sector_mapping = self.create_sector_mapping()
        
        # MEJORA: Agregar información de insider por sector con mapeo robusto
        sector_insider_activity = {}
        mapped_tickers = 0
        total_insider_tickers = len(insider_trends)
        
        for ticker, trend in insider_trends.items():
            # Buscar sector usando el mapeo comprehensivo
            sector = sector_mapping.get(ticker, 'Unknown')
            
            if sector != 'Unknown':
                mapped_tickers += 1
                
                if sector not in sector_insider_activity:
                    sector_insider_activity[sector] = {
                        'total_trades': 0,
                        'recent_trades': 0,
                        'total_value': 0,
                        'recent_value': 0,
                        'tickers_with_activity': set(),
                        'executive_activity': 0,
                        'increasing_activity': 0,
                        'insider_tickers': []
                    }
                
                activity = sector_insider_activity[sector]
                activity['total_trades'] += trend['total_trades']
                activity['recent_trades'] += trend['recent_trades']
                activity['total_value'] += trend['total_value']
                activity['recent_value'] += trend['recent_value']
                activity['tickers_with_activity'].add(ticker)
                activity['executive_activity'] += trend['executive_trades']
                activity['insider_tickers'].append(ticker)
                
                if trend['activity_trend'] == 'INCREASING':
                    activity['increasing_activity'] += 1
        
        # Estadísticas de mapeo
        mapping_coverage = (mapped_tickers / total_insider_tickers * 100) if total_insider_tickers > 0 else 0
        print(f"🎯 ESTADÍSTICAS DE MAPEO:")
        print(f"   📊 Tickers insider: {total_insider_tickers}")
        print(f"   ✅ Tickers mapeados: {mapped_tickers}")
        print(f"   📈 Sectores con actividad: {len(sector_insider_activity)}")
        print(f"   🔍 Cobertura: {mapping_coverage:.1f}%")
        
        # Mostrar correlaciones encontradas
        if sector_insider_activity:
            print(f"\n🔗 CORRELACIONES DETECTADAS:")
            for sector, activity in sorted(sector_insider_activity.items(), 
                                         key=lambda x: x[1]['recent_trades'], reverse=True):
                tickers_str = ', '.join(activity['insider_tickers'][:3])
                if len(activity['insider_tickers']) > 3:
                    tickers_str += f" (+{len(activity['insider_tickers'])-3} más)"
                print(f"   📊 {sector}: {activity['recent_trades']} trades | {tickers_str}")
        
        # Crear análisis final
        results = []
        for _, sector in latest_sectors.iterrows():
            sector_name = sector['Sector']
            base_score = sector['BaseScore']
            
            # Obtener actividad insider del sector
            insider_activity = sector_insider_activity.get(sector_name, {})
            
            final_score = base_score
            signals = []
            urgency = 'BAJA'
            
            # Bonificaciones por actividad insider
            if insider_activity.get('recent_trades', 0) > 0:
                # Bonificación por actividad reciente
                recent_bonus = min(insider_activity['recent_trades'] * 8, 30)
                final_score += recent_bonus
                signals.append(f"{insider_activity['recent_trades']} trades recientes")
                
                # Bonificación por múltiples tickers
                if len(insider_activity.get('tickers_with_activity', set())) > 1:
                    final_score += 15
                    signals.append('Múltiples empresas comprando')
                    urgency = 'MEDIA'
                
                # Bonificación por ejecutivos
                if insider_activity.get('executive_activity', 0) > 0:
                    final_score += 12
                    signals.append('Actividad ejecutiva')
                    urgency = 'ALTA'
                
                # Bonificación por volumen
                if insider_activity.get('recent_value', 0) > 1_000_000:
                    final_score += 20
                    signals.append(f"${insider_activity['recent_value']/1_000_000:.1f}M volumen")
                    urgency = 'ALTA'
                
                # Bonificación por actividad creciente
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
                'InsiderTickers': insider_activity.get('insider_tickers', []),
                'Signals': signals,
                'Urgency': urgency,
                'RiskLevel': self._calculate_risk_level(sector, insider_activity),
                'MappingCoverage': mapping_coverage
            })
        
        # Convertir a DataFrame y ordenar
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('FinalScore', ascending=False)
        
        return results_df
    
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
    
    def _calculate_risk_level(self, sector, insider_activity) -> str:
        """Calcular nivel de riesgo"""
        risk_score = 0
        
        # RSI alto = más riesgo
        rsi = sector.get('RSI', 50)
        if rsi > 70:
            risk_score += 3
        elif rsi > 60:
            risk_score += 2
        elif rsi < 30:
            risk_score -= 1
        
        # Distancia del mínimo
        distance = sector.get('DistanceFromMin', 50)
        if distance > 40:
            risk_score += 2
        elif distance < 10:
            risk_score -= 1
        
        # Actividad insider reduce riesgo
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
    
    def generate_comprehensive_report(self, top_n: int = 15) -> Dict:
        """Generar reporte completo con análisis temporal MEJORADO"""
        print('\n🚀 GENERANDO REPORTE COMPRENSIVO DE OPORTUNIDADES MEJORADO')
        print('=' * 70)
        
        # Realizar análisis cruzado
        opportunities = self.cross_analyze_opportunities()
        
        if opportunities.empty:
            return {'error': 'No hay datos suficientes para el análisis'}
        
        top_opportunities = opportunities.head(top_n)
        
        print(f'\n🎯 TOP {top_n} OPORTUNIDADES DE INVERSIÓN MEJORADAS')
        print('=' * 60)
        
        for i, (_, opp) in enumerate(top_opportunities.iterrows()):
            print(f"\n{i+1}. {opp['Sector']} ({opp['Ticker']})")
            print(f"   📊 Score: {opp['FinalScore']:.0f}/100 (Base: {opp['BaseScore']:.0f})")
            print(f"   💰 ${opp['CurrentPrice']:.2f} ({opp['DistanceFromMin']:.1f}% del mínimo)")
            print(f"   📈 RSI: {opp['RSI']:.1f} | Clasificación: {opp['Classification']}")
            print(f"   🚨 Urgencia: {opp['Urgency']} | Riesgo: {opp['RiskLevel']}")
            
            if opp['InsiderActivity']:
                print(f"   👥 Insider: {opp['InsiderTrades']} trades recientes")
                if opp['InsiderValue'] > 0:
                    print(f"   💵 Volumen: ${opp['InsiderValue']/1_000_000:.1f}M")
                if len(opp['InsiderTickers']) > 0:
                    tickers_str = ', '.join(opp['InsiderTickers'][:3])
                    if len(opp['InsiderTickers']) > 3:
                        tickers_str += f" (+{len(opp['InsiderTickers'])-3})"
                    print(f"   🏢 Empresas: {tickers_str}")
                if opp['Signals']:
                    print(f"   🎯 Señales: {', '.join(opp['Signals'])}")
        
        # Estadísticas del análisis
        critical_opportunities = top_opportunities[top_opportunities['Urgency'] == 'CRÍTICA']
        high_urgency = top_opportunities[top_opportunities['Urgency'].isin(['CRÍTICA', 'ALTA'])]
        with_insider = top_opportunities[top_opportunities['InsiderActivity'] == True]
        
        # Estadísticas de mapeo
        mapping_coverage = opportunities['MappingCoverage'].iloc[0] if len(opportunities) > 0 else 0
        
        print(f'\n📈 RESUMEN EJECUTIVO MEJORADO:')
        print('=' * 40)
        print(f'📊 {len(opportunities)} oportunidades analizadas')
        print(f'🚨 {len(critical_opportunities)} oportunidades CRÍTICAS')
        print(f'⚠️  {len(high_urgency)} de urgencia ALTA/CRÍTICA')
        print(f'👥 {len(with_insider)} con actividad insider reciente')
        print(f'🎯 Mapeo ticker-sector: {mapping_coverage:.1f}% cobertura')
        print(f'⭐ Score promedio: {opportunities["FinalScore"].mean():.1f}/100')
        
        # Detectar patrones especiales
        special_patterns = self._detect_advanced_patterns(opportunities)
        
        if special_patterns:
            print(f'\n🚨 PATRONES ESPECIALES DETECTADOS:')
            print('=' * 40)
            for i, pattern in enumerate(special_patterns[:5]):
                print(f"{i+1}. {pattern['type']}: {pattern['sector']}")
                print(f"   {pattern['description']} | Urgencia: {pattern['urgency']}")
        
        return {
            'opportunities': opportunities,
            'top_opportunities': top_opportunities,
            'special_patterns': special_patterns,
            'summary': {
                'total_analyzed': len(opportunities),
                'critical_count': len(critical_opportunities),
                'high_urgency_count': len(high_urgency),
                'with_insider_activity': len(with_insider),
                'average_score': opportunities['FinalScore'].mean(),
                'mapping_coverage': mapping_coverage,
                'data_coverage_days': self._calculate_data_coverage()
            }
        }
    
    def _detect_advanced_patterns(self, opportunities: pd.DataFrame) -> List[Dict]:
        """Detectar patrones avanzados con datos temporales"""
        patterns = []
        
        for _, opp in opportunities.iterrows():
            # Patrón: Golden Cross (mejorado)
            if (opp['InsiderActivity'] and 
                opp['InsiderTrades'] >= 2 and 
                opp['DistanceFromMin'] < 12 and
                opp['Classification'] == 'OPORTUNIDAD'):
                patterns.append({
                    'type': 'GOLDEN_CROSS_ENHANCED',
                    'sector': opp['Sector'],
                    'description': f'Múltiples insiders comprando cerca del mínimo ({opp["DistanceFromMin"]:.1f}%)',
                    'urgency': 'CRÍTICA',
                    'score': opp['FinalScore'],
                    'confidence': 'ALTA'
                })
            
            # Patrón: Volume Explosion
            if (opp['InsiderValue'] > 2_000_000 and 
                opp['InsiderTrades'] >= 3):
                patterns.append({
                    'type': 'VOLUME_EXPLOSION',
                    'sector': opp['Sector'],
                    'description': f'Alto volumen insider (${opp["InsiderValue"]/1_000_000:.1f}M) con múltiples trades',
                    'urgency': 'ALTA',
                    'score': opp['FinalScore'],
                    'confidence': 'ALTA'
                })
            
            # Patrón: Oversold Insider Rally
            if (opp['RSI'] < 35 and 
                opp['InsiderTrades'] > 0 and 
                'Actividad ejecutiva' in str(opp['Signals'])):
                patterns.append({
                    'type': 'OVERSOLD_INSIDER_RALLY',
                    'sector': opp['Sector'],
                    'description': f'Sobreventa extrema + ejecutivos comprando (RSI: {opp["RSI"]:.1f})',
                    'urgency': 'ALTA',
                    'score': opp['FinalScore'],
                    'confidence': 'MEDIA'
                })
        
        return sorted(patterns, key=lambda x: x['score'], reverse=True)
    
    def _calculate_data_coverage(self) -> int:
        """Calcular días de cobertura de datos"""
        if self.consolidated_insider.empty and self.consolidated_sector.empty:
            return 0
        
        min_days = float('inf')
        if not self.consolidated_insider.empty:
            min_days = min(min_days, self.consolidated_insider['DaysAgo'].min())
        if not self.consolidated_sector.empty:
            min_days = min(min_days, self.consolidated_sector['DaysAgo'].min())
        
        return int(min_days) if min_days != float('inf') else 0
    
    def run_full_scan(self, recent_days: int = 14) -> Dict:
        """Ejecutar escaneo completo automático MEJORADO"""
        print("🚀 INICIANDO ESCANEO COMPLETO DEL SISTEMA MEJORADO")
        print("=" * 70)
        
        # 1. Escanear estructura de directorios
        structure = self.scan_directory_structure()
        
        if not structure['insider_files'] and not structure['sector_files']:
            return {'error': 'No se encontraron archivos CSV en la estructura de directorios'}
        
        # 2. Cargar datos históricos
        print("\n📊 CARGANDO DATOS HISTÓRICOS...")
        
        if structure['insider_files']:
            self.insider_data_history = self.load_historical_insider_data(structure['insider_files'])
            print(f"✅ {len(self.insider_data_history)} archivos insider procesados")
        
        if structure['sector_files']:
            self.sector_data_history = self.load_historical_sector_data(structure['sector_files'])
            print(f"✅ {len(self.sector_data_history)} archivos sectoriales procesados")
        
        # 3. Consolidar datos
        print("\n🔄 CONSOLIDANDO DATOS...")
        self.consolidate_data()
        
        # 4. Generar reporte comprensivo
        results = self.generate_comprehensive_report()
        
        # 5. Guardar resultados
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"trading_scan_results_enhanced_{timestamp}.json"
        
        # Convertir DataFrames a dict para JSON
        json_results = {
            'scan_timestamp': timestamp,
            'summary': results.get('summary', {}),
            'special_patterns': results.get('special_patterns', []),
            'top_opportunities': results.get('top_opportunities', pd.DataFrame()).to_dict('records') if 'top_opportunities' in results else [],
            'mapping_used': 'comprehensive_enhanced',
            'total_ticker_mappings': len(self.comprehensive_ticker_mapping)
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Resultados mejorados guardados en: {output_file}")
        
        return results


# FUNCIONES DE TESTING Y DEBUGGING MEJORADAS

def test_directory_structure_enhanced(base_path: str = ".") -> Dict:
    """
    Función de testing MEJORADA para verificar que el escáner encuentra correctamente
    la estructura de directorios del usuario y el mapeo de sectores
    """
    print("🧪 MODO TEST MEJORADO: Verificando estructura + mapeo sectorial")
    print("=" * 70)
    
    scanner = AdvancedTradingScanner(base_path)
    
    # 1. Escanear estructura
    structure = scanner.scan_directory_structure()
    
    # 2. Test del mapeo de sectores
    print(f"\n🎯 TESTING MAPEO SECTORIAL MEJORADO...")
    test_tickers = ['AAPL', 'JPM', 'XOM', 'UNH', 'PFE', 'GOOGL', 'BAC', 'CVX', 'JNJ', 'UNKNOWN_TICKER']
    sector_mapping = scanner.create_sector_mapping()
    
    mapped_count = 0
    for ticker in test_tickers:
        sector = sector_mapping.get(ticker)
        if sector:
            mapped_count += 1
            print(f"   ✅ {ticker} → {sector}")
        else:
            print(f"   ❌ {ticker} → No mapeado")
    
    mapping_coverage = (mapped_count / len(test_tickers)) * 100
    print(f"   📊 Cobertura de mapeo: {mapping_coverage:.1f}%")
    print(f"   🎯 Total tickers en mapeo: {len(scanner.comprehensive_ticker_mapping)}")
    
    # 3. Verificar archivos encontrados
    test_results = {
        'structure_found': structure,
        'insider_files_count': len(structure['insider_files']),
        'sector_files_count': len(structure['sector_files']),
        'mapping_test': {
            'test_tickers': test_tickers,
            'mapped_count': mapped_count,
            'coverage_percentage': mapping_coverage,
            'total_mappings': len(scanner.comprehensive_ticker_mapping)
        },
        'test_results': {},
        'recommendations': []
    }
    
    # 4. Probar cargar un archivo de muestra de cada tipo
    if structure['insider_files']:
        print(f"\n🧪 PROBANDO CARGA DE ARCHIVO INSIDER DE MUESTRA...")
        sample_insider = structure['insider_files'][0]
        try:
            raw_data = pd.read_csv(sample_insider, encoding='utf-8', sep=',', engine='python')
            test_results['test_results']['insider_sample'] = {
                'file': sample_insider,
                'rows': len(raw_data),
                'columns': len(raw_data.columns),
                'column_names': list(raw_data.columns),
                'first_row': raw_data.iloc[0].to_dict() if len(raw_data) > 0 else {},
                'status': 'SUCCESS'
            }
            print(f"   ✅ Archivo insider de muestra cargado exitosamente")
            print(f"   📊 {len(raw_data)} filas, {len(raw_data.columns)} columnas")
        except Exception as e:
            test_results['test_results']['insider_sample'] = {
                'file': sample_insider,
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"   ❌ Error cargando archivo insider: {e}")
    
    if structure['sector_files']:
        print(f"\n🧪 PROBANDO CARGA DE ARCHIVO SECTORIAL DE MUESTRA...")
        sample_sector = structure['sector_files'][0]
        try:
            raw_data = pd.read_csv(sample_sector, encoding='utf-8', sep=',', engine='python')
            test_results['test_results']['sector_sample'] = {
                'file': sample_sector,
                'rows': len(raw_data),
                'columns': len(raw_data.columns),
                'column_names': list(raw_data.columns),
                'first_row': raw_data.iloc[0].to_dict() if len(raw_data) > 0 else {},
                'status': 'SUCCESS'
            }
            print(f"   ✅ Archivo sectorial de muestra cargado exitosamente")
            print(f"   📊 {len(raw_data)} filas, {len(raw_data.columns)} columnas")
        except Exception as e:
            test_results['test_results']['sector_sample'] = {
                'file': sample_sector,
                'status': 'ERROR',
                'error': str(e)
            }
            print(f"   ❌ Error cargando archivo sectorial: {e}")
    
    # 5. Generar recomendaciones mejoradas
    if test_results['insider_files_count'] == 0:
        test_results['recommendations'].append(
            "❌ No se encontraron archivos insider. Verifica que existan directorios reports/report_YYYY-MM-DD/ con data.csv"
        )
    else:
        test_results['recommendations'].append(
            f"✅ {test_results['insider_files_count']} archivos insider encontrados"
        )
    
    if test_results['sector_files_count'] == 0:
        test_results['recommendations'].append(
            "❌ No se encontraron archivos sectoriales. Verifica que existan directorios dj_sectorial/dj_sectorial_YYYY-MM-DD/ con data.csv"
        )
    else:
        test_results['recommendations'].append(
            f"✅ {test_results['sector_files_count']} archivos sectoriales encontrados"
        )
    
    if mapping_coverage >= 70:
        test_results['recommendations'].append(
            f"✅ Mapeo sectorial funcionando bien ({mapping_coverage:.1f}% cobertura)"
        )
    else:
        test_results['recommendations'].append(
            f"⚠️ Mapeo sectorial necesita mejoras ({mapping_coverage:.1f}% cobertura)"
        )
    
    # 6. Mostrar resumen
    print(f"\n📋 RESUMEN DEL TEST MEJORADO:")
    print("=" * 40)
    for rec in test_results['recommendations']:
        print(f"   {rec}")
    
    return test_results


# EJEMPLO DE USO MEJORADO
if __name__ == "__main__":
    import sys
    
    # Permitir diferentes modos de ejecución
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Modo test: verificar estructura de directorios y mapeo
        print("🧪 EJECUTANDO EN MODO TEST MEJORADO")
        test_results = test_directory_structure_enhanced(".")
        
        if test_results['insider_files_count'] > 0 or test_results['sector_files_count'] > 0:
            print("\n✅ Test exitoso. El escáner mejorado puede proceder con el análisis completo.")
            print("💡 Para ejecutar análisis completo: python script.py")
        else:
            print("\n❌ Test falló. Revisa la estructura de directorios.")
            print("💡 Estructura esperada:")
            print("   reports/report_YYYY-MM-DD/data.csv (insider trading)")
            print("   dj_sectorial/dj_sectorial_YYYY-MM-DD/data.csv (datos sectoriales)")
    
    elif len(sys.argv) > 1 and sys.argv[1] == 'preview':
        # Modo preview: vista rápida de datos
        print("👀 EJECUTANDO EN MODO PREVIEW")
        scanner = AdvancedTradingScanner(".")
        structure = scanner.scan_directory_structure()
        
        # Mostrar estadísticas de mapeo
        print(f"\n🎯 ESTADÍSTICAS DE MAPEO:")
        print(f"   📊 Total tickers mapeados: {len(scanner.comprehensive_ticker_mapping)}")
        
        # Mostrar sectores disponibles
        sectors = set(scanner.comprehensive_ticker_mapping.values())
        print(f"   📈 Sectores disponibles: {len(sectors)}")
        for sector in sorted(sectors):
            count = list(scanner.comprehensive_ticker_mapping.values()).count(sector)
            print(f"      • {sector}: {count} tickers")
        
        print("\n✅ Preview completado.")
    
    else:
        # Modo normal: escaneo completo
        print("🚀 EJECUTANDO ANÁLISIS COMPLETO MEJORADO")
        
        # Primero hacer un test rápido
        test_results = test_directory_structure_enhanced(".")
        
        if test_results['insider_files_count'] == 0 and test_results['sector_files_count'] == 0:
            print("\n❌ No se encontraron archivos de datos.")
            print("💡 Ejecuta 'python script.py test' para diagnosticar el problema.")
            sys.exit(1)
        
        # Si hay archivos, proceder con análisis completo
        scanner = AdvancedTradingScanner(".")
        results = scanner.run_full_scan(recent_days=14)
        
        if 'error' not in results:
            print("\n🎯 ¡ANÁLISIS COMPLETADO EXITOSAMENTE!")
            print("📄 Revisa el archivo JSON generado para resultados detallados.")
            summary = results.get('summary', {})
            print(f"🎯 Correlaciones encontradas: {summary.get('with_insider_activity', 0)} sectores")
            print(f"📊 Cobertura de mapeo: {summary.get('mapping_coverage', 0):.1f}%")
        else:
            print(f"\n❌ Error en análisis: {results['error']}")
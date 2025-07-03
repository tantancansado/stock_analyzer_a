import requests
import json
from datetime import datetime

class NYSEDataExtractor:
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
        
        # Símbolos de interés - Suite completa de indicadores
        self.symbols = {
            # === INDICADORES McCLELLAN ===
            'NYMOT': '$NYMOT',  # NYSE McClellan Oscillator (Traditional)
            'NYMO': '$NYMO',    # NYSE McClellan Oscillator 
            'NYSI': '$NYSI',    # NYSE Summation Index
            'NAMO': '$NAMO',    # NASDAQ McClellan Oscillator
            'NASI': '$NASI',    # NASDAQ Summation Index
            
            # === ADVANCE-DECLINE LINES ===
            'NYADL': '$NYADL',  # NYSE Advance-Decline Line
            'NAADL': '$NAADL',  # NASDAQ Advance-Decline Line
            'NYAD': '$NYAD',    # NYSE Advance-Decline Issues
            'NAAD': '$NAAD',    # NASDAQ Advance-Decline Issues
            
            # === ADVANCE-DECLINE PERCENTAGES ===
            'SPXADP': '$SPXADP', # S&P 500 Advance-Decline Percent
            'MIDADP': '$MIDADP', # S&P 400 MidCap AD Percent
            'SMLADP': '$SMLADP', # S&P 600 SmallCap AD Percent
            'NAADP': '$NAADP',   # NASDAQ Advance-Decline Percent
            
            # === ARMS INDEX (TRIN) ===
            'TRIN': '$TRIN',    # NYSE Arms Index (TRIN)
            'TRINQ': '$TRINQ',  # NASDAQ Arms Index
            
            # === NUEVOS MÁXIMOS/MÍNIMOS ===
            'NYHGH': '$NYHGH',  # NYSE New 52-Week Highs
            'NYLOW': '$NYLOW',  # NYSE New 52-Week Lows
            'NAHGH': '$NAHGH',  # NASDAQ New Highs
            'NALOW': '$NALOW',  # NASDAQ New Lows
            'NYHL': '$NYHL',    # NYSE Net New Highs-Lows
            'NAHL': '$NAHL',    # NASDAQ Net New Highs-Lows
            
            # === PORCENTAJES SOBRE MEDIAS MÓVILES ===
            'NYA50R': '$NYA50R',   # NYSE % Above 50-day MA
            'NYA200R': '$NYA200R', # NYSE % Above 200-day MA
            'NAA50R': '$NAA50R',   # NASDAQ % Above 50-day MA
            'NAA200R': '$NAA200R', # NASDAQ % Above 200-day MA
            'SPXA50R': '$SPXA50R', # S&P 500 % Above 50-day MA
            'SPXA200R': '$SPXA200R', # S&P 500 % Above 200-day MA
            
            # === INDICADORES DE VOLUMEN ===
            'NYUPV': '$NYUPV',  # NYSE Up Volume
            'NYDNV': '$NYDNV',  # NYSE Down Volume
            'NAUPV': '$NAUPV',  # NASDAQ Up Volume
            'NADNV': '$NADNV',  # NASDAQ Down Volume
            'NAUD': '$NAUD',    # NASDAQ Advance-Decline Volume
            'NYUD': '$NYUD',    # NYSE Up-Down Volume
            
            # === BULLISH PERCENT INDEX ===
            'BPSPX': '$BPSPX',  # S&P 500 Bullish Percent Index
            'BPNDX': '$BPNDX',  # NASDAQ 100 Bullish Percent Index
            'BPNYA': '$BPNYA',  # NYSE Bullish Percent Index
            'BPCOMPQ': '$BPCOMPQ', # NASDAQ Composite Bullish Percent
            
            # === RECORD HIGH PERCENT ===
            'RHNYA': '$RHNYA',  # NYSE Record High Percent
            'RHNDX': '$RHNDX',  # NASDAQ 100 Record High Percent
            'RHSPX': '$RHSPX',  # S&P 500 Record High Percent
            
            # === INDICADORES DE SENTIMIENTO ===
            # VIX y Volatilidad
            'VIX': '$VIX',      # CBOE Volatility Index
            'VXN': '$VXN',      # NASDAQ 100 Volatility Index
            'RVX': '$RVX',      # Russell 2000 Volatility Index
            'VXD': '$VXD',      # DJIA Volatility Index
            
            # Put/Call Ratios
            'CPC': '$CPC',      # CBOE Put/Call Ratio
            'CPCE': '$CPCE',    # CBOE Equity Put/Call Ratio
            'CPCN': '$CPCN',    # CBOE NASDAQ Put/Call Ratio
            
            # === INDICADORES DECISIONPOINT (con símbolo !) ===
            'AAIIBULL': '!AAIIBULL',  # AAII Bulls
            'AAIIBEAR': '!AAIIBEAR',  # AAII Bears
            'AAIINEUR': '!AAIINEUR',  # AAII Neutral
            'NAAIMBULL': '!NAAIMBULL', # NAAIM Bulls
            'NAAIMEXP': '!NAAIMEXP',   # NAAIM Exposure
            
            # === INDICADORES SECTORIALES IMPORTANTES ===
            'XLF': 'XLF',       # Financial Sector ETF
            'XLK': 'XLK',       # Technology Sector ETF
            'XLE': 'XLE',       # Energy Sector ETF
            'XLI': 'XLI',       # Industrial Sector ETF
            'XLV': 'XLV',       # Healthcare Sector ETF
            
            # === ÍNDICES PRINCIPALES PARA CONTEXTO ===
            'SPX': '$SPX',      # S&P 500 Index
            'COMPQ': '$COMPQ',  # NASDAQ Composite
            'NYA': '$NYA',      # NYSE Composite
            'DJI': '$DJI',      # Dow Jones Industrial Average
            'RUT': '$RUT',      # Russell 2000
            
            # === INDICADORES ADICIONALES AVANZADOS ===
            'NYTO': '$NYTO',    # NYSE Total Volume
            'NATO': '$NATO',    # NASDAQ Total Volume
            'TICK': '$TICK',    # NYSE TICK
            'TICKQ': '$TICKQ',  # NASDAQ TICK
            'TICKI': '$TICKI',  # NYSE TICK Index
            
            # === INDICADORES DE COMMODITIES Y BONDS ===
            'TNX': '$TNX',      # 10-Year Treasury Note Yield
            'TYX': '$TYX',      # 30-Year Treasury Bond Yield
            'DXY': '$DXY',      # US Dollar Index
            'GOLD': '$GOLD',    # Gold Continuous Contract
            'WTIC': '$WTIC',    # WTI Crude Oil
        }

    def get_symbol_data(self, symbol):
        """Obtiene datos de un símbolo específico"""
        params = {
            'cmd': 'get-symbol-data',
            'symbols': symbol,
            'optionalFields': 'symbolsummary'
        }
        
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
        
        # Función auxiliar para acceso seguro a datos anidados
        def safe_get(obj, *keys):
            for key in keys:
                if obj is None:
                    return None
                obj = obj.get(key) if isinstance(obj, dict) else None
            return obj
        
        # Obtener perfSummaryQuote de forma segura
        perf_data = symbol_data.get('perfSummaryQuote') or {}
        company_info = symbol_data.get('companyInfo') or {}
        
        metrics = {
            'symbol': symbol_data.get('symbol'),
            'name': company_info.get('name'),
            'current_price': symbol_data.get('quoteClose'),
            'change': safe_get(perf_data, 'now', 'chg'),
            'change_pct': safe_get(perf_data, 'now', 'pct'),
            'previous_close': symbol_data.get('quoteYesterdayClose'),
            'latest_trade': symbol_data.get('latestTrade'),
            'year_range': symbol_data.get('yearRange'),
            'all_time_high': company_info.get('allTimeHigh'),
            'sma_50': symbol_data.get('sma50'),
            'sma_200': symbol_data.get('sma200'),
            'rsi': symbol_data.get('rsi'),
            'atr': symbol_data.get('atr'),
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
        
        return metrics

    def get_specific_indicators(self, indicator_list):
        """Obtiene solo indicadores específicos de la lista"""
        results = {}
        
        print(f"Obteniendo {len(indicator_list)} indicadores específicos...")
        print("-" * 50)
        
        for indicator_name in indicator_list:
            if indicator_name in self.symbols:
                symbol = self.symbols[indicator_name]
                print(f"Obteniendo {indicator_name} ({symbol})...")
                
                data = self.get_symbol_data(symbol)
                if data:
                    metrics = self.extract_key_metrics(data)
                    if metrics:
                        results[indicator_name] = metrics
                        print(f"✓ {indicator_name}: {metrics['current_price']}")
                    else:
                        print(f"✗ Error procesando datos para {indicator_name}")
                else:
                    print(f"✗ No se pudieron obtener datos para {indicator_name}")
            else:
                print(f"✗ Indicador {indicator_name} no encontrado en la lista")
        
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
        
        return self.get_specific_indicators(core_indicators)

    def export_to_json(self, results, filename=None):
        """Exporta los resultados a un archivo JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"market_indicators_{timestamp}.json"
        
        # Preparar datos para JSON
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'total_indicators': len(results),
            'indicators': results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Datos exportados a: {filename}")
            return filename
        except Exception as e:
            print(f"✗ Error al exportar: {e}")
            return None

    def export_to_csv(self, results, filename=None):
        """Exporta los resultados a un archivo CSV"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"market_indicators_{timestamp}.csv"
        
        try:
            import csv
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Headers
                writer.writerow([
                    'Symbol', 'Name', 'Current_Price', 'Change', 'Change_Pct', 
                    'Previous_Close', 'Year_Range', 'SMA_50', 'SMA_200', 'RSI', 'ATR',
                    'Performance_1M', 'Performance_3M', 'Performance_1Y'
                ])
                
                # Datos
                for symbol, data in results.items():
                    perf = data.get('performance', {})
                    writer.writerow([
                        symbol,
                        data.get('name', ''),
                        data.get('current_price', ''),
                        data.get('change', ''),
                        data.get('change_pct', ''),
                        data.get('previous_close', ''),
                        data.get('year_range', ''),
                        data.get('sma_50', ''),
                        data.get('sma_200', ''),
                        data.get('rsi', ''),
                        data.get('atr', ''),
                        perf.get('one_month', ''),
                        perf.get('three_months', ''),
                        perf.get('one_year', '')
                    ])
            
            print(f"✓ Datos exportados a CSV: {filename}")
            return filename
        except Exception as e:
            print(f"✗ Error al exportar a CSV: {e}")
            return None

    def get_all_indicators(self):
        """Obtiene todos los indicadores de mercado disponibles"""
        results = {}
        
        print(f"Obteniendo {len(self.symbols)} indicadores de mercado...")
        print("-" * 60)
        
        total_success = 0
        total_failed = 0
        
        for name, symbol in self.symbols.items():
            print(f"📊 {name:15} ({symbol:12}) ... ", end="")
            
            try:
                data = self.get_symbol_data(symbol)
                if data:
                    metrics = self.extract_key_metrics(data)
                    if metrics:
                        results[name] = metrics
                        print(f"✅ {metrics['current_price']}")
                        total_success += 1
                    else:
                        print("❌ Error procesando")
                        total_failed += 1
                else:
                    print("❌ Sin datos")
                    total_failed += 1
            except Exception as e:
                print(f"❌ Error: {str(e)[:30]}")
                total_failed += 1
        
        print(f"\n📈 Resumen: {total_success} éxitos, {total_failed} fallos de {len(self.symbols)} total")
        return results

    def _print_section(self, title, indicators, results):
        """Imprime una sección específica de indicadores"""
        print(f"\n{title}:")
        print("-" * (len(title) + 1))
        
        found_any = False
        for indicator in indicators:
            if indicator in results:
                data = results[indicator]
                change_pct = data['change_pct'] or 0
                change_val = data['change'] or 0
                name = data['name'] or indicator
                current_price = data['current_price'] or 0
                
                # Formatear nombre para que sea más legible
                display_name = name if name and len(str(name)) < 40 else (str(name)[:37] + "..." if name else indicator)
                
                # Formatear valores de forma segura
                try:
                    price_str = f"{current_price:>10.2f}" if current_price is not None else "      N/A"
                    change_str = f"{change_val:>+8.2f}" if change_val is not None else "    N/A"
                    pct_str = f"{change_pct:>+7.2f}%" if change_pct is not None else "    N/A"
                except (TypeError, ValueError):
                    price_str = "      N/A"
                    change_str = "    N/A" 
                    pct_str = "    N/A"
                
                print(f"  {indicator:12} | {price_str} | {change_str} | {pct_str} | {display_name}")
                found_any = True
        
        if not found_any:
            print("  No hay datos disponibles para esta sección")

    def _print_market_health_summary(self, results):
        """Genera un resumen de la salud general del mercado"""
        print("\n" + "="*80)
        print("RESUMEN DE SALUD DEL MERCADO")
        print("="*80)
        
        # Análisis de breadth
        breadth_score = 0
        breadth_count = 0
        
        key_breadth_indicators = ['NYMO', 'NYMOT', 'SPXADP', 'NYA50R', 'NYA200R', 'BPSPX']
        for indicator in key_breadth_indicators:
            if indicator in results and results[indicator]['current_price'] is not None:
                value = results[indicator]['current_price']
                if indicator in ['NYMO', 'NYMOT']:
                    # McClellan: > 0 es positivo
                    breadth_score += 1 if value > 0 else -1
                elif indicator in ['SPXADP']:
                    # AD Percent: > 0 es positivo
                    breadth_score += 1 if value > 0 else -1
                elif indicator in ['NYA50R', 'NYA200R']:
                    # % sobre MA: > 50 es positivo
                    breadth_score += 1 if value > 50 else -1
                elif indicator == 'BPSPX':
                    # Bullish Percent: > 50 es positivo
                    breadth_score += 1 if value > 50 else -1
                breadth_count += 1
        
        if breadth_count > 0:
            breadth_percentage = (breadth_score / breadth_count) * 100
            print(f"🔍 AMPLITUD DE MERCADO: {breadth_score}/{breadth_count} positivos ({breadth_percentage:+.1f}%)")
            
            if breadth_percentage > 50:
                print("   ✅ AMPLITUD POSITIVA - Mercado saludable")
            elif breadth_percentage > 0:
                print("   ⚠️  AMPLITUD MIXTA - Mercado neutral")
            else:
                print("   ❌ AMPLITUD NEGATIVA - Mercado débil")
        
        # Análisis de sentimiento
        sentiment_indicators = {'VIX': 'volatilidad', 'CPC': 'put/call', 'AAIIBULL': 'bulls%'}
        sentiment_signals = []
        
        for indicator, desc in sentiment_indicators.items():
            if indicator in results and results[indicator]['current_price'] is not None:
                value = results[indicator]['current_price']
                if indicator == 'VIX':
                    if value > 30:
                        sentiment_signals.append(f"VIX alto ({value:.1f}) - Miedo extremo")
                    elif value < 15:
                        sentiment_signals.append(f"VIX bajo ({value:.1f}) - Complacencia")
                elif indicator == 'CPC':
                    if value > 1.2:
                        sentiment_signals.append(f"Put/Call alto ({value:.2f}) - Pesimismo")
                    elif value < 0.8:
                        sentiment_signals.append(f"Put/Call bajo ({value:.2f}) - Optimismo")
        
        if sentiment_signals:
            print(f"\n💭 SENTIMIENTO:")
            for signal in sentiment_signals:
                print(f"   • {signal}")
        
        print("\n" + "="*80)

    def print_market_summary(self, results):
        """Imprime un resumen completo de los indicadores de mercado"""
        print("\n" + "="*80)
        print("RESUMEN COMPLETO DE INDICADORES DE MERCADO")
        print("="*80)
        
        # === INDICADORES McCLELLAN ===
        mcclellan_indicators = ['NYMO', 'NYMOT', 'NYSI', 'NAMO', 'NASI']
        self._print_section("INDICADORES McCLELLAN", mcclellan_indicators, results)
        
        # === ADVANCE-DECLINE ===
        ad_indicators = ['NYADL', 'NAADL', 'NYAD', 'NAAD', 'SPXADP', 'MIDADP', 'SMLADP', 'NAADP']
        self._print_section("ADVANCE-DECLINE", ad_indicators, results)
        
        # === ARMS INDEX (TRIN) ===
        trin_indicators = ['TRIN', 'TRINQ']
        self._print_section("ARMS INDEX (TRIN)", trin_indicators, results)
        
        # === NUEVOS MÁXIMOS/MÍNIMOS ===
        highs_lows = ['NYHGH', 'NYLOW', 'NAHGH', 'NALOW', 'NYHL', 'NAHL']
        self._print_section("NUEVOS MÁXIMOS/MÍNIMOS", highs_lows, results)
        
        # === PORCENTAJES SOBRE MEDIAS MÓVILES ===
        ma_indicators = ['NYA50R', 'NYA200R', 'NAA50R', 'NAA200R', 'SPXA50R', 'SPXA200R']
        self._print_section("% SOBRE MEDIAS MÓVILES", ma_indicators, results)
        
        # === BULLISH PERCENT INDEX ===
        bp_indicators = ['BPSPX', 'BPNDX', 'BPNYA', 'BPCOMPQ']
        self._print_section("BULLISH PERCENT INDEX", bp_indicators, results)
        
        # === RECORD HIGH PERCENT ===
        rh_indicators = ['RHNYA', 'RHNDX', 'RHSPX']
        self._print_section("RECORD HIGH PERCENT", rh_indicators, results)
        
        # === VOLATILIDAD ===
        vix_indicators = ['VIX', 'VXN', 'RVX', 'VXD']
        self._print_section("ÍNDICES DE VOLATILIDAD", vix_indicators, results)
        
        # === PUT/CALL RATIOS ===
        pc_indicators = ['CPC', 'CPCE', 'CPCN']
        self._print_section("PUT/CALL RATIOS", pc_indicators, results)
        
        # === SENTIMIENTO ===
        sentiment_indicators = ['AAIIBULL', 'AAIIBEAR', 'AAIINEUR', 'NAAIMBULL', 'NAAIMEXP']
        self._print_section("INDICADORES DE SENTIMIENTO", sentiment_indicators, results)
        
        # === VOLUMEN ===
        volume_indicators = ['NYUPV', 'NYDNV', 'NAUPV', 'NADNV', 'NAUD', 'NYUD', 'NYTO', 'NATO']
        self._print_section("INDICADORES DE VOLUMEN", volume_indicators, results)
        
        # === TICK ===
        tick_indicators = ['TICK', 'TICKQ', 'TICKI']
        self._print_section("INDICADORES TICK", tick_indicators, results)
        
        # === ÍNDICES PRINCIPALES ===
        main_indices = ['SPX', 'COMPQ', 'NYA', 'DJI', 'RUT']
        self._print_section("ÍNDICES PRINCIPALES", main_indices, results)
        
        # === SECTORES ===
        sector_etfs = ['XLF', 'XLK', 'XLE', 'XLI', 'XLV']
        self._print_section("SECTORES PRINCIPALES", sector_etfs, results)
        
        # === COMMODITIES Y BONDS ===
        macro_indicators = ['TNX', 'TYX', 'DXY', 'GOLD', 'WTIC']
        self._print_section("MACRO (BONDS, COMMODITIES, FOREX)", macro_indicators, results)
        
        # === RESUMEN GENERAL ===
        self._print_market_health_summary(results)


# Función principal para probar
def main():
    extractor = NYSEDataExtractor()
    
    print("🔍 ANALIZADOR COMPLETO DE AMPLITUD DE MERCADO")
    print("=" * 60)
    print("Opciones disponibles:")
    print("1. Indicadores básicos (McClellan + principales)")
    print("2. Suite completa de amplitud")
    print("3. Solo indicadores de sentimiento")
    print("4. Todos los indicadores disponibles")
    
    # Por defecto, ejecutamos los indicadores básicos
    print("\n⏳ Ejecutando análisis de indicadores básicos...")
    
    # Primero probamos con NYMOT (el que tienes en el JSON)
    print("\n🧪 Probando conexión con NYMOT...")
    nymot_data = extractor.get_symbol_data('$NYMOT')
    
    if nymot_data:
        print("✅ Conexión exitosa!")
        metrics = extractor.extract_key_metrics(nymot_data)
        print(f"📊 NYMOT - Valor actual: {metrics['current_price']}")
        if metrics['change_pct']:
            print(f"📈 Cambio: {metrics['change']} ({metrics['change_pct']:.2f}%)")
    else:
        print("❌ Error en la conexión")
        return None
    
    # Obtener indicadores básicos
    print("\n📊 Obteniendo indicadores básicos de amplitud...")
    core_results = extractor.get_core_breadth_indicators()
    
    if core_results:
        extractor.print_market_summary(core_results)
        
        # Exportar resultados
        json_file = extractor.export_to_json(core_results)
        csv_file = extractor.export_to_csv(core_results)
        
        print(f"\n📁 Archivos generados:")
        if json_file:
            print(f"   • JSON: {json_file}")
        if csv_file:
            print(f"   • CSV: {csv_file}")
    
    # Opción para obtener TODOS los indicadores
    try:
        get_all = input("\n❓ ¿Quieres obtener TODOS los indicadores? (s/N): ").lower().strip()
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
        return core_results
    
    if get_all in ['s', 'si', 'sí', 'y', 'yes']:
        print("\n🔄 Obteniendo TODOS los indicadores...")
        print("⚠️  Esto puede tomar varios minutos...")
        
        try:
            all_results = extractor.get_all_indicators()
            
            if all_results:
                extractor.print_market_summary(all_results)
                
                # Exportar resultados completos
                json_file_full = extractor.export_to_json(all_results, "market_indicators_complete.json")
                csv_file_full = extractor.export_to_csv(all_results, "market_indicators_complete.csv")
                
                print(f"\n📁 Archivos completos generados:")
                if json_file_full:
                    print(f"   • JSON completo: {json_file_full}")
                if csv_file_full:
                    print(f"   • CSV completo: {csv_file_full}")
                
                return all_results
            else:
                print("❌ No se pudieron obtener datos completos")
        except Exception as e:
            print(f"❌ Error obteniendo todos los indicadores: {e}")
    
    return core_results


if __name__ == "__main__":
    results = main()
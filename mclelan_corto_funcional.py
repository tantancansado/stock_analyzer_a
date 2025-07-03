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
        
        # Símbolos de interés
        self.symbols = {
            'NYMOT': '$NYMOT',  # NYSE McClellan Oscillator (Traditional)
            'NYMO': '$NYMO',    # NYSE McClellan Oscillator 
            'NYSI': '$NYSI',    # NYSE Summation Index
            'NASI': '$NASI',    # NASDAQ Summation Index
            'NYADL': '$NYADL',  # NYSE Advance-Decline Line
            'NYHGH': '$NYHGH',  # NYSE New Highs
            'NYLOW': '$NYLOW',  # NYSE New Lows
            'NYA50R': '$NYA50R', # NYSE % Above 50-day MA
            'NYA200R': '$NYA200R', # NYSE % Above 200-day MA
            'NYUPV': '$NYUPV',  # NYSE Up Volume
            'NYDNV': '$NYDNV',  # NYSE Down Volume
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

    def get_all_indicators(self):
        """Obtiene todos los indicadores de mercado"""
        results = {}
        
        print("Obteniendo indicadores de mercado NYSE...")
        print("-" * 50)
        
        for name, symbol in self.symbols.items():
            print(f"Obteniendo datos para {name} ({symbol})...")
            
            data = self.get_symbol_data(symbol)
            if data:
                metrics = self.extract_key_metrics(data)
                if metrics:
                    results[name] = metrics
                    print(f"✓ {name}: {metrics['current_price']}")
                else:
                    print(f"✗ Error procesando datos para {name}")
            else:
                print(f"✗ No se pudieron obtener datos para {name}")
        
        return results

    def print_market_summary(self, results):
        """Imprime un resumen de los indicadores de mercado"""
        print("\n" + "="*60)
        print("RESUMEN DE INDICADORES DE MERCADO NYSE")
        print("="*60)
        
        # Indicadores principales
        key_indicators = ['NYMO', 'NYMOT', 'NYSI']
        
        for indicator in key_indicators:
            if indicator in results:
                data = results[indicator]
                change_pct = data['change_pct'] or 0
                print(f"\n{indicator} - {data['name']}")
                print(f"  Valor actual: {data['current_price']}")
                print(f"  Cambio: {data['change']} ({change_pct:.2f}%)")
                print(f"  Fecha: {data['latest_trade']}")
        
        # Otros indicadores
        print("\nOTROS INDICADORES:")
        print("-" * 30)
        
        for name, data in results.items():
            if name not in key_indicators:
                change_pct = data['change_pct'] or 0
                print(f"{name}: {data['current_price']} ({change_pct:.2f}% cambio)")


# Función principal para probar
def main():
    extractor = NYSEDataExtractor()
    
    # Primero probamos con NYMOT (el que tienes en el JSON)
    print("Probando con NYMOT...")
    nymot_data = extractor.get_symbol_data('$NYMOT')
    
    if nymot_data:
        print("✓ Datos NYMOT obtenidos correctamente")
        metrics = extractor.extract_key_metrics(nymot_data)
        print(f"NYMOT - Valor actual: {metrics['current_price']}")
        print(f"Cambio: {metrics['change']} ({metrics['change_pct']:.2f}%)")
    
    # Luego obtenemos todos los indicadores
    print("\nObteniendo todos los indicadores...")
    all_results = extractor.get_all_indicators()
    
    if all_results:
        extractor.print_market_summary(all_results)
        
        # Guardamos los resultados en un archivo JSON
        with open('nyse_indicators.json', 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n✓ Resultados guardados en 'nyse_indicators.json'")
    
    return all_results

if __name__ == "__main__":
    results = main()
#!/usr/bin/env python3
"""
Herramienta de Diagnóstico Completo
Identifica problemas de conectividad, APIs y configuración
"""

import requests
import pandas as pd
import json
import subprocess
import sys
import socket
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

class DiagnosticTool:
    def __init__(self):
        self.results = {}
        
    def test_internet_connectivity(self):
        """Test conectividad básica a internet"""
        print("\n🌐 TESTING CONECTIVIDAD A INTERNET")
        print("=" * 50)
        
        test_sites = [
            ('Google', 'https://www.google.com'),
            ('Yahoo Finance', 'https://finance.yahoo.com'),
            ('Alpha Vantage', 'https://www.alphavantage.co'),
            ('Twelve Data', 'https://api.twelvedata.com'),
            ('FMP', 'https://financialmodelingprep.com')
        ]
        
        connectivity_results = {}
        
        for name, url in test_sites:
            try:
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if response.status_code == 200:
                    print(f"✅ {name}: OK ({response.status_code})")
                    connectivity_results[name] = 'OK'
                else:
                    print(f"⚠️ {name}: Status {response.status_code}")
                    connectivity_results[name] = f'Status {response.status_code}'
            except Exception as e:
                print(f"❌ {name}: {str(e)[:50]}")
                connectivity_results[name] = f'Error: {str(e)[:30]}'
        
        self.results['connectivity'] = connectivity_results
        return connectivity_results

    def test_dns_resolution(self):
        """Test resolución DNS"""
        print("\n🔍 TESTING RESOLUCIÓN DNS")
        print("=" * 50)
        
        domains = [
            'finance.yahoo.com',
            'www.alphavantage.co',
            'api.twelvedata.com',
            'financialmodelingprep.com'
        ]
        
        dns_results = {}
        
        for domain in domains:
            try:
                ip = socket.gethostbyname(domain)
                print(f"✅ {domain}: {ip}")
                dns_results[domain] = ip
            except Exception as e:
                print(f"❌ {domain}: {str(e)}")
                dns_results[domain] = f'Error: {str(e)}'
        
        self.results['dns'] = dns_results
        return dns_results

    def test_python_packages(self):
        """Test instalación y versiones de paquetes"""
        print("\n📦 TESTING PAQUETES PYTHON")
        print("=" * 50)
        
        packages = [
            'yfinance',
            'pandas', 
            'numpy',
            'requests'
        ]
        
        package_results = {}
        
        for package in packages:
            try:
                module = __import__(package)
                version = getattr(module, '__version__', 'Unknown')
                print(f"✅ {package}: {version}")
                package_results[package] = version
            except ImportError:
                print(f"❌ {package}: Not installed")
                package_results[package] = 'Not installed'
        
        self.results['packages'] = package_results
        return package_results

    def test_yfinance_directly(self):
        """Test directo de yfinance con debugging"""
        print("\n🔬 TESTING YFINANCE DIRECTAMENTE")
        print("=" * 50)
        
        try:
            import yfinance as yf
            
            print(f"yfinance version: {getattr(yf, '__version__', 'Unknown')}")
            
            # Test con un ticker simple
            print("\nTesting AAPL...")
            ticker = yf.Ticker('AAPL')
            
            # Intentar diferentes métodos
            methods_results = {}
            
            # Método 1: history básico
            try:
                hist = ticker.history(period='5d')
                print(f"✅ history(5d): {len(hist)} rows")
                methods_results['history_5d'] = f'{len(hist)} rows'
                if len(hist) > 0:
                    print(f"   Último precio: ${hist['Close'].iloc[-1]:.2f}")
            except Exception as e:
                print(f"❌ history(5d): {str(e)[:80]}")
                methods_results['history_5d'] = f'Error: {str(e)[:50]}'
            
            # Método 2: history con parámetros específicos
            try:
                hist2 = ticker.history(period='1mo', interval='1d', timeout=30)
                print(f"✅ history(1mo, timeout=30): {len(hist2)} rows")
                methods_results['history_1mo'] = f'{len(hist2)} rows'
            except Exception as e:
                print(f"❌ history(1mo, timeout=30): {str(e)[:80]}")
                methods_results['history_1mo'] = f'Error: {str(e)[:50]}'
            
            # Método 3: info
            try:
                info = ticker.info
                print(f"✅ info: Got {len(info)} fields")
                methods_results['info'] = f'{len(info)} fields'
            except Exception as e:
                print(f"❌ info: {str(e)[:80]}")
                methods_results['info'] = f'Error: {str(e)[:50]}'
            
            self.results['yfinance'] = methods_results
            return methods_results
            
        except ImportError:
            print("❌ yfinance no está instalado")
            return {'error': 'yfinance not installed'}

    def test_alpha_vantage_api(self, api_key):
        """Test Alpha Vantage API"""
        print("\n📈 TESTING ALPHA VANTAGE API")
        print("=" * 50)
        
        if not api_key:
            print("⏭️ No API key provided")
            return {'error': 'No API key'}
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': 'AAPL',
                'outputsize': 'compact',
                'apikey': api_key
            }
            
            print(f"Testing with API key: {api_key[:8]}...")
            response = requests.get(url, params=params, timeout=30)
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response keys: {list(data.keys())}")
                
                if 'Time Series (Daily)' in data:
                    series_count = len(data['Time Series (Daily)'])
                    print(f"✅ Got {series_count} data points")
                    return {'status': 'OK', 'data_points': series_count}
                elif 'Note' in data:
                    print(f"⚠️ API Limit: {data['Note']}")
                    return {'status': 'API Limit', 'message': data['Note']}
                elif 'Error Message' in data:
                    print(f"❌ Error: {data['Error Message']}")
                    return {'status': 'Error', 'message': data['Error Message']}
                else:
                    print(f"❌ Unexpected response: {data}")
                    return {'status': 'Unexpected', 'response': str(data)[:100]}
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return {'status': 'HTTP Error', 'code': response.status_code}
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            return {'status': 'Exception', 'error': str(e)}

    def test_alternative_apis(self):
        """Test APIs alternativas"""
        print("\n🔄 TESTING APIS ALTERNATIVAS")
        print("=" * 50)
        
        alternative_results = {}
        
        # Test Twelve Data
        print("\n📊 Twelve Data:")
        try:
            url = "https://api.twelvedata.com/time_series"
            params = {
                'symbol': 'AAPL',
                'interval': '1day',
                'outputsize': 5
            }
            
            response = requests.get(url, params=params, timeout=20)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'values' in data:
                    print(f"✅ Got {len(data['values'])} data points")
                    alternative_results['twelvedata'] = 'OK'
                else:
                    print(f"❌ No values in response: {data}")
                    alternative_results['twelvedata'] = 'No values'
            else:
                print(f"❌ Error: {response.status_code}")
                alternative_results['twelvedata'] = f'HTTP {response.status_code}'
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            alternative_results['twelvedata'] = f'Error: {str(e)[:30]}'
        
        # Test Financial Modeling Prep
        print("\n💰 Financial Modeling Prep:")
        try:
            url = "https://financialmodelingprep.com/api/v3/historical-price-full/AAPL"
            
            response = requests.get(url, timeout=20)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'historical' in data and data['historical']:
                    print(f"✅ Got {len(data['historical'])} data points")
                    alternative_results['fmp'] = 'OK'
                else:
                    print(f"❌ No historical data: {data}")
                    alternative_results['fmp'] = 'No historical'
            else:
                print(f"❌ Error: {response.status_code}")
                alternative_results['fmp'] = f'HTTP {response.status_code}'
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            alternative_results['fmp'] = f'Error: {str(e)[:30]}'
        
        self.results['alternatives'] = alternative_results
        return alternative_results

    def test_simple_requests(self):
        """Test requests simples a diferentes endpoints"""
        print("\n🔗 TESTING REQUESTS SIMPLES")
        print("=" * 50)
        
        simple_tests = [
            ('Yahoo Finance Homepage', 'https://finance.yahoo.com'),
            ('Yahoo Quote AAPL', 'https://finance.yahoo.com/quote/AAPL'),
            ('Alpha Vantage Demo', 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo'),
        ]
        
        simple_results = {}
        
        for name, url in simple_tests:
            try:
                response = requests.get(url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                print(f"✅ {name}: {response.status_code} ({len(response.content)} bytes)")
                simple_results[name] = f'{response.status_code} - {len(response.content)} bytes'
            except Exception as e:
                print(f"❌ {name}: {str(e)[:50]}")
                simple_results[name] = f'Error: {str(e)[:30]}'
        
        self.results['simple_requests'] = simple_results
        return simple_results

    def run_full_diagnostic(self, alpha_vantage_key=None):
        """Ejecutar diagnóstico completo"""
        print("🔧 DIAGNÓSTICO COMPLETO DEL SISTEMA")
        print("=" * 60)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Ejecutar todos los tests
        self.test_internet_connectivity()
        self.test_dns_resolution()
        self.test_python_packages()
        self.test_yfinance_directly()
        if alpha_vantage_key:
            self.test_alpha_vantage_api(alpha_vantage_key)
        self.test_alternative_apis()
        self.test_simple_requests()
        
        # Resumen final
        self.print_summary()
        
        # Guardar resultados
        self.save_results()

    def print_summary(self):
        """Imprimir resumen de resultados"""
        print("\n📋 RESUMEN DEL DIAGNÓSTICO")
        print("=" * 60)
        
        # Conectividad
        connectivity = self.results.get('connectivity', {})
        working_sites = sum(1 for v in connectivity.values() if v == 'OK')
        print(f"🌐 Conectividad: {working_sites}/{len(connectivity)} sitios accesibles")
        
        # DNS
        dns = self.results.get('dns', {})
        working_dns = sum(1 for v in dns.values() if not v.startswith('Error'))
        print(f"🔍 DNS: {working_dns}/{len(dns)} dominios resueltos")
        
        # Paquetes
        packages = self.results.get('packages', {})
        installed_packages = sum(1 for v in packages.values() if v != 'Not installed')
        print(f"📦 Paquetes: {installed_packages}/{len(packages)} instalados")
        
        # APIs alternativas
        alternatives = self.results.get('alternatives', {})
        working_apis = sum(1 for v in alternatives.values() if v == 'OK')
        print(f"🔄 APIs alternativas: {working_apis}/{len(alternatives)} funcionando")
        
        # Diagnóstico y recomendaciones
        print(f"\n💡 DIAGNÓSTICO:")
        
        if working_sites < len(connectivity) * 0.5:
            print("❌ PROBLEMA DE CONECTIVIDAD")
            print("   - Verificar conexión a internet")
            print("   - Revisar firewall/proxy")
            print("   - Intentar desde otra red")
        elif working_dns < len(dns) * 0.5:
            print("❌ PROBLEMA DE DNS")
            print("   - Cambiar DNS (8.8.8.8, 1.1.1.1)")
            print("   - Reiniciar conexión de red")
        elif installed_packages < len(packages):
            print("❌ PROBLEMA DE PAQUETES")
            print("   - Instalar paquetes faltantes")
            print("   - Actualizar pip")
        elif working_apis == 0:
            print("❌ TODAS LAS APIS FALLAN")
            print("   - Posible bloqueo de IP")
            print("   - Restricciones de red corporativa")
            print("   - Intentar desde otra ubicación")
        else:
            print("✅ SISTEMA PARECE OK")
            print("   - Problema específico con APIs financieras")
            print("   - Intentar con VPN")
            print("   - Verificar rate limits")

    def save_results(self):
        """Guardar resultados en archivo"""
        filename = f"diagnostic_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📁 Resultados guardados en: {filename}")

def main():
    print("🔧 HERRAMIENTA DE DIAGNÓSTICO")
    print("Identifica problemas con APIs financieras")
    print("=" * 50)
    
    diagnostic = DiagnosticTool()
    
    api_key = input("API key de Alpha Vantage (opcional): ").strip()
    if not api_key:
        api_key = None
    
    print("\nIniciando diagnóstico completo...")
    diagnostic.run_full_diagnostic(api_key)
    
    print(f"\n🏁 DIAGNÓSTICO COMPLETADO")
    print("Revisa el resumen arriba para identificar problemas")

if __name__ == "__main__":
    main()
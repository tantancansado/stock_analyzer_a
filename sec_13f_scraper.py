#!/usr/bin/env python3
"""
SEC 13F SCRAPER - Enhanced Edition
Scraper robusto de 13F filings usando SEC EDGAR
"""
import requests
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

class SEC13FScraper:
    """Scraper mejorado de 13F filings"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'TradingAnalyzer/1.0 (ale@tantancansado.com)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
        self.base_url = "https://data.sec.gov"
        self.edgar_url = "https://www.sec.gov"
        self.cache_dir = Path("data/institutional/holdings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_recent_filings(self, cik, filing_type='13F-HR', count=4):
        """
        Obtiene filings recientes scrapeando la página de browse-edgar
        """
        # URL de búsqueda de filings
        url = f"{self.edgar_url}/cgi-bin/browse-edgar"
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': filing_type,
            'dateb': '',
            'owner': 'exclude',
            'count': count,
            'search_text': ''
        }

        print(f"📡 Scraping filings for CIK {cik}...")

        try:
            time.sleep(0.15)  # Rate limit
            response = requests.get(url, params=params, headers=self.headers, timeout=15)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extraer nombre de la empresa
                company_info = soup.find('span', class_='companyName')
                entity_name = company_info.text.split('CIK')[0].strip() if company_info else 'Unknown'

                print(f"   ✅ {entity_name}")

                # Buscar tabla de filings
                filings_table = soup.find('table', class_='tableFile2')

                results = []
                if filings_table:
                    rows = filings_table.find_all('tr')[1:]  # Skip header

                    for row in rows[:count]:
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            filing_date = cells[3].text.strip()
                            form_type = cells[0].text.strip()

                            # Link al filing
                            doc_link = cells[1].find('a')
                            if doc_link:
                                doc_url = f"{self.edgar_url}{doc_link.get('href')}"

                                results.append({
                                    'form': form_type,
                                    'filing_date': filing_date,
                                    'url': doc_url
                                })

                return {
                    'cik': cik,
                    'entity_name': entity_name,
                    'filings': results
                }

            else:
                print(f"   ❌ Error {response.status_code}")
                return None

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return None

    def parse_13f_holdings_txt(self, accession_number, cik):
        """
        Parsea holdings de un 13F-HR filing

        Los 13F-HR incluyen un archivo XML o TXT con la lista de holdings
        """
        # Construir URL del filing
        cik_padded = str(cik).zfill(10)
        accession_clean = accession_number.replace('-', '')

        # URL del directorio del filing
        filing_url = f"{self.edgar_url}/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_number}&xbrl_type=v"

        print(f"   📄 Filing URL: {filing_url}")

        # Por ahora, retornamos estructura placeholder
        # En producción, aquí parsearíamos el XML/TXT real

        return {
            'filing_date': datetime.now().strftime('%Y-%m-%d'),
            'holdings': [],
            'total_value': 0
        }

    def quick_scan_whale(self, cik, whale_name):
        """Escaneo rápido de un whale - solo metadata"""
        print(f"\n🐋 {whale_name}")
        print("-" * 70)

        filings_data = self.get_recent_filings(cik)

        if not filings_data:
            return None

        # Cachear resultado
        cache_file = self.cache_dir / f"{cik}_metadata.json"
        with open(cache_file, 'w') as f:
            json.dump(filings_data, f, indent=2)

        recent_filing = filings_data['filings'][0] if filings_data['filings'] else None

        if recent_filing:
            print(f"   📅 Último filing: {recent_filing['filing_date']}")
            print(f"   📋 Form: {recent_filing['form']}")

        return filings_data

    def scan_all_whales(self):
        """Escanea todos los whales para obtener metadata de 13F"""
        from institutional_tracker import WHALE_INVESTORS

        print("🐋 ESCANEANDO WHALES - METADATA 13F")
        print("=" * 80)

        results = {}

        for cik, info in WHALE_INVESTORS.items():
            result = self.quick_scan_whale(cik, info['name'])

            if result:
                results[cik] = {
                    'name': info['name'],
                    'tier': info['tier'],
                    'filings': result
                }

            time.sleep(0.2)  # Rate limiting

        # Guardar resultados
        output_file = self.cache_dir.parent / f"whale_metadata_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Scan completado: {len(results)} whales procesados")
        print(f"💾 Guardado en: {output_file}")

        return results

    def build_ticker_holdings_index(self):
        """
        Construye índice inverso: ticker -> [whales que lo tienen]
        Útil para lookup rápido
        """
        print("\n🔨 CONSTRUYENDO ÍNDICE DE HOLDINGS POR TICKER")

        # TODO: Parsear holdings reales y construir índice
        # Por ahora, estructura placeholder

        ticker_index = {
            'AAPL': ['0001086364', '0000102909'],  # BlackRock, Vanguard
            'TSLA': ['0001649339'],  # ARK
            # ... más tickers
        }

        output_file = self.cache_dir.parent / "ticker_holdings_index.json"
        with open(output_file, 'w') as f:
            json.dump(ticker_index, f, indent=2)

        print(f"✅ Índice construido: {output_file}")

        return ticker_index


def main():
    """Main execution"""
    print("🏛️  SEC 13F SCRAPER")
    print("=" * 80)

    scraper = SEC13FScraper()

    print("\nOpciones:")
    print("1. Escanear todos los whales (metadata)")
    print("2. Ver filing específico")
    print("3. Test rápido (Berkshire Hathaway)")

    choice = input("\nSelecciona (1-3): ").strip()

    if choice == '1':
        scraper.scan_all_whales()
    elif choice == '2':
        cik = input("CIK del whale: ").strip()
        name = input("Nombre: ").strip()
        scraper.quick_scan_whale(cik, name)
    else:
        # Test con Berkshire
        print("\n🧪 TEST - Berkshire Hathaway")
        scraper.quick_scan_whale('0001067983', 'Berkshire Hathaway (Warren Buffett)')


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
13F HOLDINGS PARSER
Parsea archivos XML/TXT de 13F-HR para extraer holdings institucionales
"""
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import time
from pathlib import Path
from datetime import datetime

class Holdings13FParser:
    """Parser de holdings de 13F filings"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'TradingAnalyzer/1.0 (ale@tantancansado.com)',
        }
        self.edgar_url = "https://www.sec.gov"
        self.cache_dir = Path("data/institutional/holdings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # CUSIP to Ticker mapping cache
        self.cusip_cache = {}
        self.load_cusip_cache()

    def load_cusip_cache(self):
        """Carga cache de CUSIP->Ticker si existe"""
        cache_file = self.cache_dir / "cusip_to_ticker.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                self.cusip_cache = json.load(f)

    def save_cusip_cache(self):
        """Guarda cache de CUSIP->Ticker"""
        cache_file = self.cache_dir / "cusip_to_ticker.json"
        with open(cache_file, 'w') as f:
            json.dump(self.cusip_cache, f, indent=2)

    def cusip_to_ticker(self, cusip):
        """
        Convierte CUSIP a ticker usando OpenFIGI API (gratis)
        Cachea resultados para no repetir requests
        """
        if not cusip or cusip == 'N/A':
            return None

        # Check cache
        if cusip in self.cusip_cache:
            return self.cusip_cache[cusip]

        # Query OpenFIGI
        try:
            url = "https://api.openfigi.com/v3/mapping"
            payload = [{
                "idType": "ID_CUSIP",
                "idValue": cusip
            }]

            time.sleep(0.1)  # Rate limiting
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and 'data' in data[0]:
                    figi_data = data[0]['data']
                    if figi_data:
                        ticker = figi_data[0].get('ticker')
                        if ticker:
                            self.cusip_cache[cusip] = ticker
                            return ticker
        except Exception as e:
            print(f"   ⚠️  CUSIP lookup failed for {cusip}: {e}")

        return None

    def get_filing_document_urls(self, filing_url):
        """
        Obtiene URLs de documentos dentro de un filing
        Busca el information table (XML o TXT)
        """
        print(f"📄 Descargando índice de documentos...")

        try:
            time.sleep(0.15)
            response = requests.get(filing_url, headers=self.headers, timeout=15)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Buscar tabla de documentos
                doc_table = soup.find('table', class_='tableFile')

                if doc_table:
                    docs = []
                    rows = doc_table.find_all('tr')[1:]  # Skip header

                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            doc_type = cells[3].text.strip() if len(cells) > 3 else ''
                            doc_link = cells[2].find('a')

                            if doc_link:
                                doc_url = f"{self.edgar_url}{doc_link.get('href')}"
                                filename = cells[1].text.strip()

                                # Buscar information table
                                if 'informationtable' in filename.lower() or \
                                   'infotable' in filename.lower() or \
                                   doc_type == 'INFORMATION TABLE':
                                    docs.append({
                                        'filename': filename,
                                        'url': doc_url,
                                        'type': doc_type
                                    })

                    return docs

        except Exception as e:
            print(f"   ❌ Error: {e}")

        return []

    def parse_13f_xml(self, xml_url):
        """
        Parsea archivo XML de information table

        Estructura típica:
        <informationTable>
            <infoTable>
                <nameOfIssuer>APPLE INC</nameOfIssuer>
                <titleOfClass>COM</titleOfClass>
                <cusip>037833100</cusip>
                <value>45000000</value>
                <shrsOrPrnAmt>
                    <sshPrnamt>1000000</sshPrnamt>
                    <sshPrnamtType>SH</sshPrnamtType>
                </shrsOrPrnAmt>
            </infoTable>
        </informationTable>
        """
        print(f"   📊 Parseando XML...")

        try:
            time.sleep(0.15)
            response = requests.get(xml_url, headers=self.headers, timeout=15)

            if response.status_code == 200:
                # Parse XML
                root = ET.fromstring(response.content)

                holdings = []

                # Buscar todos los infoTable elements
                # Puede tener diferentes namespaces
                for info_table in root.iter():
                    if 'infotable' in info_table.tag.lower():
                        holding = self.extract_holding_from_element(info_table)
                        if holding:
                            holdings.append(holding)

                print(f"   ✅ {len(holdings)} holdings parseados")
                return holdings

        except Exception as e:
            print(f"   ❌ Error parseando XML: {e}")

        return []

    def extract_holding_from_element(self, element):
        """Extrae datos de un elemento infoTable"""
        try:
            holding = {}

            # Buscar campos (case insensitive)
            for child in element:
                tag = child.tag.lower().split('}')[-1]  # Remove namespace

                if 'nameofissuer' in tag:
                    holding['company_name'] = child.text.strip() if child.text else ''
                elif 'titleofclass' in tag:
                    holding['security_type'] = child.text.strip() if child.text else ''
                elif 'cusip' in tag:
                    holding['cusip'] = child.text.strip() if child.text else ''
                elif 'value' in tag and 'shrs' not in tag:
                    # Value en miles de dólares
                    holding['value'] = int(child.text) * 1000 if child.text else 0
                elif 'shrsorprnamt' in tag:
                    # Shares
                    for subchild in child:
                        subtag = subchild.tag.lower().split('}')[-1]
                        if 'sshprnamt' in subtag and 'type' not in subtag:
                            holding['shares'] = int(subchild.text) if subchild.text else 0

            # Solo retornar si tiene datos mínimos
            if holding.get('cusip') or holding.get('company_name'):
                return holding

        except Exception as e:
            pass

        return None

    def parse_13f_txt(self, txt_url):
        """
        Parsea archivo TXT de information table
        Formato tab-separated o fixed-width
        """
        print(f"   📊 Parseando TXT...")

        try:
            time.sleep(0.15)
            response = requests.get(txt_url, headers=self.headers, timeout=15)

            if response.status_code == 200:
                lines = response.text.split('\n')
                holdings = []

                # Buscar tabla (usualmente después de <TABLE>)
                in_table = False
                for line in lines:
                    if '<TABLE>' in line:
                        in_table = True
                        continue
                    if '</TABLE>' in line:
                        break

                    if in_table and line.strip():
                        # Parse line (simple splitting)
                        parts = re.split(r'\s{2,}|\t', line.strip())

                        if len(parts) >= 4:
                            # Formato típico: Company, Class, CUSIP, Value, Shares
                            holding = {
                                'company_name': parts[0],
                                'security_type': parts[1] if len(parts) > 1 else '',
                                'cusip': parts[2] if len(parts) > 2 else '',
                                'value': 0,
                                'shares': 0
                            }

                            # Intentar parsear value y shares
                            try:
                                if len(parts) > 3:
                                    holding['value'] = int(parts[3].replace(',', '')) * 1000
                                if len(parts) > 4:
                                    holding['shares'] = int(parts[4].replace(',', ''))
                            except:
                                pass

                            holdings.append(holding)

                print(f"   ✅ {len(holdings)} holdings parseados")
                return holdings

        except Exception as e:
            print(f"   ❌ Error parseando TXT: {e}")

        return []

    def parse_filing(self, filing_url):
        """
        Parsea un filing completo obteniendo todos los holdings
        """
        print(f"\n📋 Parseando filing: {filing_url}")

        # Obtener documentos del filing
        docs = self.get_filing_document_urls(filing_url)

        if not docs:
            print("   ⚠️  No se encontró information table")
            return []

        # Intentar parsear cada documento
        all_holdings = []

        for doc in docs:
            print(f"   📄 {doc['filename']}")

            if doc['filename'].endswith('.xml'):
                holdings = self.parse_13f_xml(doc['url'])
            elif doc['filename'].endswith('.txt'):
                holdings = self.parse_13f_txt(doc['url'])
            else:
                # Intentar XML primero
                holdings = self.parse_13f_xml(doc['url'])
                if not holdings:
                    holdings = self.parse_13f_txt(doc['url'])

            all_holdings.extend(holdings)

        # Enriquecer con tickers
        print(f"\n🔍 Convirtiendo CUSIPs a tickers...")
        for i, holding in enumerate(all_holdings[:20], 1):  # Límite 20 para demo
            cusip = holding.get('cusip')
            if cusip:
                ticker = self.cusip_to_ticker(cusip)
                holding['ticker'] = ticker
                if ticker:
                    print(f"   {i}. {cusip} → {ticker} ({holding['company_name'][:30]})")

        # Guardar cache de CUSIPs
        self.save_cusip_cache()

        return all_holdings

    def save_holdings(self, cik, whale_name, holdings, filing_date):
        """Guarda holdings parseados en JSON"""
        output = {
            'cik': cik,
            'whale_name': whale_name,
            'filing_date': filing_date,
            'holdings_count': len(holdings),
            'total_value': sum(h.get('value', 0) for h in holdings),
            'holdings': holdings
        }

        # Guardar por whale y fecha
        filename = f"{cik}_{filing_date.replace('-', '')}.json"
        output_path = self.cache_dir / filename

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n💾 Holdings guardados: {output_path}")
        print(f"   Total holdings: {len(holdings)}")
        print(f"   Total value: ${output['total_value']:,.0f}")

        return output_path


def demo_parse_berkshire():
    """Demo: parsear último 13F de Berkshire"""
    from sec_13f_scraper import SEC13FScraper

    print("🧪 DEMO: Parseando 13F de Berkshire Hathaway")
    print("=" * 80)

    # Obtener filing más reciente
    scraper = SEC13FScraper()
    filings_data = scraper.get_recent_filings('0001067983')

    if not filings_data or not filings_data['filings']:
        print("❌ No se pudieron obtener filings")
        return

    latest_filing = filings_data['filings'][0]

    print(f"\n📅 Último filing: {latest_filing['filing_date']}")
    print(f"📋 URL: {latest_filing['url']}")

    # Parsear holdings
    parser = Holdings13FParser()
    holdings = parser.parse_filing(latest_filing['url'])

    if holdings:
        # Guardar
        parser.save_holdings(
            cik='0001067983',
            whale_name='Berkshire Hathaway',
            holdings=holdings,
            filing_date=latest_filing['filing_date']
        )

        # Top 10 holdings
        print(f"\n🏆 TOP 10 HOLDINGS DE BERKSHIRE:")
        print("-" * 80)

        sorted_holdings = sorted(holdings, key=lambda x: x.get('value', 0), reverse=True)

        for i, h in enumerate(sorted_holdings[:10], 1):
            ticker = h.get('ticker', 'N/A')
            company = h['company_name'][:40]
            value = h.get('value', 0)
            shares = h.get('shares', 0)

            print(f"{i:2}. {ticker:6} - {company:40} ${value:>15,} ({shares:,} shares)")

    return holdings


if __name__ == "__main__":
    demo_parse_berkshire()

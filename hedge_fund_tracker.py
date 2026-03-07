#!/usr/bin/env python3
"""
hedge_fund_tracker.py
─────────────────────
Descarga y parsea 13F-HR filings del SEC EDGAR para los principales
fondos de valor y calidad. Genera docs/hedge_fund_holdings.csv y
docs/hedge_fund_summary.json para el pipeline diario.

Fuentes:
  - SEC EDGAR submissions JSON API (oficial, sin auth, sin límite estricto)
  - OpenFIGI API (CUSIP → ticker, gratis sin API key)

Ejecución local:
  python hedge_fund_tracker.py

GitHub Actions: ver .github/workflows/hedge_funds.yml
"""

import requests
import json
import time
import os
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

# SEC exige User-Agent identificativo (email real o dominio)
SEC_HEADERS = {
    'User-Agent': 'StockAnalyzer ale@tantancansado.com',
    'Accept-Encoding': 'gzip, deflate',
}

EDGAR_DATA  = 'https://data.sec.gov'
EDGAR_FILES = 'https://www.sec.gov/Archives/edgar/data'
OPENFIGI    = 'https://api.openfigi.com/v3/mapping'

OUTPUT_DIR  = Path('docs')
CACHE_DIR   = Path('data/institutional/holdings')

# Fondos VALUE/QUALITY — los más relevantes para el sistema
# Se excluyen mega-índices (BlackRock, Vanguard) porque su universo
# no aporta señal de stock-picking diferencial.
VALUE_FUNDS = {
    '0001067983': 'Berkshire Hathaway (Buffett)',
    '0001336528': 'Pershing Square (Ackman)',
    '0001567892': 'Third Point (Loeb)',
    '0001079114': 'Appaloosa (Tepper)',
    '0001061219': 'Baupost Group (Klarman)',
    '0001159191': 'Lone Pine Capital',
    '0001013542': 'Viking Global',
    '0001336471': 'Coatue Management',
}

# ── Helpers SEC EDGAR ─────────────────────────────────────────────────────────

def _get(url: str, **kw) -> "requests.Response | None":
    """GET con reintentos y respeto al rate limit de SEC (max 10 req/s)."""
    time.sleep(0.15)
    try:
        r = requests.get(url, headers=SEC_HEADERS, timeout=20, **kw)
        r.raise_for_status()
        return r
    except requests.HTTPError as e:
        print(f'    HTTP {e.response.status_code}: {url}')
        return None
    except Exception as e:
        print(f'    Error: {e}')
        return None


def get_latest_13f(cik: str) -> "tuple[str, str] | None":
    """
    Devuelve (accession_number, filing_date) del 13F-HR más reciente.
    Usa la API JSON de submissions de SEC (más robusta que HTML scraping).
    """
    url = f'{EDGAR_DATA}/submissions/CIK{cik}.json'
    r = _get(url)
    if not r:
        return None

    data = r.json()
    recent = data.get('filings', {}).get('recent', {})
    forms      = recent.get('form', [])
    dates      = recent.get('filingDate', [])
    accessions = recent.get('accessionNumber', [])

    for form, date, acc in zip(forms, dates, accessions):
        if form == '13F-HR':
            return acc, date

    # Si no está en 'recent', buscar en archivos paginados
    files = data.get('filings', {}).get('files', [])
    for page in files:
        page_url = f"{EDGAR_DATA}/submissions/{page['name']}"
        pr = _get(page_url)
        if not pr:
            continue
        pd_data = pr.json()
        forms2      = pd_data.get('form', [])
        dates2      = pd_data.get('filingDate', [])
        accessions2 = pd_data.get('accessionNumber', [])
        for form, date, acc in zip(forms2, dates2, accessions2):
            if form == '13F-HR':
                return acc, date

    return None


def get_infotable_url(cik: str, accession: str) -> "str | None":
    """
    Encuentra la URL del archivo XML de information table dentro del filing.
    Usa el índice JSON del filing.
    """
    cik_num     = str(int(cik))          # sin zeros: '0001067983' → '1067983'
    acc_no_dash = accession.replace('-', '')  # '0001067983-24-000001' → '000106798324000001'

    # Índice JSON del filing
    idx_url = f'{EDGAR_FILES}/{cik_num}/{acc_no_dash}/{accession}-index.json'
    r = _get(idx_url)

    if r:
        try:
            data = r.json()
            items = data.get('directory', {}).get('item', [])
            # Prioridad 1: archivo con 'infotable' en el nombre
            for item in items:
                name = item.get('name', '').lower()
                if 'infotable' in name and name.endswith('.xml'):
                    return f'{EDGAR_FILES}/{cik_num}/{acc_no_dash}/{item["name"]}'
            # Prioridad 2: cualquier XML secundario (no el primary_doc)
            for item in items:
                name = item.get('name', '').lower()
                if name.endswith('.xml') and 'primary' not in name:
                    return f'{EDGAR_FILES}/{cik_num}/{acc_no_dash}/{item["name"]}'
        except Exception:
            pass

    # Fallback: scraping HTML del directorio
    dir_url = f'{EDGAR_FILES}/{cik_num}/{acc_no_dash}/'
    r2 = _get(dir_url)
    if r2:
        import re
        matches = re.findall(r'href="([^"]+\.xml)"', r2.text, re.I)
        for m in matches:
            if 'infotable' in m.lower() or 'informationtable' in m.lower():
                base = m if m.startswith('http') else f'{EDGAR_FILES}/{cik_num}/{acc_no_dash}/{m.split("/")[-1]}'
                return base
        # Cualquier XML que no sea el primary_doc
        for m in matches:
            fname = m.split('/')[-1].lower()
            if fname.endswith('.xml') and 'primary' not in fname:
                return f'{EDGAR_FILES}/{cik_num}/{acc_no_dash}/{m.split("/")[-1]}'

    return None


# ── Parser XML 13F ────────────────────────────────────────────────────────────

def parse_infotable_xml(xml_bytes: bytes) -> list[dict]:
    """Parsea el XML de information table y devuelve lista de holdings."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f'    XML parse error: {e}')
        return []

    holdings = []
    for elem in root.iter():
        tag = elem.tag.lower().split('}')[-1]  # strip namespace
        if tag != 'infotable':
            continue

        h: dict = {}
        for child in elem:
            ctag = child.tag.lower().split('}')[-1]
            txt  = (child.text or '').strip()

            if ctag == 'nameofissuer':
                h['name'] = txt.upper()
            elif ctag == 'cusip':
                h['cusip'] = txt
            elif ctag == 'value':
                try:
                    h['value_usd'] = int(txt.replace(',', ''))
                except ValueError:
                    h['value_usd'] = 0
            elif ctag == 'shrsorprnamt':
                for sub in child:
                    stag = sub.tag.lower().split('}')[-1]
                    if 'sshprnamt' in stag and 'type' not in stag:
                        try:
                            h['shares'] = int((sub.text or '0').replace(',', ''))
                        except ValueError:
                            h['shares'] = 0

        if h.get('cusip') or h.get('name'):
            h.setdefault('cusip', '')
            h.setdefault('name', '')
            h.setdefault('value_usd', 0)
            h.setdefault('shares', 0)
            holdings.append(h)

    return holdings


# ── CUSIP → Ticker via OpenFIGI ───────────────────────────────────────────────

_CUSIP_CACHE: dict[str, str] = {}
_CACHE_FILE  = CACHE_DIR / 'cusip_to_ticker.json'


def _load_cusip_cache():
    if _CACHE_FILE.exists():
        with open(_CACHE_FILE) as f:
            _CUSIP_CACHE.update(json.load(f))


def _save_cusip_cache():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, 'w') as f:
        json.dump(_CUSIP_CACHE, f)


def batch_cusip_to_ticker(cusips: list[str]) -> dict[str, str]:
    """
    Resuelve lista de CUSIPs → tickers usando OpenFIGI.
    Gratis sin API key (25 req/min). Usa caché persistente.
    """
    result: dict[str, str] = {}
    to_fetch = [c for c in cusips if c and c not in _CUSIP_CACHE]

    # Batches de 10 (límite OpenFIGI sin API key)
    for i in range(0, len(to_fetch), 10):
        batch = to_fetch[i:i + 10]
        payload = [{'idType': 'ID_CUSIP', 'idValue': c} for c in batch]

        try:
            r = requests.post(
                OPENFIGI, json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=20,
            )
            if r.status_code == 429:
                print('    OpenFIGI rate limit — esperando 65s...')
                time.sleep(65)
                r = requests.post(OPENFIGI, json=payload,
                                  headers={'Content-Type': 'application/json'}, timeout=20)

            if r.status_code == 200:
                for cusip, item in zip(batch, r.json()):
                    ticker = ''
                    for entry in item.get('data', []):
                        # Preferir Common Stock en bolsas US
                        if entry.get('securityType') in ('Common Stock', 'ETP') and \
                           entry.get('exchCode', '') in ('US', 'UN', 'UQ', 'UA', 'UP', 'UR', 'UW'):
                            ticker = entry.get('ticker', '')
                            break
                    if not ticker:
                        data = item.get('data', [])
                        ticker = data[0].get('ticker', '') if data else ''
                    _CUSIP_CACHE[cusip] = ticker
            else:
                for c in batch:
                    _CUSIP_CACHE[c] = ''

        except Exception as e:
            print(f'    OpenFIGI error: {e}')
            for c in batch:
                _CUSIP_CACHE[c] = ''

        time.sleep(2.5)  # respeto rate limit OpenFIGI

    _save_cusip_cache()

    for c in cusips:
        result[c] = _CUSIP_CACHE.get(c, '')
    return result


# ── Pipeline principal ────────────────────────────────────────────────────────

def scrape_fund(cik: str, fund_name: str) -> list[dict]:
    print(f'\n🐋  {fund_name}  (CIK {cik})')

    # 1. Obtener accession number del último 13F
    info = get_latest_13f(cik)
    if not info:
        print('    ⚠ No se encontró 13F-HR')
        return []
    accession, filing_date = info
    print(f'    13F: {accession}  filed {filing_date}')

    # 2. Localizar el XML de information table
    xml_url = get_infotable_url(cik, accession)
    if not xml_url:
        print('    ⚠ No se encontró infotable XML')
        return []
    print(f'    XML: {xml_url}')

    # 3. Descargar y parsear XML
    r = _get(xml_url)
    if not r:
        return []
    holdings = parse_infotable_xml(r.content)
    if not holdings:
        print('    ⚠ Sin holdings en el XML')
        return []
    print(f'    Holdings parseados: {len(holdings)}')

    # 4. Resolver CUSIP → ticker
    cusips = [h['cusip'] for h in holdings if h['cusip']]
    ticker_map = batch_cusip_to_ticker(list(set(cusips)))
    matched = sum(1 for t in ticker_map.values() if t)
    print(f'    Tickers resueltos: {matched}/{len(set(cusips))}')

    # 5. Calcular portfolio %
    total_value = sum(h['value_usd'] for h in holdings) or 1
    rows = []
    for h in holdings:
        ticker = ticker_map.get(h['cusip'], '')
        pct = round(h['value_usd'] / total_value * 100, 3)
        rows.append({
            'fund':          fund_name,
            'cik':           cik,
            'filing_date':   filing_date,
            'ticker':        ticker,
            'name':          h['name'],
            'cusip':         h['cusip'],
            'value_usd':     h['value_usd'],
            'shares':        h['shares'],
            'portfolio_pct': pct,
        })

    return sorted(rows, key=lambda x: -x['value_usd'])


def main():
    print('═' * 70)
    print('  HEDGE FUND 13F TRACKER — SEC EDGAR')
    print(f'  {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}')
    print('═' * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _load_cusip_cache()

    all_rows: list[dict] = []

    for cik, name in VALUE_FUNDS.items():
        rows = scrape_fund(cik, name)
        all_rows.extend(rows)
        time.sleep(1)

    if not all_rows:
        print('\n⚠ No se obtuvo ningún dato')
        return

    df = pd.DataFrame(all_rows)

    # ── CSV completo ──────────────────────────────────────────────────────────
    out_csv = OUTPUT_DIR / 'hedge_fund_holdings.csv'
    df.to_csv(out_csv, index=False)
    print(f'\n✅ {len(df)} filas → {out_csv}')

    # ── Resumen: stocks en múltiples fondos ───────────────────────────────────
    has_ticker = df[df['ticker'] != '']
    if has_ticker.empty:
        print('⚠ Ningún CUSIP resuelto a ticker')
        return

    summary_df = (
        has_ticker
        .groupby('ticker')
        .agg(
            funds_count      = ('fund', 'nunique'),
            funds_list       = ('fund', lambda x: ' | '.join(sorted(set(x)))),
            total_value_m    = ('value_usd', lambda x: round(x.sum() / 1e6, 1)),
            avg_portfolio_pct= ('portfolio_pct', 'mean'),
            company_name     = ('name', 'first'),
            latest_date      = ('filing_date', 'max'),
        )
        .reset_index()
        .sort_values(['funds_count', 'total_value_m'], ascending=False)
    )

    summary_csv = OUTPUT_DIR / 'hedge_fund_summary.csv'
    summary_df.to_csv(summary_csv, index=False)

    # JSON para la API
    summary_json = {
        'generated_at':   datetime.utcnow().isoformat() + 'Z',
        'funds_scraped':  list(VALUE_FUNDS.values()),
        'holdings_count': len(df),
        'top_consensus':  summary_df.head(40).to_dict('records'),
    }
    json_path = OUTPUT_DIR / 'hedge_fund_summary.json'
    with open(json_path, 'w') as f:
        json.dump(summary_json, f, indent=2)

    print(f'✅ Resumen → {summary_csv}  +  {json_path}')
    print(f'\n🏆 TOP 10 CONSENSUS (más fondos holding):')
    print('-' * 65)
    for _, row in summary_df.head(10).iterrows():
        funds_n = int(row['funds_count'])
        val_m   = row['total_value_m']
        ticker  = row['ticker']
        name    = row['company_name'][:35]
        print(f"  {ticker:6}  {name:35}  {funds_n} fondos  ${val_m:,.0f}M")


if __name__ == '__main__':
    main()

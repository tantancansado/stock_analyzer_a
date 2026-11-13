#!/usr/bin/env python3
"""
hedge_fund_tracker.py
─────────────────────
Carteras 13F de los inversores que sigue Dataroma, sacadas de la SEC, y qué
han hecho en el último trimestre con cada valor: entra, amplía, reduce o sale.

Fuentes:
  - SEC EDGAR (submissions JSON y la information table de cada 13F-HR)
  - OpenFIGI (CUSIP → ticker, gratis sin clave, con caché en el repo)
  - yfinance, solo para saber si hubo un split entre dos trimestres

Salidas:
  docs/hedge_fund_holdings.csv  lo que tiene cada gestora hoy, con su cambio
  docs/hedge_fund_summary.json  por ticker: quién la tiene, quién compra y quién vende
  data/institutional/13f_gestores.json  estado: las dos últimas carteras de cada una

Dato de la ficha, no cuenta en la nota: no está medido que seguirles dé ventaja
y llega hasta 45 días después del cierre del trimestre.
"""

import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

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
ESTADO      = Path('data/institutional/13f_gestores.json')

# Los de dataroma.com/m/managers.php (13-nov-2026), con el CIK comprobado contra
# la SEC ese día: nombre del registro y un 13F-HR de 2026. Antes había 8 fondos
# y 6 CIK eran de otra entidad (el de «Third Point» era una farmacéutica y el de
# «Appaloosa», Greenlight hasta 2024), así que la ficha solo veía a Berkshire.
# Una gestora que cambió de entidad lleva las dos: Pershing presentó el T1 con
# una y el T2 con otra, y sin la vieja no habría trimestre con que comparar.
# Fuera: Century Management y Aquamarine (sin 13F desde 2022 o sin registro) y
# Makaira (vacía en Dataroma).
GESTORES: dict[str, tuple[str, ...]] = {
    'Berkshire Hathaway (Buffett)':     ('0001067983',),
    'Dodge & Cox':                      ('0000200217',),
    'Oakmark (Nygren)':                 ('0000813917',),
    'Davis Advisors (Chris Davis)':     ('0001036325',),
    'Tweedy Browne':                    ('0000732905',),
    'Patient Capital (McLemore)':       ('0001854794',),
    'Miller Value Partners (Bill Miller)': ('0001135778',),
    'Hillman Capital':                  ('0001314620',),
    'Jensen Investment':                ('0001106129',),
    'Polen Capital':                    ('0001034524',),
    'Mairs & Power':                    ('0001070134',),
    'Pzena':                            ('0001027796',),
    'Lindsell Train':                   ('0001484150',),
    'Fundsmith (Terry Smith)':          ('0001569205',),
    'Akre Capital':                     ('0001112520',),
    'Markel (Gayner)':                  ('0001096343',),
    'Gardner Russo & Quinn (Russo)':    ('0000860643',),
    'Ruane Cunniff (Sequoia)':          ('0001720792',),
    'Yacktman':                         ('0000905567',),
    'First Eagle':                      ('0001325447',),
    'First Pacific Advisors':           ('0001377581',),
    'Southeastern (Hawkins)':           ('0000807985',),
    'Weitz':                            ('0000883965',),
    'Baupost (Klarman)':                ('0001061768',),
    'Pershing Square (Ackman)':         ('0002026053', '0001336528'),
    'Himalaya Capital (Li Lu)':         ('0001709323',),
    'H&H International (Duan Yongping)': ('0001759760',),
    'Pabrai (Dalal Street)':            ('0001549575',),
    'Fairfax (Watsa)':                  ('0000915191',),
    'Fairholme (Berkowitz)':            ('0001056831',),
    'Greenlight (Einhorn)':             ('0001489933',),
    'Third Point (Loeb)':               ('0001040273',),
    'Appaloosa (Tepper)':               ('0001656456',),
    'Lone Pine (Mandel)':               ('0001061165',),
    'Viking Global':                    ('0001103804',),
    'Tiger Global (Coleman)':           ('0001167483',),
    'TCI (Chris Hohn)':                 ('0001647251',),
    'ValueAct':                         ('0001418814',),
    'Trian (Peltz)':                    ('0001345471',),
    'Icahn':                            ('0000921669',),
    'Cooperman':                        ('0000898382',),
    'Oaktree (Howard Marks)':           ('0000949509',),
    'Gates Foundation Trust':           ('0001166559',),
    'Abrams Bison':                     ('0001317588',),
    'Abrams Capital (David Abrams)':    ('0001358706',),
    'AKO Capital':                      ('0001376879',),
    'AltaRock Partners':                ('0001631014',),
    'Atlantic Investment (Roepers)':    ('0001063296',),
    'Oakcliff Capital':                 ('0001657335',),
    'Semper Augustus (Bloomstran)':     ('0001115373',),
    'CAS Investment (Sosin)':           ('0001697591',),
    'Matrix Asset Advisors':            ('0001016287',),
    'Wedgewood Partners':               ('0000859804',),
    'ShawSpring Partners':              ('0001766908',),
    'Chou Associates':                  ('0001389403',),
    'Giverny Capital (Rochon)':         ('0001641864',),
    'Brave Warrior (Greenberg)':        ('0001553733',),
    'Engaged Capital':                  ('0001559771',),
    'Greenhaven Associates':            ('0000846222',),
    'Conifer Management':               ('0001773994',),
    'Sound Shore':                      ('0000820124',),
    'Durable Capital (Ellenbogen)':     ('0001798849',),
    'Egerton Capital':                  ('0001581811',),
    'Ariel Investments':                ('0000936753',),
    'Greenlea Lane (Tarasoff)':         ('0001766504',),
    'Kahn Brothers':                    ('0001039565',),
    'Maverick Capital':                 ('0000934639',),
    'Muhlenkamp':                       ('0001133219',),
    'Punch Card (Norbert Lou)':         ('0001631664',),
    'Dorsey Asset Management':          ('0001671657',),
    'RV Capital (Vinall)':              ('0001766596',),
    'Causeway (Ketterer)':              ('0001165797',),
    'Check Capital':                    ('0001032814',),
    'Third Avenue':                     ('0001099281',),
    'Torray':                           ('0000098758',),
    'Triple Frond Partners':            ('0001454502',),
    'Valley Forge Capital':             ('0001697868',),
    'Vulcan Value Partners':            ('0001556785',),
    'Cantillon':                        ('0001279936',),
}

# Por debajo de esto, un cambio de acciones es ruido (dividendos reinvertidos,
# ajustes de custodia), no una decisión.
CAMBIO_MINIMO_PCT = 1.0
# Fuera de esta banda, el precio implícito entre dos trimestres puede ser un
# split y se pregunta a yfinance antes de llamar «amplía» a un 10 por 1.
BANDA_SIN_SPLIT = (0.8, 1.25)

COMPRAS = ('NUEVA', 'AMPLIA')
VENTAS  = ('REDUCE', 'VENDE')


# ── SEC EDGAR ─────────────────────────────────────────────────────────────────

def _get(url: str, **kw) -> "requests.Response | None":
    """GET con reintentos y respeto al rate limit de SEC (max 10 req/s)."""
    time.sleep(0.15)
    try:
        r = requests.get(url, headers=SEC_HEADERS, timeout=30, **kw)
        r.raise_for_status()
        return r
    except requests.HTTPError as e:
        print(f'    HTTP {e.response.status_code}: {url}')
        return None
    except Exception as e:
        print(f'    Error: {e}')
        return None


def presentaciones_13f(ciks: tuple[str, ...]) -> "list[dict] | None":
    """El 13F-HR original más reciente de cada trimestre, del más nuevo al más
    viejo, juntando todas las entidades de la gestora. None si la SEC no
    contestó por alguna: sin saber si hay una nueva, no se puede decir que no."""
    por_periodo: dict[str, dict] = {}
    for cik in ciks:
        r = _get(f'{EDGAR_DATA}/submissions/CIK{cik}.json')
        if not r:
            return None
        rec = r.json().get('filings', {}).get('recent', {})
        for form, fecha, periodo, acc in zip(rec.get('form', []), rec.get('filingDate', []),
                                             rec.get('reportDate', []), rec.get('accessionNumber', [])):
            # Las enmiendas (13F-HR/A) se ignoran: unas reemplazan y otras
            # añaden, y el original es lo que se publicó a su plazo.
            if form != '13F-HR' or not periodo:
                continue
            previa = por_periodo.get(periodo)
            if previa is None or fecha > previa['filing_date']:
                por_periodo[periodo] = {'cik': cik, 'accession': acc,
                                        'filing_date': fecha, 'periodo': periodo}
    return [por_periodo[p] for p in sorted(por_periodo, reverse=True)]


def get_infotable_url(cik: str, accession: str) -> "str | None":
    """URL del XML de information table dentro del filing."""
    cik_num     = str(int(cik))
    acc_no_dash = accession.replace('-', '')
    base        = f'{EDGAR_FILES}/{cik_num}/{acc_no_dash}'

    r = _get(f'{base}/{accession}-index.json')
    if r:
        try:
            items = r.json().get('directory', {}).get('item', [])
            nombres = [i.get('name', '') for i in items]
            for n in nombres:
                if 'infotable' in n.lower() and n.lower().endswith('.xml'):
                    return f'{base}/{n}'
            for n in nombres:
                if n.lower().endswith('.xml') and 'primary' not in n.lower():
                    return f'{base}/{n}'
        except Exception:
            pass

    r2 = _get(f'{base}/')
    if r2:
        import re
        matches = [m.split('/')[-1] for m in re.findall(r'href="([^"]+\.xml)"', r2.text, re.I)]
        for m in matches:
            if 'infotable' in m.lower() or 'informationtable' in m.lower():
                return f'{base}/{m}'
        for m in matches:
            if 'primary' not in m.lower():
                return f'{base}/{m}'
    return None


def parse_infotable_xml(xml_bytes: bytes) -> "dict[str, list] | None":
    """{cusip: [nombre, acciones, valor_usd]} sumando las filas de un mismo
    valor (una gestora declara una por cada subgestor). Fuera las opciones
    (una put no es tener la acción) y los bonos (PRN es nominal, no acciones).
    None si el XML no se puede leer: no es lo mismo que una cartera vacía."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f'    XML parse error: {e}')
        return None

    def _num(txt):
        try:
            return int(float((txt or '0').replace(',', '')))
        except ValueError:
            return 0

    pos: dict[str, list] = {}
    for elem in root.iter():
        if elem.tag.lower().split('}')[-1] != 'infotable':
            continue
        nombre = cusip = ''
        valor = acciones = 0
        tipo = 'SH'
        opcion = False
        for child in elem:
            ctag = child.tag.lower().split('}')[-1]
            txt = (child.text or '').strip()
            if ctag == 'nameofissuer':
                nombre = txt.upper()
            elif ctag == 'cusip':
                cusip = txt.upper()
            elif ctag == 'value':
                valor = _num(txt)
            elif ctag == 'putcall' and txt:
                opcion = True
            elif ctag == 'shrsorprnamt':
                for sub in child:
                    stag = sub.tag.lower().split('}')[-1]
                    if stag == 'sshprnamt':
                        acciones = _num(sub.text)
                    elif stag == 'sshprnamttype':
                        tipo = (sub.text or 'SH').strip().upper()
        if not cusip or opcion or tipo != 'SH':
            continue
        if cusip in pos:
            pos[cusip][1] += acciones
            pos[cusip][2] += valor
        else:
            pos[cusip] = [nombre, acciones, valor]
    return pos


def descargar_cartera(cik: str, accession: str) -> "dict[str, list] | None":
    url = get_infotable_url(cik, accession)
    if not url:
        print('    ⚠ No se encontró infotable XML')
        return None
    r = _get(url)
    if not r:
        return None
    return parse_infotable_xml(r.content)


# ── CUSIP → ticker (OpenFIGI) ─────────────────────────────────────────────────

_CUSIP_CACHE: dict[str, str] = {}
_CACHE_FILE  = CACHE_DIR / 'cusip_to_ticker.json'


def _load_cusip_cache():
    if _CACHE_FILE.exists():
        with open(_CACHE_FILE) as f:
            _CUSIP_CACHE.update(json.load(f))


def _save_cusip_cache():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, 'w') as f:
        json.dump(_CUSIP_CACHE, f, indent=0, sort_keys=True)


def _ticker_de_figi(item: dict) -> "str | None":
    """Ticker de la respuesta de OpenFIGI; '' si dice que no existe y None si
    no respondió (eso se vuelve a preguntar, no se guarda como «no tiene»)."""
    if 'data' not in item:
        return '' if 'warning' in item else None
    datos = item['data']
    for e in datos:
        if e.get('exchCode') == 'US':
            return str(e.get('ticker', '')).replace('/', '-')
    return str(datos[0].get('ticker', '')).replace('/', '-') if datos else ''


def batch_cusip_to_ticker(cusips: list[str]) -> dict[str, str]:
    """CUSIP → ticker de bolsa de EE. UU. Gratis sin clave (25 peticiones por
    minuto, 10 valores cada una) y con caché persistente."""
    pendientes = sorted({c for c in cusips if c and c not in _CUSIP_CACHE})
    if pendientes:
        print(f'  OpenFIGI: {len(pendientes)} CUSIP nuevos (~{len(pendientes) // 250 + 1} min)')
    for i in range(0, len(pendientes), 10):
        lote = pendientes[i:i + 10]
        payload = [{'idType': 'ID_CUSIP', 'idValue': c, 'exchCode': 'US'} for c in lote]
        try:
            r = requests.post(OPENFIGI, json=payload, timeout=20,
                              headers={'Content-Type': 'application/json'})
            if r.status_code == 429:
                print('    OpenFIGI rate limit — esperando 65s...')
                time.sleep(65)
                r = requests.post(OPENFIGI, json=payload, timeout=20,
                                  headers={'Content-Type': 'application/json'})
            if r.status_code == 200:
                for c, item in zip(lote, r.json()):
                    t = _ticker_de_figi(item)
                    if t is not None:
                        _CUSIP_CACHE[c] = t
            else:
                print(f'    OpenFIGI HTTP {r.status_code}: se reintenta mañana')
        except Exception as e:
            print(f'    OpenFIGI error: {e}')
        time.sleep(2.5)
        if i and i % 500 == 0:
            _save_cusip_cache()
    _save_cusip_cache()
    return {c: _CUSIP_CACHE.get(c, '') for c in cusips}


# ── Splits ────────────────────────────────────────────────────────────────────

def factor_split(ticker: str, desde: str, hasta: str) -> "float | None":
    """Producto de los splits entre dos cierres de trimestre (1.0 si no hubo).
    None si yfinance no contesta: entonces el cambio no se sabe."""
    if not ticker:
        return None
    try:
        import yfinance as yf
        s = yf.Ticker(ticker).splits
    except Exception:
        return None
    if s is None:
        return None
    f = 1.0
    for fecha, ratio in s.items():
        dia = pd.Timestamp(fecha).strftime('%Y-%m-%d')
        if desde < dia <= hasta and ratio and ratio > 0:
            f *= float(ratio)
    return f


def _sospecha_split(ahora: list, antes: list) -> bool:
    """El precio implícito (valor / acciones) cambió tanto que puede ser un split."""
    if not (ahora[1] and antes[1] and ahora[2] and antes[2]):
        return False
    p = (ahora[2] / ahora[1]) / (antes[2] / antes[1])
    return not (BANDA_SIN_SPLIT[0] <= p <= BANDA_SIN_SPLIT[1])


# ── Qué ha hecho cada gestora ─────────────────────────────────────────────────

def comparar(ahora: dict, antes: "dict | None", periodo: str, periodo_antes: "str | None",
             tickers: dict[str, str], splits: dict[str, "float | None"]) -> list[dict]:
    """Una fila por valor: lo que tiene hoy y lo que vendió entero.

    `activity` vacío = no se sabe (sin trimestre anterior, o un posible split
    que yfinance no confirmó). Un «no lo sé» no se convierte en «mantiene»."""
    filas = []
    total = sum(v[2] for v in ahora.values()) or 1
    for cusip, (nombre, acciones, valor) in ahora.items():
        fila = {'ticker': tickers.get(cusip, ''), 'name': nombre, 'cusip': cusip,
                'value_usd': valor, 'shares': acciones,
                'portfolio_pct': round(valor / total * 100, 3),
                'shares_prev': None, 'change_pct': None, 'activity': ''}
        if antes is None:
            filas.append(fila)
            continue
        previa = antes.get(cusip)
        if previa is None or not previa[1]:
            fila['activity'] = 'NUEVA'
            filas.append(fila)
            continue
        fila['shares_prev'] = previa[1]
        f = 1.0
        if acciones != previa[1] and _sospecha_split([nombre, acciones, valor], previa):
            clave = f'{cusip}|{periodo_antes}|{periodo}'
            if clave not in splits:
                splits[clave] = factor_split(tickers.get(cusip, ''), periodo_antes, periodo)
            f = splits[clave]
            if f is None:
                filas.append(fila)
                continue
        cambio = (acciones / (previa[1] * f) - 1) * 100
        fila['change_pct'] = round(cambio, 1)
        fila['activity'] = ('MANTIENE' if abs(cambio) < CAMBIO_MINIMO_PCT
                            else 'AMPLIA' if cambio > 0 else 'REDUCE')
        filas.append(fila)
    if antes is not None:
        for cusip, (nombre, acciones, valor) in antes.items():
            if cusip not in ahora and acciones:
                filas.append({'ticker': tickers.get(cusip, ''), 'name': nombre, 'cusip': cusip,
                              'value_usd': 0, 'shares': 0, 'portfolio_pct': 0.0,
                              'shares_prev': acciones, 'change_pct': -100.0, 'activity': 'VENDE'})
    return filas


def actualizar_gestora(nombre: str, ciks: tuple[str, ...], guardado: "dict | None") -> "dict | None":
    """Las dos últimas carteras de la gestora: reutiliza lo guardado si la
    presentación es la misma y lo conserva entero si la SEC no contesta."""
    lista = presentaciones_13f(ciks)
    if lista is None:
        print(f'    ⚠ La SEC no contestó: se conserva lo guardado de {nombre}')
        return guardado
    if not lista:
        print(f'    ⚠ Sin 13F-HR para {nombre}')
        return guardado
    previos = {p['accession']: p for p in (guardado or {}).get('periodos', [])}
    periodos = []
    for p in lista[:2]:
        if p['accession'] in previos:
            periodos.append(previos[p['accession']])
            continue
        cartera = descargar_cartera(p['cik'], p['accession'])
        if cartera is None:
            print(f"    ⚠ No se pudo leer el 13F de {p['periodo']}: se conserva lo guardado")
            return guardado
        print(f"    13F {p['periodo']} (presentado {p['filing_date']}): {len(cartera)} posiciones")
        periodos.append({**p, 'posiciones': cartera})
    return {'periodos': periodos}


_MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
          'septiembre', 'octubre', 'noviembre', 'diciembre')


def frase_inversores(movs: list[dict], maximo: int = 6) -> str:
    """«Dodge & Cox +25 %, Tweedy Browne entra (a 30 de junio)», agrupando por
    trimestre: en plena temporada de 13F unos ya han presentado el nuevo y
    otros no, y mezclar los dos sin decirlo engaña."""
    if not movs:
        return ''
    grupos: dict[str, list[str]] = {}
    for m in movs:
        if m['accion'] == 'NUEVA':
            que = 'entra'
        elif m['accion'] == 'VENDE':
            que = 'sale'
        elif m.get('cambio_pct') is None:
            continue
        else:
            que = f"{m['cambio_pct']:+.0f} %".replace('-', '−')
        grupos.setdefault(m['periodo'], []).append(f"{m['fondo']} {que}")
    partes = []
    for periodo in sorted(grupos, reverse=True):
        nombres = grupos[periodo]
        texto = ', '.join(nombres[:maximo])
        if len(nombres) > maximo:
            texto += f' y {len(nombres) - maximo} más'
        _, mes, dia = (int(x) for x in periodo.split('-'))
        partes.append(f'{texto} (a {dia} de {_MESES[mes - 1]})')
    return ' · '.join(partes)


def _resumen(df: pd.DataFrame) -> list[dict]:
    """Por ticker: quién la tiene y qué han hecho con ella en su último 13F."""
    con_ticker = df[df['ticker'] != '']
    salida = []
    for ticker, g in con_ticker.groupby('ticker'):
        tienen = g[g['activity'] != 'VENDE']
        movs = []
        for _, r in g[g['activity'].isin(COMPRAS + VENTAS)].iterrows():
            movs.append({'fondo': r['fund'], 'accion': r['activity'], 'periodo': r['period'],
                         'cambio_pct': None if pd.isna(r['change_pct']) else float(r['change_pct']),
                         'pct_cartera': float(r['portfolio_pct'])})
        movs.sort(key=lambda m: -m['pct_cartera'])
        salida.append({
            'ticker':            ticker,
            'funds_count':       int(tienen['fund'].nunique()),
            'funds_list':        ' | '.join(sorted(set(tienen['fund']))),
            'total_value_m':     round(float(tienen['value_usd'].sum()) / 1e6, 1),
            'avg_portfolio_pct': float(tienen['portfolio_pct'].mean()) if len(tienen) else 0.0,
            'company_name':      str(g['name'].iloc[0]),
            'latest_date':       str(g['filing_date'].max()),
            'compran':           [m for m in movs if m['accion'] in COMPRAS],
            'venden':            [m for m in movs if m['accion'] in VENTAS],
        })
    salida.sort(key=lambda r: (-r['funds_count'], -r['total_value_m']))
    return salida


def main():
    print('═' * 70)
    print('  INVERSORES 13F (los de Dataroma) — SEC EDGAR')
    print(f'  {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')
    print('═' * 70)

    OUTPUT_DIR.mkdir(exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _load_cusip_cache()

    estado = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    gestoras = estado.get('gestoras', {})
    splits: dict = estado.get('splits', {})

    for nombre, ciks in GESTORES.items():
        print(f'\n🐋  {nombre}')
        nuevo = actualizar_gestora(nombre, ciks, gestoras.get(nombre))
        if nuevo is not None:
            gestoras[nombre] = nuevo

    cusips = {c for g in gestoras.values() for p in g['periodos'] for c in p['posiciones']}
    tickers = batch_cusip_to_ticker(sorted(cusips))
    print(f'\n  Tickers resueltos: {sum(1 for t in tickers.values() if t)}/{len(cusips)}')

    filas = []
    for nombre, g in gestoras.items():
        if nombre not in GESTORES:
            continue
        ahora = g['periodos'][0]
        antes = g['periodos'][1] if len(g['periodos']) > 1 else None
        for f in comparar(ahora['posiciones'], antes and antes['posiciones'], ahora['periodo'],
                          antes and antes['periodo'], tickers, splits):
            filas.append({'fund': nombre, 'cik': ahora['cik'], 'filing_date': ahora['filing_date'],
                          'period': ahora['periodo'], **f})

    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps({'gestoras': gestoras, 'splits': splits}, separators=(',', ':')))

    if not filas:
        print('\n⚠ No se obtuvo ningún dato')
        return

    df = pd.DataFrame(filas)
    tiene = df[df['activity'] != 'VENDE'].sort_values(['fund', 'value_usd'], ascending=[True, False])
    tiene.to_csv(OUTPUT_DIR / 'hedge_fund_holdings.csv', index=False)
    print(f'\n✅ {len(tiene)} posiciones de {tiene["fund"].nunique()} gestoras → docs/hedge_fund_holdings.csv')
    sin_saber = (tiene['activity'] == '').sum()
    if sin_saber:
        print(f'   {sin_saber} sin cambio conocido (sin trimestre anterior o split sin confirmar)')

    resumen = _resumen(df)
    with open(OUTPUT_DIR / 'hedge_fund_summary.json', 'w') as f:
        json.dump({
            'generated_at':   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'funds_scraped':  sorted(n for n in gestoras if n in GESTORES),
            'holdings_count': len(tiene),
            'top_consensus':  resumen,
        }, f, indent=1, ensure_ascii=False)

    print('\n🏆 Más compradas en el último trimestre:')
    for r in sorted(resumen, key=lambda r: -len(r['compran']))[:10]:
        print(f"  {r['ticker']:6}  {r['company_name'][:32]:32}  compran {len(r['compran'])}"
              f"  venden {len(r['venden'])}  la tienen {r['funds_count']}")


if __name__ == '__main__':
    main()

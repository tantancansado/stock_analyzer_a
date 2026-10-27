#!/usr/bin/env python3
"""Sincroniza la cartera de la app con las posiciones abiertas de Interactive Brokers.

Vía Flex Web Service: un informe de SOLO LECTURA que IBKR genera con un token.
Sin sesión, sin doble factor y sin poder tocar la cuenta — un fallo aquí no
puede comprar ni vender nada. El informe es del cierre del día anterior.

PRIVACIDAD: el repositorio es público y los logs de GitHub Actions también.
Este script nunca imprime tickers, cantidades ni el número de cuenta, solo
recuentos, y no escribe nada en `docs/`. Las posiciones solo van a Supabase.

Modos (`IBKR_SYNC_MODE`):
  solo_añadir  (por defecto) añade y actualiza; nunca borra nada.
  espejo       además borra de la app lo que ya no está en IBKR. Solo si no
               hay posiciones de otros brókers que conservar.

Entorno: IBKR_FLEX_TOKEN, IBKR_FLEX_QUERY_ID, SUPABASE_URL,
SUPABASE_SERVICE_ROLE_KEY, SUPABASE_MONITOR_USER_ID.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from supabase_auth import bearer

FLEX_URL = 'https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest'
UA = {'User-Agent': 'stock-analyzer-ibkr-sync/1.0'}
TABLA = 'personal_portfolio_positions'

# Bolsa de IBKR → sufijo de Yahoo, que es como la app nombra los tickers.
SUFIJO_BOLSA = {
    'IBIS': '.DE', 'IBIS2': '.DE', 'XETRA': '.DE', 'FWB': '.F', 'FWB2': '.F',
    'LSE': '.L', 'LSEETF': '.L', 'SBF': '.PA', 'AEB': '.AS', 'ENEXT.BE': '.BR',
    'BM': '.MC', 'BVME': '.MI', 'BVME.ETF': '.MI', 'EBS': '.SW', 'SWX': '.SW',
    'SFB': '.ST', 'KFX': '.CO', 'OSE': '.OL', 'HEX': '.HE', 'TSE': '.TO',
    'VENTURE': '.V', 'ASX': '.AX', 'SEHK': '.HK', 'TSEJ': '.T',
}
BOLSAS_US = {'NYSE', 'NASDAQ', 'ARCA', 'AMEX', 'BATS', 'IEX', 'PINK', 'NYSENAT', 'ISLAND', ''}

# Errores de Flex que significan «aún no está listo, vuelve a pedirlo».
REINTENTABLES = {'1019', '1018'}


class FlexError(RuntimeError):
    pass


# ── IBKR ─────────────────────────────────────────────────────────────────────

def _get(url: str, params: dict) -> str:
    req = urllib.request.Request(f'{url}?{urllib.parse.urlencode(params)}', headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', errors='replace')


def descargar_informe(token: str, query_id: str, intentos: int = 10, espera: float = 6.0) -> str:
    """XML del informe Flex. Lanza FlexError con el código de IBKR si falla."""
    raiz = ET.fromstring(_get(FLEX_URL, {'t': token, 'q': query_id, 'v': 3}))
    if (raiz.findtext('Status') or '') != 'Success':
        raise FlexError(f"IBKR rechazó la petición: {raiz.findtext('ErrorCode')} "
                        f"{raiz.findtext('ErrorMessage')}")
    ref, url = raiz.findtext('ReferenceCode'), raiz.findtext('Url')
    for _ in range(intentos):
        time.sleep(espera)
        xml = _get(url, {'t': token, 'q': ref, 'v': 3})
        if '<FlexQueryResponse' in xml:
            return xml
        r = ET.fromstring(xml)
        codigo = r.findtext('ErrorCode') or ''
        if codigo not in REINTENTABLES:
            raise FlexError(f"IBKR no entregó el informe: {codigo} {r.findtext('ErrorMessage')}")
    raise FlexError('IBKR no terminó de generar el informe a tiempo')


def _ticker_yahoo(simbolo: str, bolsa: str) -> str:
    s = simbolo.strip().replace(' ', '-')
    b = (bolsa or '').strip().upper()
    if b in BOLSAS_US:
        return s
    return s + SUFIJO_BOLSA.get(b, '')


def _fecha(v: str) -> str | None:
    v = (v or '').strip().replace('-', '')
    return f'{v[:4]}-{v[4:6]}-{v[6:8]}' if len(v) == 8 and v.isdigit() else None


def _f(v) -> float | None:
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def posiciones_de_ibkr(xml: str) -> tuple[list[dict], dict]:
    """Posiciones largas de acciones/ETF y opciones, en el formato de la app.

    Devuelve (posiciones, omitidas) — omitidas es un recuento por motivo. Las
    cortas y los bonos no se traen: la app no los modela igual y un dato mal
    traducido es peor que uno ausente.
    """
    raiz = ET.fromstring(xml)
    out, omitidas = [], {}

    def _omitir(motivo):
        omitidas[motivo] = omitidas.get(motivo, 0) + 1

    for p in raiz.iter('OpenPosition'):
        a = p.attrib
        if a.get('levelOfDetail') and a['levelOfDetail'].upper() != 'SUMMARY':
            continue                     # los lotes repiten la posición agregada
        cat = (a.get('assetCategory') or '').upper()
        pos = _f(a.get('position'))
        if not pos:
            continue
        if pos < 0:
            _omitir('cortas'); continue
        mult = _f(a.get('multiplier')) or 1.0
        coste = _f(a.get('costBasisMoney'))
        precio_medio = (coste / (pos * mult)) if coste else _f(a.get('costBasisPrice'))
        if precio_medio is None or precio_medio <= 0:
            _omitir('sin precio medio'); continue
        base = {'shares': pos, 'avg_price': round(precio_medio, 4),
                'currency': (a.get('currency') or 'USD').upper()}
        if cat == 'STK':
            out.append({**base, 'ticker': _ticker_yahoo(a.get('symbol', ''), a.get('listingExchange', '')),
                        'asset_type': 'stock', 'option_type': None,
                        'option_strike': None, 'option_expiry': None})
        elif cat == 'OPT':
            tipo = {'C': 'call', 'P': 'put'}.get((a.get('putCall') or '').upper())
            exp, strike = _fecha(a.get('expiry', '')), _f(a.get('strike'))
            subyacente = a.get('underlyingSymbol') or (a.get('symbol') or '').split()[0]
            if not (tipo and exp and strike):
                _omitir('opción incompleta'); continue
            out.append({**base, 'ticker': subyacente.strip().replace(' ', '-'),
                        'asset_type': 'option', 'option_type': tipo,
                        'option_strike': strike, 'option_expiry': exp})
        else:
            _omitir(f'tipo {cat or "?"}')
    return out, omitidas


# ── Supabase ─────────────────────────────────────────────────────────────────

def _clave(r: dict) -> tuple:
    strike = r.get('option_strike')
    return (str(r.get('ticker', '')).upper(), (r.get('asset_type') or 'stock').lower(),
            (r.get('option_type') or '') or None,
            round(float(strike), 2) if strike not in (None, '') else None,
            (str(r.get('option_expiry'))[:10] if r.get('option_expiry') else None))


def plan_de_cambios(app: list[dict], ibkr: list[dict], espejo: bool) -> dict:
    """Qué añadir, actualizar y (en espejo) borrar. Puro, sin red."""
    en_app = {_clave(r): r for r in app}
    en_ibkr = {_clave(r): r for r in ibkr}
    añadir = [r for k, r in en_ibkr.items() if k not in en_app]
    actualizar = []
    for k, r in en_ibkr.items():
        viejo = en_app.get(k)
        if viejo is None:
            continue
        if (abs(float(viejo.get('shares') or 0) - r['shares']) > 1e-6
                or abs(float(viejo.get('avg_price') or 0) - r['avg_price']) > r['avg_price'] * 1e-4):
            actualizar.append((viejo['id'], {'shares': r['shares'], 'avg_price': r['avg_price']}))
    borrar = []
    # Un informe vacío no es «lo has vendido todo»: es un informe roto. Nunca
    # se vacía la cartera por eso.
    if espejo and ibkr:
        borrar = [r['id'] for k, r in en_app.items()
                  if k not in en_ibkr and k[1] in ('stock', 'option')]
    return {'añadir': añadir, 'actualizar': actualizar, 'borrar': borrar}


class Supabase:
    def __init__(self, url: str, clave: str, usuario: str):
        self.base, self.clave, self.usuario = url.rstrip('/'), clave, usuario

    def _req(self, metodo: str, ruta: str, cuerpo=None):
        h = {'apikey': self.clave, **bearer(self.clave), 'Content-Type': 'application/json',
             'Prefer': 'return=minimal', **UA}
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(f'{self.base}/rest/v1/{ruta}', data=datos, headers=h, method=metodo)
        with urllib.request.urlopen(req, timeout=20) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else None

    def leer(self) -> list[dict]:
        cols = 'id,ticker,shares,avg_price,currency,asset_type,option_type,option_strike,option_expiry'
        return self._req('GET', f'{TABLA}?select={cols}&user_id=eq.{self.usuario}') or []

    def aplicar(self, plan: dict) -> None:
        for r in plan['añadir']:
            self._req('POST', TABLA, {**r, 'user_id': self.usuario})
        for id_, cambios in plan['actualizar']:
            self._req('PATCH', f'{TABLA}?id=eq.{id_}', cambios)
        for id_ in plan['borrar']:
            self._req('DELETE', f'{TABLA}?id=eq.{id_}')


def main() -> int:
    token = os.environ.get('IBKR_FLEX_TOKEN', '').strip()
    query = os.environ.get('IBKR_FLEX_QUERY_ID', '').strip()
    if not token or not query:
        print('IBKR: sin IBKR_FLEX_TOKEN / IBKR_FLEX_QUERY_ID — nada que sincronizar')
        return 0
    sb_url, sb_key = os.environ.get('SUPABASE_URL', ''), os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    usuario = os.environ.get('SUPABASE_MONITOR_USER_ID', '').strip()
    if not (sb_url and sb_key and usuario):
        print('IBKR: faltan credenciales de Supabase — no se toca la cartera')
        return 1
    espejo = os.environ.get('IBKR_SYNC_MODE', 'solo_añadir').strip().lower() == 'espejo'
    seco = '--dry-run' in sys.argv

    try:
        ibkr, omitidas = posiciones_de_ibkr(descargar_informe(token, query))
    except FlexError as e:
        print(f'IBKR: {e}')
        return 1
    except Exception as e:
        print(f'IBKR: no se pudo leer el informe ({type(e).__name__})')
        return 1

    sb = Supabase(sb_url, sb_key, usuario)
    try:
        app = sb.leer()
    except Exception as e:
        print(f'IBKR: no se pudo leer la cartera de la app ({type(e).__name__}) — no se toca nada')
        return 1

    plan = plan_de_cambios(app, ibkr, espejo)
    n_acc = sum(1 for r in ibkr if r['asset_type'] == 'stock')
    resumen = (f"IBKR: {len(ibkr)} posiciones ({n_acc} acciones/ETF, {len(ibkr) - n_acc} opciones)"
               f" · app: {len(app)} · añadir {len(plan['añadir'])}, actualizar "
               f"{len(plan['actualizar'])}, borrar {len(plan['borrar'])}"
               f" · modo {'espejo' if espejo else 'solo añadir'}")
    if omitidas:
        resumen += ' · omitidas: ' + ', '.join(f'{n} {m}' for m, n in omitidas.items())
    print(resumen)
    if seco:
        print('IBKR: dry-run, no se escribe nada')
        return 0
    try:
        sb.aplicar(plan)
    except Exception as e:
        print(f'IBKR: la escritura en Supabase falló a medias ({type(e).__name__}); '
              'la próxima pasada lo completa')
        return 1
    print('IBKR: cartera sincronizada')
    return 0


if __name__ == '__main__':
    sys.exit(main())

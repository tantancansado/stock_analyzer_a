#!/usr/bin/env python3
"""
Currency Normalizer — los estados financieros y la cotización no siempre vienen
en la misma divisa, y nadie lo estaba cruzando.

yfinance expone dos campos que hay que mirar juntos:
  currency          divisa a la que cotiza la acción
  financialCurrency divisa de los estados financieros

Medido el 3-ago-2026 sobre la propia lista VALUE:

  ATLKY    USD / SEK    FCF 25.972M SEK contra market cap 103.670M USD
                        → 25.05% de FCF yield (real: 2.38%). Ese 25% le daba el
                        bonus máximo (+8 pts) y lo ponía 3º en la lista.
  ASAZY    USD / SEK    44.76% de FCF yield
  CLPBY    USD / DKK    27.84%
  DBOEY    USD / EUR    error del 8% — parecía sano y no lo estaba
  EXPN.L   GBp / USD    dos desajustes a la vez
  AUTO.L   GBp / GBP    PER 100x por los peniques

Hay DOS conversiones distintas y confundirlas rompe la mitad de los ratios:

  1. Agregados (FCF, ingresos, deuda) se comparan con marketCap, que yfinance
     da en la divisa MAYOR (libras, no peniques) → factor `fx_to_major`.
  2. Por acción (EPS, book value) se comparan con el precio, que puede venir en
     peniques → factor `fx_to_price`, que incluye el ×100 de GBp.

Regla de la casa: sin tipo de cambio no se convierte a ojo ni se deja pasar el
dato crudo — se marca `fx_reliable=False` y quien lo consuma lo descarta. Nunca
se inventa un número.
"""
from __future__ import annotations

import yfinance as yf

# Vienen en financialCurrency y se comparan contra marketCap
AGGREGATE_FIELDS = (
    'freeCashflow',
    'operatingCashflow',
    'totalRevenue',
    'grossProfits',
    'ebitda',
    'netIncomeToCommon',
    'totalCash',
    'totalDebt',
)

# Vienen en financialCurrency y se comparan contra el precio por acción
PER_SHARE_FIELDS = (
    'trailingEps',
    'forwardEps',
    'bookValue',
    'revenuePerShare',
    'totalCashPerShare',
)

# Divisas que se cotizan en subunidad: 1 unidad mayor = 100 subunidades
SUBUNIT_CURRENCIES = {'GBP': 'GBp', 'ZAR': 'ZAc', 'ILS': 'ILA'}

_fx_cache: dict[str, float | None] = {}


def _major(ccy: str) -> str:
    """GBp → GBP. Devuelve la divisa mayor, preservando el resto igual."""
    if not ccy:
        return ''
    for major, sub in SUBUNIT_CURRENCIES.items():
        if ccy == sub:
            return major
    return ccy.upper()


def _is_subunit(ccy: str) -> bool:
    return ccy in SUBUNIT_CURRENCIES.values()


def get_fx_rate(from_ccy: str, to_ccy: str) -> float | None:
    """Tipo de cambio entre divisas MAYORES. None si no se puede obtener."""
    if not from_ccy or not to_ccy:
        return None
    from_ccy, to_ccy = from_ccy.upper(), to_ccy.upper()
    if from_ccy == to_ccy:
        return 1.0

    key = f'{from_ccy}{to_ccy}'
    if key in _fx_cache:
        return _fx_cache[key]

    rate = None
    try:
        hist = yf.Ticker(f'{key}=X').history(period='5d')
        if not hist.empty:
            r = float(hist['Close'].iloc[-1])
            rate = r if r > 0 else None
    except Exception as e:
        print(f'   ⚠️  FX {key} no disponible: {e}')

    _fx_cache[key] = rate
    return rate


def normalize_info(info: dict, ticker: str = '') -> tuple[dict, dict]:
    """Devuelve (info normalizada, metadatos).

    Deja `info` intacto y marca fx_reliable=False si hace falta convertir y no
    hay tipo de cambio: es preferible que el consumidor descarte el ticker a
    publicar un ratio que mezcla divisas.
    """
    price_ccy_raw = (info.get('currency') or '').strip()
    fin_ccy_raw   = (info.get('financialCurrency') or '').strip()

    meta = {
        'ticker': ticker,
        'price_currency': price_ccy_raw,
        'financial_currency': fin_ccy_raw,
        'fx_to_major': 1.0,
        'fx_to_price': 1.0,
        'fx_applied': False,
        'fx_reliable': True,
        'fx_fields_converted': [],
    }

    if not price_ccy_raw or not fin_ccy_raw:
        return info, meta

    price_major = _major(price_ccy_raw)
    fin_major   = _major(fin_ccy_raw)
    subunit     = _is_subunit(price_ccy_raw)

    # Mismo caso trivial: misma divisa mayor y el precio no está en subunidad
    if price_major == fin_major and not subunit:
        return info, meta

    fx_to_major = get_fx_rate(fin_major, price_major)
    if fx_to_major is None:
        meta['fx_reliable'] = False
        print(f'   ⚠️  {ticker}: {fin_major}→{price_major} sin tipo de cambio — ratios no fiables')
        return info, meta

    # El precio en peniques necesita los importes por acción también en peniques
    fx_to_price = fx_to_major * (100.0 if subunit else 1.0)

    out = dict(info)
    converted = []
    for field in AGGREGATE_FIELDS:
        if out.get(field) is None:
            continue
        try:
            out[field] = float(out[field]) * fx_to_major
            converted.append(field)
        except (TypeError, ValueError):
            continue
    for field in PER_SHARE_FIELDS:
        if out.get(field) is None:
            continue
        try:
            out[field] = float(out[field]) * fx_to_price
            converted.append(field)
        except (TypeError, ValueError):
            continue

    meta.update({
        'fx_to_major': fx_to_major,
        'fx_to_price': fx_to_price,
        'fx_applied': bool(converted),
        'fx_fields_converted': converted,
    })
    if converted:
        print(f'   💱 {ticker}: {fin_ccy_raw}→{price_ccy_raw} '
              f'(agregados ×{fx_to_major:.4f}, por acción ×{fx_to_price:.4f}) — {len(converted)} campos')
    return out, meta

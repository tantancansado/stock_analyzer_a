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

Hay DOS conversiones distintas y confundirlas rompe la mitad de los ratios:

  1. Agregados (FCF, ingresos, deuda) se comparan con marketCap, que yfinance
     da en la divisa de cotización → SÍ vienen en `financialCurrency` y SÍ
     necesitan `fx_to_major` (financialCurrency → currency).
  2. Por acción (EPS, book value): re-verificado el 5-ago-2026 cruzando
     price/trailingEps contra trailingPE en 9 tickers reales con
     financialCurrency≠currency (DBOEY, ATLKY, ASAZY, JD, PDD, STLA, NIO,
     EXPN.L, AUTO.L) — SIEMPRE cuadran ya en la divisa de cotización, pese a
     traer financialCurrency distinto. yfinance ya los da convertidos. La
     primera versión de este módulo aplicaba `fx_to_major` también aquí (p.ej.
     EXPN.L financialCurrency=USD recibía ×0.79 en vez de dejar los EPS tal
     cual) — corrompía justo lo que debía arreglar. Lo único real que hace
     falta es el ×100 cuando el precio cotiza en subunidad (GBp/ZAc/ILA,
     AUTO.L: PER 100x por los peniques), y ESO no depende de ningún tipo de
     cambio — es aritmética fija, nunca falla.

Regla de la casa: sin tipo de cambio no se convierte a ojo ni se deja pasar el
dato crudo — se marca `fx_reliable=False` y quien lo consuma descarta los
AGREGADOS (los por-acción no dependen de FX, así que no se ven afectados).
Nunca se inventa un número.
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

# yfinance ya las da en la divisa MAYOR de cotización (nunca en
# financialCurrency, verificado) — solo necesitan el ×100 si el precio
# cotiza en subunidad (GBp/ZAc/ILA)
PER_SHARE_FIELDS = (
    'trailingEps',
    'forwardEps',
    'epsForward',        # alias exacto de forwardEps — mismo valor siempre,
                          # pero algunos consumidores lo leen primero
    'epsTrailingTwelveMonths',  # alias exacto de trailingEps
    'epsCurrentYear',
    'bookValue',
    'revenuePerShare',
    'totalCashPerShare',
    'dividendRate',
    'lastDividendValue',
    'trailingAnnualDividendRate',
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

    Dos correcciones independientes:
      - Por acción (EPS, book value...): solo el ×100 de subunidad (GBp).
        No usa tipo de cambio, no puede fallar.
      - Agregados (FCF, ingresos, deuda...): sí necesitan `financialCurrency
        → currency` real. Si no hay tipo de cambio, se marca
        `fx_reliable=False` y el consumidor descarta esos campos — nunca se
        inventa un número.
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

    if not price_ccy_raw:
        return info, meta

    subunit     = _is_subunit(price_ccy_raw)
    price_major = _major(price_ccy_raw)
    fin_major   = _major(fin_ccy_raw) if fin_ccy_raw else price_major

    out = dict(info)
    converted = []

    # Por acción: yfinance ya las da en la divisa MAYOR de cotización sea cual
    # sea financialCurrency (verificado en 9 tickers reales) — solo falta el
    # ×100 si el precio cotiza en subunidad.
    fx_to_price = 100.0 if subunit else 1.0
    if subunit:
        for field in PER_SHARE_FIELDS:
            if out.get(field) is None:
                continue
            try:
                out[field] = float(out[field]) * fx_to_price
                converted.append(field)
            except (TypeError, ValueError):
                continue

    # Agregados: sí vienen en financialCurrency, sí necesitan tipo de cambio.
    fx_to_major = 1.0
    if fin_ccy_raw and fin_major != price_major:
        rate = get_fx_rate(fin_major, price_major)
        if rate is None:
            meta['fx_reliable'] = False
            print(f'   ⚠️  {ticker}: {fin_major}→{price_major} sin tipo de cambio — agregados no fiables')
        else:
            fx_to_major = rate
            for field in AGGREGATE_FIELDS:
                if out.get(field) is None:
                    continue
                try:
                    out[field] = float(out[field]) * fx_to_major
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
        print(f'   💱 {ticker}: agregados ×{fx_to_major:.4f}, por acción ×{fx_to_price:.4f} '
              f'— {len(converted)} campos')
    return out, meta

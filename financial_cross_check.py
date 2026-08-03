#!/usr/bin/env python3
"""
Financial Cross-Check — rellena huecos desde la fuente primaria y comprueba que
los datos cuadran entre sí antes de usarlos.

Dos funciones, en este orden:

1. derive_from_statements()
   `info` es un resumen y a veces le faltan campos que SÍ están en los estados
   financieros (`stock.cashflow`, `.financials`, `.balance_sheet`). ATLKY el
   3-ago-2026: `operatingCashflow` = None en info, y el estado de flujos tenía
   'Free Cash Flow' y 'Capital Expenditure' de 2023, 2024 y 2025. Antes de
   preguntarle a nadie, se mira donde el dato ya está.

2. check_coherence()
   Cuadres contables que deben cumplirse siempre. El más útil es también el más
   simple:

       sharesOutstanding × precio ≈ marketCap

   MCO da 1.0000 y ATLKY 0.6801. Ese 0.68 NO es el tipo de cambio (0.105): es el
   ratio del ADR — `sharesOutstanding` son las acciones ordinarias suecas y el
   precio es el del ADS, que representa otra fracción. Por eso convertir la
   divisa no bastaba: todo ratio POR ACCIÓN (EPS, FCF/acción y el DCF que sale
   de ahí) sigue mal. De ahí el DCF de +568.9% de ATLKY.

   Cuando el cuadre falla, los agregados (FCF yield, EBIT/EV, que usan marketCap)
   siguen siendo válidos; los por acción no. Se marcan y no se usan, en vez de
   publicar un DCF inventado por una discrepancia de unidades.
"""
from __future__ import annotations

from typing import Any

# Cuánto puede desviarse shares×price de marketCap y seguir siendo cuadre.
# Holgura para recompras y acciones emitidas entre el cierre y el dato.
SHARES_PRICE_TOLERANCE = 0.05

# Filas de los estados financieros por campo de `info`
STATEMENT_ROWS = {
    'freeCashflow':      ('cashflow', 'Free Cash Flow'),
    'operatingCashflow': ('cashflow', 'Operating Cash Flow'),
    'capitalExpenditure': ('cashflow', 'Capital Expenditure'),
    'totalRevenue':      ('financials', 'Total Revenue'),
    'netIncomeToCommon': ('financials', 'Net Income'),
    'ebitda':            ('financials', 'EBITDA'),
    'totalDebt':         ('balance_sheet', 'Total Debt'),
    'totalCash':         ('balance_sheet', 'Cash And Cash Equivalents'),
}


def _latest(df, row_name: str):
    """Valor más reciente de una fila del estado financiero, o None."""
    if df is None or getattr(df, 'empty', True):
        return None
    try:
        if row_name not in df.index:
            return None
        series = df.loc[row_name].dropna()
        if series.empty:
            return None
        return float(series.iloc[0])
    except Exception:
        return None


def derive_from_statements(stock, info: dict, fields: list[str] | None = None) -> tuple[dict, list[str]]:
    """Rellena campos ausentes en `info` desde los estados financieros.

    Devuelve (info, campos rellenados). Fuente primaria y misma divisa que el
    resto de estados — sin IA y sin estimaciones.
    """
    wanted = fields or list(STATEMENT_ROWS)
    missing = [f for f in wanted if info.get(f) is None and f in STATEMENT_ROWS]
    if not missing:
        return info, []

    cache: dict[str, Any] = {}
    out, filled = dict(info), []
    for field in missing:
        stmt_name, row = STATEMENT_ROWS[field]
        if stmt_name not in cache:
            try:
                cache[stmt_name] = getattr(stock, stmt_name)
            except Exception:
                cache[stmt_name] = None
        val = _latest(cache[stmt_name], row)
        if val is not None:
            out[field] = val
            filled.append(field)

    # FCF derivado: flujo operativo menos capex (capex viene en negativo)
    if out.get('freeCashflow') is None:
        ocf, capex = out.get('operatingCashflow'), out.get('capitalExpenditure')
        if ocf is not None and capex is not None:
            out['freeCashflow'] = float(ocf) - abs(float(capex))
            filled.append('freeCashflow(derivado OCF-capex)')

    if filled:
        print(f"   📄 Estados financieros aportan: {', '.join(filled)}")
    return out, filled


def check_coherence(info: dict, ticker: str = '') -> dict:
    """Cuadres contables. Devuelve qué se puede usar y qué no.

    {'per_share_reliable': bool, 'aggregate_reliable': bool, 'issues': [...],
     'shares_price_ratio': float|None}
    """
    issues: list[str] = []
    per_share_ok = True
    aggregate_ok = True
    ratio = None

    shares = info.get('sharesOutstanding')
    price  = info.get('currentPrice') or info.get('regularMarketPrice')
    mcap   = info.get('marketCap')

    if shares and price and mcap:
        try:
            ratio = (float(shares) * float(price)) / float(mcap)
            if abs(ratio - 1.0) > SHARES_PRICE_TOLERANCE:
                per_share_ok = False
                issues.append(
                    f'acciones × precio no cuadra con la capitalización '
                    f'(ratio {ratio:.4f}): el dato por acción y el precio no '
                    f'están en la misma unidad — típico de ADR. Los ratios por '
                    f'acción (EPS, FCF/acción, DCF) no son utilizables'
                )
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    # FCF declarado contra el derivado del propio estado de flujos
    fcf, ocf, capex = info.get('freeCashflow'), info.get('operatingCashflow'), info.get('capitalExpenditure')
    if fcf and ocf and capex:
        try:
            derived = float(ocf) - abs(float(capex))
            if derived and abs(float(fcf) - derived) / abs(derived) > 0.25:
                issues.append(
                    f'FCF declarado ({float(fcf):,.0f}) se aparta del derivado '
                    f'de flujo operativo menos capex ({derived:,.0f})'
                )
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    if issues and ticker:
        for i in issues:
            print(f'   🔍 {ticker}: {i}')

    return {
        'per_share_reliable': per_share_ok,
        'aggregate_reliable': aggregate_ok,
        'shares_price_ratio': round(ratio, 4) if ratio is not None else None,
        'issues': issues,
    }

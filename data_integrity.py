#!/usr/bin/env python3
"""
Data Integrity — comprueba que los números de un pick son posibles antes de que
lleguen a la lista o a Telegram.

Nace de un caso real: el 3-ago-2026 ATLKY salía 3º en VALUE con un FCF yield del
25.05% (dato en coronas suecas contra capitalización en dólares) y cobraba por
ello el bonus máximo. Nadie comprobaba si el número era siquiera posible.

Dos capas, en este orden:

  1. Esta — determinista, gratis y sin red. Rangos que ninguna empresa cotizada
     grande cruza. Detecta el 90% de la basura y NO necesita IA.
  2. ai_pick_verifier — juicio sobre la coherencia del conjunto, para lo que
     ninguna regla fija anticipa.

Filosofía del repo: un dato imposible no se corrige a ojo ni se ignora. Se marca,
y quien publica decide — con `BLOCK` el ticker no sale.

Severidades:
  BLOCK  el dato es imposible → el ticker no se recomienda
  WARN   sospechoso pero puede ser legítimo → sale con aviso
"""
from __future__ import annotations

# (campo, mínimo, máximo, severidad, por qué)
# Los rangos son deliberadamente anchos: buscamos lo imposible, no lo raro.
RULES = (
    ('fcf_yield_pct',               -50.0,   20.0, 'BLOCK',
     'FCF yield fuera de rango: por encima del 20% suele ser divisa sin convertir'),
    ('dividend_yield_pct',            0.0,   25.0, 'BLOCK',
     'Dividend yield imposible (yfinance ya lo da en %, no en decimal)'),
    ('payout_ratio_pct',           -100.0,  500.0, 'WARN',
     'Payout ratio extremo'),
    ('target_price_dcf_upside_pct', -95.0,  200.0, 'BLOCK',
     'DCF fuera de rango: no es una valoración, es un dato roto'),
    ('target_price_pe_upside_pct',  -95.0,  300.0, 'BLOCK',
     'Target por P/E fuera de rango'),
    ('analyst_upside_pct',          -90.0,  300.0, 'BLOCK',
     'Upside de analistas imposible'),
    ('peg_ratio',                     0.1,   20.0, 'WARN',
     'PEG fuera de rango razonable'),
    ('ebit_ev_yield',               -50.0,   50.0, 'WARN',
     'EBIT/EV extremo'),
    ('piotroski_score',               0.0,    9.0, 'BLOCK',
     'Piotroski fuera de 0-9'),
    ('roe_pct',                    -200.0,  500.0, 'WARN',
     'ROE extremo'),
    ('current_price',                 0.01, 1_000_000.0, 'BLOCK',
     'Precio imposible'),
)

# Campos sin los cuales no se puede sostener una recomendación VALUE
REQUIRED_FOR_VALUE = ('current_price', 'value_score', 'analyst_upside_pct')


def _num(v):
    if v is None or v == '':
        return None
    try:
        f = float(v)
        return None if f != f else f   # NaN
    except (TypeError, ValueError):
        return None


def check_row(row: dict, require_value_fields: bool = True) -> dict:
    """Valida una fila. Devuelve {'ok', 'blocking', 'issues': [...]}.

    `ok` es False solo con problemas BLOCK: un WARN informa pero no veta.
    """
    issues = []

    for field, lo, hi, severity, why in RULES:
        val = _num(row.get(field))
        if val is None:
            continue
        if val < lo or val > hi:
            issues.append({
                'field': field, 'value': val, 'severity': severity,
                'reason': f'{why} (visto {val:g}, esperado entre {lo:g} y {hi:g})',
            })

    # La conversión de divisa falló → cualquier ratio mezcla monedas
    if row.get('fx_reliable') in (False, 'False', 'false'):
        issues.append({
            'field': 'fx_reliable', 'value': False, 'severity': 'BLOCK',
            'reason': 'Sin tipo de cambio: los ratios mezclan la divisa de los '
                      'estados financieros con la de la cotización',
        })

    if require_value_fields:
        for field in REQUIRED_FOR_VALUE:
            if _num(row.get(field)) is None:
                issues.append({
                    'field': field, 'value': None, 'severity': 'BLOCK',
                    'reason': f'Falta {field}: no se recomienda lo que no se puede evaluar',
                })

    blocking = [i for i in issues if i['severity'] == 'BLOCK']
    return {'ok': not blocking, 'blocking': blocking, 'issues': issues}


def filter_dataframe(df, require_value_fields: bool = True, label: str = ''):
    """Quita del DataFrame las filas con problemas BLOCK. Devuelve (df, informe)."""
    if df is None or df.empty:
        return df, {'checked': 0, 'blocked': 0, 'warned': 0, 'detail': []}

    keep, detail, warned = [], [], 0
    for _, row in df.iterrows():
        res = check_row(row.to_dict(), require_value_fields)
        ticker = str(row.get('ticker', '?'))
        if res['ok']:
            keep.append(True)
            if res['issues']:
                warned += 1
                for i in res['issues']:
                    print(f"   ⚠️  {ticker}: {i['reason']}")
        else:
            keep.append(False)
            for i in res['blocking']:
                detail.append({'ticker': ticker, **i})
                print(f"   🚫 {ticker} BLOQUEADO — {i['reason']}")

    out = df[keep].copy()
    report = {
        'checked': len(df),
        'blocked': int(len(df) - len(out)),
        'warned': warned,
        'detail': detail,
    }
    if report['blocked']:
        print(f"   🛡️  {label or 'integridad'}: {report['blocked']}/{report['checked']} "
              f"fuera por datos imposibles")
    return out, report

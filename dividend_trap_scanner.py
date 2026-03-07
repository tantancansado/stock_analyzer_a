#!/usr/bin/env python3
"""
DIVIDEND TRAP SCANNER
Detecta empresas con dividendo aparentemente atractivo pero en riesgo de recorte.

Trampas clásicas VALUE:
- Yield alto (>4%) + Payout ratio >80% = presión en el dividendo
- FCF yield < dividend yield = dividendo no cubierto por caja libre
- Debt/equity alto + earnings decelerating = recorte probable
- Negative ROE = empresa perdiendo dinero mientras paga dividendo

Output: docs/dividend_traps.json
"""
import json
import ast
from datetime import datetime
from pathlib import Path
import pandas as pd

DOCS = Path('docs')


def _sf(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return None if (f != f) else f
    except Exception:
        return default


def _parse_details(raw: str) -> dict:
    """Parse a Python dict string safely."""
    if not raw or pd.isna(raw):
        return {}
    try:
        return ast.literal_eval(str(raw))
    except Exception:
        return {}


def _trap_score(row) -> tuple:
    """
    Calculate dividend trap risk score (0-100, higher = more dangerous).
    Returns (trap_score, reasons: list[str])
    """
    score = 0
    reasons = []

    div_yield = _sf(row.get('dividend_yield_pct'), 0) or 0
    payout    = _sf(row.get('payout_ratio_pct'), 0) or 0
    fcf_yield = _sf(row.get('fcf_yield_pct'))
    de_ratio  = _sf(row.get('debt_to_equity'))
    interest  = _sf(row.get('interest_coverage'))

    # Parse health_details for additional data
    health  = _parse_details(row.get('health_details', ''))
    earn    = _parse_details(row.get('earnings_details', ''))

    roe       = _sf(health.get('roe_pct'))
    op_margin = _sf(health.get('operating_margin_pct'))
    de_fund   = _sf(health.get('debt_to_equity')) or de_ratio
    profit_m  = _sf(earn.get('profit_margin_pct'))
    accelerating = earn.get('earnings_accelerating', True)

    # ── Red flags ────────────────────────────────────────────────────────

    # 1. Yield muy alto = mercado ya descuenta riesgo
    if div_yield >= 8:
        score += 30
        reasons.append(f"Yield {div_yield:.1f}% — extremo, mercado descuenta recorte")
    elif div_yield >= 6:
        score += 15
        reasons.append(f"Yield {div_yield:.1f}% — elevado, vigilar sostenibilidad")

    # 2. Payout ratio alto
    if payout > 100:
        score += 35
        reasons.append(f"Payout {payout:.0f}% — dividendo > beneficios (insostenible)")
    elif payout > 80:
        score += 20
        reasons.append(f"Payout {payout:.0f}% — poco margen de seguridad")
    elif payout > 65:
        score += 8
        reasons.append(f"Payout {payout:.0f}% — moderadamente elevado")

    # 3. FCF no cubre el dividendo
    if fcf_yield is not None and div_yield > 0:
        if fcf_yield < 0:
            score += 30
            reasons.append(f"FCF yield negativo ({fcf_yield:.1f}%) — empresa consume caja")
        elif fcf_yield < div_yield:
            gap = div_yield - fcf_yield
            score += min(25, int(gap * 5))
            reasons.append(f"FCF yield ({fcf_yield:.1f}%) < dividend yield ({div_yield:.1f}%) — dividendo sin respaldo de caja")

    # 4. ROE negativo = empresa perdiendo dinero
    if roe is not None and roe < 0:
        score += 20
        reasons.append(f"ROE negativo ({roe:.1f}%) — empresa pierde dinero mientras paga dividendo")

    # 5. Deuda alta
    if de_fund is not None and de_fund > 2:
        score += 15
        reasons.append(f"Deuda/equity {de_fund:.1f}x — apalancamiento alto, presión en dividendo")
    elif de_fund is not None and de_fund > 1.5:
        score += 8
        reasons.append(f"Deuda/equity {de_fund:.1f}x — moderado")

    # 6. Cobertura de intereses baja
    if interest is not None and interest < 2:
        score += 20
        reasons.append(f"Interest coverage {interest:.1f}x — earnings apenas cubren deuda")
    elif interest is not None and interest < 3:
        score += 10
        reasons.append(f"Interest coverage {interest:.1f}x — ajustado")

    # 7. Márgenes en deterioro
    if op_margin is not None and op_margin < 5:
        score += 10
        reasons.append(f"Margen operativo {op_margin:.1f}% — muy comprimido")
    if profit_m is not None and profit_m < 0:
        score += 15
        reasons.append(f"Margen neto negativo ({profit_m:.1f}%)")

    # 8. Earnings decelerando
    if accelerating is False:
        score += 5
        reasons.append("Earnings decelerando — tendencia negativa")

    return min(100, score), reasons


def run_dividend_trap_scanner():
    print("=== DIVIDEND TRAP SCANNER ===")

    # Load fundamental scores
    fund_path = DOCS / 'fundamental_scores.csv'
    if not fund_path.exists():
        print("fundamental_scores.csv not found")
        return

    df = pd.read_csv(fund_path)

    # Only scan tickers that actually pay a dividend
    df_div = df[df['dividend_yield_pct'].notna() & (df['dividend_yield_pct'].astype(str) != 'nan')].copy()
    df_div['dividend_yield_pct'] = pd.to_numeric(df_div['dividend_yield_pct'], errors='coerce')
    df_div = df_div[df_div['dividend_yield_pct'] > 0.5].copy()  # >0.5% yield

    print(f"  Scanning {len(df_div)} dividend-paying stocks...")

    traps = []
    safe  = []

    for _, row in df_div.iterrows():
        trap_score, reasons = _trap_score(row)

        entry = {
            'ticker':           str(row.get('ticker', '')),
            'company':          str(row.get('company_name', '')),
            'sector':           str(row.get('sector', '')),
            'current_price':    _sf(row.get('current_price')),
            'dividend_yield':   _sf(row.get('dividend_yield_pct')),
            'payout_ratio':     _sf(row.get('payout_ratio_pct')),
            'fcf_yield':        _sf(row.get('fcf_yield_pct')),
            'fundamental_score':_sf(row.get('fundamental_score')),
            'trap_score':       trap_score,
            'reasons':          reasons,
            'risk_level':       'HIGH' if trap_score >= 50 else ('MEDIUM' if trap_score >= 25 else 'LOW'),
        }

        if trap_score >= 25:
            traps.append(entry)
        else:
            safe.append(entry)

    traps.sort(key=lambda x: -x['trap_score'])
    safe.sort(key=lambda x: -(x['dividend_yield'] or 0))

    output = {
        'timestamp': datetime.now().isoformat(),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'total_scanned': len(df_div),
        'traps_high': len([t for t in traps if t['risk_level'] == 'HIGH']),
        'traps_medium': len([t for t in traps if t['risk_level'] == 'MEDIUM']),
        'safe_count': len(safe),
        'traps': traps,
        'safe_dividends': safe[:20],  # top 20 safe dividend payers
    }

    out_path = DOCS / 'dividend_traps.json'
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"  HIGH risk: {output['traps_high']} | MEDIUM: {output['traps_medium']} | SAFE: {output['safe_count']}")
    print(f"  Saved to {out_path}")
    return output


if __name__ == '__main__':
    run_dividend_trap_scanner()

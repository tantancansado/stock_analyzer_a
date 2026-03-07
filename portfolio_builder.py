#!/usr/bin/env python3
"""
SMART PORTFOLIO BUILDER
Construye una cartera estructurada y equilibrada combinando:
  - Macro Radar (regime context)
  - VALUE opportunities (score + conviction grade)
  - Dividend Trap Radar (excluye trampas)
  - Earnings calendar (evita entradas pre-earnings)
  - Diversificación sectorial (max 2 por sector)
  - Groq AI para tesis narrativa del portfolio completo

Output: docs/smart_portfolio.json
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

DOCS = Path('docs')

# ── Parámetros por régimen ────────────────────────────────────────────────────
REGIME_PARAMS = {
    'CALM':   {'n_picks': 7, 'min_score': 55, 'cash_pct': 5,  'require_rr': 1.5},
    'WATCH':  {'n_picks': 6, 'min_score': 60, 'cash_pct': 10, 'require_rr': 1.5},
    'STRESS': {'n_picks': 5, 'min_score': 65, 'cash_pct': 20, 'require_rr': 2.0},
    'ALERT':  {'n_picks': 4, 'min_score': 70, 'cash_pct': 30, 'require_rr': 2.5},
    'CRISIS': {'n_picks': 3, 'min_score': 75, 'cash_pct': 50, 'require_rr': 3.0},
}

GRADE_WEIGHT = {'A': 1.0, 'B': 0.88, 'C': 0.75}


def _sf(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return None if f != f else f
    except Exception:
        return default


def _load_macro_regime() -> dict:
    path = DOCS / 'macro_radar.json'
    if path.exists():
        try:
            with open(path) as f:
                d = json.load(f)
            return d.get('regime', {})
        except Exception:
            pass
    return {'name': 'WATCH', 'color': '#84cc16', 'description': ''}


def _load_value_df() -> pd.DataFrame:
    for fname in ('value_conviction.csv', 'value_opportunities_filtered.csv', 'value_opportunities.csv'):
        p = DOCS / fname
        if p.exists():
            try:
                df = pd.read_csv(p)
                if 'value_score' in df.columns and 'ticker' in df.columns:
                    print(f"  Loaded {fname}: {len(df)} rows")
                    return df
            except Exception:
                pass
    return pd.DataFrame()


def _load_trap_tickers() -> set:
    """Return set of HIGH-risk dividend trap tickers to exclude."""
    path = DOCS / 'dividend_traps.json'
    if path.exists():
        try:
            with open(path) as f:
                d = json.load(f)
            return {t['ticker'] for t in d.get('traps', []) if t.get('risk_level') == 'HIGH'}
        except Exception:
            pass
    return set()


def _rank_score(row: pd.Series, regime_name: str) -> float:
    """Composite ranking score for pick selection."""
    val   = _sf(row.get('value_score'), 0) or 0
    grade = str(row.get('conviction_grade', 'C'))
    gw    = GRADE_WEIGHT.get(grade, 0.7)
    rr    = _sf(row.get('risk_reward_ratio'), 1) or 1
    fcf   = _sf(row.get('fcf_yield_pct'), 0) or 0
    up    = _sf(row.get('analyst_upside_pct'), 0) or 0

    rr_bonus = min(1.3, 1 + max(0, rr - 1) * 0.1)
    fcf_bonus = 1.05 if fcf >= 5 else 1.02 if fcf >= 3 else 1.0

    # In danger regimes, upside matters more
    upside_factor = 1 + max(0, up) * 0.002 if regime_name in ('ALERT', 'CRISIS') else 1.0

    return val * gw * rr_bonus * fcf_bonus * upside_factor


def _select_picks(df: pd.DataFrame, regime: str, params: dict, trap_tickers: set) -> list:
    """Filter, rank and select final picks respecting sector limits."""
    min_score = params['min_score']
    min_rr    = params['require_rr']
    n_picks   = params['n_picks']

    # ── Hard filters ─────────────────────────────────────────────────────
    mask = df['value_score'] >= min_score

    if 'earnings_warning' in df.columns:
        # Exclude earnings <7 days UNLESS it's a catalyst
        mask &= ~(
            (df['earnings_warning'].fillna(False).astype(bool)) &
            (~df.get('earnings_catalyst', pd.Series(False, index=df.index)).fillna(False).astype(bool))
        )

    if 'risk_reward_ratio' in df.columns:
        mask &= df['risk_reward_ratio'].fillna(0) >= min_rr

    # Exclude dividend traps
    mask &= ~df['ticker'].isin(trap_tickers)

    # Exclude negative ROE / overvalued (analyst_upside_pct < 0)
    if 'analyst_upside_pct' in df.columns:
        mask &= df['analyst_upside_pct'].fillna(0) >= 0

    filtered = df[mask].copy()
    if filtered.empty:
        # Relax earnings filter if too strict
        filtered = df[df['value_score'] >= min_score].copy()

    if filtered.empty:
        return []

    # ── Rank ─────────────────────────────────────────────────────────────
    filtered['_rank'] = filtered.apply(lambda r: _rank_score(r, regime), axis=1)
    filtered = filtered.sort_values('_rank', ascending=False)

    # ── Sector-balanced selection (max 2 per sector) ─────────────────────
    picks = []
    sector_count: dict = {}
    for _, row in filtered.iterrows():
        if len(picks) >= n_picks:
            break
        sector = str(row.get('sector', 'Unknown'))
        if sector_count.get(sector, 0) >= 2:
            continue
        picks.append(row)
        sector_count[sector] = sector_count.get(sector, 0) + 1

    return picks


def _calc_allocations(picks: list, cash_pct: float, regime: str) -> list:
    """Calculate position sizes with grade-based tilting."""
    if not picks:
        return []

    investable = 100 - cash_pct
    base = investable / len(picks)

    # Grade tilt: A gets +2pts, C gets -2pts, then renormalize
    raw = []
    for row in picks:
        grade = str(row.get('conviction_grade', 'B'))
        adj = base + (2 if grade == 'A' else -2 if grade == 'C' else 0)
        raw.append(max(2, adj))

    total = sum(raw)
    scale = investable / total

    result = []
    for i, row in enumerate(picks):
        alloc = round(raw[i] * scale, 1)
        result.append({
            'ticker':           str(row.get('ticker', '')),
            'company':          str(row.get('company_name', '')),
            'sector':           str(row.get('sector', '')),
            'current_price':    _sf(row.get('current_price')),
            'value_score':      round(_sf(row.get('value_score'), 0), 1),
            'conviction_grade': str(row.get('conviction_grade', '—')),
            'conviction_score': _sf(row.get('conviction_score')),
            'analyst_upside_pct': _sf(row.get('analyst_upside_pct')),
            'target_price_analyst': _sf(row.get('target_price_analyst')),
            'fcf_yield_pct':    _sf(row.get('fcf_yield_pct')),
            'risk_reward_ratio': _sf(row.get('risk_reward_ratio')),
            'dividend_yield_pct': _sf(row.get('dividend_yield_pct')),
            'buyback_active':   bool(row.get('buyback_active', False)),
            'days_to_earnings': _sf(row.get('days_to_earnings')),
            'earnings_date':    str(row.get('earnings_date', '')) or None,
            'earnings_catalyst': bool(row.get('earnings_catalyst', False)),
            'stop_loss':        _sf(row.get('stop_loss')),
            'entry_price':      _sf(row.get('entry_price')),
            'allocation_pct':   alloc,
            'rank_score':       round(_sf(row.get('_rank'), 0), 2),
        })
    return result


def _groq_portfolio_thesis(picks: list, regime: dict, params: dict) -> Optional[str]:
    """Ask Groq for a narrative of the assembled portfolio."""
    try:
        from groq import Groq
        key = os.environ.get('GROQ_API_KEY', '')
        if not key:
            return None
        client = Groq(api_key=key)
    except Exception:
        return None

    regime_name = regime.get('name', 'WATCH')
    lines = []
    for p in picks:
        extras = []
        if p['fcf_yield_pct'] and p['fcf_yield_pct'] >= 3:
            extras.append(f"FCF {p['fcf_yield_pct']:.1f}%")
        if p['analyst_upside_pct']:
            extras.append(f"upside {p['analyst_upside_pct']:.0f}%")
        if p['conviction_grade']:
            extras.append(f"grado {p['conviction_grade']}")
        extras_str = ', '.join(extras)
        lines.append(f"- {p['ticker']} ({p['company'][:20]}, {p['sector']}): score {p['value_score']}, alloc {p['allocation_pct']}%, {extras_str}")

    picks_str = '\n'.join(lines)
    cash = params['cash_pct']

    prompt = f"""Eres un gestor de fondos VALUE con 25 años de experiencia (estilo Lynch/Buffett).
Se ha construido la siguiente cartera algorítmica para el régimen actual de mercado {regime_name}.
Cash reservado: {cash}% del portfolio.

Picks seleccionados ({len(picks)} posiciones):
{picks_str}

Proporciona en español (máximo 150 palabras):
1. Lógica general de la cartera dado el régimen {regime_name}
2. Por qué estos picks tienen sentido juntos (diversificación, calidad)
3. Principal riesgo de la cartera y cómo el cash buffer lo mitiga
4. Una frase de posicionamiento concreto para el inversor

Tono profesional, directo, sin disclaimers genéricos."""

    try:
        resp = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=250,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Groq portfolio thesis failed: {e}")
        return None


def _build_risk_notes(picks: list, regime: dict, params: dict, trap_count: int) -> list:
    """Generate human-readable risk notes for the portfolio."""
    notes = []
    regime_name = regime.get('name', 'WATCH')

    if params['cash_pct'] >= 20:
        notes.append(f"Régimen {regime_name}: {params['cash_pct']}% en cash como colchón de seguridad")

    # Sector concentration
    sectors: dict = {}
    for p in picks:
        s = p['sector']
        sectors[s] = sectors.get(s, 0) + 1
    concentrated = [f"{s} ({n})" for s, n in sectors.items() if n >= 2]
    if concentrated:
        notes.append(f"Concentración sectorial: {', '.join(concentrated)} — vigilar correlación")

    # Earnings proximity
    near_earn = [p['ticker'] for p in picks if p['days_to_earnings'] is not None and p['days_to_earnings'] <= 21]
    if near_earn:
        notes.append(f"Earnings próximos en <21 días: {', '.join(near_earn)} — considerar entrada post-reporte")

    if trap_count > 0:
        notes.append(f"{trap_count} tickers excluidos por ser trampas de dividendo de alto riesgo")

    # Avg metrics
    avg_rr = sum(p['risk_reward_ratio'] or 0 for p in picks) / len(picks) if picks else 0
    avg_fcf = sum(p['fcf_yield_pct'] or 0 for p in picks) / len(picks) if picks else 0
    if avg_rr > 0:
        notes.append(f"R:R medio de la cartera: {avg_rr:.1f}x | FCF yield medio: {avg_fcf:.1f}%")

    return notes


def run_portfolio_builder() -> dict:
    print("=== SMART PORTFOLIO BUILDER ===")
    print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Load context ──────────────────────────────────────────────────────
    regime    = _load_macro_regime()
    regime_name = regime.get('name', 'WATCH')
    params    = REGIME_PARAMS.get(regime_name, REGIME_PARAMS['WATCH'])
    print(f"  Regime: {regime_name} | Min score: {params['min_score']} | Cash: {params['cash_pct']}% | Target picks: {params['n_picks']}")

    df = _load_value_df()
    if df.empty:
        print("  No value opportunities found")
        return {}

    trap_tickers = _load_trap_tickers()
    print(f"  Excluded dividend traps (HIGH): {len(trap_tickers)}")

    # ── Select picks ──────────────────────────────────────────────────────
    picks_rows = _select_picks(df, regime_name, params, trap_tickers)
    print(f"  Selected {len(picks_rows)} picks")

    if not picks_rows:
        output = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'regime': regime,
            'picks': [],
            'cash_pct': params['cash_pct'],
            'total_picks': 0,
            'portfolio_thesis': f"Régimen {regime_name}: no se encontraron picks que superen los criterios de calidad actuales. Mantener liquidez.",
            'risk_notes': [f"Régimen {regime_name}: máxima exigencia, 0 picks calificados"],
            'params': params,
        }
        out_path = DOCS / 'smart_portfolio.json'
        with open(out_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        return output

    # ── Allocations ───────────────────────────────────────────────────────
    portfolio_picks = _calc_allocations(picks_rows, params['cash_pct'], regime_name)

    # ── Risk notes ────────────────────────────────────────────────────────
    trap_excluded = len(df[df['ticker'].isin(trap_tickers)]) if trap_tickers else 0
    risk_notes = _build_risk_notes(portfolio_picks, regime, params, trap_excluded)

    # ── Groq thesis ───────────────────────────────────────────────────────
    print("  Requesting Groq portfolio thesis...")
    thesis = _groq_portfolio_thesis(portfolio_picks, regime, params)
    if thesis:
        print(f"  Thesis: {thesis[:80]}...")

    # ── Output ────────────────────────────────────────────────────────────
    total_alloc = sum(p['allocation_pct'] for p in portfolio_picks)
    output = {
        'date':             datetime.now().strftime('%Y-%m-%d'),
        'timestamp':        datetime.now().isoformat(),
        'regime':           regime,
        'regime_name':      regime_name,
        'picks':            portfolio_picks,
        'cash_pct':         params['cash_pct'],
        'total_picks':      len(portfolio_picks),
        'invested_pct':     round(total_alloc, 1),
        'portfolio_thesis': thesis,
        'risk_notes':       risk_notes,
        'params':           params,
        'trap_tickers_excluded': list(trap_tickers)[:10],
    }

    out_path = DOCS / 'smart_portfolio.json'
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nSaved to {out_path}")
    print(f"Portfolio: {len(portfolio_picks)} picks | Cash: {params['cash_pct']}% | Invested: {total_alloc:.1f}%")
    for p in portfolio_picks:
        print(f"  {p['ticker']:6} {p['conviction_grade']} score={p['value_score']} alloc={p['allocation_pct']}% [{p['sector']}]")

    return output


if __name__ == '__main__':
    run_portfolio_builder()
